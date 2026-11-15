"""Estatística offline; unidades pareadas e clusters explícitos."""

import math
from collections.abc import Callable, Mapping, Sequence
from itertools import combinations

import numpy as np
from scipy.stats import binomtest

LABELS = ("VALIDADO", "DIVERGENTE", "INCONCLUSIVO")

PROTOCOL_BOOTSTRAP_REPLICATES = 2000
PROTOCOL_BOOTSTRAP_CONFIDENCE = 0.95
PILOT_WORKBENCH_FAMILIES = 10
FINAL_WORKBENCH_FAMILIES = 20

APPROVED_EXP2_REFERENCE = "LEVENSHTEIN_NORM"
APPROVED_EXP2_COMPARATORS: tuple[str, ...] = (
    "A",
    "B",
    "JARO_WINKLER",
    "TOKEN_HYBRID",
)
APPROVED_EXP2_VARIANTS: tuple[str, ...] = (
    "A",
    "B",
    "LEVENSHTEIN_NORM",
    "JARO_WINKLER",
    "TOKEN_HYBRID",
)
APPROVED_EXP2_COMPARISONS: tuple[tuple[str, str], ...] = tuple(
    (APPROVED_EXP2_REFERENCE, comparator) for comparator in APPROVED_EXP2_COMPARATORS
)


def _validate_family_labels(families: Sequence[str]) -> list[str]:
    if isinstance(families, (str, bytes)) or not families:
        raise ValueError("Clusters/famílias não vazios são obrigatórios")
    normalized: list[str] = []
    for family in families:
        if not isinstance(family, str) or not family.strip():
            raise ValueError("Identificador de família/cluster inválido")
        normalized.append(family)
    return normalized


def _validate_bootstrap_params(seed: int, replicates: int, confidence: float) -> float:
    if type(seed) is not int:
        raise ValueError("Semente inteira explícita é obrigatória")
    if type(replicates) is not int or replicates < 2:
        raise ValueError("Clusters, réplicas >=2 e confiança em (0,1) obrigatórios")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(confidence)
        or not 0 < float(confidence) < 1
    ):
        raise ValueError("Clusters, réplicas >=2 e confiança em (0,1) obrigatórios")
    return float(confidence)


def _validate_unit_outcomes(units: Mapping[str, bool], method_name: str = "") -> set[str]:
    prefix = f" ({method_name})" if method_name else ""
    if not isinstance(units, Mapping) or not units:
        raise ValueError(f"Unidades pareadas não vazias são obrigatórias{prefix}")
    keys: set[str] = set()
    for key, value in units.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"Chave de unidade inválida{prefix}")
        if type(value) is not bool:
            raise ValueError(f"Resultado binário booleano obrigatório para unidade '{key}'{prefix}")
        keys.add(key)
    return keys


def classification(truth: Sequence[str], predicted: Sequence[str]) -> dict:
    if not truth or len(truth) != len(predicted):
        raise ValueError("Pares não vazios com mesmo N são obrigatórios")
    if any(a not in LABELS or b not in LABELS for a, b in zip(truth, predicted, strict=True)):
        raise ValueError("Classes fora do conjunto permitido (VALIDADO, DIVERGENTE, INCONCLUSIVO)")
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
    replicates: int = PROTOCOL_BOOTSTRAP_REPLICATES,
    confidence: float = PROTOCOL_BOOTSTRAP_CONFIDENCE,
) -> dict:
    validated_families = _validate_family_labels(families)
    conf = _validate_bootstrap_params(seed, replicates, confidence)
    groups = [
        [i for i, f in enumerate(validated_families) if f == name]
        for name in sorted(set(validated_families))
    ]
    rng = np.random.default_rng(seed)
    samples = [
        float(statistic([i for j in rng.integers(0, len(groups), len(groups)) for i in groups[j]]))
        for _ in range(replicates)
    ]
    estimate = float(statistic(list(range(len(validated_families)))))
    if not math.isfinite(estimate) or not np.isfinite(samples).all():
        raise ValueError("Estatística bootstrap não finita")
    alpha = (1 - conf) / 2
    low, high = np.quantile(samples, [alpha, 1 - alpha])
    is_protocol_default = bool(
        replicates == PROTOCOL_BOOTSTRAP_REPLICATES
        and math.isclose(conf, PROTOCOL_BOOTSTRAP_CONFIDENCE)
    )
    below_final_workbench = len(groups) < FINAL_WORKBENCH_FAMILIES
    warnings = (
        [
            (
                f"Amostra com {len(groups)} famílias (abaixo das {FINAL_WORKBENCH_FAMILIES} "
                f"famílias da bancada final AD-016; {FINAL_WORKBENCH_FAMILIES} é contagem da "
                "bancada sintética, não limiar científico nem garantia de validade): "
                "intervalo percentil por cluster possui resolução discreta limitada e maior incerteza."
            )
        ]
        if below_final_workbench
        else []
    )
    return {
        "estimate": estimate,
        "low": float(low),
        "high": float(high),
        "families": len(groups),
        "clusters": len(groups),
        "n": len(validated_families),
        "seed": seed,
        "replicates": replicates,
        "confidence": conf,
        "method": "family percentile",
        "resampling_unit": "family",
        "absent_class_f1": 0,
        "protocol_default_replicates": PROTOCOL_BOOTSTRAP_REPLICATES,
        "protocol_default_confidence": PROTOCOL_BOOTSTRAP_CONFIDENCE,
        "is_protocol_default": is_protocol_default,
        "parameter_regime": (
            "approved_protocol_default" if is_protocol_default else "custom_caller_override"
        ),
        "final_workbench_families": FINAL_WORKBENCH_FAMILIES,
        "below_final_workbench_family_count": below_final_workbench,
        "low_family_count_warning": below_final_workbench,
        "workbench_count_is_validity_guarantee": False,
        "automatic_independence_claimed": False,
        "population_sampling_claimed": False,
        "warnings": warnings,
        "cluster_resolution_note": (
            f"{FINAL_WORKBENCH_FAMILIES} famílias é a contagem da bancada final aprovada (AD-016), "
            "não limiar recomendável nem garantia científica de validade; mesmo com 20 famílias, "
            "intervalos percentis possuem resolução discreta limitada e não provam independência."
        ),
        "inference_scope": "synthetic_workbench_cluster_resampling; not_population_sampling",
    }


def mean_cluster_bootstrap(
    families: Sequence[str],
    run_statistics: Sequence[Callable[[list[int]], float]],
    *,
    seed: int,
    replicates: int = PROTOCOL_BOOTSTRAP_REPLICATES,
    confidence: float = PROTOCOL_BOOTSTRAP_CONFIDENCE,
) -> dict:
    """Reamostra famílias inteiras preservando casos e repetições; tira média por réplica."""
    validated_families = _validate_family_labels(families)
    if not run_statistics:
        raise ValueError("Pelo menos uma execução é obrigatória para estatística da média")
    full_ix = list(range(len(validated_families)))
    per_run_estimates = [float(fn(full_ix)) for fn in run_statistics]
    if not np.isfinite(per_run_estimates).all():
        raise ValueError("Estatística por repetição não finita")

    def mean_statistic(ix: list[int]) -> float:
        values = [float(fn(ix)) for fn in run_statistics]
        return sum(values) / len(values)

    interval = cluster_bootstrap(
        families,
        mean_statistic,
        seed=seed,
        replicates=replicates,
        confidence=confidence,
    )
    return {
        **interval,
        "repeats": len(run_statistics),
        "per_run_estimates": per_run_estimates,
        "range": [min(per_run_estimates), max(per_run_estimates)],
        "aggregation_method": (
            "mean_of_separate_run_metrics_per_replicate; matrices_not_pooled; n_not_multiplied"
        ),
        "pooled_matrices": False,
        "voting_used": False,
    }


def mcnemar_exact(first: Mapping[str, bool], second: Mapping[str, bool]) -> dict:
    first_keys = _validate_unit_outcomes(first, "first")
    second_keys = _validate_unit_outcomes(second, "second")
    if first_keys != second_keys:
        raise ValueError("Métodos devem conter exatamente as mesmas unidades")
    b = sum(first[k] and not second[k] for k in first)
    c = sum(second[k] and not first[k] for k in first)
    discordant = b + c
    concordant_correct = sum(first[k] and second[k] for k in first)
    concordant_incorrect = sum((not first[k]) and (not second[k]) for k in first)
    return {
        "n": len(first),
        "b": b,
        "c": c,
        "discordant": discordant,
        "concordant_correct": concordant_correct,
        "concordant_incorrect": concordant_incorrect,
        "p_value": (
            float(binomtest(b, discordant, 0.5, alternative="two-sided").pvalue)
            if discordant
            else 1.0
        ),
        "alternative": "two-sided",
        "method": "exact_binomial",
        "zero_discordant_policy": "p_value=1.0 when b+c==0",
    }


def holm(p_values: Mapping[str, float]) -> dict[str, float]:
    if not isinstance(p_values, Mapping) or not p_values:
        raise ValueError("Mapa não vazio de valores-p é obrigatório")
    for p in p_values.values():
        if (
            isinstance(p, bool)
            or not isinstance(p, (int, float))
            or not math.isfinite(p)
            or not 0 <= float(p) <= 1
        ):
            raise ValueError("p fora de [0,1]")
    ordered = sorted(p_values, key=lambda name: float(p_values[name]))
    adjusted, previous = {}, 0.0
    for i, name in enumerate(ordered):
        previous = max(previous, min(1.0, float(p_values[name]) * (len(ordered) - i)))
        adjusted[name] = previous
    return adjusted


def _resolve_comparison_pairs(
    methods: Mapping[str, Mapping[str, bool]],
    *,
    pairs: Sequence[tuple[str, str]] | None = None,
    reference: str | None = None,
    comparators: Sequence[str] | None = None,
) -> list[tuple[str, str]]:
    if not isinstance(methods, Mapping) or len(methods) < 2:
        raise ValueError("Pelo menos dois métodos pareados são obrigatórios")
    expected_units: set[str] | None = None
    for name, outcomes in methods.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Nome de método inválido")
        keys = _validate_unit_outcomes(outcomes, name)
        if expected_units is None:
            expected_units = keys
        elif keys != expected_units:
            raise ValueError("Métodos devem conter exatamente as mesmas unidades")

    if pairs is not None and (reference is not None or comparators is not None):
        raise ValueError("Especifique pairs ou reference/comparators, não ambos")

    if reference is not None:
        if reference not in methods:
            raise ValueError(f"Método de referência ausente: {reference}")
        target_comparators = (
            [m for m in methods if m != reference]
            if comparators is None
            else list(comparators)
        )
        if not target_comparators:
            raise ValueError("Pelo menos um comparador é obrigatório")
        seen_comp: set[str] = set()
        resolved: list[tuple[str, str]] = []
        for comp in target_comparators:
            if comp == reference:
                raise ValueError(f"Comparador não pode ser idêntico à referência: {reference}")
            if comp not in methods:
                raise ValueError(f"Método comparador ausente: {comp}")
            if comp in seen_comp:
                raise ValueError(f"Comparador duplicado: {comp}")
            seen_comp.add(comp)
            resolved.append((reference, comp))
        return resolved

    if comparators is not None:
        raise ValueError("comparators exige reference explícito")

    if pairs is not None:
        if not pairs:
            raise ValueError("Lista de pares não pode ser vazia")
        resolved = []
        seen_unordered: set[frozenset[str]] = set()
        for pair in pairs:
            if not isinstance(pair, Sequence) or isinstance(pair, (str, bytes)) or len(pair) != 2:
                raise ValueError("Cada par deve conter exatamente dois nomes de métodos")
            a, b = pair[0], pair[1]
            if a == b:
                raise ValueError(f"Comparação de método consigo mesmo inválida: {a}")
            if a not in methods or b not in methods:
                raise ValueError(f"Par referencia método inexistente: {a}:{b}")
            unordered = frozenset((a, b))
            if unordered in seen_unordered:
                raise ValueError(f"Par duplicado ou simétrico já incluído: {a}:{b}")
            seen_unordered.add(unordered)
            resolved.append((a, b))
        return resolved

    return list(combinations(methods, 2))


def paired_comparisons(
    methods: Mapping[str, Mapping[str, bool]],
    *,
    pairs: Sequence[tuple[str, str]] | None = None,
    reference: str | None = None,
    comparators: Sequence[str] | None = None,
) -> dict:
    selected_pairs = _resolve_comparison_pairs(
        methods,
        pairs=pairs,
        reference=reference,
        comparators=comparators,
    )
    tests = {
        f"{a}:{b}": mcnemar_exact(methods[a], methods[b])
        for a, b in selected_pairs
    }
    adjusted = holm({k: v["p_value"] for k, v in tests.items()})
    return {
        k: dict(
            v,
            p_holm=adjusted[k],
            reference=a,
            comparator=b,
            n_comparisons=len(selected_pairs),
        )
        for (a, b), (k, v) in zip(selected_pairs, tests.items(), strict=True)
    }
