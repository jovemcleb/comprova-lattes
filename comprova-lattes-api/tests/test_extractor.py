"""Testes offline: o cliente SDK é sempre substituído por mocks."""

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import httpx
import pytest
from google.genai import Client as SDKClient
from google.genai import errors, types

from comprova_lattes.config import Settings
from comprova_lattes.extractor import ExtractionPayload, GeminiExtractor
from comprova_lattes.extractor.gemini import PROMPT, PROMPT_VERSION
from comprova_lattes.matcher.models import ExtractedDocumentRecord, ExtractionStatus


@pytest.fixture(autouse=True)
def forbid_real_client():
    with patch("google.genai.Client", side_effect=AssertionError("Real SDK client forbidden")):
        yield


def response(text):
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(parts=[types.Part(text=text)]))],
        model_version="gemini-test-pinned-001",
        response_id="response-1",
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=20,
            candidates_token_count=10,
            total_token_count=30,
        ),
    )


def extractor(text):
    client = Mock()
    client.models.generate_content.return_value = response(text)
    ticks = iter([1.0, 1.125])
    return GeminiExtractor(client, model="gemini-test", clock=lambda: next(ticks), max_attempts=1), client


def payload(**fields):
    return json.dumps({"extraction_status": "OK", "activity_count": 1, **fields})


def test_sdk_sends_json_schema_without_legacy_schema_conversion():
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=response(payload()).model_dump(
            mode="json", by_alias=True, exclude_none=True,
        ))

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        SDKClient(api_key="synthetic-test-key", http_options=types.HttpOptions(
            httpx_client=http_client,
        )) as client,
    ):
        result = GeminiExtractor(client, model="gemini-test").extract(
            "doc", b"synthetic", "application/pdf",
        )
    assert result.extraction_status == ExtractionStatus.OK
    assert len(requests) == 1
    generation = requests[0]["generationConfig"]
    assert "responseSchema" not in generation
    assert generation["responseJsonSchema"] == ExtractionPayload.model_json_schema()
    assert generation["responseJsonSchema"]["additionalProperties"] is False


def test_explicit_issuer_relation_survives_extraction():
    snippet = "Instituto Fictício 205 (IF205)"
    service, _ = extractor(payload(
        issuer_institution="Instituto Fictício 205", issuer_acronym="IF205",
        issuer_name_acronym_evidence=snippet,
    ))
    result = service.extract("doc", b"synthetic", "application/pdf")
    assert result.extraction_status == "OK"
    assert result.issuer_name_acronym_evidence == snippet


@pytest.mark.parametrize("model,temperature", [
    ("gemini-2.5-flash", 0.0), ("gemini-3.8-flash", None),
    ("models/gemini-4-hydrogen", None), ("gemini-3.1-flash-lite", None),
])
def test_model_temperature_policy(model, temperature):
    service, client = extractor(payload())
    service.model = model
    result = service.extract("doc", b"synthetic", "application/pdf")
    assert client.models.generate_content.call_args.kwargs["config"].temperature == temperature
    assert result.raw_metadata["temperature"] == temperature


@pytest.mark.parametrize("code,calls", [(400, 1), (403, 1), (503, 2), (504, 2)])
def test_retry_is_bounded_and_audited(code, calls):
    service, client = extractor(payload())
    service.max_attempts = 2
    service.wait = Mock()
    error = errors.APIError(code, {"error": {"message": "private"}})
    client.models.generate_content.side_effect = [error, response(payload())]
    result = service.extract("doc", b"synthetic", "application/pdf")
    assert client.models.generate_content.call_count == calls
    assert len(result.raw_metadata["attempts"]) == calls
    assert service.wait.call_count == calls - 1
    assert result.extraction_status == ("OK" if calls == 2 else "API_ERROR")
    assert "private" not in result.model_dump_json()


@pytest.mark.parametrize("exc_module", ["httpx", "httpx2"])
def test_http_and_httpx2_read_timeout_retry_and_recover(exc_module):
    mod = pytest.importorskip(exc_module)
    service, client = extractor(payload())
    service.max_attempts = 2
    service.wait = Mock()
    client.models.generate_content.side_effect = [
        mod.ReadTimeout("secret timeout details"),
        response(payload()),
    ]
    result = service.extract("doc", b"synthetic", "application/pdf")
    assert client.models.generate_content.call_count == 2
    assert len(result.raw_metadata["attempts"]) == 2
    assert result.raw_metadata["attempts"][0]["error_type"] == "ReadTimeout"
    assert service.wait.call_count == 1
    assert result.extraction_status == ExtractionStatus.OK
    assert "secret timeout details" not in result.model_dump_json()


def test_httpx2_read_timeout_single_attempt_returns_sanitized_api_error():
    httpx2 = pytest.importorskip("httpx2")
    service, client = extractor(payload())
    service.max_attempts = 1
    client.models.generate_content.side_effect = httpx2.ReadTimeout("secret timeout details")
    result = service.extract("doc", b"synthetic", "application/pdf")
    assert client.models.generate_content.call_count == 1
    assert result.extraction_status == ExtractionStatus.API_ERROR
    assert result.raw_metadata["error_type"] == "ReadTimeout"
    assert "secret timeout details" not in result.model_dump_json()


@pytest.mark.parametrize("fields", [
    {"issuer_acronym": "IF205", "issuer_name_acronym_evidence": "IF205"},
    {"issuer_institution": "Instituto Fictício 205", "issuer_acronym": "IF205",
     "issuer_name_acronym_evidence": "Instituto Fictício 205 (IF2050)"},
    {"extraction_status": "UNREADABLE", "activity_count": 0,
     "issuer_name_acronym_evidence": "Texto"},
])
def test_incomplete_or_invalid_issuer_evidence_rejected(fields):
    service, _ = extractor(payload(**fields))
    assert service.extract("doc", b"synthetic", "application/pdf").extraction_status == "INVALID_JSON"


@pytest.mark.parametrize("mime", ["application/pdf", "image/png", "image/jpeg", "image/webp"])
def test_request_and_decimal_conversion(mime):
    service, client = extractor(
        payload(
            holder_name=" Pessoa Fictícia ",
            activity_title="Título específico",
            event_name="Evento fictício",
            participation_role_raw="palestrante",
            issuer_institution="Instituição fictícia",
            issuer_acronym="IF",
            start_year=2020,
            end_year=2021,
            activity_year=2021,
            workload_hours="40.00000000000000000001",
        )
    )
    record = service.extract("doc-1", b"synthetic document", mime)
    assert isinstance(record, ExtractedDocumentRecord)
    assert record.extraction_status == ExtractionStatus.OK
    assert record.holder_name == "Pessoa Fictícia"
    assert record.activity_title == "Título específico"
    assert record.event_name == "Evento fictício"
    assert record.participation_role_raw == "palestrante"
    assert record.workload_hours == Decimal("40.00000000000000000001")
    assert record.activity_year == 2021
    assert record.confianca_extracao is None
    assert record.categoria_sugerida is None
    client.models.generate_content.assert_called_once()
    args = client.models.generate_content.call_args.kwargs
    assert args["model"] == "gemini-test"
    assert args["contents"][0].inline_data.data == b"synthetic document"
    assert args["contents"][0].inline_data.mime_type == mime
    config = args["config"]
    assert config.temperature is None
    assert config.response_mime_type == "application/json"
    assert config.response_schema is None
    assert config.response_json_schema == ExtractionPayload.model_json_schema()
    assert config.system_instruction == PROMPT


def test_reproducibility_metadata():
    service, _ = extractor(payload())
    metadata = service.extract("doc", b"synthetic", "application/pdf").raw_metadata
    assert metadata["model"] == "gemini-test"
    assert metadata["model_version"] == "gemini-test-pinned-001"
    assert metadata["temperature"] is None
    assert metadata["temperature_policy"] == "provider_default"
    assert metadata["strategy"] == "zero-shot"
    assert metadata["latency_ms"] == 125.0
    assert metadata["tokens"]["total_token_count"] == 30
    assert metadata["tokens"]["prompt_token_count"] == 20
    assert metadata["tokens"]["candidates_token_count"] == 10
    assert metadata["prompt"] == PROMPT
    assert metadata["prompt_version"] == PROMPT_VERSION
    assert metadata["schema"] == ExtractionPayload.model_json_schema()
    assert metadata["sdk_version"]
    assert datetime.fromisoformat(metadata["executed_at"]).tzinfo is not None
    assert len(metadata["document_sha256"]) == 64


def test_missing_fields_are_not_unreadable_or_inferred():
    service, _ = extractor(payload(event_name="Evento", participation_role_raw="participante"))
    record = service.extract("doc", b"synthetic", "application/pdf")
    assert record.extraction_status == ExtractionStatus.OK
    assert record.activity_title is None
    assert record.workload_hours is None
    assert record.participation_role_raw == "participante"


def test_explicit_unreadable():
    service, _ = extractor(payload(extraction_status="UNREADABLE", activity_count=0))
    record = service.extract("doc", b"synthetic", "image/png")
    assert record.extraction_status == ExtractionStatus.UNREADABLE
    assert record.holder_name is None
    assert record.raw_metadata["tokens"]["total_token_count"] == 30


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not JSON",
        "```json\n{}\n```",
        "null",
        "[]",
        "{}",
        payload(workload_hours="NaN"),
        payload(workload_hours="Infinity"),
        payload(workload_hours="-1"),
        payload(workload_hours="40 hours"),
        payload(workload_hours=True),
        payload(workload_hours=40.5),
        payload(activity_year=True),
        payload(activity_year=2020.5),
        payload(activity_count=2),
        payload(activity_count=0),
        payload(activity_count=True),
        payload(extraction_status="VALIDADO"),
        payload(categoria_sugerida="evento"),
        payload(confianca_extracao=0.9),
        payload(document_id="model-controlled"),
        payload(extraction_status="UNREADABLE", holder_name="invented"),
    ],
)
def test_invalid_json_or_contract_is_separate_from_unreadable(text):
    service, _ = extractor(text)
    record = service.extract("doc", b"synthetic", "application/pdf")
    assert record.extraction_status == ExtractionStatus.INVALID_JSON
    assert record.holder_name is None
    assert record.raw_metadata["model_version"] == "gemini-test-pinned-001"
    assert record.raw_metadata["error_type"] == "INVALID_RESPONSE"


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("secret"),
        errors.ServerError(503, {"error": {"message": "private document"}}),
    ],
)
def test_api_error_does_not_leak_message_or_retry(error):
    service, client = extractor(payload())
    client.models.generate_content.side_effect = error
    record = service.extract("doc", b"synthetic", "application/pdf")
    assert record.extraction_status == ExtractionStatus.API_ERROR
    assert record.raw_metadata["model_version"] is None
    assert record.raw_metadata["tokens"] is None
    assert record.raw_metadata["latency_ms"] == 125.0
    assert str(error) not in record.model_dump_json()
    client.models.generate_content.assert_called_once()


def test_empty_response_is_invalid_not_unreadable():
    service, client = extractor(payload())
    client.models.generate_content.return_value = types.GenerateContentResponse()
    record = service.extract("doc", b"synthetic", "application/pdf")
    assert record.extraction_status == ExtractionStatus.INVALID_JSON
    assert record.raw_metadata["tokens"] is None


@pytest.mark.parametrize(
    "fields",
    [
        {"document_id": " "},
        {"data": b""},
        {"mime_type": "text/plain"},
    ],
)
def test_local_invalid_input_never_calls_provider(fields):
    service, client = extractor(payload())
    inputs = {"document_id": "doc", "data": b"synthetic", "mime_type": "application/pdf"}
    with pytest.raises(ValueError):
        service.extract(**(inputs | fields))
    client.models.generate_content.assert_not_called()


def test_settings_factory_uses_explicit_configuration():
    settings = Settings(_env_file=None, gemini_api_key="fake-key", gemini_model="chosen-model")
    with patch("comprova_lattes.extractor.gemini.genai.Client") as factory:
        service = GeminiExtractor.from_settings(settings)
    factory.assert_called_once()
    assert factory.call_args.kwargs["api_key"] == "fake-key"
    assert factory.call_args.kwargs["http_options"].timeout == 120000
    assert factory.call_args.kwargs["http_options"].retry_options.attempts == 1
    assert service.client is factory.return_value
    assert service.model == "chosen-model"


@pytest.mark.parametrize(
    "fields",
    [
        {"gemini_api_key": ""},
        {"gemini_temperature": 0.5},
    ],
)
def test_invalid_configuration_never_constructs_client(fields):
    settings = Settings(_env_file=None, **({"gemini_api_key": "fake"} | fields))
    with pytest.raises(ValueError):
        GeminiExtractor.from_settings(settings)


def test_model_must_be_explicit():
    with pytest.raises(ValueError):
        GeminiExtractor(Mock(), model=" ")
