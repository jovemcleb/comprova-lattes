"""Experimentos puros com extrações reutilizáveis e resultados pré-revisão."""

from collections import Counter
from collections.abc import Sequence
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
from .statistics import classification, cluster_bootstrap, paired_comparisons
from .synthetic import Case


class Extractor(Protocol):
    def extract(self, document_id: str, data: bytes, mime_type: str) -> ExtractedDocumentRecord: ...


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
    return {
        "n": len(documents),
        "repeats": 3,
        "outputs": runs,
        "baseline_outputs": ocr,
        "literal": literal,
        "equivalent": equivalent,
        "baseline": baseline_report,
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
        "unstable_documents": sum(bool(v) for v in unstable.values()),
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
    return {
        "n": len(cases),
        "runs": run_reports,
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


def extraction_inference(
    report: dict, cases: Sequence[Case], *, seed: int, replicates: int, confidence: float
) -> dict:
    """Sensibilidade por repetição e análise conservadora (3 acertos), por família."""
    documents = [c for c in cases if c.gold]
    methods = {f"repeat_{i + 1}": run["correct"] for i, run in enumerate(report["literal"])}
    methods["all_three"] = {
        c.case_id: all(run["correct"][c.case_id] for run in report["literal"]) for c in documents
    }
    methods["OCR_regex"] = report["baseline"]["correct"]
    families = [c.family_id for c in documents]
    intervals, clustered = {}, {}
    for name, results in methods.items():
        values = [results[c.case_id] for c in documents]
        intervals[name] = cluster_bootstrap(
            families,
            lambda ix, values=values: sum(values[i] for i in ix) / len(ix),
            seed=seed,
            replicates=replicates,
            confidence=confidence,
        )
        clustered[name] = {
            f: all(results[c.case_id] for c in documents if c.family_id == f)
            for f in sorted(set(families))
        }
    return {
        "intervals": intervals,
        "mcnemar": paired_comparisons(clustered),
        "paired_unit": "family; all documents correct",
        "correction": "Holm",
    }


def inference(
    reports: dict[str, dict],
    cases: Sequence[Case],
    *,
    seed: int,
    replicates: int,
    confidence: float,
) -> dict:
    """McNemar usa família inteira correta, preservando pareamento e independência."""
    intervals, methods = {}, {}
    for name, report in reports.items():
        rows = report["rows"]
        if [r["case_id"] for r in rows] != [c.case_id for c in cases]:
            raise ValueError("Pareamento dos casos divergente")
        intervals[name] = cluster_bootstrap(
            [c.family_id for c in cases],
            lambda ix, rows=rows: classification(
                [rows[i]["expected"] for i in ix], [rows[i]["status"] for i in ix]
            )["macro_f1"],
            seed=seed,
            replicates=replicates,
            confidence=confidence,
        )
        methods[name] = {
            f: all(r["correct"] for r in rows if r["family_id"] == f)
            for f in sorted({c.family_id for c in cases})
        }
    return {
        "intervals": intervals,
        "mcnemar": paired_comparisons(methods),
        "paired_unit": "family; all records correct",
        "correction": "Holm",
    }
