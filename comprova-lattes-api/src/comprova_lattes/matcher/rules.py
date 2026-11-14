"""Etapa 2: evidências por atributo e precedência da tabela aprovada."""

from decimal import MAX_EMAX, MIN_EMIN, localcontext

from comprova_lattes.schemas.lattes import ActivityStatus, LattesCategory, LattesRecord

from .models import ExtractedDocumentRecord, FieldEvidence, FieldOutcome, MatcherConfig, MatchMode
from .text import acronym_identity, normalize_role, normalize_text, text_similarity

O = FieldOutcome
EVENT_CATEGORIES = {
    LattesCategory.PARTICIPACAO_EVENTO,
    LattesCategory.APRESENTACAO_TRABALHO,
    LattesCategory.ORGANIZACAO_EVENTO,
}


def evidence(
    name: str, left: object, right: object, outcome: FieldOutcome, rule: str, **details: object
) -> FieldEvidence:
    return FieldEvidence(
        field_name=name,
        lattes_raw=left,
        document_raw=right,
        outcome=outcome,
        rule_applied=rule,
        justification_pt={
            O.MATCH: "Atributo comprovado pela regra indicada.",
            O.CONFLICT: "Valores presentes contradizem o fato declarado.",
            O.INCONCLUSIVE_BORDERLINE: "Evidência insuficiente para confirmar ou contradizer.",
            O.MISSING_LATTES: "Valor ausente no currículo.",
            O.MISSING_DOCUMENT: "Detalhe declarado sem comprovação no documento.",
            O.MISSING_BOTH: "Valor ausente em ambas as fontes.",
            O.NOT_APPLICABLE: "Atributo não aplicável à estrutura deste registro.",
        }[outcome],
        **details,
    )


def missing(left: object, right: object) -> FieldOutcome | None:
    if left is None and right is None:
        return O.MISSING_BOTH
    if left is None:
        return O.MISSING_LATTES
    if right is None:
        return O.MISSING_DOCUMENT
    return None


def compare_text(
    name: str, left: str | None, right: str | None, config: MatcherConfig
) -> FieldEvidence:
    a, b = normalize_text(left), normalize_text(right)
    absent = missing(a, b)
    if absent:
        return evidence(name, left, right, absent, f"{absent.value}_VALUE")
    if config.mode == MatchMode.BASELINE_EXACT:
        score = float(left.strip() == right.strip())
        rule = "EXACT_MATCH" if score else "EXACT_CONFLICT"
    elif a == b:
        score, rule = 1.0, "NORMALIZED_MATCH"
    elif config.mode == MatchMode.BASELINE_NORMALIZED:
        score, rule = 0.0, "NORMALIZED_CONFLICT"
    elif name == "instituicao" and (
        acronym_identity(a, config.acronym_table) == acronym_identity(b, config.acronym_table)
    ):
        score, rule = 1.0, "ACRONYM_EQUIVALENCE"
    else:
        score, rule = text_similarity(a, b, config.text_metric), "SIMILARITY"
    prefix = {"titular": "holder", "instituicao": "institution"}.get(name, "title")
    high = getattr(config.thresholds, f"{prefix}_high")
    low = getattr(config.thresholds, f"{prefix}_low")
    if config.mode != MatchMode.PROPOSED:
        outcome = O.MATCH if score == 1 else O.CONFLICT
    else:
        outcome = (
            O.MATCH if score >= high else (O.CONFLICT if score < low else O.INCONCLUSIVE_BORDERLINE)
        )
    return evidence(
        name,
        left,
        right,
        outcome,
        rule,
        similarity_score=score,
        lattes_normalized=a,
        document_normalized=b,
    )


def compare_role(
    record: LattesRecord, doc: ExtractedDocumentRecord, config: MatcherConfig
) -> FieldEvidence:
    left = (
        record.participation_role or record.participation_type_raw or record.participation_form_raw
    )
    left = left or {
        LattesCategory.APRESENTACAO_TRABALHO: "APRESENTADOR",
        LattesCategory.ORGANIZACAO_EVENTO: "ORGANIZADOR",
    }.get(record.category)
    right = doc.participation_role_raw
    absent = missing(normalize_text(left), normalize_text(right))
    if absent:
        return evidence("papel_participacao", left, right, absent, absent.value)
    if config.mode != MatchMode.PROPOSED:
        result = compare_text("papel_participacao", left, right, config)
        return (
            result
            if result.outcome == O.MATCH
            else result.model_copy(
                update={
                    "outcome": O.INCONCLUSIVE_BORDERLINE,
                    "rule_applied": "ROLE_UNPROVEN",
                    "justification_pt": "Papéis distintos podem coexistir no mesmo evento.",
                }
            )
        )
    a, b = normalize_role(left), normalize_role(right)
    compatible = a == b if a and b else normalize_text(left) == normalize_text(right)
    return evidence(
        "papel_participacao",
        left,
        right,
        O.MATCH if compatible else O.INCONCLUSIVE_BORDERLINE,
        "ROLE_COMPATIBLE" if compatible else "ROLE_COEXISTENCE",
        lattes_normalized=a,
        document_normalized=b,
    )


def compare_institution(
    record: LattesRecord, doc: ExtractedDocumentRecord, config: MatcherConfig
) -> FieldEvidence:
    left = record.institution or record.institution_acronym
    right = doc.issuer_institution or doc.issuer_acronym
    result = compare_text("instituicao", left, right, config)
    if config.mode != MatchMode.PROPOSED:
        return result
    known = {normalize_text(value) for value in config.acronym_table.values()}
    a = {
        acronym_identity(value, config.acronym_table)
        for value in (record.institution, record.institution_acronym)
        if normalize_text(value)
    }
    b = {
        acronym_identity(value, config.acronym_table)
        for value in (doc.issuer_institution, doc.issuer_acronym)
        if normalize_text(value)
    }
    if a & b & known:
        return evidence(
            "instituicao",
            left,
            right,
            O.MATCH,
            "ACRONYM_EQUIVALENCE",
            similarity_score=1.0,
            lattes_normalized=normalize_text(left),
            document_normalized=normalize_text(right),
        )
    if a & known and b & known and not a & b:
        return evidence(
            "instituicao",
            left,
            right,
            O.CONFLICT,
            "DISTINCT_KNOWN_INSTITUTIONS",
            similarity_score=0.0,
            lattes_normalized=normalize_text(left),
            document_normalized=normalize_text(right),
        )
    return result


def compare_year(record: LattesRecord, doc: ExtractedDocumentRecord) -> FieldEvidence:
    left = record.end_year if record.end_year is not None else record.start_year
    right = doc.activity_year
    if right is None:
        right = doc.end_year if doc.end_year is not None else doc.start_year
    absent = missing(left, right)
    if absent:
        return evidence("ano", left, right, absent, absent.value)
    ongoing = record.status == ActivityStatus.EM_ANDAMENTO and record.start_year is not None
    matches = right >= record.start_year if ongoing else left == right
    if (
        record.start_year is not None
        and doc.start_year is not None
        and record.start_year != doc.start_year
    ):
        return evidence("ano", record.start_year, doc.start_year, O.CONFLICT, "START_YEAR_EXACT")
    return evidence(
        "ano",
        left,
        right,
        O.MATCH if matches else O.CONFLICT,
        "YEAR_INTERVAL" if ongoing else "YEAR_EXACT",
    )


def workload_applicable(record: LattesRecord) -> bool:
    if record.category in EVENT_CATEGORIES:
        return False
    if record.category == LattesCategory.FORMACAO_COMPLEMENTAR:
        return True
    return normalize_text(record.subtype) in {
        "especializacao",
        "aperfeicoamento",
        "residencia medica",
    }


def compare_workload(record: LattesRecord, doc: ExtractedDocumentRecord) -> FieldEvidence:
    left, right = record.workload_hours, doc.workload_hours
    if not workload_applicable(record):
        return evidence("carga", left, right, O.NOT_APPLICABLE, "STRUCTURAL_NOT_APPLICABLE")
    absent = missing(left, right)
    if absent:
        return evidence("carga", left, right, absent, absent.value)
    # Align all coefficient digits, independent of the caller's Decimal context.
    exponent = min(left.as_tuple().exponent, right.as_tuple().exponent)
    with localcontext() as context:
        context.prec = max(left.adjusted(), right.adjusted()) - exponent + 2
        context.Emax, context.Emin = MAX_EMAX, MIN_EMIN
        difference = (left - right).copy_abs()
    return evidence(
        "carga",
        left,
        right,
        O.MATCH if left == right else O.CONFLICT,
        "WORKLOAD_DECIMAL_MATCH" if not difference else "WORKLOAD_DECIMAL_CONFLICT",
        numeric_difference=difference,
    )


def compare_fields(
    record: LattesRecord,
    doc: ExtractedDocumentRecord,
    config: MatcherConfig,
    holder_name: str | None = None,
) -> list[FieldEvidence]:
    fields = [
        compare_text("titular", record.holder_name or holder_name, doc.holder_name, config),
        compare_text("titulo", record.title, doc.activity_title, config),
        compare_institution(record, doc, config),
        compare_year(record, doc),
        compare_workload(record, doc),
    ]
    if record.category in EVENT_CATEGORIES:
        fields.extend(
            [
                evidence(
                    "evento", record.event_name, doc.event_name,
                    O.NOT_APPLICABLE, "STRUCTURAL_NOT_APPLICABLE",
                )
                if record.category == LattesCategory.ORGANIZACAO_EVENTO
                and record.event_name is None
                else compare_text("evento", record.event_name, doc.event_name, config),
                compare_role(record, doc, config),
            ]
        )
    else:
        fields.extend(
            evidence(name, None, None, O.NOT_APPLICABLE, "CATEGORY_NOT_APPLICABLE")
            for name in ("evento", "papel_participacao")
        )
    return fields


def essential_fields(record: LattesRecord) -> set[str]:
    required = {"titular"}
    if record.category not in EVENT_CATEGORIES:
        required.update({"titulo", "instituicao"})
    else:
        required.add(
            "titulo"
            if record.category == LattesCategory.ORGANIZACAO_EVENTO and record.event_name is None
            else "evento"
        )
        if record.category != LattesCategory.PARTICIPACAO_EVENTO or (
            record.participation_role
            or record.participation_type_raw
            or record.participation_form_raw
        ):
            required.add("papel_participacao")
        if record.title:
            required.add("titulo")
    if record.start_year is not None or record.end_year is not None:
        required.add("ano")
    if workload_applicable(record) and record.workload_hours is not None:
        required.add("carga")
    return required
