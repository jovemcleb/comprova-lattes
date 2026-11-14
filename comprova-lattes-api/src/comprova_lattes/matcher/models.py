"""Contratos offline; limiares devem vir da calibração piloto."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from comprova_lattes.schemas.lattes import (
    FiniteDecimal,
    LattesCategory,
    NonEmptyStr,
    OptionalCleanStr,
    StrictXmlInt,
)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExtractionStatus(StrEnum):
    OK = "OK"
    UNREADABLE = "UNREADABLE"
    INVALID_JSON = "INVALID_JSON"
    API_ERROR = "API_ERROR"


class MatchMode(StrEnum):
    PROPOSED = "PROPOSED"
    BASELINE_EXACT = "BASELINE_EXACT"
    BASELINE_NORMALIZED = "BASELINE_NORMALIZED"


class MatchStatus(StrEnum):
    VALIDADO = "VALIDADO"
    DIVERGENTE = "DIVERGENTE"
    INCONCLUSIVO = "INCONCLUSIVO"


class FieldOutcome(StrEnum):
    MATCH = "MATCH"
    CONFLICT = "CONFLICT"
    INCONCLUSIVE_BORDERLINE = "INCONCLUSIVE_BORDERLINE"
    MISSING_LATTES = "MISSING_LATTES"
    MISSING_DOCUMENT = "MISSING_DOCUMENT"
    MISSING_BOTH = "MISSING_BOTH"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ExtractedDocumentRecord(Contract):
    document_id: NonEmptyStr
    extraction_status: ExtractionStatus = ExtractionStatus.OK
    holder_name: OptionalCleanStr = None
    activity_title: OptionalCleanStr = None
    event_name: OptionalCleanStr = None
    participation_role_raw: OptionalCleanStr = None
    issuer_institution: OptionalCleanStr = None
    issuer_acronym: OptionalCleanStr = None
    start_year: StrictXmlInt | None = None
    end_year: StrictXmlInt | None = None
    activity_year: StrictXmlInt | None = None
    workload_hours: Annotated[FiniteDecimal, Field(ge=0)] | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    confianca_extracao: Any = None
    categoria_sugerida: Any = None


Score = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class MatcherThresholds(Contract):
    association: Score
    ambiguity_margin: Score
    holder_low: Score
    holder_high: Score
    title_low: Score
    title_high: Score
    institution_low: Score
    institution_high: Score

    @model_validator(mode="after")
    def ordered_thresholds(self) -> "MatcherThresholds":
        for name in ("holder", "title", "institution"):
            if getattr(self, f"{name}_low") > getattr(self, f"{name}_high"):
                raise ValueError(f"{name}: low deve ser <= high")
        if self.association == 0:
            raise ValueError("association deve ser positivo")
        return self


class MatcherConfig(Contract):
    thresholds: MatcherThresholds
    mode: MatchMode = MatchMode.PROPOSED
    text_metric: Literal["LEVENSHTEIN_NORM", "JARO_WINKLER", "TOKEN_HYBRID"] = "LEVENSHTEIN_NORM"
    acronym_table: dict[str, str] = Field(default_factory=dict)
    acronym_table_version: NonEmptyStr = "unconfigured"
    calibration_metadata: dict[str, Any] = Field(default_factory=dict)


FieldName = Literal[
    "titular", "titulo", "evento", "papel_participacao", "instituicao", "ano", "carga"
]
RawValue = str | int | Decimal | None


class FieldEvidence(Contract):
    field_name: FieldName
    lattes_raw: RawValue = None
    document_raw: RawValue = None
    lattes_normalized: RawValue = None
    document_normalized: RawValue = None
    rule_applied: str
    similarity_score: Score | None = None
    numeric_difference: Annotated[FiniteDecimal, Field(ge=0)] | None = None
    outcome: FieldOutcome
    justification_pt: str

    @model_validator(mode="before")
    @classmethod
    def restore_workload_decimals(cls, values: Any) -> Any:
        # JSON representa Decimal como string; o campo identifica seu tipo sem
        # converter títulos numéricos ou nomes brutos em números.
        if isinstance(values, dict) and values.get("field_name") == "carga":
            values = dict(values)
            for key in ("lattes_raw", "document_raw", "lattes_normalized", "document_normalized"):
                if values.get(key) is not None:
                    values[key] = Decimal(str(values[key]))
        return values


class AssociationCandidate(Contract):
    document_id: str
    association_score: Score
    field_evidences: list[FieldEvidence] = Field(default_factory=list)


class HumanReviewRecord(Contract):
    reviewer: NonEmptyStr
    reviewed_at: datetime
    status: MatchStatus
    justification: NonEmptyStr
    matched_document_id: str | None = None
    rejected_document_ids: list[str] = Field(default_factory=list)


class RecordVerdict(Contract):
    record_index: int
    record_id: str | None
    category: LattesCategory
    matched_document_id: str | None = None
    association_score: Score | None = None
    status: MatchStatus
    reason_code: str
    ambiguity_candidates: list[AssociationCandidate] = Field(default_factory=list)
    field_evidences: list[FieldEvidence] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    review_required: bool = False
    human_review: HumanReviewRecord | None = None


class AssociationPair(Contract):
    record_index: int
    record_id: str | None
    document_id: str
    association_score: Score


class OrphanDocumentReport(Contract):
    document_id: str
    reason_code: Literal["DOCUMENTO_NAO_ASSOCIADO"] = "DOCUMENTO_NAO_ASSOCIADO"
    best_candidate_record_id: str | None = None
    best_association_score: Score | None = None


class MatchingResult(Contract):
    mode: MatchMode
    record_verdicts: list[RecordVerdict]
    orphan_documents: list[OrphanDocumentReport]
    association_pairs: list[AssociationPair]
