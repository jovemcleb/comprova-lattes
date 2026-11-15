"""Contrato de avaliação de desempenho: métricas fiéis e visibilidade de erros reais.

Separa a verificação do cálculo e relato de métricas (`rows`, matriz 3x3,
`per_class`, `accuracy`, `macro_f1`, `without_no_document`, `by_category`,
`error_causes`) dos testes unitários/estruturais, sem exigir superioridade ou
`macro_f1 == 1` sob limiares não calibrados.
"""

from collections import Counter

import pytest

from comprova_lattes.experiments.runner import evaluate, experiment2
from comprova_lattes.experiments.statistics import LABELS, classification
from comprova_lattes.experiments.synthetic import Case, generate, synthetic_acronyms
from comprova_lattes.matcher.models import (
    ExtractedDocumentRecord,
    MatcherConfig,
    MatcherThresholds,
    MatchStatus,
)
from comprova_lattes.schemas.lattes import (
    ActivityStatus,
    LattesCategory,
    LattesCurriculum,
    LattesRecord,
    XmlProvenance,
)


def _uncalibrated_config(acronym_table: dict[str, str] | None = None) -> MatcherConfig:
    return MatcherConfig(
        acronym_table=acronym_table or {},
        acronym_table_version="contract-test-only",
        thresholds=MatcherThresholds(
            association=0.3,
            ambiguity_margin=0.01,
            holder_low=0.4,
            holder_high=0.95,
            title_low=0.4,
            title_high=0.95,
            institution_low=0.4,
            institution_high=0.95,
        ),
    )


def _small_case(
    *,
    case_id: str,
    family_id: str,
    operator: str,
    expected: MatchStatus,
    record: LattesRecord,
    gold: ExtractedDocumentRecord | None,
) -> Case:
    return Case(
        case_id=case_id,
        family_id=family_id,
        template_id=f"t-{family_id}",
        issuer_id=family_id,
        partition="pilot",
        operator=operator,
        degradation=0,
        xml=b"<CURRICULO-VITAE/>",
        curriculum=LattesCurriculum(
            full_name=record.holder_name,
            records=[record],
        ),
        expected=expected,
        gold=gold,
        document=b"doc" if gold is not None else None,
        mime_type="application/pdf",
    )


def _build_independent_small_cases() -> list[Case]:
    provenance = XmlProvenance(section_tag="S", record_tag="R")
    c1 = _small_case(
        case_id="case-1",
        family_id="fam1",
        operator="identity",
        expected=MatchStatus.VALIDADO,
        record=LattesRecord(
            record_id="r1",
            category=LattesCategory.FORMACAO_COMPLEMENTAR,
            subtype="EXTENSAO",
            provenance=provenance,
            holder_name="MARIA SOUZA 0001",
            institution="INSTITUTO BETA 0001",
            title="CURSO DE PYTHON 0001",
            start_year=2024,
            end_year=2024,
            workload_hours="40",
            status=ActivityStatus.CONCLUIDO,
        ),
        gold=ExtractedDocumentRecord(
            document_id="case-1",
            holder_name="MARIA SOUZA 0001",
            activity_title="CURSO DE PYTHON 0001",
            issuer_institution="INSTITUTO BETA 0001",
            start_year=2024,
            end_year=2024,
            activity_year=2024,
            workload_hours="40",
        ),
    )
    # Borderline institution in ORGANIZACAO_EVENTO (4/20 chars differ -> similarity 0.80 in [0.4, 0.95))
    # yields INCONCLUSIVO under the approved event institution policy while expected remains DIVERGENTE.
    c2 = _small_case(
        case_id="case-2",
        family_id="fam2",
        operator="factual_mutation",
        expected=MatchStatus.DIVERGENTE,
        record=LattesRecord(
            record_id="r2",
            category=LattesCategory.ORGANIZACAO_EVENTO,
            provenance=provenance,
            holder_name="JOAO PEREIRA 0002",
            institution="INSTITUTO ALPHA 0001",
            title="SIMPOSIO DE DADOS 0002",
            event_name=None,
            start_year=2024,
            end_year=2024,
            status=ActivityStatus.CONCLUIDO,
        ),
        gold=ExtractedDocumentRecord(
            document_id="case-2",
            holder_name="JOAO PEREIRA 0002",
            activity_title="SIMPOSIO DE DADOS 0002",
            issuer_institution="INSTITUTO ALPHA 9999",
            participation_role_raw="ORGANIZADOR",
            start_year=2024,
            end_year=2024,
            activity_year=2024,
        ),
    )
    # Borderline holder in APRESENTACAO_TRABALHO (4/20 chars differ -> similarity 0.80 in [0.4, 0.95))
    # yields INCONCLUSIVO while expected remains DIVERGENTE.
    c3 = _small_case(
        case_id="case-3",
        family_id="fam3",
        operator="factual_mutation",
        expected=MatchStatus.DIVERGENTE,
        record=LattesRecord(
            record_id="r3",
            category=LattesCategory.APRESENTACAO_TRABALHO,
            provenance=provenance,
            holder_name="ANA MARIA SILVA 0001",
            institution="INSTITUTO GAMA 0003",
            title="PAINEL CIENTIFICO 0003",
            event_name="CONGRESSO NACIONAL 0003",
            start_year=2024,
            end_year=2024,
            participation_role="APRESENTADOR",
            status=ActivityStatus.CONCLUIDO,
        ),
        gold=ExtractedDocumentRecord(
            document_id="case-3",
            holder_name="ANA MARIA SILVA 9999",
            activity_title="PAINEL CIENTIFICO 0003",
            event_name="CONGRESSO NACIONAL 0003",
            issuer_institution="INSTITUTO GAMA 0003",
            participation_role_raw="APRESENTADOR",
            start_year=2024,
            end_year=2024,
            activity_year=2024,
        ),
    )
    c4 = _small_case(
        case_id="case-4",
        family_id="fam4",
        operator="factual_mutation",
        expected=MatchStatus.DIVERGENTE,
        record=LattesRecord(
            record_id="r4",
            category=LattesCategory.PARTICIPACAO_EVENTO,
            provenance=provenance,
            holder_name="CARLOS LIMA 0004",
            institution="INSTITUTO DELTA 0004",
            title="OFICINA DE DADOS 0004",
            event_name="ENCONTRO REGIONAL 0004",
            start_year=2024,
            end_year=2024,
            participation_role="PARTICIPANTE",
            status=ActivityStatus.CONCLUIDO,
        ),
        gold=ExtractedDocumentRecord(
            document_id="case-4",
            holder_name="CARLOS LIMA 0004",
            activity_title="OFICINA DE DADOS 0004",
            event_name="ENCONTRO REGIONAL 0004",
            issuer_institution="INSTITUTO DELTA 0004",
            participation_role_raw="PARTICIPANTE",
            start_year=2031,
            end_year=2031,
            activity_year=2031,
        ),
    )
    c5 = _small_case(
        case_id="case-5",
        family_id="fam5",
        operator="no_document",
        expected=MatchStatus.INCONCLUSIVO,
        record=LattesRecord(
            record_id="r5",
            category=LattesCategory.FORMACAO_ACADEMICA,
            subtype="ESPECIALIZACAO",
            provenance=provenance,
            holder_name="PEDRO ALVES 0005",
            institution="INSTITUTO EPSILON 0005",
            title="ESPECIALIZACAO EM IA 0005",
            start_year=2024,
            end_year=2024,
            workload_hours="360",
            status=ActivityStatus.CONCLUIDO,
        ),
        gold=None,
    )
    return [c1, c2, c3, c4, c5]


def test_classification_known_expected_metrics_and_absent_class():
    truth = [
        "VALIDADO",
        "VALIDADO",
        "DIVERGENTE",
        "DIVERGENTE",
        "INCONCLUSIVO",
        "INCONCLUSIVO",
    ]
    predicted = [
        "VALIDADO",
        "INCONCLUSIVO",
        "VALIDADO",
        "DIVERGENTE",
        "INCONCLUSIVO",
        "INCONCLUSIVO",
    ]
    report = classification(truth, predicted)
    assert report["n"] == 6
    assert report["labels"] == LABELS
    assert report["matrix"] == [
        [1, 0, 1],
        [1, 1, 0],
        [0, 0, 2],
    ]
    assert report["per_class"]["VALIDADO"] == pytest.approx(
        {"precision": 0.5, "recall": 0.5, "support": 2, "f1": 0.5}
    )
    assert report["per_class"]["DIVERGENTE"] == pytest.approx(
        {"precision": 1.0, "recall": 0.5, "support": 2, "f1": 2 / 3}
    )
    assert report["per_class"]["INCONCLUSIVO"] == pytest.approx(
        {"precision": 2 / 3, "recall": 1.0, "support": 2, "f1": 0.8}
    )
    assert report["accuracy"] == pytest.approx(4 / 6)
    assert report["macro_f1"] == pytest.approx((0.5 + (2 / 3) + 0.8) / 3)
    assert report["warnings"] == []

    absent = classification(
        ["VALIDADO", "INCONCLUSIVO", "VALIDADO"],
        ["VALIDADO", "INCONCLUSIVO", "INCONCLUSIVO"],
    )
    assert absent["zero_division"] == 0
    assert absent["warnings"] == ["DIVERGENTE"]
    assert absent["per_class"]["VALIDADO"] == pytest.approx(
        {"precision": 1.0, "recall": 0.5, "support": 2, "f1": 2 / 3}
    )
    assert absent["per_class"]["DIVERGENTE"] == {
        "precision": 0.0,
        "recall": 0.0,
        "support": 0,
        "f1": 0.0,
    }
    assert absent["per_class"]["INCONCLUSIVO"] == pytest.approx(
        {"precision": 0.5, "recall": 1.0, "support": 1, "f1": 2 / 3}
    )
    assert absent["macro_f1"] == pytest.approx(((2 / 3) + 0.0 + (2 / 3)) / 3)


def test_evaluate_and_experiment2_small_fixture_preserve_real_errors():
    cases = _build_independent_small_cases()
    config = _uncalibrated_config()

    reports = experiment2(cases, config)
    lev = reports["LEVENSHTEIN_NORM"]

    assert [row["case_id"] for row in lev["rows"]] == [c.case_id for c in cases]
    assert [row["expected"] for row in lev["rows"]] == [
        "VALIDADO",
        "DIVERGENTE",
        "DIVERGENTE",
        "DIVERGENTE",
        "INCONCLUSIVO",
    ]
    assert [row["status"] for row in lev["rows"]] == [
        "VALIDADO",
        "INCONCLUSIVO",
        "INCONCLUSIVO",
        "DIVERGENTE",
        "INCONCLUSIVO",
    ]
    assert [row["correct"] for row in lev["rows"]] == [True, False, False, True, True]
    assert [row["error_cause"] for row in lev["rows"]] == [None, "rule", "rule", None, None]
    assert all(row["association_correct"] for row in lev["rows"])

    assert lev["matrix"] == [
        [1, 0, 0],
        [0, 1, 2],
        [0, 0, 1],
    ]
    assert lev["error_causes"] == {"rule": 2}
    assert lev["accuracy"] == pytest.approx(3 / 5)
    assert lev["per_class"]["VALIDADO"] == pytest.approx(
        {"precision": 1.0, "recall": 1.0, "support": 1, "f1": 1.0}
    )
    assert lev["per_class"]["DIVERGENTE"] == pytest.approx(
        {"precision": 1.0, "recall": 1 / 3, "support": 3, "f1": 0.5}
    )
    assert lev["per_class"]["INCONCLUSIVO"] == pytest.approx(
        {"precision": 1 / 3, "recall": 1.0, "support": 1, "f1": 0.5}
    )
    assert lev["macro_f1"] == pytest.approx((1.0 + 0.5 + 0.5) / 3)

    without_no_doc = lev["without_no_document"]
    assert without_no_doc["n"] == 4
    assert without_no_doc["matrix"] == [
        [1, 0, 0],
        [0, 1, 2],
        [0, 0, 0],
    ]
    assert without_no_doc["accuracy"] == pytest.approx(0.5)

    org_cat = lev["by_category"]["ORGANIZACAO_EVENTO"]
    assert org_cat["matrix"] == [[0, 0, 0], [0, 0, 1], [0, 0, 0]]
    assert org_cat["error_causes"] == {"rule": 1}
    assert org_cat["rows"][0]["expected"] == "DIVERGENTE"
    assert org_cat["rows"][0]["status"] == "INCONCLUSIVO"

    # Verify association and extraction error causes against oracle are also preserved accurately.
    oracle_ref = {row["case_id"]: row for row in lev["rows"]}
    noisy_outputs = {c.case_id: c.gold for c in cases if c.gold is not None}
    noisy_outputs["case-1"] = ExtractedDocumentRecord(
        document_id="case-1", extraction_status="UNREADABLE"
    )
    noisy_outputs["case-4"] = noisy_outputs["case-4"].model_copy(
        update={"start_year": 2024, "end_year": 2024, "activity_year": 2024}
    )
    noisy_report = evaluate(cases, noisy_outputs, config, oracle=oracle_ref)
    assert noisy_report["error_causes"] == {"association": 1, "rule": 2, "extraction": 1}
    assert noisy_report["association"]["fn"] == 1
    assert len(noisy_report["DOCUMENTO_NAO_ASSOCIADO"]) == 1
    assert noisy_report["matrix"] == [
        [0, 0, 1],
        [1, 0, 2],
        [0, 0, 1],
    ]


@pytest.mark.parametrize("partition", ["pilot", "final"])
def test_experiment2_factual_mutation_integrity_and_reporting_consistency(partition):
    corpus = generate(seed=93, pilot_families=5, final_families=5)
    cases = corpus.select(partition)
    config = _uncalibrated_config(synthetic_acronyms(corpus.select("pilot")))
    reports = experiment2(cases, config)

    expected_divergente_n = sum(c.operator == "factual_mutation" for c in cases)
    assert expected_divergente_n == 5

    for name, report in reports.items():
        rows = report["rows"]
        assert len(rows) == len(cases), name

        mut_rows = [
            row
            for c, row in zip(cases, rows, strict=True)
            if c.operator == "factual_mutation"
        ]
        assert len(mut_rows) == expected_divergente_n
        assert all(row["expected"] == "DIVERGENTE" for row in mut_rows)
        assert sum(report["matrix"][LABELS.index("DIVERGENTE")]) == expected_divergente_n
        assert report["per_class"]["DIVERGENTE"]["support"] == expected_divergente_n
        assert (
            report["without_no_document"]["per_class"]["DIVERGENTE"]["support"]
            == expected_divergente_n
        )

        recomputed = classification(
            [row["expected"] for row in rows],
            [row["status"] for row in rows],
        )
        assert report["matrix"] == recomputed["matrix"]
        assert report["per_class"] == recomputed["per_class"]
        assert report["accuracy"] == pytest.approx(recomputed["accuracy"])
        assert report["macro_f1"] == pytest.approx(recomputed["macro_f1"])

        misclassified = [row for row in rows if not row["correct"]]
        expected_causes = Counter(row["error_cause"] for row in misclassified)
        assert all(row["error_cause"] is not None for row in misclassified)
        assert report["error_causes"] == dict(expected_causes)
        assert sum(report["error_causes"].values()) == len(misclassified)
        off_diagonal = sum(
            report["matrix"][i][j]
            for i in range(3)
            for j in range(3)
            if i != j
        )
        assert off_diagonal == len(misclassified)

        if misclassified:
            assert report["accuracy"] < 1.0
            assert report["macro_f1"] < 1.0

        by_cat = report["by_category"]
        assert sum(cat["n"] for cat in by_cat.values()) == len(cases)
        assert (
            sum(cat["per_class"]["DIVERGENTE"]["support"] for cat in by_cat.values())
            == expected_divergente_n
        )
        cat_causes = Counter()
        for cat_report in by_cat.values():
            for cause, count in cat_report["error_causes"].items():
                cat_causes[cause] += count
        assert dict(cat_causes) == report["error_causes"]

        mut_errors = [row for row in mut_rows if not row["correct"]]
        if mut_errors:
            assert all(row["error_cause"] == "rule" for row in mut_errors)
            assert report["per_class"]["DIVERGENTE"]["recall"] < 1.0
