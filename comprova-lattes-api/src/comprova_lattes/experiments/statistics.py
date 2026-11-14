"""Estatística offline; unidades pareadas e clusters explícitos."""

from collections.abc import Callable, Mapping, Sequence
from itertools import combinations

import numpy as np
from scipy.stats import binomtest

LABELS = ("VALIDADO", "DIVERGENTE", "INCONCLUSIVO")


def classification(truth: Sequence[str], predicted: Sequence[str]) -> dict:
    if not truth or len(truth) != len(predicted):
        raise ValueError("Pares não vazios com mesmo N são obrigatórios")
    matrix = [[0] * 3 for _ in LABELS]
    for a, b in zip(truth, predicted, strict=True):
        matrix[LABELS.index(a)][LABELS.index(b)] += 1
    per_class = {}
    for i, label in enumerate(LABELS):
        tp = matrix[i][i]
        support = sum(matrix[i])
        positive = sum(row[i] for row in matrix)
        precision = tp / positive if positive else 0.0
        recall = tp / support if support else 0.0
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "support": support,
            "f1": 2 * tp / (support + positive) if support + positive else 0.0,
        }
    return {
        "n": len(truth),
        "labels": LABELS,
        "matrix": matrix,
        "per_class": per_class,
        "accuracy": sum(matrix[i][i] for i in range(3)) / len(truth),
        "macro_f1": sum(c["f1"] for c in per_class.values()) / 3,
        "zero_division": 0,
        "warnings": [k for k, v in per_class.items() if not v["support"]],
    }


def cohen_kappa(first: Sequence[str], second: Sequence[str]) -> dict:
    if not first or len(first) != len(second):
        raise ValueError("Anotações independentes devem ter mesmo N não vazio")
    labels = sorted(set(first) | set(second))
    matrix = [
        [sum(a == x and b == y for a, b in zip(first, second, strict=True)) for y in labels]
        for x in labels
    ]
    n = len(first)
    observed = sum(a == b for a, b in zip(first, second, strict=True)) / n
    expected = sum(first.count(x) * second.count(x) for x in labels) / n**2
    return {
        "n": n,
        "labels": labels,
        "matrix": matrix,
        "agreement": observed,
        "kappa": (observed - expected) / (1 - expected) if expected < 1 else None,
        "warning": "Degenerate marginals" if expected == 1 else None,
    }


def cluster_bootstrap(
    families: Sequence[str],
    statistic: Callable[[list[int]], float],
    *,
    seed: int,
    replicates: int,
    confidence: float,
) -> dict:
    if not families or replicates < 2 or not 0 < confidence < 1:
        raise ValueError("Clusters, réplicas >=2 e confiança em (0,1) obrigatórios")
    groups = [[i for i, f in enumerate(families) if f == name] for name in sorted(set(families))]
    rng = np.random.default_rng(seed)
    samples = [
        statistic([i for j in rng.integers(0, len(groups), len(groups)) for i in groups[j]])
        for _ in range(replicates)
    ]
    if not np.isfinite(samples).all():
        raise ValueError("Estatística bootstrap não finita")
    alpha = (1 - confidence) / 2
    low, high = np.quantile(samples, [alpha, 1 - alpha])
    return {
        "estimate": statistic(list(range(len(families)))),
        "low": float(low),
        "high": float(high),
        "families": len(groups),
        "n": len(families),
        "seed": seed,
        "replicates": replicates,
        "confidence": confidence,
        "method": "family percentile",
        "absent_class_f1": 0,
    }


def mcnemar_exact(first: Mapping[str, bool], second: Mapping[str, bool]) -> dict:
    if not first or first.keys() != second.keys():
        raise ValueError("Métodos devem conter exatamente as mesmas unidades")
    b = sum(first[k] and not second[k] for k in first)
    c = sum(second[k] and not first[k] for k in first)
    return {
        "n": len(first),
        "b": b,
        "c": c,
        "p_value": float(binomtest(b, b + c, 0.5).pvalue) if b + c else 1.0,
    }


def holm(p_values: Mapping[str, float]) -> dict[str, float]:
    if any(not 0 <= p <= 1 for p in p_values.values()):
        raise ValueError("p fora de [0,1]")
    ordered = sorted(p_values, key=p_values.get)
    adjusted, previous = {}, 0.0
    for i, name in enumerate(ordered):
        previous = max(previous, min(1.0, p_values[name] * (len(ordered) - i)))
        adjusted[name] = previous
    return adjusted


def paired_comparisons(methods: Mapping[str, Mapping[str, bool]]) -> dict:
    tests = {f"{a}:{b}": mcnemar_exact(methods[a], methods[b]) for a, b in combinations(methods, 2)}
    adjusted = holm({k: v["p_value"] for k, v in tests.items()})
    return {k: dict(v, p_holm=adjusted[k]) for k, v in tests.items()}
