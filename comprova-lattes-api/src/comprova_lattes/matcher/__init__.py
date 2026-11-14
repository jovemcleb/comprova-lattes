"""Módulo P0-C: Motor determinístico de associação e classificação (Regras + Levenshtein)."""

"""Motor determinístico M2, sem dependências de extração ou persistência."""
from .engine import classify, match_curriculum
from .models import (
    AssociationCandidate,
    AssociationPair,
    ExtractedDocumentRecord,
    ExtractionStatus,
    FieldEvidence,
    FieldOutcome,
    HumanReviewRecord,
    MatcherConfig,
    MatcherThresholds,
    MatchingResult,
    MatchMode,
    MatchStatus,
    OrphanDocumentReport,
    RecordVerdict,
)

__all__ = [
    "AssociationCandidate",
    "AssociationPair",
    "ExtractedDocumentRecord",
    "ExtractionStatus",
    "FieldEvidence",
    "FieldOutcome",
    "HumanReviewRecord",
    "MatchMode",
    "MatchStatus",
    "MatcherConfig",
    "MatcherThresholds",
    "MatchingResult",
    "OrphanDocumentReport",
    "RecordVerdict",
    "classify",
    "match_curriculum",
]
