"""Integração HTTP/SQL/pipeline sem broker, banco externo ou chamadas LLM."""

import base64
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from comprova_lattes.api.db import Base, Review, Validation
from comprova_lattes.api.main import create_app
from comprova_lattes.api.service import process_validation
from comprova_lattes.matcher.models import ExtractedDocumentRecord

XML = '''<?xml version="1.0" encoding="UTF-8"?>
<CURRICULO-VITAE NUMERO-IDENTIFICADOR="123">
<DADOS-GERAIS NOME-COMPLETO="Ana Silva"/>
<DADOS-COMPLEMENTARES>
<FORMACAO-COMPLEMENTAR><FORMACAO-COMPLEMENTAR-CURSO-DE-CURTA-DURACAO
SEQUENCIA-FORMACAO="1" NOME-CURSO="Curso Python"
NOME-INSTITUICAO="Universidade Alfa" ANO-DE-INICIO="2024"
ANO-DE-CONCLUSAO="2024" CARGA-HORARIA="40" STATUS-DO-CURSO="CONCLUIDO"/>
</FORMACAO-COMPLEMENTAR></DADOS-COMPLEMENTARES></CURRICULO-VITAE>'''
CONFIG = {"thresholds": {
    "association": 0.4, "ambiguity_margin": 0.05,
    "holder_low": 0.6, "holder_high": 0.9,
    "title_low": 0.6, "title_high": 0.9,
    "institution_low": 0.6, "institution_high": 0.9,
}}


class FakeExtractor:
    def __init__(self):
        self.calls = []
        self.hours = "40"
        self.failure = False
        self.status = "OK"

    def extract(self, document_id, data, mime_type):
        self.calls.append((document_id, data, mime_type))
        if self.failure:
            raise RuntimeError("sensitive document or credential")
        return ExtractedDocumentRecord(
            document_id=document_id, holder_name="Ana Silva", activity_title="Curso Python",
            issuer_institution="Universidade Alfa", start_year=2024, end_year=2024,
            workload_hours=self.hours, extraction_status=self.status,
            confianca_extracao=0, categoria_sugerida="untrusted",
        )


def payload(*ids):
    return {
        "xml_content": XML, "matcher_config": deepcopy(CONFIG),
        "documents": [
            {"document_id": doc_id, "filename": f"{doc_id}.pdf",
             "mime_type": "application/pdf",
             "content_base64": base64.b64encode(b"synthetic PDF").decode()}
            for doc_id in ids
        ],
    }


@pytest.fixture
def harness():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    extractor = FakeExtractor()
    app = create_app(
        session_factory=factory,
        dispatcher=lambda key: process_validation(key, factory, extractor),
    )
    with TestClient(app) as client:
        yield client, factory, extractor
    engine.dispose()


def create(client, request):
    response = client.post("/validations", json=request)
    assert response.status_code == 202, response.text
    return response.json()


def review(client, key, **changes):
    request = {
        "reviewer": "Revisor A", "status": "VALIDADO", "justification": "Conferido manualmente",
        **changes,
    }
    return client.post(f"/validations/{key}/records/0/review", json=request)


def test_health_cors_and_openapi(harness):
    client, _, _ = harness
    assert client.get("/health").json()["status"] == "ok"
    response = client.options("/validations", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    response = client.options("/validations", headers={
        "Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST",
    })
    assert "access-control-allow-origin" not in response.headers
    assert "multipart/form-data" not in str(client.get("/openapi.json").json())


def test_pipeline_persisted_with_evidence_and_document(harness):
    client, factory, extractor = harness
    detail = create(client, payload("doc1"))
    assert detail["status"] == "COMPLETED"
    assert detail["automatic_summary"] == {"VALIDADO": 1, "DIVERGENTE": 0, "INCONCLUSIVO": 0}
    assert detail["automatic_summary"] == detail["reviewed_summary"]
    assert detail["automatic_result"]["record_verdicts"][0]["field_evidences"]
    assert detail["parsed"]["curriculum"]["records"][0]["record_id"]
    assert detail["extractions"][0]["confianca_extracao"] == 0
    assert extractor.calls == [("doc1", b"synthetic PDF", "application/pdf")]
    key = detail["id"]
    assert client.get(f"/validations/{key}").json() == detail
    assert client.get("/validations").json()[0]["id"] == key
    with factory() as db:
        row = db.get(Validation, key)
        assert row.automatic_result == detail["automatic_result"]
        assert row.payload["documents"][0]["content_base64"]
    # Redelivery must not re-extract or overwrite automatic evidence.
    assert process_validation(key, factory, extractor)["status"] == "COMPLETED"
    assert len(extractor.calls) == 1


@pytest.mark.parametrize("initial", ["VALIDADO", "DIVERGENTE", "INCONCLUSIVO"])
def test_reviews_all_classes_append_history_and_preserve_snapshot(harness, initial):
    client, factory, extractor = harness
    extractor.hours = "45" if initial == "DIVERGENTE" else "40"
    detail = create(client, payload() if initial == "INCONCLUSIVO" else payload("doc1"))
    key = detail["id"]
    assert detail["automatic_summary"][initial] == 1
    assert detail["records"][0]["review_required"] == (initial == "INCONCLUSIVO")
    result = review(client, key, status="DIVERGENTE").json()
    assert result["automatic_result"] == detail["automatic_result"]
    assert result["automatic_summary"] == detail["automatic_summary"]
    assert result["reviewed_summary"]["DIVERGENTE"] == 1
    assert not result["records"][0]["review_required"]
    result = review(client, key, status="INCONCLUSIVO", reviewer="Revisor B").json()
    assert len(result["reviews"]) == 2
    assert result["reviews"][0]["reviewer"] == "Revisor A"
    assert result["reviews"][1]["reviewer"] == "Revisor B"
    assert result["reviews"][1]["reviewed_at"].endswith("Z")
    assert result["reviewed_summary"]["INCONCLUSIVO"] == 1
    assert result["automatic_result"] == detail["automatic_result"]
    with factory() as db:
        assert len(db.scalars(select(Review)).all()) == 2


def test_ambiguous_review_confirm_reject_and_correction(harness):
    client, _, _ = harness
    detail = create(client, payload("a", "b"))
    key = detail["id"]
    verdict = detail["automatic_result"]["record_verdicts"][0]
    assert verdict["reason_code"] == "ASSOCIACAO_AMBIGUA"
    assert {d["document_id"] for d in verdict["ambiguity_candidates"]} == {"a", "b"}
    result = review(client, key, matched_document_id="b", rejected_document_ids=["a"])
    assert result.status_code == 200
    assert result.json()["records"][0]["human_review"]["matched_document_id"] == "b"
    result = review(client, key, matched_document_id="a", rejected_document_ids=["b"])
    assert result.json()["records"][0]["human_review"]["matched_document_id"] == "a"
    assert result.json()["automatic_result"] == detail["automatic_result"]


@pytest.mark.parametrize("changes", [
    {"justification": "  "}, {"reviewer": " "}, {"status": "OTHER"},
    {"matched_document_id": "outside"}, {"rejected_document_ids": ["outside"]},
    {"matched_document_id": "a", "rejected_document_ids": ["a"]},
    {"rejected_document_ids": ["a", "a"]}, {"reviewed_at": "2000-01-01"},
])
def test_invalid_review_is_atomic(harness, changes):
    client, _, _ = harness
    detail = create(client, payload("a"))
    assert review(client, detail["id"], **changes).status_code == 422
    assert client.get(f'/validations/{detail["id"]}').json() == detail


@pytest.mark.parametrize("case", [
    "missing_xml", "two_xml", "bad_base64", "empty_doc", "bad_mime", "duplicate",
    "malformed", "dtd", "no_config",
])
def test_invalid_submission_never_dispatches(harness, case):
    client, _, extractor = harness
    request = payload("a")
    if case == "missing_xml":
        del request["xml_content"]
    elif case == "two_xml":
        request["xml_base64"] = base64.b64encode(XML.encode()).decode()
    elif case in {"bad_base64", "empty_doc"}:
        request["documents"][0]["content_base64"] = "!!!" if case == "bad_base64" else ""
    elif case == "bad_mime":
        request["documents"][0]["mime_type"] = "text/plain"
    elif case == "duplicate":
        request["documents"].append(request["documents"][0])
    elif case == "malformed":
        request["xml_content"] = "<broken>"
    elif case == "dtd":
        request["xml_content"] = '<!DOCTYPE CURRICULO-VITAE><CURRICULO-VITAE/>'
    elif case == "no_config":
        del request["matcher_config"]
    assert client.post("/validations", json=request).status_code == 422
    assert extractor.calls == []
    assert client.get("/validations").json() == []


def test_base64_xml_and_missing_routes(harness):
    client, _, _ = harness
    request = payload()
    request["xml_base64"] = base64.b64encode(request.pop("xml_content").encode()).decode()
    detail = create(client, request)
    assert detail["automatic_summary"]["INCONCLUSIVO"] == 1
    assert client.get("/validations/missing").status_code == 404
    assert review(client, "missing").status_code == 404
    for index in [-1, 1]:
        assert client.post(
            f'/validations/{detail["id"]}/records/{index}/review',
            json={"reviewer": "A", "status": "INCONCLUSIVO", "justification": "Sem evidência"},
        ).status_code == 404
    assert client.get("/validations?offset=-1").status_code == 422
    assert client.get("/validations?limit=101").status_code == 422


def test_worker_failure_is_sanitized_and_not_reviewable(harness):
    client, _, extractor = harness
    extractor.failure = True
    detail = create(client, payload("a"))
    assert detail["status"] == "FAILED"
    assert detail["error_code"] == "RuntimeError"
    assert detail["automatic_result"] is None
    assert "sensitive" not in str(detail)
    assert review(client, detail["id"]).status_code == 409


def test_extraction_failure_contract_still_reaches_matcher(harness):
    client, _, extractor = harness
    extractor.status = "UNREADABLE"
    detail = create(client, payload("a"))
    assert detail["status"] == "COMPLETED"
    assert detail["records"][0]["automatic"]["reason_code"] == "DOCUMENTO_ILEGIVEL"
    assert detail["records"][0]["review_required"]


def test_pending_dispatch_failure_and_celery_task(harness, monkeypatch):
    _, factory, extractor = harness
    queued = []
    with TestClient(create_app(session_factory=factory, dispatcher=queued.append)) as client:
        detail = create(client, payload("a"))
        assert detail["status"] == "PENDING"
        assert queued == [detail["id"]]
        assert review(client, detail["id"]).status_code == 409

    from comprova_lattes.api import db as db_module
    from comprova_lattes.api import service
    from comprova_lattes.worker import ping_task, process_validation_task

    monkeypatch.setattr(db_module, "get_session_factory", lambda: factory)
    monkeypatch.setattr(
        service.GeminiExtractor, "from_settings", lambda _: extractor,
    )
    monkeypatch.setattr(extractor, "client", type("Client", (), {"close": lambda _: None})(),
                        raising=False)
    assert process_validation_task.apply(args=[detail["id"]]).get()["status"] == "COMPLETED"
    assert ping_task.run() == {"status": "pong"}
    assert process_validation_task.name == "comprova_lattes.process_validation"
    assert process_validation("missing", factory, extractor)["status"] == "NOT_FOUND"

    def broken_dispatch(_):
        raise RuntimeError("redis secret")

    with TestClient(create_app(session_factory=factory, dispatcher=broken_dispatch)) as client:
        response = client.post("/validations", json=payload())
        assert response.status_code == 503
        key = response.json()["detail"]["id"]
        detail = client.get(f"/validations/{key}").json()
        assert detail["status"] == "DISPATCH_FAILED"
        assert "secret" not in str(detail)


def test_review_reject_all_and_cross_validation_documents(harness):
    client, _, _ = harness
    first = create(client, payload("a", "b"))
    other = create(client, payload("other-document"))
    response = review(client, first["id"], matched_document_id="other-document")
    assert response.status_code == 422
    assert client.get(f'/validations/{other["id"]}').json()["reviews"] == []
    response = review(
        client, first["id"], status="INCONCLUSIVO", rejected_document_ids=["a", "b"],
    )
    assert response.status_code == 200
    result = response.json()
    assert result["records"][0]["human_review"]["matched_document_id"] is None
    assert result["records"][0]["human_review"]["rejected_document_ids"] == ["a", "b"]
    assert result["automatic_result"] == first["automatic_result"]


def test_correction_to_document_outside_automatic_candidates(harness):
    client, _, _ = harness
    # Association is deliberately disabled for the document by an explicit high threshold.
    request = payload("a")
    request["xml_content"] = XML.replace("Curso Python", "Outro assunto")
    request["matcher_config"]["thresholds"]["association"] = 1
    detail = create(client, request)
    assert detail["automatic_result"]["orphan_documents"][0]["document_id"] == "a"
    result = review(client, detail["id"], matched_document_id="a").json()
    assert result["records"][0]["human_review"]["matched_document_id"] == "a"
    assert result["automatic_result"] == detail["automatic_result"]


def test_default_dispatch_queues_task_without_broker(monkeypatch):
    from comprova_lattes.api.main import dispatch_validation
    from comprova_lattes.worker import process_validation_task

    calls = []
    monkeypatch.setattr(process_validation_task, "delay", calls.append)
    dispatch_validation("persisted-id")
    assert calls == ["persisted-id"]
