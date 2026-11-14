from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from comprova_lattes import __version__
from comprova_lattes.config import settings
from comprova_lattes.matcher.models import HumanReviewRecord
from comprova_lattes.parser.exceptions import LattesParserError
from comprova_lattes.parser.xml_parser import parse_lattes_xml_with_report

from .db import Review, Validation, get_session_factory
from .schemas import HumanReviewRequest, ValidationCreateRequest
from .service import now, validation_detail


def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "version": __version__,
        "environment": settings.environment,
        "gemini_model": settings.gemini_model,
    }


def dispatch_validation(validation_id: str):
    from comprova_lattes.worker import process_validation_task

    return process_validation_task.delay(validation_id)


def create_app(*, session_factory=None, dispatcher=None, cors_origins=None) -> FastAPI:
    application = FastAPI(
        title="Comprova Lattes API", version=__version__,
        description="Validação semiautomatizada do Currículo Lattes",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
    )
    application.add_api_route("/health", health_check, methods=["GET"])

    def sessions():
        return session_factory if session_factory is not None else get_session_factory()

    def find(db, validation_id: str):
        row = db.get(Validation, validation_id)
        if row is None:
            raise HTTPException(404, "Validação não encontrada")
        return row

    @application.post("/validations", status_code=202)
    def create_validation(request: ValidationCreateRequest):
        try:
            parse_lattes_xml_with_report(request.xml_bytes())
        except LattesParserError as exc:
            raise HTTPException(422, type(exc).__name__) from exc
        with sessions()() as db:
            row = Validation(
                id=str(uuid4()), created_at=now(), status="PENDING",
                payload=request.model_dump(mode="json"),
            )
            db.add(row)
            db.commit()
            validation_id = row.id
        try:
            (dispatcher or dispatch_validation)(validation_id)
        except Exception as exc:
            with sessions()() as db:
                row = find(db, validation_id)
                if row.status == "PENDING":
                    row.status = "DISPATCH_FAILED"
                    row.error_code = "DISPATCH_FAILED"
                    db.commit()
            raise HTTPException(
                503, {"id": validation_id, "error_code": "DISPATCH_FAILED"}
            ) from exc
        with sessions()() as db:
            return validation_detail(db, find(db, validation_id))

    @application.get("/validations")
    def list_validations(
        offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    ):
        with sessions()() as db:
            rows = db.scalars(
                select(Validation).order_by(Validation.created_at, Validation.id)
                .offset(offset).limit(limit)
            ).all()
            return [
                {"id": r.id, "created_at": r.created_at, "status": r.status,
                 "error_code": r.error_code}
                for r in rows
            ]

    @application.get("/validations/{validation_id}")
    def get_validation(validation_id: str):
        with sessions()() as db:
            return validation_detail(db, find(db, validation_id))

    @application.post("/validations/{validation_id}/records/{record_index}/review")
    def review_record(validation_id: str, record_index: int, request: HumanReviewRequest):
        with sessions()() as db:
            row = find(db, validation_id)
            if row.status != "COMPLETED":
                raise HTTPException(409, "Validação ainda não concluída")
            verdicts = row.automatic_result["record_verdicts"]
            if record_index < 0 or record_index >= len(verdicts):
                raise HTTPException(404, "Registro não encontrado")
            document_ids = {d["document_id"] for d in row.payload["documents"]}
            selected = set(request.rejected_document_ids)
            if request.matched_document_id is not None:
                selected.add(request.matched_document_id)
            if not selected <= document_ids:
                raise HTTPException(422, "Documento não pertence à validação")
            review = HumanReviewRecord(
                **request.model_dump(), reviewed_at=now(),
            )
            db.add(Review(
                validation_id=row.id, record_index=record_index,
                decision=review.model_dump(mode="json"),
            ))
            db.commit()
            return validation_detail(db, row)

    return application


app = create_app()
