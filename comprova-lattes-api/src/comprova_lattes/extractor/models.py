"""Contrato de transporte Gemini sem regras de classificação."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from comprova_lattes.matcher.models import ExtractedDocumentRecord
from comprova_lattes.schemas.lattes import OptionalCleanStr, StrictXmlInt


class ExtractionPayload(BaseModel):
    """JSON Schema enviado ao SDK; horas em texto preservam precisão decimal."""

    model_config = ConfigDict(extra="forbid")

    extraction_status: Literal["OK", "UNREADABLE"]
    activity_count: int = Field(ge=0, strict=True)
    holder_name: OptionalCleanStr = None
    activity_title: OptionalCleanStr = None
    event_name: OptionalCleanStr = None
    participation_role_raw: OptionalCleanStr = None
    issuer_institution: OptionalCleanStr = None
    issuer_acronym: OptionalCleanStr = None
    start_year: StrictXmlInt | None = None
    end_year: StrictXmlInt | None = None
    activity_year: StrictXmlInt | None = None
    workload_hours: str | None = Field(
        default=None,
        description="Horas não negativas em texto decimal, ex.: 40.5; null se ausente.",
    )

    @model_validator(mode="after")
    def validate_record(self) -> "ExtractionPayload":
        if self.activity_count > 1:
            raise ValueError("Múltiplas atividades estão fora do contrato (AD-004).")
        if self.extraction_status == "OK" and self.activity_count != 1:
            raise ValueError("OK exige exatamente uma atividade (AD-004).")
        fields = self.model_dump(exclude={"activity_count", "extraction_status"})
        if self.extraction_status == "UNREADABLE" and any(v is not None for v in fields.values()):
            raise ValueError("Documento ilegível não pode fornecer entidades.")
        ExtractedDocumentRecord(document_id="validation", **fields)
        return self

    def to_record(self, document_id: str, metadata: dict[str, Any]) -> ExtractedDocumentRecord:
        return ExtractedDocumentRecord(
            document_id=document_id,
            raw_metadata=metadata,
            **self.model_dump(exclude={"activity_count"}),
        )
