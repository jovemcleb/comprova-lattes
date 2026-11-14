"""Testes offline: o cliente SDK é sempre substituído por mocks."""

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
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
    return GeminiExtractor(client, model="gemini-test", clock=lambda: next(ticks)), client


def payload(**fields):
    return json.dumps({"extraction_status": "OK", "activity_count": 1, **fields})


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
    assert config.temperature == 0.0
    assert config.response_mime_type == "application/json"
    assert config.response_schema is ExtractionPayload
    assert config.system_instruction == PROMPT


def test_reproducibility_metadata():
    service, _ = extractor(payload())
    metadata = service.extract("doc", b"synthetic", "application/pdf").raw_metadata
    assert metadata["model"] == "gemini-test"
    assert metadata["model_version"] == "gemini-test-pinned-001"
    assert metadata["temperature"] == 0.0
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
    factory.assert_called_once_with(api_key="fake-key")
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
