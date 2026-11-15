"""Regressões da política aprovada de instituição nas três categorias de eventos."""

import pytest

from comprova_lattes.matcher import (
    ExtractedDocumentRecord,
    MatcherConfig,
    MatcherThresholds,
    MatchMode,
    match_curriculum,
)
from comprova_lattes.matcher.rules import compare_institution, essential_fields
from comprova_lattes.schemas.lattes import (
    ActivityStatus,
    LattesCategory,
    LattesCurriculum,
    LattesRecord,
    XmlProvenance,
)

EVENT_CATEGORIES = [
    LattesCategory.PARTICIPACAO_EVENTO,
    LattesCategory.APRESENTACAO_TRABALHO,
    LattesCategory.ORGANIZACAO_EVENTO,
]


@pytest.fixture
def config() -> MatcherConfig:
    return MatcherConfig(
        thresholds=MatcherThresholds(
            association=0.35,
            ambiguity_margin=0.02,
            holder_low=0.4,
            holder_high=0.95,
            title_low=0.4,
            title_high=0.95,
            institution_low=0.4,
            institution_high=0.95,
        ),
        acronym_table={
            "UFRA": "Universidade Federal Rural da Amazônia",
            "UFPA": "Universidade Federal do Pará",
        },
        acronym_table_version="policy-test-v1",
    )


def _event_record(category: LattesCategory, **changes) -> LattesRecord:
    defaults = {
        "record_id": "evt-1",
        "category": category,
        "provenance": XmlProvenance(section_tag="S", record_tag="R"),
        "holder_name": "Maria Silva",
        "institution": "Instituto Alpha 0001",
        "institution_acronym": None,
        "title": "Painel de Dados 0001" if category != LattesCategory.PARTICIPACAO_EVENTO else None,
        "event_name": None
        if category == LattesCategory.ORGANIZACAO_EVENTO
        else "Congresso Regional 0001",
        "start_year": 2024,
        "end_year": 2024,
        "status": ActivityStatus.CONCLUIDO,
        "participation_role": {
            LattesCategory.PARTICIPACAO_EVENTO: "PARTICIPANTE",
            LattesCategory.APRESENTACAO_TRABALHO: "APRESENTADOR",
            LattesCategory.ORGANIZACAO_EVENTO: "ORGANIZADOR",
        }[category],
    }
    defaults.update(changes)
    return LattesRecord(**defaults)


def _event_doc(category: LattesCategory, **changes) -> ExtractedDocumentRecord:
    defaults = {
        "document_id": "doc-1",
        "holder_name": "Maria Silva",
        "activity_title": (
            "Painel de Dados 0001" if category != LattesCategory.PARTICIPACAO_EVENTO else None
        ),
        "event_name": None
        if category == LattesCategory.ORGANIZACAO_EVENTO
        else "Congresso Regional 0001",
        "participation_role_raw": {
            LattesCategory.PARTICIPACAO_EVENTO: "Participante",
            LattesCategory.APRESENTACAO_TRABALHO: "Apresentador",
            LattesCategory.ORGANIZACAO_EVENTO: "Organizador",
        }[category],
        "issuer_institution": "Instituto Alpha 0001",
        "issuer_acronym": None,
        "start_year": 2024,
        "end_year": 2024,
        "activity_year": 2024,
    }
    defaults.update(changes)
    return ExtractedDocumentRecord(**defaults)


def _run(config: MatcherConfig, rec: LattesRecord, doc: ExtractedDocumentRecord):
    return match_curriculum(LattesCurriculum(records=[rec]), [doc], config).record_verdicts[0]


def _field(verdict, name: str):
    return next(f for f in verdict.field_evidences if f.field_name == name)


@pytest.mark.parametrize("category", EVENT_CATEGORIES)
def test_declared_institution_is_essential_and_missing_doc_is_inconclusive(config, category):
    rec = _event_record(category)
    assert "instituicao" in essential_fields(rec)

    verdict = _run(config, rec, _event_doc(category, issuer_institution=None, issuer_acronym=None))
    inst = _field(verdict, "instituicao")
    assert inst.outcome == "MISSING_DOCUMENT"
    assert inst.rule_applied == "MISSING_DOCUMENT_VALUE"
    assert verdict.status == "INCONCLUSIVO"
    assert verdict.reason_code == "EVIDENCIA_INSUFICIENTE"
    assert verdict.review_required


@pytest.mark.parametrize("category", EVENT_CATEGORIES)
def test_declared_institution_borderline_is_inconclusive(config, category):
    rec = _event_record(category, institution="Instituto Alpha 0001")
    verdict = _run(config, rec, _event_doc(category, issuer_institution="Instituto Alpha 9999"))
    inst = _field(verdict, "instituicao")
    assert inst.outcome == "INCONCLUSIVE_BORDERLINE"
    assert inst.rule_applied == "SIMILARITY"
    assert verdict.status == "INCONCLUSIVO"
    assert verdict.reason_code == "EVIDENCIA_INSUFICIENTE"


@pytest.mark.parametrize("category", EVENT_CATEGORIES)
def test_declared_institution_unknown_isolated_acronym_in_doc_is_inconclusive(config, category):
    rec = _event_record(category, institution="Instituto Alpha 0001")
    verdict = _run(
        config,
        rec,
        _event_doc(category, issuer_institution=None, issuer_acronym="SIGLAUNK"),
    )
    inst = _field(verdict, "instituicao")
    assert inst.outcome == "INCONCLUSIVE_BORDERLINE"
    assert inst.rule_applied == "UNKNOWN_INSTITUTION_ACRONYM"
    assert verdict.status == "INCONCLUSIVO"
    assert verdict.reason_code == "EVIDENCIA_INSUFICIENTE"


@pytest.mark.parametrize("category", EVENT_CATEGORIES)
def test_declared_acronym_only_in_xml_unknown_without_doc_relation_is_inconclusive(
    config, category
):
    rec = _event_record(category, institution=None, institution_acronym="SIGLAUNK")
    assert "instituicao" in essential_fields(rec)

    verdict = _run(
        config, rec, _event_doc(category, issuer_institution="Instituto Desconhecido 0001")
    )
    inst = _field(verdict, "instituicao")
    assert inst.outcome == "INCONCLUSIVE_BORDERLINE"
    assert inst.rule_applied == "UNKNOWN_INSTITUTION_ACRONYM"
    assert verdict.status == "INCONCLUSIVO"

    absent_doc = _run(
        config, rec, _event_doc(category, issuer_institution=None, issuer_acronym=None)
    )
    absent_inst = _field(absent_doc, "instituicao")
    assert absent_inst.outcome == "MISSING_DOCUMENT"
    assert absent_inst.rule_applied == "MISSING_DOCUMENT_VALUE"
    assert absent_doc.status == "INCONCLUSIVO"


@pytest.mark.parametrize("category", EVENT_CATEGORIES)
def test_declared_institution_factual_conflict_is_divergente(config, category):
    rec = _event_record(category, institution="UFRA")
    verdict = _run(config, rec, _event_doc(category, issuer_institution="UFPA"))
    inst = _field(verdict, "instituicao")
    assert inst.outcome == "CONFLICT"
    assert inst.rule_applied == "DISTINCT_KNOWN_INSTITUTIONS"
    assert verdict.status == "DIVERGENTE"
    assert verdict.reason_code == "CONFLITO_ATRIBUTO_DECISIVO"

    text_conflict = _run(
        config,
        _event_record(category, institution="Instituto Alpha 0001"),
        _event_doc(category, issuer_institution="Organizacao ZZZ"),
    )
    assert _field(text_conflict, "instituicao").outcome == "CONFLICT"
    assert text_conflict.status == "DIVERGENTE"


@pytest.mark.parametrize("category", EVENT_CATEGORIES)
def test_declared_institution_ad014_local_and_dict_fallback_validate(config, category):
    no_dict = config.model_copy(update={"acronym_table": {}})
    rec_acronym = _event_record(category, institution=None, institution_acronym="IF205")
    doc_ad014 = _event_doc(
        category,
        issuer_institution="Instituto Fictício 205",
        issuer_acronym="IF205",
        issuer_name_acronym_evidence="Instituto Fictício 205 (IF205)",
    )
    verdict_local = _run(no_dict, rec_acronym, doc_ad014)
    inst_local = _field(verdict_local, "instituicao")
    assert inst_local.outcome == "MATCH"
    assert inst_local.rule_applied == "DOCUMENT_ACRONYM_EQUIVALENCE"
    assert inst_local.document_evidence == "Instituto Fictício 205 (IF205)"
    assert verdict_local.status == "VALIDADO"

    rec_ufra = _event_record(category, institution=None, institution_acronym="UFRA")
    doc_ufra = _event_doc(
        category,
        issuer_institution="Universidade Federal Rural da Amazônia",
        issuer_acronym=None,
    )
    verdict_dict = _run(config, rec_ufra, doc_ufra)
    inst_dict = _field(verdict_dict, "instituicao")
    assert inst_dict.outcome == "MATCH"
    assert inst_dict.rule_applied == "ACRONYM_EQUIVALENCE"
    assert verdict_dict.status == "VALIDADO"


@pytest.mark.parametrize("category", EVENT_CATEGORIES)
@pytest.mark.parametrize(
    "doc_changes,expected_outcome,expected_rule",
    [
        ({"issuer_institution": None, "issuer_acronym": None}, "MISSING_BOTH", "MISSING_BOTH_VALUE"),
        (
            {"issuer_institution": "Instituto Emitente Qualquer", "issuer_acronym": None},
            "MISSING_LATTES",
            "MISSING_LATTES_VALUE",
        ),
        (
            {"issuer_institution": None, "issuer_acronym": "SIGLAUNK"},
            "MISSING_LATTES",
            "MISSING_LATTES_VALUE",
        ),
    ],
)
def test_absent_xml_institution_does_not_block_validado_or_invent_conflict(
    config, category, doc_changes, expected_outcome, expected_rule
):
    rec = _event_record(category, institution=None, institution_acronym=None)
    assert "instituicao" not in essential_fields(rec)

    verdict = _run(config, rec, _event_doc(category, **doc_changes))
    inst = _field(verdict, "instituicao")
    assert inst.outcome == expected_outcome
    assert inst.rule_applied == expected_rule
    assert verdict.status == "VALIDADO"
    assert verdict.reason_code == "VALIDADO_CORRESPONDENCIA_COMPLETA"


@pytest.mark.parametrize("mode", list(MatchMode))
def test_compare_institution_left_none_unknown_right_never_invents_conflict(config, mode):
    cfg = config.model_copy(update={"mode": mode})
    rec = _event_record(LattesCategory.PARTICIPACAO_EVENTO, institution=None, institution_acronym=None)
    for doc_kwargs in (
        {"issuer_institution": "Entidade Desconhecida", "issuer_acronym": None},
        {"issuer_institution": None, "issuer_acronym": "XYZUNK"},
    ):
        ev = compare_institution(rec, _event_doc(rec.category, **doc_kwargs), cfg)
        assert ev.outcome == "MISSING_LATTES"
        assert ev.rule_applied == "MISSING_LATTES_VALUE"


@pytest.mark.parametrize("category", EVENT_CATEGORIES)
@pytest.mark.parametrize(
    "inst_doc_changes",
    [
        {"issuer_institution": None, "issuer_acronym": None},
        {"issuer_institution": "Instituto Alpha 9999", "issuer_acronym": None},
        {"issuer_institution": None, "issuer_acronym": "SIGLAUNK"},
    ],
)
def test_decisive_conflict_in_another_field_overrides_institution_uncertainty(
    config, category, inst_doc_changes
):
    rec = _event_record(category, institution="Instituto Alpha 0001")
    doc = _event_doc(category, end_year=2031, activity_year=2031, **inst_doc_changes)
    verdict = _run(config, rec, doc)
    assert _field(verdict, "instituicao").outcome in {"MISSING_DOCUMENT", "INCONCLUSIVE_BORDERLINE"}
    assert _field(verdict, "ano").outcome == "CONFLICT"
    assert verdict.status == "DIVERGENTE"
    assert verdict.reason_code == "CONFLITO_ATRIBUTO_DECISIVO"


def test_trim_normalize_empty_punctuation_for_event_institution(config):
    punct_only = _event_record(
        LattesCategory.PARTICIPACAO_EVENTO, institution="---", institution_acronym=None
    )
    assert "instituicao" not in essential_fields(punct_only)
    verdict_punct = _run(
        config,
        punct_only,
        _event_doc(
            LattesCategory.PARTICIPACAO_EVENTO, issuer_institution=None, issuer_acronym="SIGLAUNK"
        ),
    )
    assert _field(verdict_punct, "instituicao").outcome == "MISSING_LATTES"
    assert verdict_punct.status == "VALIDADO"

    punct_with_acronym = _event_record(
        LattesCategory.ORGANIZACAO_EVENTO, institution="---", institution_acronym="UFRA"
    )
    assert "instituicao" in essential_fields(punct_with_acronym)
    verdict_fallback = _run(
        config,
        punct_with_acronym,
        _event_doc(
            LattesCategory.ORGANIZACAO_EVENTO,
            issuer_institution="Universidade Federal Rural da Amazônia",
        ),
    )
    assert _field(verdict_fallback, "instituicao").outcome == "MATCH"
    assert verdict_fallback.status == "VALIDADO"

    ws_constructed = _event_record(LattesCategory.APRESENTACAO_TRABALHO).model_copy(
        update={"institution": "   ", "institution_acronym": None}
    )
    assert "instituicao" not in essential_fields(ws_constructed)
    assert (
        compare_institution(
            ws_constructed,
            _event_doc(
                LattesCategory.APRESENTACAO_TRABALHO,
                issuer_institution=None,
                issuer_acronym="SIGLAUNK",
            ),
            config,
        ).outcome
        == "MISSING_LATTES"
    )
