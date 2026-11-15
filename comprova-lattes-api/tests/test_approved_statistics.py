"""Testes puros das decisões estatísticas aprovadas no protocolo experimental."""

import json
import math
from decimal import Decimal

import pytest

from comprova_lattes.experiments.__main__ import _default, main, read, write
from comprova_lattes.experiments.runner import (
    experiment1,
    experiment3_inference,
    extraction_inference,
    inference,
    integrated_inference,
)
from comprova_lattes.experiments.statistics import (
    APPROVED_EXP2_COMPARATORS,
    APPROVED_EXP2_COMPARISONS,
    APPROVED_EXP2_REFERENCE,
    APPROVED_EXP2_VARIANTS,
    FINAL_WORKBENCH_FAMILIES,
    LABELS,
    PROTOCOL_BOOTSTRAP_CONFIDENCE,
    PROTOCOL_BOOTSTRAP_REPLICATES,
    classification,
    cluster_bootstrap,
    holm,
    mcnemar_exact,
    mean_cluster_bootstrap,
    paired_comparisons,
)
from comprova_lattes.experiments.synthetic import Case, generate, synthetic_acronyms
from comprova_lattes.matcher.models import (
    ExtractedDocumentRecord,
    MatcherConfig,
    MatcherThresholds,
)


def _assert_strict_json_no_nan(payload) -> str:
    serialized = json.dumps(payload, default=_default, sort_keys=True, allow_nan=False)
    assert "NaN" not in serialized
    assert "Infinity" not in serialized
    return serialized


_CACHED_CORPUS_6 = None


def _make_small_cases(n_families: int = 6, cases_per_family: int = 2) -> list[Case]:
    global _CACHED_CORPUS_6
    if _CACHED_CORPUS_6 is None:
        _CACHED_CORPUS_6 = generate(seed=42, pilot_families=6, final_families=2)
    pilot = _CACHED_CORPUS_6.select("pilot")
    families_ordered = sorted({c.family_id for c in pilot})[:n_families]
    selected: list[Case] = []
    for fam in families_ordered:
        fam_cases = [c for c in pilot if c.family_id == fam and c.gold is not None]
        selected.extend(fam_cases[:cases_per_family])
    return selected


def _build_report_from_predictions(cases: list[Case], predicted_statuses: list[str]) -> dict:
    assert len(cases) == len(predicted_statuses)
    truth = [str(c.expected) for c in cases]
    cls = classification(truth, predicted_statuses)
    rows = [
        {
            "case_id": c.case_id,
            "family_id": c.family_id,
            "category": c.curriculum.records[0].category.value,
            "status": status,
            "expected": str(c.expected),
            "correct": status == str(c.expected),
            "association_correct": True,
            "reason": "SYNTHETIC_TEST",
            "error_cause": None if status == str(c.expected) else "rule",
            "automatic": {},
        }
        for c, status in zip(cases, predicted_statuses, strict=True)
    ]
    return {**cls, "rows": rows}


def test_known_mcnemar_exact_and_holm_four_approved_pairs():
    units = [f"fam_{i}" for i in range(6)]
    ref = {u: True for u in units}
    # A: 6 discordantes (b=6, c=0) -> p = 2 * 0.5^6 = 0.03125
    comp_a = {u: False for u in units}
    # B: 5 discordantes (b=5, c=0) -> p = 2 * 0.5^5 = 0.0625
    comp_b = {u: (i == 0) for i, u in enumerate(units)}
    # JARO_WINKLER: 5 discordantes (b=4, c=1) -> p = 2 * (1 + 5) / 32 = 0.375
    ref_for_jw = {u: (i < 5) for i, u in enumerate(units)}
    comp_jw = {u: (i in (0, 5)) for i, u in enumerate(units)}
    # Zero discordantes -> p = 1.0
    zero_disc = mcnemar_exact(ref, dict(ref))
    assert zero_disc["b"] == 0 and zero_disc["c"] == 0 and zero_disc["discordant"] == 0
    assert zero_disc["p_value"] == 1.0
    assert zero_disc["concordant_correct"] == 6 and zero_disc["concordant_incorrect"] == 0

    res_a = mcnemar_exact(ref, comp_a)
    assert res_a["b"] == 6 and res_a["c"] == 0 and res_a["p_value"] == pytest.approx(0.03125)

    res_b = mcnemar_exact(ref, comp_b)
    assert res_b["b"] == 5 and res_b["c"] == 0 and res_b["p_value"] == pytest.approx(0.0625)

    res_jw = mcnemar_exact(ref_for_jw, comp_jw)
    assert res_jw["b"] == 4 and res_jw["c"] == 1 and res_jw["p_value"] == pytest.approx(0.375)

    methods = {
        "LEVENSHTEIN_NORM": ref,
        "A": comp_a,
        "B": comp_b,
        "JARO_WINKLER": {u: (i < 2) for i, u in enumerate(units)},  # b=4, c=0 -> p=0.125
        "TOKEN_HYBRID": dict(ref),  # b=0, c=0 -> p=1.0
    }
    comparisons = paired_comparisons(
        methods,
        reference=APPROVED_EXP2_REFERENCE,
        comparators=APPROVED_EXP2_COMPARATORS,
    )
    assert list(comparisons.keys()) == [
        "LEVENSHTEIN_NORM:A",
        "LEVENSHTEIN_NORM:B",
        "LEVENSHTEIN_NORM:JARO_WINKLER",
        "LEVENSHTEIN_NORM:TOKEN_HYBRID",
    ]
    assert "A:B" not in comparisons
    assert comparisons["LEVENSHTEIN_NORM:A"]["p_value"] == pytest.approx(0.03125)
    assert comparisons["LEVENSHTEIN_NORM:B"]["p_value"] == pytest.approx(0.0625)
    assert comparisons["LEVENSHTEIN_NORM:JARO_WINKLER"]["p_value"] == pytest.approx(0.125)
    assert comparisons["LEVENSHTEIN_NORM:TOKEN_HYBRID"]["p_value"] == pytest.approx(1.0)

    # Holm somente nesses 4 pares: m=4 -> 4*0.03125=0.125, 3*0.0625=0.1875, 2*0.125=0.25, 1*1.0=1.0
    assert comparisons["LEVENSHTEIN_NORM:A"]["p_holm"] == pytest.approx(0.125)
    assert comparisons["LEVENSHTEIN_NORM:B"]["p_holm"] == pytest.approx(0.1875)
    assert comparisons["LEVENSHTEIN_NORM:JARO_WINKLER"]["p_holm"] == pytest.approx(0.25)
    assert comparisons["LEVENSHTEIN_NORM:TOKEN_HYBRID"]["p_holm"] == pytest.approx(1.0)

    # Monotonicidade step-down do ajuste de Holm
    step_down = holm({"p1": 0.02, "p2": 0.025, "p3": 0.20, "p4": 0.90})
    assert step_down == pytest.approx(
        {
            "p1": 0.08,  # 4 * 0.02 = 0.08
            "p2": 0.08,  # max(0.08, 3 * 0.025 = 0.075) = 0.08
            "p3": 0.40,  # max(0.08, 2 * 0.20 = 0.40) = 0.40
            "p4": 0.90,  # max(0.40, 1 * 0.90 = 0.90) = 0.90
        }
    )

    # Compatibilidade do default de paired_comparisons (todos os pares = 10 para 5 métodos)
    all_pairs = paired_comparisons(methods)
    assert len(all_pairs) == 10
    assert "A:B" in all_pairs


def test_paired_comparisons_validation_rejects_invalid_pairs_and_groupings():
    valid_methods = {
        "LEVENSHTEIN_NORM": {"f1": True, "f2": False},
        "A": {"f1": False, "f2": False},
        "B": {"f1": True, "f2": True},
    }
    with pytest.raises(ValueError, match="referência ausente"):
        paired_comparisons(valid_methods, reference="UNKNOWN")
    with pytest.raises(ValueError, match="comparador ausente"):
        paired_comparisons(valid_methods, reference="LEVENSHTEIN_NORM", comparators=["UNKNOWN"])
    with pytest.raises(ValueError, match="idêntico à referência"):
        paired_comparisons(
            valid_methods, reference="LEVENSHTEIN_NORM", comparators=["LEVENSHTEIN_NORM"]
        )
    with pytest.raises(ValueError, match="Comparador duplicado"):
        paired_comparisons(valid_methods, reference="LEVENSHTEIN_NORM", comparators=["A", "A"])
    with pytest.raises(ValueError, match="não ambos"):
        paired_comparisons(
            valid_methods,
            pairs=[("LEVENSHTEIN_NORM", "A")],
            reference="LEVENSHTEIN_NORM",
        )
    with pytest.raises(ValueError, match="consigo mesmo"):
        paired_comparisons(valid_methods, pairs=[("A", "A")])
    with pytest.raises(ValueError, match="duplicado ou simétrico"):
        paired_comparisons(
            valid_methods,
            pairs=[("LEVENSHTEIN_NORM", "A"), ("A", "LEVENSHTEIN_NORM")],
        )
    with pytest.raises(ValueError, match="booleano"):
        mcnemar_exact({"f1": 1}, {"f1": True})  # type: ignore[dict-item]


def test_exp2_inference_four_pairs_resolution_loss_and_all_variants_required():
    cases = _make_small_cases(n_families=6, cases_per_family=2)
    assert len(cases) == 12
    truth = [str(c.expected) for c in cases]
    wrong = ["DIVERGENTE" if t != "DIVERGENTE" else "INCONCLUSIVO" for t in truth]

    # LEVENSHTEIN_NORM acerta todas as 6 famílias (12/12 casos)
    pred_lev = list(truth)
    # A erra o 1º caso de todas as 6 famílias (acerta 1/2 por família -> 0/6 famílias completas!)
    pred_a = [wrong[i] if i % 2 == 0 else truth[i] for i in range(len(cases))]
    # B erra apenas nas 5 primeiras famílias e acerta a última família inteira (1/6 famílias completas)
    pred_b = [wrong[i] if (i % 2 == 0 and i < 10) else truth[i] for i in range(len(cases))]
    # JARO_WINKLER acerta todas as 6 famílias (0 discordantes com LEVENSHTEIN_NORM -> p=1.0)
    pred_jw = list(truth)
    # TOKEN_HYBRID erra o 1º caso nas 4 primeiras famílias (2/6 famílias completas -> b=4, c=0 -> p=0.125)
    pred_tok = [wrong[i] if (i % 2 == 0 and i < 8) else truth[i] for i in range(len(cases))]

    reports = {
        "A": _build_report_from_predictions(cases, pred_a),
        "B": _build_report_from_predictions(cases, pred_b),
        "LEVENSHTEIN_NORM": _build_report_from_predictions(cases, pred_lev),
        "JARO_WINKLER": _build_report_from_predictions(cases, pred_jw),
        "TOKEN_HYBRID": _build_report_from_predictions(cases, pred_tok),
    }

    stats = inference(reports, cases, seed=17, replicates=20, confidence=0.95)
    _assert_strict_json_no_nan(stats)

    assert stats["reference_method"] == "LEVENSHTEIN_NORM"
    assert stats["comparators"] == ["A", "B", "JARO_WINKLER", "TOKEN_HYBRID"]
    assert stats["n_comparisons"] == 4
    assert list(stats["mcnemar"].keys()) == [
        "LEVENSHTEIN_NORM:A",
        "LEVENSHTEIN_NORM:B",
        "LEVENSHTEIN_NORM:JARO_WINKLER",
        "LEVENSHTEIN_NORM:TOKEN_HYBRID",
    ]
    assert "A:B" not in stats["mcnemar"]
    assert stats["tests_macro_f1_difference"] is False
    assert stats["automatic_independence_claimed"] is False
    assert stats["population_sampling_claimed"] is False

    # Perda de resolução documentada: variante A tem 50% de acerto por caso, mas 0% por família
    res_a = stats["family_resolution_summary"]["A"]
    assert res_a["case_accuracy"] == pytest.approx(0.5)
    assert res_a["complete_families"] == 0
    assert res_a["partial_correct_families_collapsed_to_false"] == 6
    assert res_a["family_accuracy"] == 0.0

    # Valores-p exatos e Holm nos 4 pares
    assert stats["mcnemar"]["LEVENSHTEIN_NORM:A"]["p_value"] == pytest.approx(0.03125)
    assert stats["mcnemar"]["LEVENSHTEIN_NORM:B"]["p_value"] == pytest.approx(0.0625)
    assert stats["mcnemar"]["LEVENSHTEIN_NORM:TOKEN_HYBRID"]["p_value"] == pytest.approx(0.125)
    assert stats["mcnemar"]["LEVENSHTEIN_NORM:JARO_WINKLER"]["p_value"] == pytest.approx(1.0)
    assert stats["mcnemar"]["LEVENSHTEIN_NORM:A"]["p_holm"] == pytest.approx(0.125)
    assert stats["mcnemar"]["LEVENSHTEIN_NORM:B"]["p_holm"] == pytest.approx(0.1875)
    assert stats["mcnemar"]["LEVENSHTEIN_NORM:TOKEN_HYBRID"]["p_holm"] == pytest.approx(0.25)
    assert stats["mcnemar"]["LEVENSHTEIN_NORM:JARO_WINKLER"]["p_holm"] == pytest.approx(1.0)

    # Exige todas as 5 variantes juntas em inference (Exp 2)
    incomplete_reports = {k: v for k, v in reports.items() if k != "TOKEN_HYBRID"}
    with pytest.raises(ValueError, match="todas as 5 variantes juntas"):
        inference(incomplete_reports, cases, seed=17, replicates=10, confidence=0.95)


def test_alignment_validation_rejects_misaligned_cases_rows_and_families():
    cases = _make_small_cases(n_families=3, cases_per_family=2)
    truth = [str(c.expected) for c in cases]
    base_reports = {
        name: _build_report_from_predictions(cases, truth) for name in APPROVED_EXP2_VARIANTS
    }

    # 1. Ordem de case_id trocada em uma variante
    swapped_rows = list(reversed(base_reports["A"]["rows"]))
    bad_order = {**base_reports, "A": {**base_reports["A"], "rows": swapped_rows}}
    with pytest.raises(ValueError, match="Pareamento dos casos divergente"):
        inference(bad_order, cases, seed=5, replicates=10, confidence=0.95)

    # 2. family_id adulterado na linha sem mudar case_id
    bad_fam_rows = [dict(r) for r in base_reports["B"]["rows"]]
    bad_fam_rows[0]["family_id"] = "familia_invalida"
    bad_fam = {**base_reports, "B": {**base_reports["B"], "rows": bad_fam_rows}}
    with pytest.raises(ValueError, match="Alinhamento de família divergente"):
        inference(bad_fam, cases, seed=5, replicates=10, confidence=0.95)

    # 3. Indicador 'correct' inconsistente com status == expected
    bad_correct_rows = [dict(r) for r in base_reports["LEVENSHTEIN_NORM"]["rows"]]
    bad_correct_rows[0]["correct"] = False
    bad_correct = {
        **base_reports,
        "LEVENSHTEIN_NORM": {**base_reports["LEVENSHTEIN_NORM"], "rows": bad_correct_rows},
    }
    with pytest.raises(ValueError, match="Indicador 'correct' inconsistente"):
        inference(bad_correct, cases, seed=5, replicates=10, confidence=0.95)

    # 4. cluster_bootstrap rejeita famílias vazias ou rótulos em branco
    with pytest.raises(ValueError, match="família/cluster inválido"):
        cluster_bootstrap(["f1", "   "], lambda ix: 1.0, seed=1, replicates=10, confidence=0.95)


def test_bootstrap_protocol_defaults_caller_overrides_and_seed_determinism():
    families = ["fam_1", "fam_1", "fam_2", "fam_2", "fam_3", "fam_3"]
    values = [1.0, 0.5, 0.0, 0.5, 1.0, 1.0]
    stat_fn = lambda ix: sum(values[i] for i in ix) / len(ix)

    # Semente explícita é obrigatória (TypeError se omitida; ValueError se bool)
    with pytest.raises(TypeError):
        cluster_bootstrap(families, stat_fn)  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="Semente inteira explícita"):
        cluster_bootstrap(families, stat_fn, seed=True)  # type: ignore[arg-type]

    # Padrão de protocolo: 2000 réplicas e 95% de confiança quando omitidos
    default_ci = cluster_bootstrap(families, stat_fn, seed=99)
    default_ci_repeat = cluster_bootstrap(families, stat_fn, seed=99)
    assert default_ci == default_ci_repeat
    assert default_ci["replicates"] == PROTOCOL_BOOTSTRAP_REPLICATES == 2000
    assert default_ci["confidence"] == pytest.approx(PROTOCOL_BOOTSTRAP_CONFIDENCE)
    assert default_ci["is_protocol_default"] is True
    assert default_ci["parameter_regime"] == "approved_protocol_default"
    assert default_ci["n"] == 6 and default_ci["families"] == 3

    # Caller escolhe replicates=10 e confidence=0.80: relatório marca valores reais sem fingir 2000/0.95
    custom_ci = cluster_bootstrap(families, stat_fn, seed=99, replicates=10, confidence=0.80)
    assert custom_ci["replicates"] == 10
    assert custom_ci["confidence"] == pytest.approx(0.80)
    assert custom_ci["protocol_default_replicates"] == 2000
    assert custom_ci["protocol_default_confidence"] == pytest.approx(0.95)
    assert custom_ci["is_protocol_default"] is False
    assert custom_ci["parameter_regime"] == "custom_caller_override"


def test_mean_ci_differs_from_pooled_confusion_matrix_and_preserves_n():
    cases = _make_small_cases(n_families=5, cases_per_family=2)
    assert len(cases) == 10
    # Ajusta classes esperadas para ter as 3 classes representadas
    forced_expected = [LABELS[i % 3] for i in range(len(cases))]
    cases = [
        c.model_copy(update={"expected": forced_expected[i]}) for i, c in enumerate(cases)
    ]

    # Três execuções com padrões distintos de erro entre classes (denominadores FP/FN diferentes por run)
    run1_pred = [
        "VALIDADO" if i in (0, 1, 2, 3, 4) else forced_expected[i] for i in range(len(cases))
    ]
    run2_pred = [
        "DIVERGENTE" if i in (2, 3, 5, 6, 7) else forced_expected[i] for i in range(len(cases))
    ]
    run3_pred = [
        "INCONCLUSIVO" if i in (0, 4, 7, 8, 9) else forced_expected[i] for i in range(len(cases))
    ]

    run_reports = [
        _build_report_from_predictions(cases, pred)
        for pred in (run1_pred, run2_pred, run3_pred)
    ]
    oracle_report = _build_report_from_predictions(cases, forced_expected)
    exp3_report = {
        "n": len(cases),
        "repeats": 3,
        "runs": run_reports,
        "oracle": oracle_report,
        "calls": 0,
        "reused": True,
    }

    stats = integrated_inference(exp3_report, cases, seed=23, replicates=200, confidence=0.95)
    _assert_strict_json_no_nan(stats)
    assert experiment3_inference is integrated_inference

    # N e famílias preservados nas 3 repetições e na média (nunca 3*N = 30!)
    assert stats["n"] == 10
    assert stats["families"] == 5
    assert stats["calls"] == 0 and stats["reused"] is True
    for key in ("repeat_1", "repeat_2", "repeat_3", "mean_3", "oracle"):
        assert stats["intervals"][key]["n"] == 10
        assert stats["intervals"][key]["families"] == 5

    # Estimativa pontual da média == média aritmética das 3 execuções
    r1, r2, r3 = (stats["intervals"][f"repeat_{i}"]["estimate"] for i in (1, 2, 3))
    mean_est = stats["mean_3"]["estimate"]
    assert mean_est == pytest.approx((r1 + r2 + r3) / 3)

    # Pooling (concatenar as 3 matrizes em 3N=30 casos) altera tanto o ponto quanto o IC bootstrap
    pooled_truth = forced_expected * 3
    pooled_pred = run1_pred + run2_pred + run3_pred
    pooled_families = [c.family_id for c in cases] * 3
    pooled_macro_f1 = classification(pooled_truth, pooled_pred)["macro_f1"]
    pooled_ci = cluster_bootstrap(
        [f"{fam}_rep_{r}" for r in range(3) for fam in [c.family_id for c in cases]],
        lambda ix: classification(
            [pooled_truth[i] for i in ix], [pooled_pred[i] for i in ix]
        )["macro_f1"],
        seed=23,
        replicates=200,
        confidence=0.95,
    )
    assert len(pooled_families) == 30
    assert mean_est != pytest.approx(pooled_macro_f1)
    assert (stats["mean_3"]["low"], stats["mean_3"]["high"]) != pytest.approx(
        (pooled_ci["low"], pooled_ci["high"])
    )


def test_exp1_inference_per_run_baseline_mean3_instability_and_secondary_all_three():
    cases = _make_small_cases(n_families=4, cases_per_family=2)
    gold = {c.case_id: c.gold for c in cases if c.gold is not None}
    assert len(gold) == 8

    run1 = dict(gold)
    run2 = dict(gold)
    run3 = dict(gold)
    baseline = dict(gold)

    # Introduz instabilidade entre execuções em 2 documentos
    doc_ids = [c.case_id for c in cases]
    run2[doc_ids[0]] = cases[0].gold.model_copy(update={"holder_name": "DIVERGENTE RUN 2"})
    run3[doc_ids[0]] = ExtractedDocumentRecord(
        document_id=doc_ids[0], extraction_status="API_ERROR"
    )
    run3[doc_ids[2]] = cases[2].gold.model_copy(update={"workload_hours": Decimal(999)})
    baseline[doc_ids[0]] = cases[0].gold.model_copy(update={"holder_name": "OCR ERRO"})
    baseline[doc_ids[4]] = cases[4].gold.model_copy(update={"holder_name": "OCR ERRO 2"})

    from comprova_lattes.experiments.__main__ import Replay

    exp1_report = experiment1(cases, Replay([run1, run2, run3]), Replay([baseline]))
    stats = extraction_inference(exp1_report, cases, seed=11, replicates=50, confidence=0.90)
    _assert_strict_json_no_nan({"exp1": exp1_report, "stats": stats})

    # Verifica IC por repetição, baseline e média das 3 execuções sem inflar N
    for key in ("repeat_1", "repeat_2", "repeat_3", "mean_3", "baseline", "OCR_regex"):
        interval = stats["intervals"][key]
        assert interval["n"] == 8
        assert interval["families"] == 4
        assert interval["replicates"] == 50
        assert interval["confidence"] == pytest.approx(0.90)
        assert interval["is_primary"] is True
        assert interval["voting_used"] is False

    assert stats["intervals"]["repeat_1"]["estimate"] == pytest.approx(8 / 8)
    assert stats["intervals"]["repeat_2"]["estimate"] == pytest.approx(7 / 8)
    assert stats["intervals"]["repeat_3"]["estimate"] == pytest.approx(6 / 8)
    assert stats["intervals"]["mean_3"]["estimate"] == pytest.approx((1.0 + 7 / 8 + 6 / 8) / 3)
    assert stats["intervals"]["baseline"]["estimate"] == pytest.approx(6 / 8)

    # all_three preservado apenas como análise secundária descritiva claramente identificada
    all_three = stats["intervals"]["all_three"]
    assert all_three == stats["secondary_descriptive"]["all_three"]
    assert all_three["is_primary"] is False
    assert all_three["voting_used"] is False
    assert all_three["role"] == "secondary_descriptive_conservative_stability_only"
    assert all_three["estimate"] == pytest.approx(6 / 8)

    # Sem McNemar inventado entre repetições
    assert stats["mcnemar"] == {}
    assert stats["inter_repetition_mcnemar_removed"] is True

    # Instabilidade relatada
    inst = stats["instability"]
    assert inst["unstable_documents"] == 2
    assert set(inst["unstable_document_ids"]) == {doc_ids[0], doc_ids[2]}
    assert inst["accuracy_range"] == pytest.approx([6 / 8, 1.0])


def test_few_families_no_crash_warning_and_no_nan_with_absent_classes():
    # Apenas 2 famílias e apenas 1 classe presente (2 classes ausentes -> zero_division=0, sem NaN)
    families = ["fam_a", "fam_a", "fam_b", "fam_b"]
    truth = ["VALIDADO", "VALIDADO", "VALIDADO", "VALIDADO"]
    pred = ["VALIDADO", "INCONCLUSIVO", "VALIDADO", "VALIDADO"]

    ci = cluster_bootstrap(
        families,
        lambda ix: classification([truth[i] for i in ix], [pred[i] for i in ix])["macro_f1"],
        seed=7,
        replicates=25,
        confidence=0.95,
    )
    _assert_strict_json_no_nan(ci)
    assert ci["families"] == 2
    assert ci["final_workbench_families"] == FINAL_WORKBENCH_FAMILIES == 20
    assert ci["below_final_workbench_family_count"] is True
    assert ci["low_family_count_warning"] is True
    assert ci["workbench_count_is_validity_guarantee"] is False
    assert ci["automatic_independence_claimed"] is False
    assert ci["population_sampling_claimed"] is False
    assert len(ci["warnings"]) == 1
    assert str(FINAL_WORKBENCH_FAMILIES) in ci["warnings"][0]
    assert "não limiar científico nem garantia de validade" in ci["warnings"][0]
    assert math.isfinite(ci["estimate"]) and math.isfinite(ci["low"]) and math.isfinite(ci["high"])

    # Mesmo com 20 famílias (contagem da bancada final AD-016), não se alega garantia de validade nem independência
    families_20 = [f"fam_{i:02d}" for i in range(20) for _ in range(2)]
    ci_20 = cluster_bootstrap(
        families_20,
        lambda ix: sum(i % 2 for i in ix) / len(ix),
        seed=7,
        replicates=10,
        confidence=0.95,
    )
    assert ci_20["families"] == 20
    assert ci_20["below_final_workbench_family_count"] is False
    assert ci_20["low_family_count_warning"] is False
    assert ci_20["workbench_count_is_validity_guarantee"] is False
    assert ci_20["automatic_independence_claimed"] is False
    assert ci_20["population_sampling_claimed"] is False

    # Se uma função de estatística retornar NaN, cluster_bootstrap e mean_cluster_bootstrap falham explicitamente
    with pytest.raises(ValueError, match="não finita"):
        cluster_bootstrap(families, lambda _: float("nan"), seed=7, replicates=10, confidence=0.95)
    with pytest.raises(ValueError, match="não finita"):
        mean_cluster_bootstrap(
            families, [lambda _: float("inf")], seed=7, replicates=10, confidence=0.95
        )


def test_cli_integration_exp1_exp2_exp3_explicit_seed_and_real_parameters(tmp_path):
    corpus = generate(seed=31, pilot_families=2, final_families=2)
    pilot_cases = corpus.select("pilot")
    final_cases = corpus.select("final")
    config = MatcherConfig(
        acronym_table=synthetic_acronyms(pilot_cases),
        acronym_table_version="synthetic-test-only",
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

    write(tmp_path / "corpus.json", corpus)
    write(tmp_path / "candidates.json", [config])
    main(
        [
            "calibrate",
            "--corpus",
            str(tmp_path / "corpus.json"),
            "--candidates",
            str(tmp_path / "candidates.json"),
            "--output",
            str(tmp_path / "calibration.json"),
        ]
    )
    artifacts = {}
    for name in (
        "schema",
        "prompt",
        "regex",
        "acronyms",
        "normalization",
        "generator",
        "code",
        "environment",
    ):
        p = tmp_path / name
        p.write_bytes(name.encode())
        artifacts[name] = str(p)
    write(tmp_path / "artifacts.json", artifacts)
    main(
        [
            "freeze",
            "--corpus",
            str(tmp_path / "corpus.json"),
            "--calibration",
            str(tmp_path / "calibration.json"),
            "--artifacts",
            str(tmp_path / "artifacts.json"),
            "--output",
            str(tmp_path / "manifest.json"),
        ]
    )

    gold = {c.case_id: c.gold for c in final_cases if c.gold is not None}
    first_doc_id = next(iter(gold))
    gold_with_nan_meta = dict(gold)
    gold_with_nan_meta[first_doc_id] = gold[first_doc_id].model_copy(
        update={"raw_metadata": {"provider_float": float("nan")}}
    )
    write(tmp_path / "runs.json", [gold_with_nan_meta, gold, gold])
    write(tmp_path / "ocr.json", gold)

    common = [
        "--corpus",
        str(tmp_path / "corpus.json"),
        "--manifest",
        str(tmp_path / "manifest.json"),
        "--artifacts",
        str(tmp_path / "artifacts.json"),
        "--partition",
        "final",
    ]

    # Rejeita --replicates sem --seed explícita no CLI
    with pytest.raises(ValueError, match="--seed explícita"):
        main(
            [
                "exp3",
                *common,
                "--extractions",
                str(tmp_path / "runs.json"),
                "--replicates",
                "10",
                "--output",
                str(tmp_path / "bad.json"),
            ]
        )

    # Exp 1 no CLI com --seed, --replicates e --confidence explícitos e Replay sanitizando NaN em raw_metadata
    main(
        [
            "exp1",
            *common,
            "--extractions",
            str(tmp_path / "runs.json"),
            "--baseline",
            str(tmp_path / "ocr.json"),
            "--seed",
            "12",
            "--replicates",
            "10",
            "--confidence",
            "0.90",
            "--output",
            str(tmp_path / "exp1.json"),
        ]
    )
    exp1_out = read(tmp_path / "exp1.json")
    assert exp1_out["mean_3"]["n"] == len(gold)
    assert exp1_out["statistics"]["mean_3"]["replicates"] == 10
    assert exp1_out["statistics"]["mean_3"]["confidence"] == pytest.approx(0.90)
    assert exp1_out["statistics"]["mcnemar"] == {}
    assert exp1_out["statistics"]["inter_repetition_mcnemar_removed"] is True

    # Exp 3 no CLI com --seed, --replicates e --confidence explícitos
    main(
        [
            "exp3",
            *common,
            "--extractions",
            str(tmp_path / "runs.json"),
            "--seed",
            "12",
            "--replicates",
            "10",
            "--confidence",
            "0.90",
            "--output",
            str(tmp_path / "exp3.json"),
        ]
    )
    exp3_out = read(tmp_path / "exp3.json")
    assert exp3_out["calls"] == 0 and exp3_out["reused"] is True
    assert exp3_out["mean_3"]["n"] == len(final_cases)
    assert exp3_out["statistics"]["mean_3"]["replicates"] == 10
    assert exp3_out["statistics"]["mean_3"]["confidence"] == pytest.approx(0.90)
    assert exp3_out["statistics"]["mean_3"]["is_protocol_default"] is False
    assert exp3_out["statistics"]["mcnemar"] == {}

    # Exp 2 no CLI com --seed, --replicates e --confidence explícitos
    main(
        [
            "exp2",
            *common,
            "--seed",
            "12",
            "--replicates",
            "10",
            "--confidence",
            "0.95",
            "--output",
            str(tmp_path / "exp2.json"),
        ]
    )
    exp2_out = read(tmp_path / "exp2.json")
    assert list(exp2_out["statistics"]["mcnemar"].keys()) == [
        f"{a}:{b}" for a, b in APPROVED_EXP2_COMPARISONS
    ]
