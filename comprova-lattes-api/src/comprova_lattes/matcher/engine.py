"""Fluxo puro: associação, classificação e relatórios fora da matriz 3×3."""

from collections.abc import Sequence
from typing import Protocol

from comprova_lattes.schemas.lattes import LattesCurriculum, LattesRecord

from .association import associate, association_score
from .models import (
    AssociationCandidate,
    AssociationPair,
    ExtractedDocumentRecord,
    FieldEvidence,
    FieldOutcome,
    MatcherConfig,
    MatchingResult,
    MatchStatus,
    OrphanDocumentReport,
    RecordVerdict,
)
from .rules import compare_fields, essential_fields


class ParseDiagnostic(Protocol):
    """Interface estrutural dos diagnósticos M1, sem dependência do parser."""

    code: str
    record_index: int | None


def classify(
    record: LattesRecord, document: ExtractedDocumentRecord, fields: list[FieldEvidence]
) -> tuple[MatchStatus, str]:
    if document.extraction_status != "OK":
        reason = (
            "DOCUMENTO_ILEGIVEL" if document.extraction_status == "UNREADABLE" else "FALHA_EXTRACAO"
        )
        return MatchStatus.INCONCLUSIVO, reason
    if any(f.outcome == FieldOutcome.CONFLICT for f in fields):
        return MatchStatus.DIVERGENTE, "CONFLITO_ATRIBUTO_DECISIVO"
    required = essential_fields(record)
    if any(f.field_name in required and f.outcome != FieldOutcome.MATCH for f in fields):
        return MatchStatus.INCONCLUSIVO, "EVIDENCIA_INSUFICIENTE"
    return MatchStatus.VALIDADO, "VALIDADO_CORRESPONDENCIA_COMPLETA"


def match_curriculum(
    curriculum: LattesCurriculum,
    documents: list[ExtractedDocumentRecord],
    config: MatcherConfig,
    *,
    parse_diagnostics: Sequence[ParseDiagnostic] = (),
) -> MatchingResult:
    if len({d.document_id for d in documents}) != len(documents):
        raise ValueError("document_id deve ser único no lote")
    comparisons = [
        [compare_fields(r, d, config, curriculum.full_name) for d in documents]
        for r in curriculum.records
    ]
    scores = [
        [
            association_score(fields) if documents[j].extraction_status == "OK" else 0.0
            for j, fields in enumerate(row)
        ]
        for row in comparisons
    ]
    failures = [d for d in documents if d.extraction_status != "OK"]
    chosen, ambiguous = associate(scores, config)
    verdicts, pairs, reserved = [], [], set()
    for i, record in enumerate(curriculum.records):
        diagnostics = [d.code for d in parse_diagnostics if d.record_index == i]
        j = chosen[i]
        candidates = []
        if i in ambiguous:
            reserved.update(ambiguous[i])
            candidates = [
                AssociationCandidate(
                    document_id=documents[k].document_id,
                    association_score=scores[i][k],
                    field_evidences=comparisons[i][k],
                )
                for k in ambiguous[i]
            ]
            status, reason, j = MatchStatus.INCONCLUSIVO, "ASSOCIACAO_AMBIGUA", None
        elif j is None:
            status, reason = MatchStatus.INCONCLUSIVO, "SEM_COMPROVANTE"
            if failures:
                reason = (
                    "DOCUMENTO_ILEGIVEL"
                    if all(d.extraction_status == "UNREADABLE" for d in failures)
                    else "FALHA_EXTRACAO"
                )
                diagnostics.extend(
                    f"EXTRACTION_FAILURE:{d.document_id}:{d.extraction_status}" for d in failures
                )
        else:
            reserved.add(j)
            status, reason = classify(record, documents[j], comparisons[i][j])
            if "INVALID_WORKLOAD_HOURS" in diagnostics and any(
                f.field_name == "carga" and f.outcome != FieldOutcome.NOT_APPLICABLE
                for f in comparisons[i][j]
            ):
                comparisons[i][j] = [
                    f.model_copy(update={"rule_applied": "PARSER_DISCARDED_INVALID_WORKLOAD"})
                    if f.field_name == "carga" and f.outcome != FieldOutcome.NOT_APPLICABLE
                    else f
                    for f in comparisons[i][j]
                ]
                if status == MatchStatus.VALIDADO:
                    status, reason = MatchStatus.INCONCLUSIVO, "EVIDENCIA_INSUFICIENTE"
            pairs.append(
                AssociationPair(
                    record_index=i,
                    record_id=record.record_id,
                    document_id=documents[j].document_id,
                    association_score=scores[i][j],
                )
            )
        placeholders = compare_fields(
            record, ExtractedDocumentRecord(document_id="placeholder"), config, curriculum.full_name
        )
        verdicts.append(
            RecordVerdict(
                record_index=i,
                record_id=record.record_id,
                category=record.category,
                status=status,
                reason_code=reason,
                review_required=status == MatchStatus.INCONCLUSIVO,
                matched_document_id=documents[j].document_id if j is not None else None,
                association_score=scores[i][j] if j is not None else None,
                field_evidences=comparisons[i][j] if j is not None else placeholders,
                ambiguity_candidates=candidates,
                diagnostics=diagnostics,
            )
        )
    orphans = []
    for j, doc in enumerate(documents):
        if j in reserved:
            continue
        best = max(range(len(scores)), key=lambda i: scores[i][j], default=None)
        orphans.append(
            OrphanDocumentReport(
                document_id=doc.document_id,
                best_candidate_record_id=curriculum.records[best].record_id
                if best is not None
                else None,
                best_association_score=scores[best][j] if best is not None else None,
            )
        )
    return MatchingResult(
        mode=config.mode,
        record_verdicts=verdicts,
        association_pairs=pairs,
        orphan_documents=orphans,
    )
