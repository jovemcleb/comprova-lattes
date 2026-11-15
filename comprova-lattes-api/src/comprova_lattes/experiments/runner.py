"""Experimentos puros com extrações reutilizáveis e resultados pré-revisão."""

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Protocol

from comprova_lattes.matcher.engine import match_curriculum
from comprova_lattes.matcher.models import ExtractedDocumentRecord, MatcherConfig, MatchMode
from comprova_lattes.matcher.text import normalize_text

from .baseline import FIELDS
from .reporting import (
    classification_by_category,
    experiment1_by_category,
    experiment3_by_category,
    extraction_by_category,
    sanitize_json_value,
    summarize_experiment1_telemetry,
    summarize_experiment3_telemetry,
)
from .statistics import (
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
    mean_cluster_bootstrap,
    paired_comparisons,
)
from .synthetic import Case


class Extractor(Protocol):
    def extract(self, document_id: str, data: bytes, mime_type: str) -> ExtractedDocumentRecord: ...


def _validate_cases_alignment(cases: Sequence[Case]) -> list[str]:
    if not isinstance(cases, Sequence) or not cases:
        raise ValueError("Casos únicos não vazios obrigatórios")
    case_ids: list[str] = []
    families: list[str] = []
    for c in cases:
        if not isinstance(c.case_id, str) or not c.case_id.strip():
            raise ValueError("case_id inválido nos casos")
        if not isinstance(c.family_id, str) or not c.family_id.strip():
            raise ValueError(f"family_id inválido no caso {c.case_id}")
        case_ids.append(c.case_id)
        families.append(c.family_id)
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("Casos únicos não vazios obrigatórios")
    return families


def _validate_rows_alignment(
    rows: Sequence[Mapping], cases: Sequence[Case], method_name: str = ""
) -> None:
    prefix = f" ({method_name})" if method_name else ""
    if not isinstance(rows, Sequence) or len(rows) != len(cases):
        raise ValueError(f"Pareamento dos casos divergente{prefix}")
    for row, case in zip(rows, cases, strict=True):
        if not isinstance(row, Mapping) or row.get("case_id") != case.case_id:
            raise ValueError(f"Pareamento dos casos divergente{prefix}")
        if row.get("family_id") != case.family_id:
            raise ValueError(f"Alinhamento de família divergente para {case.case_id}{prefix}")
        expected_str = str(case.expected)
        if row.get("expected") != expected_str:
            raise ValueError(f"Classe esperada divergente para {case.case_id}{prefix}")
        status = row.get("status")
        if status not in LABELS:
            raise ValueError(f"Status previsto inválido para {case.case_id}{prefix}: {status}")
        correct = row.get("correct")
        if type(correct) is not bool or correct != (status == expected_str):
            raise ValueError(f"Indicador 'correct' inconsistente para {case.case_id}{prefix}")


def _bootstrap_metadata(
    *, seed: int, replicates: int, confidence: float, n_families: int, n_units: int
) -> dict:
    conf = float(confidence)
    is_default = bool(
        replicates == PROTOCOL_BOOTSTRAP_REPLICATES
        and math.isclose(conf, PROTOCOL_BOOTSTRAP_CONFIDENCE)
    )
    below_final_workbench = n_families < FINAL_WORKBENCH_FAMILIES
    return {
        "seed": seed,
        "replicates": replicates,
        "confidence": conf,
        "n_families": n_families,
        "n_units": n_units,
        "final_workbench_families": FINAL_WORKBENCH_FAMILIES,
        "protocol_default_replicates": PROTOCOL_BOOTSTRAP_REPLICATES,
        "protocol_default_confidence": PROTOCOL_BOOTSTRAP_CONFIDENCE,
        "is_protocol_default": is_default,
        "parameter_regime": (
            "approved_protocol_default" if is_default else "custom_caller_override"
        ),
        "below_final_workbench_family_count": below_final_workbench,
        "low_family_count_warning": below_final_workbench,
        "workbench_count_is_validity_guarantee": False,
        "warnings": (
            [
                (
                    f"Amostra com {n_families} famílias (abaixo das {FINAL_WORKBENCH_FAMILIES} "
                    f"famílias da bancada final AD-016; {FINAL_WORKBENCH_FAMILIES} é contagem da "
                    "bancada sintética, não limiar científico nem garantia de validade): "
                    "intervalos percentis por família possuem resolução discreta limitada."
                )
            ]
            if below_final_workbench
            else []
        ),
        "cluster_resolution_note": (
            f"{FINAL_WORKBENCH_FAMILIES} famílias é a contagem da bancada final aprovada (AD-016), "
            "não regra científica de validade nem garantia de cobertura assintótica."
        ),
        "inference_scope": "synthetic_workbench_cluster_resampling; not_population_sampling",
        "automatic_independence_claimed": False,
        "population_sampling_claimed": False,
    }


def _equal(a, b, equivalent):
    if equivalent and isinstance(a, str) and isinstance(b, str):
        return normalize_text(a) == normalize_text(b)
    return a == b


def _extraction_metrics_core(
    cases: Sequence[Case], outputs: dict[str, ExtractedDocumentRecord], *, equivalent: bool = False
) -> dict:
    documents = [c for c in cases if c.gold is not None]
    if set(outputs) != {c.case_id for c in documents}:
        raise ValueError("Extrações devem cobrir os mesmos documentos")
    counts = {field: Counter() for field in FIELDS}
    conditional_counts = {field: Counter() for field in FIELDS}
    failures, correct, conditional = Counter(), {}, {}
    for c in documents:
        out = outputs[c.case_id]
        if out.document_id != c.case_id:
            raise ValueError("ID de extração divergente")
        failed = out.extraction_status != "OK"
        if failed:
            failures[str(out.extraction_status)] += 1
        all_correct = not failed
        for field in FIELDS:
            gold = getattr(c.gold, field)
            value = None if failed else getattr(out, field)
            equal = _equal(gold, value, equivalent)
            kind = (
                ("absent_correct" if gold is None else "correct")
                if equal
                else ("spurious" if gold is None else "omitted" if value is None else "incorrect")
            )
            counts[field][kind] += 1
            if not failed:
                conditional_counts[field][kind] += 1
            all_correct &= equal
        correct[c.case_id] = all_correct
        if not failed:
            conditional[c.case_id] = all_correct
    per_field = {}
    for field, count in counts.items():
        tp, fp, fn = (
            count["correct"],
            count["incorrect"] + count["spurious"],
            (count["incorrect"] + count["omitted"]),
        )
        per_field[field] = dict(
            count,
            precision=tp / (tp + fp) if tp + fp else 0,
            recall=tp / (tp + fn) if tp + fn else 0,
            f1=2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0,
            accuracy=(tp + count["absent_correct"]) / len(documents) if documents else 0,
        )
    return {
        "n": len(documents),
        "fields": per_field,
        "conditional_field_counts": {k: dict(v) for k, v in conditional_counts.items()},
        "failures": dict(failures),
        "failure_rate": sum(failures.values()) / len(documents) if documents else 0,
        "correct": correct,
        "all_fields_accuracy": sum(correct.values()) / len(correct) if correct else 0,
        "conditional_n": len(conditional),
        "conditional_accuracy": sum(conditional.values()) / len(conditional)
        if conditional
        else None,
        "failure_policy": "omission; failed document is incorrect",
    }


def extraction_metrics(
    cases: Sequence[Case], outputs: dict[str, ExtractedDocumentRecord], *, equivalent: bool = False
) -> dict:
    result = _extraction_metrics_core(cases, outputs, equivalent=equivalent)
    result["by_category"] = (
        extraction_by_category(
            cases,
            outputs,
            equivalent=equivalent,
            metric_fn=_extraction_metrics_core,
        )
        if cases
        else {}
    )
    return result


def _summarize_extraction_mean_3(
    literal: Sequence[Mapping], equivalent: Sequence[Mapping], n_documents: int
) -> dict:
    repeats = len(literal)
    lit_acc = [float(r["all_fields_accuracy"]) for r in literal]
    eq_acc = [float(r["all_fields_accuracy"]) for r in equivalent]
    fail_rates = [float(r["failure_rate"]) for r in literal]
    fields_mean = {}
    for field in FIELDS:
        fields_mean[field] = {
            metric: sum(float(r["fields"][field][metric]) for r in literal) / repeats
            for metric in ("precision", "recall", "f1", "accuracy")
        }
    return {
        "n": n_documents,
        "repeats": repeats,
        "all_fields_accuracy_mean": sum(lit_acc) / repeats,
        "all_fields_accuracy_per_run": lit_acc,
        "all_fields_accuracy_range": [min(lit_acc), max(lit_acc)],
        "equivalent_all_fields_accuracy_mean": sum(eq_acc) / repeats,
        "equivalent_all_fields_accuracy_per_run": eq_acc,
        "equivalent_all_fields_accuracy_range": [min(eq_acc), max(eq_acc)],
        "failure_rate_mean": sum(fail_rates) / repeats,
        "failure_rate_per_run": fail_rates,
        "fields": fields_mean,
        "aggregation_method": (
            "arithmetic_mean_of_separate_run_metrics; counts_not_pooled; n_not_tripled"
        ),
        "voting_used": False,
    }


def experiment1(cases: Sequence[Case], extractor: Extractor, baseline: Extractor) -> dict:
    documents = [c for c in cases if c.document is not None]
    runs = [
        {c.case_id: extractor.extract(c.case_id, c.document, c.mime_type) for c in documents}
        for _ in range(3)
    ]
    ocr = {c.case_id: baseline.extract(c.case_id, c.document, c.mime_type) for c in documents}
    unstable = {
        c.case_id: [
            f
            for f in (*FIELDS, "extraction_status")
            if len({getattr(run[c.case_id], f) for run in runs}) > 1
        ]
        for c in documents
    }
    literal = [extraction_metrics(cases, r) for r in runs]
    equivalent = [extraction_metrics(cases, r, equivalent=True) for r in runs]
    baseline_report = extraction_metrics(cases, ocr)
    accuracies = [r["all_fields_accuracy"] for r in literal]
    unstable_doc_ids = [c.case_id for c in documents if unstable[c.case_id]]
    return {
        "n": len(documents),
        "repeats": 3,
        "outputs": runs,
        "baseline_outputs": ocr,
        "literal": literal,
        "equivalent": equivalent,
        "baseline": baseline_report,
        "mean_3": _summarize_extraction_mean_3(literal, equivalent, len(documents)),
        "by_category": experiment1_by_category(
            cases,
            runs,
            ocr,
            literal_reports=literal,
            equivalent_reports=equivalent,
            baseline_report=baseline_report,
        ),
        "telemetry": summarize_experiment1_telemetry(cases, runs, ocr),
        "unstable_fields": unstable,
        "unstable_document_ids": unstable_doc_ids,
        "unstable_documents": len(unstable_doc_ids),
        "unstable_documents_rate": len(unstable_doc_ids) / len(documents) if documents else 0.0,
        "stability_by_field": {
            f: sum(f not in unstable[c.case_id] for c in documents) / len(documents)
            if documents
            else None
            for f in (*FIELDS, "extraction_status")
        },
        "accuracy_mean": sum(accuracies) / 3,
        "accuracy_range": [min(accuracies), max(accuracies)],
        "repetition_policy": "report separately; never pool repetitions as N",
    }


def evaluate(
    cases: Sequence[Case],
    outputs: dict[str, ExtractedDocumentRecord],
    config: MatcherConfig,
    *,
    oracle: dict | None = None,
) -> dict:
    if not cases or len({c.case_id for c in cases}) != len(cases):
        raise ValueError("Casos únicos não vazios obrigatórios")
    if set(outputs) != {c.case_id for c in cases if c.gold is not None}:
        raise ValueError("Saídas devem cobrir exatamente documentos dos casos")
    truth, predicted, rows, causes, reasons = [], [], [], Counter(), Counter()
    tp = fp = fn = association_correct = 0
    orphans, conditional = [], []
    for c in cases:
        result = match_curriculum(c.curriculum, [outputs[c.case_id]] if c.gold else [], config)
        if len(result.record_verdicts) != 1:
            raise ValueError("Case representa exatamente um registro curricular")
        v = result.record_verdicts[0]
        expected_pair = c.case_id if c.gold else None
        assoc_ok = v.matched_document_id == expected_pair
        association_correct += assoc_ok
        tp += int(expected_pair is not None and assoc_ok)
        fp += int(v.matched_document_id is not None and not assoc_ok)
        fn += int(expected_pair is not None and not assoc_ok)
        ok = v.status == c.expected
        if assoc_ok:
            conditional.append(ok)
        cause = None
        if not ok:
            if not assoc_ok:
                cause = "association"
            elif oracle is not None and oracle[c.case_id]["status"] == c.expected:
                cause = "extraction"
            else:
                cause = "rule"
            causes[cause] += 1
        reasons[v.reason_code] += 1
        truth.append(str(c.expected))
        predicted.append(str(v.status))
        rows.append(
            {
                "case_id": c.case_id,
                "family_id": c.family_id,
                "category": c.curriculum.records[0].category.value,
                "status": str(v.status),
                "expected": str(c.expected),
                "correct": ok,
                "association_correct": assoc_ok,
                "reason": v.reason_code,
                "error_cause": cause,
                "automatic": v.model_dump(mode="json", exclude={"human_review"}),
            }
        )
        orphans.extend(o.model_dump(mode="json") for o in result.orphan_documents)
    return dict(
        classification(truth, predicted),
        rows=rows,
        reasons=dict(reasons),
        association={
            "accuracy": association_correct / len(cases),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else 0,
            "recall": tp / (tp + fn) if tp + fn else 0,
        },
        DOCUMENTO_NAO_ASSOCIADO=orphans,
        error_causes=dict(causes),
        conditional_association_n=len(conditional),
        conditional_class_accuracy=sum(conditional) / len(conditional) if conditional else None,
        review_stage="automatic_before_human_review",
        without_no_document=classification(
            [str(c.expected) for c in cases if c.gold],
            [row["status"] for c, row in zip(cases, rows, strict=True) if c.gold],
        )
        if any(c.gold for c in cases)
        else None,
        by_category=classification_by_category(cases, rows, orphans=orphans),
    )


def experiment2(cases: Sequence[Case], config: MatcherConfig) -> dict:
    gold = {c.case_id: c.gold for c in cases if c.gold is not None}
    configurations = {
        "A": config.model_copy(update={"mode": MatchMode.BASELINE_EXACT}),
        "B": config.model_copy(update={"mode": MatchMode.BASELINE_NORMALIZED}),
        **{
            metric: config.model_copy(update={"mode": MatchMode.PROPOSED, "text_metric": metric})
            for metric in ("LEVENSHTEIN_NORM", "JARO_WINKLER", "TOKEN_HYBRID")
        },
    }
    return {name: evaluate(cases, gold, cfg) for name, cfg in configurations.items()}


def _summarize_experiment3_mean_3(run_reports: Sequence[Mapping], n_cases: int) -> dict:
    repeats = len(run_reports)
    macro_f1_per_run = [float(r["macro_f1"]) for r in run_reports]
    accuracy_per_run = [float(r["accuracy"]) for r in run_reports]
    per_class_mean = {}
    for label in LABELS:
        per_class_mean[label] = {
            "precision": sum(float(r["per_class"][label]["precision"]) for r in run_reports)
            / repeats,
            "recall": sum(float(r["per_class"][label]["recall"]) for r in run_reports) / repeats,
            "f1": sum(float(r["per_class"][label]["f1"]) for r in run_reports) / repeats,
            "support": run_reports[0]["per_class"][label]["support"],
        }
    assoc_mean = {
        metric: sum(float(r["association"][metric]) for r in run_reports) / repeats
        for metric in ("accuracy", "precision", "recall")
    }
    return {
        "n": n_cases,
        "repeats": repeats,
        "macro_f1": sum(macro_f1_per_run) / repeats,
        "macro_f1_per_run": macro_f1_per_run,
        "macro_f1_range": [min(macro_f1_per_run), max(macro_f1_per_run)],
        "accuracy": sum(accuracy_per_run) / repeats,
        "accuracy_per_run": accuracy_per_run,
        "accuracy_range": [min(accuracy_per_run), max(accuracy_per_run)],
        "per_class": per_class_mean,
        "association": assoc_mean,
        "zero_division": 0,
        "warnings": list(run_reports[0].get("warnings", [])),
        "aggregation_method": (
            "arithmetic_mean_of_separate_run_metrics; matrices_not_pooled; n_not_tripled"
        ),
        "pooled_matrices": False,
        "voting_used": False,
    }


def experiment3(
    cases: Sequence[Case],
    outputs: Sequence[dict[str, ExtractedDocumentRecord]],
    config: MatcherConfig,
) -> dict:
    if len(outputs) != 3:
        raise ValueError("Exp 3 reutiliza exatamente as 3 extrações de Exp 1")
    oracle = evaluate(cases, {c.case_id: c.gold for c in cases if c.gold}, config)
    reference = {r["case_id"]: r for r in oracle["rows"]}
    run_reports = [evaluate(cases, run, config, oracle=reference) for run in outputs]
    mean_3 = _summarize_experiment3_mean_3(run_reports, len(cases))
    return {
        "n": len(cases),
        "repeats": 3,
        "runs": run_reports,
        "mean_3": mean_3,
        "macro_f1_mean": mean_3["macro_f1"],
        "macro_f1_range": mean_3["macro_f1_range"],
        "accuracy_mean": mean_3["accuracy"],
        "accuracy_range": mean_3["accuracy_range"],
        "oracle": oracle,
        "calls": 0,
        "reused": True,
        "extraction_metadata": [
            {key: sanitize_json_value(value.raw_metadata) for key, value in run.items()}
            for run in outputs
        ],
        "telemetry": summarize_experiment3_telemetry(cases, outputs),
        "by_category": experiment3_by_category({"runs": run_reports, "oracle": oracle}),
        "repetition_policy": "separate; N unchanged",
    }


def _validate_doc_outcomes(
    outcomes: Mapping, expected_doc_ids: set[str], label: str
) -> dict[str, bool]:
    if not isinstance(outcomes, Mapping) or set(outcomes.keys()) != expected_doc_ids:
        raise ValueError(f"Documentos avaliados divergentes em {label}")
    validated: dict[str, bool] = {}
    for doc_id, val in outcomes.items():
        if type(val) is not bool:
            raise ValueError(f"Resultado binário booleano obrigatório para {doc_id} em {label}")
        validated[doc_id] = val
    return validated


def extraction_inference(
    report: dict,
    cases: Sequence[Case],
    *,
    seed: int,
    replicates: int = PROTOCOL_BOOTSTRAP_REPLICATES,
    confidence: float = PROTOCOL_BOOTSTRAP_CONFIDENCE,
) -> dict:
    """IC por repetição, baseline e média das 3 execuções; all_three apenas secundário descritivo."""
    _validate_cases_alignment(cases)
    documents = [c for c in cases if c.gold is not None]
    if not documents:
        raise ValueError("Pelo menos um documento com gabarito é obrigatório no Exp 1")
    all_case_families = {c.family_id for c in cases}
    doc_families = {c.family_id for c in documents}
    if doc_families != all_case_families:
        raise ValueError("Agrupamento inválido: existem famílias sem documentos avaliáveis no Exp 1")

    if not isinstance(report, Mapping) or not report:
        raise ValueError("Relatório do Exp 1 inválido")
    literal_runs = report.get("literal")
    if not isinstance(literal_runs, Sequence) or len(literal_runs) != 3:
        raise ValueError("Exp 1 exige exatamente 3 repetições em 'literal'")
    baseline_section = report.get("baseline")
    if not isinstance(baseline_section, Mapping) or "correct" not in baseline_section:
        raise ValueError("Relatório do Exp 1 exige seção 'baseline' com resultados por documento")

    expected_doc_ids = {c.case_id for c in documents}
    run_correct_maps = [
        _validate_doc_outcomes(run.get("correct"), expected_doc_ids, f"repeat_{i + 1}")
        for i, run in enumerate(literal_runs)
    ]
    baseline_correct_map = _validate_doc_outcomes(
        baseline_section.get("correct"), expected_doc_ids, "baseline"
    )

    families = [c.family_id for c in documents]
    n_families = len(set(families))
    run_values = [[run_map[c.case_id] for c in documents] for run_map in run_correct_maps]
    baseline_values = [baseline_correct_map[c.case_id] for c in documents]
    all_three_values = [
        all(run_map[c.case_id] for run_map in run_correct_maps) for c in documents
    ]

    primary_intervals: dict[str, dict] = {}
    for idx, values in enumerate(run_values, start=1):
        name = f"repeat_{idx}"
        interval = cluster_bootstrap(
            families,
            lambda ix, values=values: sum(values[i] for i in ix) / len(ix),
            seed=seed,
            replicates=replicates,
            confidence=confidence,
        )
        primary_intervals[name] = {
            **interval,
            "role": "primary_per_run",
            "is_primary": True,
            "voting_used": False,
            "estimand": "document_all_fields_accuracy",
        }

    mean_3_interval = mean_cluster_bootstrap(
        families,
        [
            (lambda ix, values=values: sum(values[i] for i in ix) / len(ix))
            for values in run_values
        ],
        seed=seed,
        replicates=replicates,
        confidence=confidence,
    )
    primary_intervals["mean_3"] = {
        **mean_3_interval,
        "role": "primary_three_run_mean",
        "is_primary": True,
        "voting_used": False,
        "estimand": "mean_document_all_fields_accuracy_across_3_runs",
    }

    baseline_interval = cluster_bootstrap(
        families,
        lambda ix, values=baseline_values: sum(values[i] for i in ix) / len(ix),
        seed=seed,
        replicates=replicates,
        confidence=confidence,
    )
    baseline_tagged = {
        **baseline_interval,
        "role": "primary_baseline",
        "is_primary": True,
        "voting_used": False,
        "estimand": "document_all_fields_accuracy",
    }
    primary_intervals["baseline"] = baseline_tagged
    primary_intervals["OCR_regex"] = dict(baseline_tagged)

    all_three_interval = cluster_bootstrap(
        families,
        lambda ix, values=all_three_values: sum(values[i] for i in ix) / len(ix),
        seed=seed,
        replicates=replicates,
        confidence=confidence,
    )
    all_three_tagged = {
        **all_three_interval,
        "role": "secondary_descriptive_conservative_stability_only",
        "is_primary": False,
        "voting_used": False,
        "estimand": "simultaneous_correct_across_all_3_runs_descriptive",
        "note": (
            "Análise secundária descritiva de estabilidade (acerto simultâneo nas 3 repetições); "
            "não constitui estimando principal nem combinação por voto."
        ),
    }

    intervals = {
        **primary_intervals,
        "all_three": all_three_tagged,
    }

    accuracies = [float(r["estimate"]) for r in (
        primary_intervals["repeat_1"],
        primary_intervals["repeat_2"],
        primary_intervals["repeat_3"],
    )]
    unstable_fields = report.get("unstable_fields")
    if not isinstance(unstable_fields, Mapping):
        unstable_fields = {
            c.case_id: (
                ["all_fields_correct"]
                if len({run_map[c.case_id] for run_map in run_correct_maps}) > 1
                else []
            )
            for c in documents
        }
    unstable_doc_ids = [c.case_id for c in documents if unstable_fields.get(c.case_id)]

    return {
        "intervals": intervals,
        "primary_intervals": primary_intervals,
        "secondary_descriptive": {
            "all_three": all_three_tagged,
        },
        "mean_3": primary_intervals["mean_3"],
        "baseline": primary_intervals["baseline"],
        "instability": {
            "n_documents": len(documents),
            "unstable_documents": len(unstable_doc_ids),
            "unstable_documents_rate": len(unstable_doc_ids) / len(documents),
            "unstable_document_ids": unstable_doc_ids,
            "unstable_fields": dict(unstable_fields),
            "stability_by_field": report.get("stability_by_field"),
            "accuracy_per_run": accuracies,
            "accuracy_mean": sum(accuracies) / 3,
            "accuracy_range": [min(accuracies), max(accuracies)],
            "accuracy_amplitude": max(accuracies) - min(accuracies),
        },
        "mcnemar": {},
        "inter_repetition_mcnemar_removed": True,
        "mcnemar_policy": (
            "approved_mcnemar_is_exp2_only; no_hypothesis_tests_between_repetitions"
        ),
        "bootstrap_parameters": _bootstrap_metadata(
            seed=seed,
            replicates=replicates,
            confidence=confidence,
            n_families=n_families,
            n_units=len(documents),
        ),
        "repetition_policy": (
            "three_runs_reported_separately_plus_mean_3; all_three_secondary_descriptive_only; "
            "no_voting; n_never_tripled"
        ),
    }


def inference(
    reports: Mapping[str, dict],
    cases: Sequence[Case],
    *,
    seed: int,
    replicates: int = PROTOCOL_BOOTSTRAP_REPLICATES,
    confidence: float = PROTOCOL_BOOTSTRAP_CONFIDENCE,
) -> dict:
    """Exp 2: IC por família para as 5 variantes e McNemar exato apenas nos 4 pares com LEVENSHTEIN_NORM."""
    families = _validate_cases_alignment(cases)
    if not isinstance(reports, Mapping) or set(reports.keys()) != set(APPROVED_EXP2_VARIANTS):
        raise ValueError(
            "inference (Exp 2) exige todas as 5 variantes juntas: "
            f"{', '.join(APPROVED_EXP2_VARIANTS)}"
        )

    ordered_families = sorted(set(families))
    n_families = len(ordered_families)
    intervals: dict[str, dict] = {}
    methods: dict[str, dict[str, bool]] = {}
    family_resolution: dict[str, dict] = {}

    for name in APPROVED_EXP2_VARIANTS:
        report = reports[name]
        if not isinstance(report, Mapping) or "rows" not in report:
            raise ValueError(f"Relatório inválido para variante {name}")
        rows = report["rows"]
        _validate_rows_alignment(rows, cases, name)

        intervals[name] = cluster_bootstrap(
            families,
            lambda ix, rows=rows: classification(
                [rows[i]["expected"] for i in ix], [rows[i]["status"] for i in ix]
            )["macro_f1"],
            seed=seed,
            replicates=replicates,
            confidence=confidence,
        )

        family_outcomes: dict[str, bool] = {}
        partial_families = 0
        for fam in ordered_families:
            fam_rows = [r for r in rows if r["family_id"] == fam]
            correct_count = sum(1 for r in fam_rows if r["correct"])
            all_ok = correct_count == len(fam_rows)
            if 0 < correct_count < len(fam_rows):
                partial_families += 1
            family_outcomes[fam] = all_ok
        methods[name] = family_outcomes
        complete_count = sum(family_outcomes.values())
        family_resolution[name] = {
            "total_families": n_families,
            "complete_families": complete_count,
            "incomplete_families": n_families - complete_count,
            "partial_correct_families_collapsed_to_false": partial_families,
            "family_accuracy": complete_count / n_families,
            "case_accuracy": sum(1 for r in rows if r["correct"]) / len(rows),
        }

    mcnemar_results = paired_comparisons(
        methods,
        pairs=APPROVED_EXP2_COMPARISONS,
    )
    return {
        "intervals": intervals,
        "mcnemar": mcnemar_results,
        "reference_method": APPROVED_EXP2_REFERENCE,
        "comparators": list(APPROVED_EXP2_COMPARATORS),
        "approved_pairs": [f"{a}:{b}" for a, b in APPROVED_EXP2_COMPARISONS],
        "n_comparisons": len(APPROVED_EXP2_COMPARISONS),
        "paired_unit": "family; all records correct",
        "correction": "Holm",
        "test_type": "exact_binomial_two_sided",
        "role": "complementary_descriptive_family_accuracy; does_not_test_macro_f1",
        "tests_macro_f1_difference": False,
        "automatic_independence_claimed": False,
        "population_sampling_claimed": False,
        "family_resolution_summary": family_resolution,
        "bootstrap_parameters": _bootstrap_metadata(
            seed=seed,
            replicates=replicates,
            confidence=confidence,
            n_families=n_families,
            n_units=len(cases),
        ),
        "assumptions_and_limits": {
            "unit_definition": (
                "Cada família (cluster de casos compartilhando registro-base) vale True "
                "somente se todos os seus casos forem classificados corretamente."
            ),
            "resolution_loss": (
                "Perda de resolução: uma família com 4/5 acertos é reduzida a False da mesma "
                "forma que 0/5 acertos; o teste não mede diretamente diferenças de Macro-F1."
            ),
            "independence_assumption": (
                "O teste de McNemar por família trata cada família como unidade pareada, "
                "mas a separação determinística de registros-base, emissores e layouts na "
                "bancada sintética não comprova independência estatística entre famílias "
                "nem amostragem populacional."
            ),
            "cluster_sample_size_limit": (
                f"Com {n_families} famílias avaliadas (a bancada final AD-016 tem "
                f"{FINAL_WORKBENCH_FAMILIES} famílias; {FINAL_WORKBENCH_FAMILIES} é contagem da "
                "bancada e não limiar científico nem garantia de validade), há resolução discreta "
                "e potência estatística limitadas para detectar pequenas diferenças marginais."
            ),
            "zero_discordant_rule": "Quando b + c == 0, p_value = 1.0.",
        },
    }


def integrated_inference(
    report: dict,
    cases: Sequence[Case],
    *,
    seed: int,
    replicates: int = PROTOCOL_BOOTSTRAP_REPLICATES,
    confidence: float = PROTOCOL_BOOTSTRAP_CONFIDENCE,
) -> dict:
    """Exp 3: IC de Macro-F1 por repetição e para a média das 3 execuções, preservando calls=0."""
    families = _validate_cases_alignment(cases)
    if not isinstance(report, Mapping) or not report:
        raise ValueError("Relatório do Exp 3 inválido")
    if (
        type(report.get("calls")) is not int
        or report.get("calls") != 0
        or report.get("reused") is not True
    ):
        raise ValueError("Exp 3 deve reutilizar extrações do Exp 1 com zero chamadas novas (calls=0)")
    runs = report.get("runs")
    if not isinstance(runs, Sequence) or len(runs) != 3:
        raise ValueError("Exp 3 exige exatamente 3 execuções em 'runs'")

    all_run_rows: list[Sequence[Mapping]] = []
    for idx, run in enumerate(runs, start=1):
        if not isinstance(run, Mapping) or "rows" not in run:
            raise ValueError(f"Execução repeat_{idx} inválida no Exp 3")
        rows = run["rows"]
        _validate_rows_alignment(rows, cases, f"repeat_{idx}")
        all_run_rows.append(rows)

    n_families = len(set(families))
    intervals: dict[str, dict] = {}
    run_stat_fns = []
    for idx, rows in enumerate(all_run_rows, start=1):
        name = f"repeat_{idx}"
        stat_fn = lambda ix, rows=rows: classification(
            [rows[i]["expected"] for i in ix], [rows[i]["status"] for i in ix]
        )["macro_f1"]
        run_stat_fns.append(stat_fn)
        interval = cluster_bootstrap(
            families,
            stat_fn,
            seed=seed,
            replicates=replicates,
            confidence=confidence,
        )
        intervals[name] = {
            **interval,
            "role": "primary_per_run",
            "is_primary": True,
            "voting_used": False,
            "estimand": "macro_f1",
        }

    mean_3_interval = mean_cluster_bootstrap(
        families,
        run_stat_fns,
        seed=seed,
        replicates=replicates,
        confidence=confidence,
    )
    intervals["mean_3"] = {
        **mean_3_interval,
        "role": "primary_three_run_mean",
        "is_primary": True,
        "voting_used": False,
        "estimand": "mean_macro_f1_across_3_runs",
    }

    oracle_report = report.get("oracle")
    if isinstance(oracle_report, Mapping) and "rows" in oracle_report:
        oracle_rows = oracle_report["rows"]
        _validate_rows_alignment(oracle_rows, cases, "oracle")
        oracle_interval = cluster_bootstrap(
            families,
            lambda ix, rows=oracle_rows: classification(
                [rows[i]["expected"] for i in ix], [rows[i]["status"] for i in ix]
            )["macro_f1"],
            seed=seed,
            replicates=replicates,
            confidence=confidence,
        )
        intervals["oracle"] = {
            **oracle_interval,
            "role": "reference_oracle_gold_extraction",
            "is_primary": False,
            "voting_used": False,
            "estimand": "macro_f1",
        }

    per_run_estimates = [
        float(intervals[f"repeat_{i}"]["estimate"]) for i in (1, 2, 3)
    ]
    return {
        "n": len(cases),
        "families": n_families,
        "repeats": 3,
        "calls": 0,
        "reused": True,
        "intervals": intervals,
        "per_run": {f"repeat_{i}": intervals[f"repeat_{i}"] for i in (1, 2, 3)},
        "mean_3": intervals["mean_3"],
        "macro_f1_per_run": per_run_estimates,
        "macro_f1_mean": float(intervals["mean_3"]["estimate"]),
        "macro_f1_range": [min(per_run_estimates), max(per_run_estimates)],
        "mcnemar": {},
        "mcnemar_policy": "approved_mcnemar_is_exp2_only; no_hypothesis_tests_between_repetitions",
        "bootstrap_parameters": _bootstrap_metadata(
            seed=seed,
            replicates=replicates,
            confidence=confidence,
            n_families=n_families,
            n_units=len(cases),
        ),
        "repetition_policy": (
            "separate_per_run_and_mean_3; matrices_never_pooled; n_never_tripled; no_voting"
        ),
    }


experiment3_inference = integrated_inference
