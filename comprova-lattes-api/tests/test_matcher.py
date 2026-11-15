"""Casos sintéticos da tabela aprovada, sem banco ou extrator."""

from decimal import Decimal, localcontext
from itertools import permutations
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from comprova_lattes.matcher import (
    ExtractedDocumentRecord,
    MatcherConfig,
    MatcherThresholds,
    MatchingResult,
    MatchMode,
    match_curriculum,
)
from comprova_lattes.matcher.association import _optimal, associate
from comprova_lattes.matcher.engine import classify
from comprova_lattes.matcher.rules import compare_fields, compare_institution, essential_fields
from comprova_lattes.schemas.lattes import LattesCategory, LattesCurriculum, LattesRecord


@pytest.fixture
def config():
    # Valores apenas dos testes; não constituem calibração científica.
    return MatcherConfig(
        thresholds=MatcherThresholds(
            association=0.55,
            ambiguity_margin=0.02,
            holder_low=0.5,
            holder_high=0.9,
            title_low=0.4,
            title_high=0.9,
            institution_low=0.4,
            institution_high=0.9,
        ),
        acronym_table={"UFRA": "Universidade Federal Rural da Amazônia"},
        acronym_table_version="synthetic-v1",
    )


def test_document_issuer_relation_is_local_and_auditable(config):
    config = config.model_copy(update={"acronym_table": {}})
    curricular = record(institution="IF205")
    doc = document(
        issuer_institution="Instituto Fictício 205", issuer_acronym="IF205",
        issuer_name_acronym_evidence="Instituto Fictício 205 (IF205)",
    )
    result = compare_institution(curricular, doc, config)
    assert result.outcome == "MATCH"
    assert result.rule_applied == "DOCUMENT_ACRONYM_EQUIVALENCE"
    assert result.document_evidence == doc.issuer_name_acronym_evidence
    assert config.acronym_table == {}
    without_relation = doc.model_copy(update={"issuer_name_acronym_evidence": None})
    assert compare_institution(curricular, without_relation, config).outcome != "MATCH"
    assert compare_institution(
        curricular, doc, config.model_copy(update={"mode": MatchMode.BASELINE_NORMALIZED})
    ).rule_applied != "DOCUMENT_ACRONYM_EQUIVALENCE"


def test_unknown_acronym_alone_is_inconclusive(config):
    result = compare_institution(
        record(institution="Instituto Fictício 205"),
        document(issuer_institution=None, issuer_acronym="IF205"), config,
    )
    assert result.outcome == "INCONCLUSIVE_BORDERLINE"
    assert result.rule_applied == "UNKNOWN_INSTITUTION_ACRONYM"


def test_absent_xml_institution_with_unknown_doc_acronym_keeps_missing_lattes(config):
    result = compare_institution(
        record("PARTICIPACAO_EVENTO", institution=None, institution_acronym=None),
        document(issuer_institution=None, issuer_acronym="IF205"),
        config,
    )
    assert result.outcome == "MISSING_LATTES"
    assert result.rule_applied == "MISSING_LATTES_VALUE"


def test_document_relation_does_not_override_distinct_declared_name(config):
    result = compare_institution(
        record(institution="Outra Universidade", institution_acronym="IF205"),
        document(issuer_institution="Instituto Fictício 205", issuer_acronym="IF205",
                 issuer_name_acronym_evidence="Instituto Fictício 205 (IF205)"), config,
    )
    assert result.outcome != "MATCH"


def record(category="FORMACAO_COMPLEMENTAR", **changes):
    values = {
        "category": category,
        "record_id": "r1",
        "title": "Ciência de Dados",
        "holder_name": "Maria Silva",
        "institution": "UFRA",
        "end_year": 2024,
        "workload_hours": "40",
        "subtype": "CURSO",
        "provenance": {"section_tag": "S", "record_tag": "R"},
    }
    if category in {"PARTICIPACAO_EVENTO", "APRESENTACAO_TRABALHO", "ORGANIZACAO_EVENTO"}:
        values.update(event_name="Congresso de Ciência", title=None, workload_hours=None)
    if category == "FORMACAO_ACADEMICA":
        values.update(subtype="GRADUACAO", workload_hours=None)
    values.update(changes)
    return LattesRecord(**values)


def document(**changes):
    values = {
        "document_id": "d1",
        "activity_title": "Ciência de Dados",
        "holder_name": "Maria Silva",
        "issuer_institution": "UFRA",
        "end_year": 2024,
        "workload_hours": "40",
    }
    values.update(changes)
    return ExtractedDocumentRecord(**values)


def run(config, rec=None, doc=None):
    return match_curriculum(
        LattesCurriculum(records=[rec or record()]), [doc or document()], config
    ).record_verdicts[0]


@pytest.mark.parametrize("category", list(LattesCategory))
def test_five_categories_validated(config, category):
    rec = record(category)
    role = {"APRESENTACAO_TRABALHO": "Apresentador", "ORGANIZACAO_EVENTO": "Organizador"}.get(
        category
    )
    result = run(config, rec, document(event_name=rec.event_name, participation_role_raw=role))
    assert result.status == "VALIDADO"
    assert len(result.field_evidences) == 7
    assert not result.review_required


@pytest.mark.parametrize("event_name", [None, "Congresso de Ciencia"])
def test_organization_m1_title_without_event_name(config, event_name):
    rec = record("ORGANIZACAO_EVENTO", event_name=None, title="Congresso de Ciencia")
    doc = document(
        activity_title=rec.title, event_name=event_name, participation_role_raw="Organizador"
    )
    assert "titulo" in essential_fields(rec)
    assert "evento" not in essential_fields(rec)
    assert "titulo" in essential_fields(rec.model_copy(update={"title": None}))
    result = run(config, rec, doc)
    assert result.status == "VALIDADO"
    event = next(f for f in result.field_evidences if f.field_name == "evento")
    assert event.outcome == "NOT_APPLICABLE"
    assert event.rule_applied == "STRUCTURAL_NOT_APPLICABLE"
    assert event.lattes_raw is None
    assert event.document_raw == event_name
    missing_title = run(config, rec, doc.model_copy(update={"activity_title": None}))
    assert missing_title.status == "INCONCLUSIVO"


@pytest.mark.parametrize(
    "changes,field",
    [
        ({"holder_name": "Carlos Souza"}, "titular"),
        ({"activity_title": "Zoologia Tropical"}, "titulo"),
        ({"issuer_institution": "Instituto ZZZ"}, "instituicao"),
        ({"end_year": 2021}, "ano"),
        ({"workload_hours": "45"}, "carga"),
    ],
)
def test_factual_conflicts_after_association(config, changes, field):
    result = run(config, doc=document(**changes))
    assert result.matched_document_id == "d1"
    assert result.status == "DIVERGENTE"
    assert next(f for f in result.field_evidences if f.field_name == field).outcome == "CONFLICT"


def test_conflict_precedes_missing_essential(config):
    result = run(config, doc=document(holder_name=None, workload_hours="45"))
    assert result.status == "DIVERGENTE"


@pytest.mark.parametrize(
    "hours,difference,status",
    [
        ("40.0", "0", "VALIDADO"),
        ("45", "5", "DIVERGENTE"),
        ("400", "360", "DIVERGENTE"),
        ("40.000000000000001", "0.000000000000001", "DIVERGENTE"),
    ],
)
def test_decimal_exact(config, hours, difference, status):
    result = run(config, doc=document(workload_hours=hours))
    field = next(f for f in result.field_evidences if f.field_name == "carga")
    assert field.numeric_difference == Decimal(difference)
    assert result.status == status


@pytest.mark.parametrize(
    "left,right,expected",
    [
        ("1E-100", "0", "1E-100"),
        ("1E100", "0", "1E100"),
        ("40", "40.000000000000000000000000000001", "1E-30"),
        ("100000000000000000000000000001", "1", "1E29"),
        ("40", "40.0", "0"),
    ],
)
def test_workload_independent_of_decimal_context(config, left, right, expected):
    with localcontext() as context:
        context.prec, context.Emin, context.Emax = 3, -9, 9
        result = run(config, record(workload_hours=left), document(workload_hours=right))
        assert (context.prec, context.Emin, context.Emax) == (3, -9, 9)
    field = next(f for f in result.field_evidences if f.field_name == "carga")
    assert field.numeric_difference == Decimal(expected)
    assert field.outcome == ("MATCH" if Decimal(left) == Decimal(right) else "CONFLICT")
    assert MatchingResult.model_validate_json(
        MatchingResult(
            mode=config.mode, record_verdicts=[result], orphan_documents=[], association_pairs=[]
        ).model_dump_json()
    ).record_verdicts == [result]


@pytest.mark.parametrize("mode", list(MatchMode))
@pytest.mark.parametrize("category", ["FORMACAO_COMPLEMENTAR", "PARTICIPACAO_EVENTO"])
def test_punctuation_is_not_association_anchor(config, mode, category):
    rec = record(category, title="!!!", event_name="..." if "EVENTO" in category else None)
    doc = document(activity_title="???", event_name="---")
    result = match_curriculum(
        LattesCurriculum(records=[rec]), [doc], config.model_copy(update={"mode": mode})
    )
    assert result.record_verdicts[0].reason_code == "SEM_COMPROVANTE"
    assert not result.association_pairs
    assert len(result.orphan_documents) == 1


@pytest.mark.parametrize("status", ["CONCLUIDO", "EM_ANDAMENTO"])
@pytest.mark.parametrize("activity_year", [None, 2024])
def test_start_year_conflict_even_with_matching_end(config, status, activity_year):
    result = run(
        config,
        record(start_year=2020, status=status),
        document(start_year=2021, activity_year=activity_year),
    )
    field = next(f for f in result.field_evidences if f.field_name == "ano")
    assert result.status == "DIVERGENTE"
    assert (field.lattes_raw, field.document_raw) == (2020, 2021)
    assert field.rule_applied == "START_YEAR_EXACT"


@pytest.mark.parametrize("start_year", [None, 2020])
def test_start_year_equal_or_absent_preserves_end_year_rule(config, start_year):
    assert (
        run(config, record(start_year=2020), document(start_year=start_year)).status == "VALIDADO"
    )


@pytest.mark.parametrize("status", ["UNREADABLE", "INVALID_JSON", "API_ERROR"])
def test_failed_partial_entities_cannot_take_valid_pair(config, status):
    result = match_curriculum(
        LattesCurriculum(records=[record()]),
        [document(extraction_status=status), document(document_id="ok")],
        config,
    )
    assert result.record_verdicts[0].status == "VALIDADO"
    assert result.record_verdicts[0].matched_document_id == "ok"
    assert [d.document_id for d in result.orphan_documents] == ["d1"]


@pytest.mark.parametrize("left,right", [("!!!", "Curso"), ("Curso", "!!!")])
def test_one_sided_punctuation_does_not_anchor(config, left, right):
    result = match_curriculum(
        LattesCurriculum(records=[record(title=left)]),
        [document(activity_title=right)],
        config,
    )
    assert result.record_verdicts[0].reason_code == "SEM_COMPROVANTE"
    assert not result.association_pairs


def test_valid_event_anchor_survives_punctuation_title(config):
    result = run(
        config,
        record("PARTICIPACAO_EVENTO", title="!!!"),
        document(activity_title="???", event_name="Congresso de Ciência"),
    )
    assert result.matched_document_id == "d1"
    assert result.status == "INCONCLUSIVO"


@pytest.mark.parametrize(
    "field", ["holder_name", "activity_title", "issuer_institution", "end_year", "workload_hours"]
)
def test_missing_essential_is_inconclusive(config, field):
    result = run(config, doc=document(**{field: None}))
    assert result.status == "INCONCLUSIVO"
    assert result.review_required


@pytest.mark.parametrize(
    "category", ["PARTICIPACAO_EVENTO", "APRESENTACAO_TRABALHO", "ORGANIZACAO_EVENTO"]
)
def test_declared_title_omitted(config, category):
    rec = record(category, title="Palestra sobre Dados", participation_role="PALESTRANTE")
    result = run(
        config,
        rec,
        document(
            event_name=rec.event_name, activity_title=None, participation_role_raw="Palestrante"
        ),
    )
    assert result.status == "INCONCLUSIVO"
    assert (
        next(f for f in result.field_evidences if f.field_name == "titulo").outcome
        == "MISSING_DOCUMENT"
    )


@pytest.mark.parametrize("category", ["APRESENTACAO_TRABALHO", "ORGANIZACAO_EVENTO"])
@pytest.mark.parametrize("role", ["Ouvinte", "Participante", "Debatedor", None])
def test_role_does_not_prove_presentation_or_organization(config, category, role):
    rec = record(category)
    result = run(config, rec, document(event_name=rec.event_name, participation_role_raw=role))
    assert result.status == "INCONCLUSIVO"
    assert all(f.outcome != "CONFLICT" for f in result.field_evidences)


def test_unknown_role_equal_and_raw_preserved(config):
    rec = record("PARTICIPACAO_EVENTO", participation_type_raw="Debatedor de Mesa")
    result = run(
        config, rec, document(event_name=rec.event_name, participation_role_raw="DEBATEDOR DE MESA")
    )
    role = next(f for f in result.field_evidences if f.field_name == "papel_participacao")
    assert result.status == "VALIDADO"
    assert role.lattes_raw == "Debatedor de Mesa"


def test_document_only_role_does_not_fabricate_xml_role(config):
    rec = record("PARTICIPACAO_EVENTO", nature_raw="Conferencia")
    result = run(
        config, rec, document(event_name=rec.event_name, participation_role_raw="Palestrante")
    )
    assert (
        next(f for f in result.field_evidences if f.field_name == "papel_participacao").outcome
        == "MISSING_LATTES"
    )


@pytest.mark.parametrize(
    "category,subtype",
    [
        ("FORMACAO_ACADEMICA", "GRADUACAO"),
        ("FORMACAO_ACADEMICA", "MESTRADO"),
        ("FORMACAO_ACADEMICA", "DOUTORADO"),
        ("PARTICIPACAO_EVENTO", "CONGRESSO"),
        ("APRESENTACAO_TRABALHO", "CONFERENCIA"),
        ("ORGANIZACAO_EVENTO", "CONGRESSO"),
    ],
)
def test_structural_workload_not_applicable(config, category, subtype):
    rec = record(category, subtype=subtype)
    fields = compare_fields(rec, document(workload_hours="999"), config)
    assert next(f for f in fields if f.field_name == "carga").outcome == "NOT_APPLICABLE"


@pytest.mark.parametrize(
    "year,status", [(2020, "DIVERGENTE"), (2022, "VALIDADO"), (2030, "VALIDADO")]
)
def test_ongoing_year_interval(config, year, status):
    rec = record(start_year=2022, end_year=None, status="EM_ANDAMENTO")
    assert run(config, rec, document(end_year=year)).status == status


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("PROPOSED", "VALIDADO"),
        ("BASELINE_NORMALIZED", "VALIDADO"),
        ("BASELINE_EXACT", "DIVERGENTE"),
    ],
)
def test_baselines_normalization(config, mode, expected):
    cfg = config.model_copy(update={"mode": MatchMode(mode)})
    assert run(cfg, doc=document(activity_title="CIENCIA DE DADOS")).status == expected


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("PROPOSED", "VALIDADO"),
        ("BASELINE_NORMALIZED", "DIVERGENTE"),
        ("BASELINE_EXACT", "DIVERGENTE"),
    ],
)
def test_acronyms_only_in_proposed(config, mode, expected):
    cfg = config.model_copy(update={"mode": MatchMode(mode)})
    result = run(cfg, doc=document(issuer_institution="Universidade Federal Rural da Amazônia"))
    assert result.status == expected


def test_no_documents_and_orphans(config):
    result = match_curriculum(LattesCurriculum(records=[record()]), [], config)
    assert result.record_verdicts[0].reason_code == "SEM_COMPROVANTE"
    assert len(result.record_verdicts[0].field_evidences) == 7
    result = match_curriculum(LattesCurriculum(), [document()], config)
    assert not result.record_verdicts
    assert result.orphan_documents[0].reason_code == "DOCUMENTO_NAO_ASSOCIADO"


def test_unrelated_document_orphan(config):
    result = match_curriculum(
        LattesCurriculum(records=[record()]),
        [
            document(
                holder_name="ZZZZ", activity_title="ZZZZ", issuer_institution="ZZZZ", end_year=1900
            )
        ],
        config,
    )
    assert result.record_verdicts[0].reason_code == "SEM_COMPROVANTE"
    assert len(result.orphan_documents) == 1


def test_duplicate_documents_ambiguous(config):
    result = match_curriculum(
        LattesCurriculum(records=[record()]), [document(), document(document_id="d2")], config
    )
    verdict = result.record_verdicts[0]
    assert verdict.reason_code == "ASSOCIACAO_AMBIGUA"
    assert len(verdict.ambiguity_candidates) == 2
    assert all(c.field_evidences for c in verdict.ambiguity_candidates)
    assert not result.association_pairs
    assert not result.orphan_documents


def test_competing_records_ambiguous(config):
    result = match_curriculum(
        LattesCurriculum(records=[record(), record(record_id="r2")]), [document()], config
    )
    assert all(v.reason_code == "ASSOCIACAO_AMBIGUA" for v in result.record_verdicts)
    assert not result.association_pairs


def test_global_assignment_beats_greedy(config):
    cfg = config.model_copy(
        update={"thresholds": config.thresholds.model_copy(update={"association": 0.1})}
    )
    chosen, ambiguous = associate([[0.9, 0.8], [0.85, 0.1]], cfg)
    assert chosen == [1, 0]
    assert not ambiguous


@pytest.mark.parametrize("delta,ambiguous", [(0.01, True), (0.03, False)])
def test_ambiguity_margin(config, delta, ambiguous):
    _, result = associate([[1, 1 - delta]], config)
    assert bool(result) == ambiguous


def test_assignment_matches_brute_force():
    scores = [[0.9, 0.8, 0.1], [0.85, 0.2, 0.7], [0.3, 0.6, 0.9]]
    expected = max(sum(scores[i][j] for i, j in enumerate(p)) for p in permutations(range(3)))
    total, assignment = _optimal(scores, 0.1)
    assert total == pytest.approx(expected)
    assert len(set(assignment)) == 3


def test_metadata_ignored_and_input_unchanged(config):
    curriculum = LattesCurriculum(full_name="Maria Silva", records=[record(holder_name=None)])
    doc = document()
    original = curriculum.model_dump_json()
    a = match_curriculum(curriculum, [doc], config)
    b = match_curriculum(
        curriculum,
        [
            doc.model_copy(
                update={
                    "confianca_extracao": 0,
                    "categoria_sugerida": "ZZZ",
                    "raw_metadata": {"confianca_extracao": 1, "categoria_sugerida": "ZZZ"},
                }
            )
        ],
        config,
    )
    assert a == b
    assert original == curriculum.model_dump_json()
    assert MatchingResult.model_validate_json(a.model_dump_json()) == a


@pytest.mark.parametrize("status", ["UNREADABLE", "API_ERROR", "INVALID_JSON"])
def test_extraction_failure_precedes_classification(config, status):
    doc = document(extraction_status=status, workload_hours="45")
    fields = compare_fields(record(), doc, config)
    assert classify(record(), doc, fields)[0] == "INCONCLUSIVO"


@pytest.mark.parametrize("hours", ["NaN", "Infinity", "-1", True])
def test_reject_invalid_extracted_workload(hours):
    with pytest.raises(ValidationError):
        document(workload_hours=hours)


def test_invalid_thresholds_and_duplicate_ids(config):
    with pytest.raises(ValidationError):
        MatcherConfig()
    with pytest.raises(ValidationError):
        MatcherThresholds(**{**config.thresholds.model_dump(), "holder_low": 0.95})
    with pytest.raises(ValueError, match="único"):
        match_curriculum(LattesCurriculum(), [document(), document()], config)


def test_known_distinct_acronyms_are_factual_conflict(config):
    cfg = config.model_copy(
        update={
            "acronym_table": {
                **config.acronym_table,
                "UFPA": "Universidade Federal do Pará",
            }
        }
    )
    result = run(cfg, doc=document(issuer_institution="UFPA"))
    assert result.status == "DIVERGENTE"
    assert (
        next(f for f in result.field_evidences if f.field_name == "instituicao").rule_applied
        == "DISTINCT_KNOWN_INSTITUTIONS"
    )


def test_explicit_acronyms_support_full_names(config):
    result = run(
        config,
        record(institution="Universidade Rural", institution_acronym="UFRA"),
        document(issuer_institution="Universidade Federal Rural da Amazônia"),
    )
    assert result.status == "VALIDADO"


def test_parser_discarded_workload_propagated(config):
    curriculum = LattesCurriculum(records=[record(workload_hours=None)])
    result = match_curriculum(
        curriculum,
        [document()],
        config,
        parse_diagnostics=[
            SimpleNamespace(code="INVALID_WORKLOAD_HOURS", record_index=0),
            SimpleNamespace(code="OTHER_RECORD", record_index=1),
        ],
    )
    verdict = result.record_verdicts[0]
    assert verdict.status == "INCONCLUSIVO"
    assert verdict.diagnostics == ["INVALID_WORKLOAD_HOURS"]
    assert (
        next(f for f in verdict.field_evidences if f.field_name == "carga").rule_applied
        == "PARSER_DISCARDED_INVALID_WORKLOAD"
    )


@pytest.mark.parametrize("mode", list(MatchMode))
def test_baselines_decimal_equivalence(config, mode):
    assert (
        run(config.model_copy(update={"mode": mode}), doc=document(workload_hours="40.0")).status
        == "VALIDADO"
    )


def test_text_threshold_boundaries(config):
    from comprova_lattes.matcher.rules import compare_text

    # Uma substituição em dez caracteres tem escore exato 0.9.
    assert compare_text("titulo", "abcdefghij", "abcdefghiX", config).outcome == "MATCH"
    assert (
        compare_text("titulo", "abcdefghij", "abcdeXXXXX", config).outcome
        == "INCONCLUSIVE_BORDERLINE"
    )
    assert compare_text("titulo", "abcdefghij", "XXXXXXXXXX", config).outcome == "CONFLICT"


def test_input_order_does_not_resolve_ambiguity(config):
    recs = [record(), record(record_id="r2")]
    docs = [document(), document(document_id="d2")]
    for records_order in permutations(recs):
        for docs_order in permutations(docs):
            result = match_curriculum(
                LattesCurriculum(records=list(records_order)), list(docs_order), config
            )
            assert all(v.reason_code == "ASSOCIACAO_AMBIGUA" for v in result.record_verdicts)


def test_confirmed_pairs_are_one_to_one(config):
    result = match_curriculum(
        LattesCurriculum(
            records=[
                record(),
                record(
                    record_id="r2",
                    title="Zoologia Tropical",
                    holder_name="Carlos Souza",
                    institution="Instituto ZZZ",
                    end_year=2020,
                ),
            ]
        ),
        [
            document(),
            document(
                document_id="d2",
                activity_title="Zoologia Tropical",
                holder_name="Carlos Souza",
                issuer_institution="Instituto ZZZ",
                end_year=2020,
            ),
        ],
        config,
    )
    assert len(result.association_pairs) == 2
    assert len({p.document_id for p in result.association_pairs}) == 2
    assert all(v.status == "VALIDADO" for v in result.record_verdicts)


def test_import_matcher_without_services():
    import os
    import subprocess
    import sys

    code = """
import importlib.abc
import sys
class NoServices(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'google', 'redis', 'sqlalchemy', 'psycopg', 'celery'}:
            raise AssertionError(fullname)
sys.meta_path.insert(0, NoServices())
from comprova_lattes.matcher import MatcherConfig, match_curriculum
"""
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    completed = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
