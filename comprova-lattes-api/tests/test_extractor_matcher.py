"""Integração M3 -> M2 com documentos sintéticos e transporte SDK simulado."""

import json
from unittest.mock import Mock, patch

import pytest
from google.genai import errors, types
from test_matcher import config as matcher_config
from test_matcher import record

from comprova_lattes.extractor import GeminiExtractor
from comprova_lattes.matcher import MatchingResult, match_curriculum
from comprova_lattes.schemas.lattes import LattesCurriculum


@pytest.fixture
def config():
    return matcher_config.__wrapped__()


def extract(status="OK", **entities):
    client = Mock()
    if status == "API_ERROR":
        client.models.generate_content.side_effect = errors.ServerError(503, {})
    else:
        text = (
            "invalid json"
            if status == "INVALID_JSON"
            else json.dumps({"extraction_status": status, "activity_count": 1, **entities})
        )
        client.models.generate_content.return_value = types.GenerateContentResponse(
            candidates=[types.Candidate(content=types.Content(parts=[types.Part(text=text)]))]
        )
    with patch("google.genai.Client", side_effect=AssertionError("Real client forbidden")):
        return GeminiExtractor(client, model="synthetic-test").extract(
            "m3", b"synthetic document", "application/pdf"
        )


@pytest.mark.parametrize("status", ["UNREADABLE", "INVALID_JSON", "API_ERROR"])
@pytest.mark.parametrize("mixed", [False, True])
def test_m3_failures_survive_batch_without_invented_association(config, status, mixed):
    failed = extract(status)
    records = [record()]
    docs = [failed]
    if mixed:
        records.append(record(record_id="r2", title="Zoologia Tropical"))
        docs.append(
            extract(
                activity_title="Zoologia Tropical",
                holder_name="Maria Silva",
                issuer_institution="UFRA",
                end_year=2024,
                workload_hours="40",
            )
        )
        docs[1] = docs[1].model_copy(update={"document_id": "ok"})
    result = match_curriculum(LattesCurriculum(records=records), docs, config)
    verdict = result.record_verdicts[0]
    assert failed.extraction_status == status
    assert verdict.status == "INCONCLUSIVO"
    assert verdict.reason_code == (
        "DOCUMENTO_ILEGIVEL" if status == "UNREADABLE" else "FALHA_EXTRACAO"
    )
    assert verdict.review_required
    assert verdict.matched_document_id is None
    assert verdict.diagnostics == [f"EXTRACTION_FAILURE:m3:{status}"]
    assert [d.document_id for d in result.orphan_documents] == ["m3"]
    if mixed:
        assert result.record_verdicts[1].status == "VALIDADO"
        assert result.association_pairs[0].document_id == "ok"
    assert MatchingResult.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    "hours,status", [("40.0", "VALIDADO"), ("40.000000000000000000000000000001", "DIVERGENTE")]
)
def test_m3_success_preserves_exact_hours_in_m2(config, hours, status):
    doc = extract(
        activity_title="Ciência de Dados",
        holder_name="Maria Silva",
        issuer_institution="UFRA",
        end_year=2024,
        workload_hours=hours,
    )
    result = match_curriculum(LattesCurriculum(records=[record()]), [doc], config)
    assert result.record_verdicts[0].status == status
    assert result.record_verdicts[0].matched_document_id == "m3"
    assert doc.raw_metadata["model"] == "synthetic-test"


def test_mixed_failure_types_and_no_records(config):
    docs = [extract("UNREADABLE"), extract("API_ERROR").model_copy(update={"document_id": "api"})]
    result = match_curriculum(LattesCurriculum(records=[record()]), docs, config)
    assert result.record_verdicts[0].reason_code == "FALHA_EXTRACAO"
    assert len(result.record_verdicts[0].diagnostics) == 2
    empty = match_curriculum(LattesCurriculum(), docs, config)
    assert not empty.record_verdicts
    assert len(empty.orphan_documents) == 2


def test_m3_start_year_conflict_reaches_m2(config):
    doc = extract(
        activity_title="Ciência de Dados",
        holder_name="Maria Silva",
        issuer_institution="UFRA",
        start_year=2021,
        end_year=2024,
        activity_year=2024,
        workload_hours="40",
    )
    result = match_curriculum(LattesCurriculum(records=[record(start_year=2020)]), [doc], config)
    verdict = result.record_verdicts[0]
    assert verdict.status == "DIVERGENTE"
    assert next(f for f in verdict.field_evidences if f.field_name == "ano").rule_applied == (
        "START_YEAR_EXACT"
    )
