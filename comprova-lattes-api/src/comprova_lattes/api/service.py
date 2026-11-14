"""Pipeline compartilhado pelo worker e testes offline."""

import logging
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select, update

from comprova_lattes.config import settings
from comprova_lattes.extractor.gemini import GeminiExtractor
from comprova_lattes.matcher.engine import match_curriculum
from comprova_lattes.matcher.models import ExtractedDocumentRecord, MatchStatus
from comprova_lattes.parser.xml_parser import parse_lattes_xml_with_report

from .db import Review, Validation
from .schemas import ValidationCreateRequest, decode_content


class Extractor(Protocol):
    def extract(self, document_id: str, data: bytes, mime_type: str) -> ExtractedDocumentRecord:
        ...


def now() -> str:
    return datetime.now(UTC).isoformat()


def process_validation(validation_id: str, session_factory, extractor: Extractor | None = None):
    with session_factory() as db:
        claimed = db.execute(
            update(Validation)
            .where(Validation.id == validation_id, Validation.status == "PENDING")
            .values(status="PROCESSING")
        ).rowcount
        db.commit()
        if not claimed:
            row = db.get(Validation, validation_id)
            return {"id": validation_id, "status": row.status if row else "NOT_FOUND"}
        row = db.get(Validation, validation_id)
        owned_extractor = None
        try:
            request = ValidationCreateRequest.model_validate(row.payload)
            parsed = parse_lattes_xml_with_report(request.xml_bytes())
            if request.documents and extractor is None:
                owned_extractor = GeminiExtractor.from_settings(settings)
                extractor = owned_extractor
            documents = []
            for doc in request.documents:
                extracted = extractor.extract(
                    doc.document_id, decode_content(doc.content_base64), doc.mime_type
                )
                if extracted.document_id != doc.document_id:
                    raise ValueError("Extractor document_id mismatch")
                documents.append(extracted)
            result = match_curriculum(
                parsed.curriculum, documents, request.matcher_config,
                parse_diagnostics=parsed.diagnostics,
            )
            row.parsed = {
                "curriculum": parsed.curriculum.model_dump(mode="json"),
                "diagnostics": [asdict(d) for d in parsed.diagnostics],
                "declared_encoding": parsed.declared_encoding,
                "unverified_variants": list(parsed.unverified_variants),
                "unrecognized_elements": list(parsed.unrecognized_elements),
            }
            row.extractions = [d.model_dump(mode="json") for d in documents]
            row.automatic_result = result.model_dump(mode="json")
            row.status = "COMPLETED"
        except Exception as exc:  # noqa: BLE001 -- fronteira da tarefa: persistir falha sanitizada
            # Não persistir mensagens que possam conter credenciais ou documentos.
            row.status = "FAILED"
            row.error_code = type(exc).__name__
        finally:
            if owned_extractor is not None:
                try:
                    owned_extractor.client.close()
                except Exception as exc:  # noqa: BLE001 -- limpeza não invalida resultado persistido
                    logging.getLogger(__name__).warning("Extractor cleanup: %s", type(exc).__name__)
        db.commit()
        return {"id": row.id, "status": row.status}


def validation_detail(db, row: Validation) -> dict:
    reviews = db.scalars(
        select(Review).where(Review.validation_id == row.id).order_by(Review.id)
    ).all()
    history = [dict(id=r.id, record_index=r.record_index, **r.decision) for r in reviews]
    latest = {r.record_index: r.decision for r in reviews}
    verdicts = (row.automatic_result or {}).get("record_verdicts", [])
    automatic_summary = {status.value: 0 for status in MatchStatus}
    reviewed_summary = dict(automatic_summary)
    records = []
    for verdict in verdicts:
        index = verdict["record_index"]
        review = latest.get(index)
        automatic_summary[verdict["status"]] += 1
        reviewed_summary[review["status"] if review else verdict["status"]] += 1
        records.append({
            "record_index": index, "automatic": verdict, "human_review": review,
            "review_required": verdict["review_required"] and review is None,
        })
    return {
        "id": row.id, "created_at": row.created_at, "status": row.status,
        "error_code": row.error_code, "input": row.payload, "parsed": row.parsed,
        "extractions": row.extractions, "automatic_result": row.automatic_result,
        "records": records, "reviews": history, "automatic_summary": automatic_summary,
        "reviewed_summary": reviewed_summary,
    }
