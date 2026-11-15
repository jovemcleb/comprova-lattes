"""Relatórios descritivos offline de telemetria (raw_metadata) e métricas por categoria."""

import math
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal
from enum import Enum
from typing import Any

from comprova_lattes.matcher.models import ExtractedDocumentRecord

from .statistics import LABELS, classification
from .synthetic import CATEGORY_ORDER, Case

CURRICULUM_CATEGORIES: tuple[str, ...] = tuple(c.value for c in CATEGORY_ORDER)
DECISION_CLASSES: tuple[str, ...] = LABELS

CANONICAL_SDK_TOKEN_NAMES: dict[str, str] = {
    "input": "prompt_token_count",
    "output": "candidates_token_count",
    "total": "total_token_count",
    "thinking": "thoughts_token_count",
    "cache": "cached_content_token_count",
}

TOKEN_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "input": (
        "prompt_token_count",
        "input_token_count",
        "input_tokens",
        "prompt_tokens",
        "input",
    ),
    "output": (
        "candidates_token_count",
        "output_token_count",
        "output_tokens",
        "candidate_token_count",
        "candidates_tokens",
        "completion_token_count",
        "output",
    ),
    "total": (
        "total_token_count",
        "total_tokens",
        "total",
    ),
    "thinking": (
        "thoughts_token_count",
        "thinking_token_count",
        "thinking_tokens",
        "thoughts_tokens",
        "thought_token_count",
        "thinking",
    ),
    "cache": (
        "cached_content_token_count",
        "cached_token_count",
        "cache_token_count",
        "cached_tokens",
        "cache_tokens",
        "cache",
    ),
}


def sanitize_json_value(value: Any) -> Any:
    """Converte floats não finitos (NaN/Infinity) em None para serialização JSON estrita."""
    if isinstance(value, Enum):
        return sanitize_json_value(value.value)
    if value is None or isinstance(value, (str, bool)):
        return value
    if type(value) is int:
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        return str(value) if value.is_finite() else None
    if isinstance(value, Mapping):
        return {str(k): sanitize_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_json_value(v) for v in value]
    return str(value)


def _is_valid_latency(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    as_float = float(value)
    return math.isfinite(as_float) and as_float >= 0.0


def _is_valid_token_count(value: Any) -> bool:
    return not isinstance(value, bool) and type(value) is int and value >= 0


def _is_valid_http_code(value: Any) -> bool:
    return not isinstance(value, bool) and type(value) is int and 100 <= value <= 599


def _is_valid_attempt_number(value: Any) -> bool:
    return not isinstance(value, bool) and type(value) is int and value >= 1


def _non_empty_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None


def _case_category(case: Case) -> str:
    if len(case.curriculum.records) != 1:
        raise ValueError("Case representa exatamente um registro curricular")
    raw_cat = case.curriculum.records[0].category
    cat = raw_cat.value if isinstance(raw_cat, Enum) else str(raw_cat)
    if cat in DECISION_CLASSES:
        raise ValueError(f"Categoria curricular inválida (classe de decisão): {cat}")
    return cat


def _ordered_categories(cases: Sequence[Case]) -> list[str]:
    present = {_case_category(c) for c in cases}
    return [cat for cat in CURRICULUM_CATEGORIES if cat in present] + sorted(
        present - set(CURRICULUM_CATEGORIES)
    )


def _extract_single_token_metric(
    tokens_map: Mapping[str, Any], aliases: tuple[str, ...]
) -> tuple[str, int | None, bool]:
    """Retorna (state, value, duplicate_alias_ignored) sem somar aliases duplicados."""
    present_keys = [k for k in aliases if k in tokens_map and tokens_map[k] is not None]
    if not present_keys:
        return "absent", None, False
    dup_ignored = len(present_keys) > 1
    chosen_val = tokens_map[present_keys[0]]
    if _is_valid_token_count(chosen_val):
        return "observed", int(chosen_val), dup_ignored
    return "invalid", None, dup_ignored


def _build_token_counter_summary(
    kind: str,
    values: list[int],
    absent_n: int,
    invalid_n: int,
    duplicate_alias_ignored_n: int,
) -> dict[str, Any]:
    observed_n = len(values)
    total = sum(values) if observed_n > 0 else None
    mean = (total / observed_n) if observed_n > 0 and total is not None else None
    return {
        "sdk_field": CANONICAL_SDK_TOKEN_NAMES[kind],
        "total": total,
        "mean": mean,
        "observed_n": observed_n,
        "missing_n": absent_n + invalid_n,
        "absent_n": absent_n,
        "invalid_n": invalid_n,
        "duplicate_alias_ignored_n": duplicate_alias_ignored_n,
    }


def summarize_run_telemetry(
    outputs: Mapping[str, ExtractedDocumentRecord],
    *,
    cases: Sequence[Case] | None = None,
    reused: bool = False,
) -> dict[str, Any]:
    """Resume raw_metadata de uma execução (uma repetição ou baseline) sem fabricar zeros."""
    if cases is not None:
        expected_ids = {
            c.case_id for c in cases if c.document is not None or c.gold is not None
        }
        if set(outputs) != expected_ids:
            raise ValueError("Extrações devem cobrir os mesmos documentos dos casos")
        ordered_ids = [
            c.case_id
            for c in cases
            if c.document is not None or c.gold is not None
        ]
        total_cases = len(cases)
        no_document_cases = len(cases) - len(ordered_ids)
    else:
        ordered_ids = list(outputs.keys())
        total_cases = len(ordered_ids)
        no_document_cases = 0

    unique_documents = len(ordered_ids)
    metadata_observed_n = 0

    latencies: list[float] = []
    latency_absent_n = 0
    latency_invalid_n = 0

    token_values: dict[str, list[int]] = {k: [] for k in TOKEN_FIELD_ALIASES}
    token_absent_n: dict[str, int] = {k: 0 for k in TOKEN_FIELD_ALIASES}
    token_invalid_n: dict[str, int] = {k: 0 for k in TOKEN_FIELD_ALIASES}
    token_dup_ignored_n: dict[str, int] = {k: 0 for k in TOKEN_FIELD_ALIASES}
    tokens_doc_observed_n = 0
    tokens_doc_absent_n = 0
    tokens_doc_invalid_n = 0

    attempts_observed_n = 0
    attempts_absent_n = 0
    attempts_invalid_n = 0
    total_attempts_sum = 0
    retries_sum = 0
    docs_with_retries = 0
    failed_attempts_sum = 0
    provider_attempts: list[dict[str, Any]] = []
    attempts_by_document: dict[str, list[dict[str, Any]]] = {}
    attempt_failures_by_status: Counter[str] = Counter()
    attempt_failures_by_error_type: Counter[str] = Counter()
    attempt_failures_by_http_code: Counter[str] = Counter()
    attempt_http_code_observed_n = 0
    attempt_http_code_missing_n = 0
    attempt_http_code_invalid_n = 0

    status_counts: Counter[str] = Counter()
    failures_by_status: Counter[str] = Counter()
    failures_by_error_type: Counter[str] = Counter()
    failures_by_http_code: Counter[str] = Counter()
    document_failures_by_http_code: Counter[str] = Counter()
    failed_documents_without_http_code_n = 0
    document_http_code_invalid_n = 0

    models: list[str] = []
    model_versions: list[str] = []
    prompt_versions: list[str] = []
    temperature_policies: list[str] = []

    for doc_id in ordered_ids:
        record = outputs[doc_id]
        if record.document_id != doc_id:
            raise ValueError("ID de extração divergente")

        status_str = str(record.extraction_status)
        status_counts[status_str] += 1
        doc_failed = status_str != "OK"
        if doc_failed:
            failures_by_status[status_str] += 1

        raw = record.raw_metadata if isinstance(record.raw_metadata, Mapping) else {}
        if isinstance(record.raw_metadata, Mapping) and len(record.raw_metadata) > 0:
            metadata_observed_n += 1

        model_name = _non_empty_str(raw.get("model"))
        if model_name and model_name not in models:
            models.append(model_name)
        model_ver = _non_empty_str(raw.get("model_version"))
        if model_ver and model_ver not in model_versions:
            model_versions.append(model_ver)
        prompt_ver = _non_empty_str(raw.get("prompt_version"))
        if prompt_ver and prompt_ver not in prompt_versions:
            prompt_versions.append(prompt_ver)
        temp_policy = _non_empty_str(raw.get("temperature_policy"))
        if temp_policy and temp_policy not in temperature_policies:
            temperature_policies.append(temp_policy)

        # 1. latency_ms
        if "latency_ms" not in raw or raw["latency_ms"] is None:
            latency_absent_n += 1
        elif _is_valid_latency(raw["latency_ms"]):
            latencies.append(float(raw["latency_ms"]))
        else:
            latency_invalid_n += 1

        # 2. tokens (input, output, total, thinking, cache)
        if "tokens" not in raw or raw["tokens"] is None:
            tokens_doc_absent_n += 1
            for kind in TOKEN_FIELD_ALIASES:
                token_absent_n[kind] += 1
        elif not isinstance(raw["tokens"], Mapping):
            tokens_doc_invalid_n += 1
            for kind in TOKEN_FIELD_ALIASES:
                token_invalid_n[kind] += 1
        else:
            tokens_map = raw["tokens"]
            any_observed = False
            any_invalid = False
            for kind, aliases in TOKEN_FIELD_ALIASES.items():
                state, val, dup_ignored = _extract_single_token_metric(tokens_map, aliases)
                if dup_ignored:
                    token_dup_ignored_n[kind] += 1
                if state == "observed" and val is not None:
                    token_values[kind].append(val)
                    any_observed = True
                elif state == "absent":
                    token_absent_n[kind] += 1
                else:
                    token_invalid_n[kind] += 1
                    any_invalid = True
            if any_observed:
                tokens_doc_observed_n += 1
            elif any_invalid:
                tokens_doc_invalid_n += 1
            else:
                tokens_doc_absent_n += 1
            if any_observed and any_invalid:
                tokens_doc_invalid_n += 1

        # 3. attempts & HTTP / error_type failures
        raw_attempts = raw.get("attempts")
        doc_has_valid_attempts = False
        last_failed_attempt_http_code: int | None = None

        if "attempts" not in raw or raw_attempts is None or raw_attempts == []:
            attempts_absent_n += 1
        elif not isinstance(raw_attempts, list) or any(
            not isinstance(item, Mapping) for item in raw_attempts
        ):
            attempts_invalid_n += 1
        else:
            doc_has_valid_attempts = True
            attempts_observed_n += 1
            doc_attempt_count = len(raw_attempts)
            doc_retries = max(0, doc_attempt_count - 1)
            total_attempts_sum += doc_attempt_count
            retries_sum += doc_retries
            if doc_retries > 0:
                docs_with_retries += 1

            normalized_doc_attempts: list[dict[str, Any]] = []
            for idx, item in enumerate(raw_attempts, start=1):
                raw_num = item.get("number")
                num = raw_num if _is_valid_attempt_number(raw_num) else idx
                att_status = _non_empty_str(item.get("status"))
                att_error = _non_empty_str(item.get("error_type"))
                raw_code = item.get("http_code")
                if raw_code is None:
                    att_code = None
                elif _is_valid_http_code(raw_code):
                    att_code = int(raw_code)
                else:
                    att_code = None
                    attempt_http_code_invalid_n += 1

                attempt_failed = (
                    (att_status is not None and att_status != "OK")
                    or att_error is not None
                    or (att_code is not None and att_code >= 400)
                )
                effective_status = (
                    att_status
                    if att_status is not None
                    else ("ERROR" if attempt_failed else "OK")
                )
                entry = {
                    "document_id": doc_id,
                    "number": num,
                    "status": effective_status,
                    "error_type": att_error,
                    "http_code": att_code,
                }
                normalized_doc_attempts.append(entry)
                provider_attempts.append(entry)

                if attempt_failed:
                    failed_attempts_sum += 1
                    status_key = (
                        att_status
                        if (att_status is not None and att_status != "OK")
                        else (att_error or "ERROR")
                    )
                    attempt_failures_by_status[status_key] += 1
                    if att_error is not None:
                        attempt_failures_by_error_type[att_error] += 1
                    if att_code is not None:
                        code_key = str(att_code)
                        attempt_failures_by_http_code[code_key] += 1
                        failures_by_http_code[code_key] += 1
                        attempt_http_code_observed_n += 1
                        last_failed_attempt_http_code = att_code
                    else:
                        attempt_http_code_missing_n += 1

            attempts_by_document[doc_id] = normalized_doc_attempts

        raw_top_code = raw.get("http_code")
        top_http_code: int | None = None
        if raw_top_code is not None:
            if _is_valid_http_code(raw_top_code):
                top_http_code = int(raw_top_code)
            else:
                document_http_code_invalid_n += 1

        top_error_type = _non_empty_str(raw.get("error_type"))
        if doc_failed and top_error_type is not None:
            failures_by_error_type[top_error_type] += 1

        if doc_failed:
            doc_code = (
                top_http_code
                if top_http_code is not None
                else last_failed_attempt_http_code
            )
            if doc_code is not None:
                document_failures_by_http_code[str(doc_code)] += 1
                if not doc_has_valid_attempts:
                    failures_by_http_code[str(doc_code)] += 1
            else:
                failed_documents_without_http_code_n += 1
        elif not doc_has_valid_attempts and top_http_code is not None and top_http_code >= 400:
            failures_by_http_code[str(top_http_code)] += 1

    latency_observed_n = len(latencies)
    latency_total = sum(latencies) if latency_observed_n > 0 else None
    latency_mean = (
        latency_total / latency_observed_n
        if latency_observed_n > 0 and latency_total is not None
        else None
    )
    latency_min = min(latencies) if latency_observed_n > 0 else None
    latency_max = max(latencies) if latency_observed_n > 0 else None

    token_summaries = {
        kind: _build_token_counter_summary(
            kind,
            token_values[kind],
            token_absent_n[kind],
            token_invalid_n[kind],
            token_dup_ignored_n[kind],
        )
        for kind in TOKEN_FIELD_ALIASES
    }

    total_attempts_val = total_attempts_sum if attempts_observed_n > 0 else None
    mean_attempts_val = (
        total_attempts_sum / attempts_observed_n if attempts_observed_n > 0 else None
    )
    retries_val = retries_sum if attempts_observed_n > 0 else None
    docs_with_retries_val = docs_with_retries if attempts_observed_n > 0 else None
    failed_attempts_val = failed_attempts_sum if attempts_observed_n > 0 else None
    succeeded_attempts_val = (
        total_attempts_sum - failed_attempts_sum if attempts_observed_n > 0 else None
    )

    return sanitize_json_value(
        {
            "unique_documents": unique_documents,
            "total_cases": total_cases,
            "no_document_cases": no_document_cases,
            "logical_executions": 0 if reused else unique_documents,
            "source_logical_executions": unique_documents,
            "reused": bool(reused),
            "calls": 0 if reused else total_attempts_val,
            "new_calls": 0 if reused else total_attempts_val,
            "metadata_observed_n": metadata_observed_n,
            "metadata_missing_n": unique_documents - metadata_observed_n,
            "latency_ms": {
                "total": latency_total,
                "mean": latency_mean,
                "min": latency_min,
                "max": latency_max,
                "total_ms": latency_total,
                "mean_ms": latency_mean,
                "min_ms": latency_min,
                "max_ms": latency_max,
                "observed_n": latency_observed_n,
                "missing_n": latency_absent_n + latency_invalid_n,
                "absent_n": latency_absent_n,
                "invalid_n": latency_invalid_n,
            },
            "tokens": {
                "observed_n": tokens_doc_observed_n,
                "missing_n": unique_documents - tokens_doc_observed_n,
                "absent_n": tokens_doc_absent_n,
                "invalid_n": tokens_doc_invalid_n,
                "total_inferred_from_parts": False,
                "input": token_summaries["input"],
                "output": token_summaries["output"],
                "total": token_summaries["total"],
                "thinking": token_summaries["thinking"],
                "cache": token_summaries["cache"],
                "prompt_token_count": dict(token_summaries["input"]),
                "candidates_token_count": dict(token_summaries["output"]),
                "total_token_count": dict(token_summaries["total"]),
                "thoughts_token_count": dict(token_summaries["thinking"]),
                "cached_content_token_count": dict(token_summaries["cache"]),
            },
            "attempts": {
                "observed_n": attempts_observed_n,
                "missing_n": attempts_absent_n + attempts_invalid_n,
                "absent_n": attempts_absent_n,
                "invalid_n": attempts_invalid_n,
                "total_attempts": total_attempts_val,
                "mean_attempts": mean_attempts_val,
                "retries": retries_val,
                "documents_with_retries": docs_with_retries_val,
                "failed_attempts": failed_attempts_val,
                "succeeded_attempts": succeeded_attempts_val,
                "provider_attempts": provider_attempts,
                "by_document": attempts_by_document,
                "failures_by_status": dict(attempt_failures_by_status),
                "failures_by_error_type": dict(attempt_failures_by_error_type),
                "failures_by_http_code": dict(attempt_failures_by_http_code),
                "http_code_observed_n": attempt_http_code_observed_n,
                "http_code_missing_n": attempt_http_code_missing_n,
                "http_code_invalid_n": attempt_http_code_invalid_n,
            },
            "status_counts": dict(status_counts),
            "failures_by_status": dict(failures_by_status),
            "failures_by_error_type": dict(failures_by_error_type),
            "failures_by_http_code": dict(failures_by_http_code),
            "document_failures_by_http_code": dict(document_failures_by_http_code),
            "failed_documents_without_http_code_n": failed_documents_without_http_code_n,
            "document_http_code_invalid_n": document_http_code_invalid_n,
            "models": models,
            "model_versions": model_versions,
            "prompt_versions": prompt_versions,
            "temperature_policies": temperature_policies,
            "cost_estimate": None,
        }
    )


def _aggregate_run_telemetries(
    run_summaries: Sequence[Mapping[str, Any]],
    *,
    unique_documents: int,
    total_cases: int,
    no_document_cases: int,
    reused: bool,
) -> dict[str, Any]:
    """Agrega descritivamente execuções sem somar documentos únicos (N) nem fabricar zeros."""
    repeats = len(run_summaries)
    source_logical_executions = repeats * unique_documents
    logical_executions = 0 if reused else source_logical_executions

    lat_obs = sum(int(r["latency_ms"]["observed_n"]) for r in run_summaries)
    lat_abs = sum(int(r["latency_ms"]["absent_n"]) for r in run_summaries)
    lat_inv = sum(int(r["latency_ms"]["invalid_n"]) for r in run_summaries)
    lat_totals = [
        float(r["latency_ms"]["total"])
        for r in run_summaries
        if r["latency_ms"]["total"] is not None
    ]
    lat_mins = [
        float(r["latency_ms"]["min"])
        for r in run_summaries
        if r["latency_ms"]["min"] is not None
    ]
    lat_maxs = [
        float(r["latency_ms"]["max"])
        for r in run_summaries
        if r["latency_ms"]["max"] is not None
    ]
    lat_total = sum(lat_totals) if lat_obs > 0 else None
    lat_mean = (lat_total / lat_obs) if lat_obs > 0 and lat_total is not None else None
    lat_min = min(lat_mins) if lat_obs > 0 and lat_mins else None
    lat_max = max(lat_maxs) if lat_obs > 0 and lat_maxs else None

    tokens_agg: dict[str, Any] = {
        "observed_n": sum(int(r["tokens"]["observed_n"]) for r in run_summaries),
        "missing_n": sum(int(r["tokens"]["missing_n"]) for r in run_summaries),
        "absent_n": sum(int(r["tokens"]["absent_n"]) for r in run_summaries),
        "invalid_n": sum(int(r["tokens"]["invalid_n"]) for r in run_summaries),
        "total_inferred_from_parts": False,
    }
    for kind in TOKEN_FIELD_ALIASES:
        obs_n = sum(int(r["tokens"][kind]["observed_n"]) for r in run_summaries)
        abs_n = sum(int(r["tokens"][kind]["absent_n"]) for r in run_summaries)
        inv_n = sum(int(r["tokens"][kind]["invalid_n"]) for r in run_summaries)
        dup_n = sum(
            int(r["tokens"][kind]["duplicate_alias_ignored_n"]) for r in run_summaries
        )
        part_totals = [
            int(r["tokens"][kind]["total"])
            for r in run_summaries
            if r["tokens"][kind]["total"] is not None
        ]
        tot_val = sum(part_totals) if obs_n > 0 else None
        mean_val = (tot_val / obs_n) if obs_n > 0 and tot_val is not None else None
        entry = {
            "sdk_field": CANONICAL_SDK_TOKEN_NAMES[kind],
            "total": tot_val,
            "mean": mean_val,
            "observed_n": obs_n,
            "missing_n": abs_n + inv_n,
            "absent_n": abs_n,
            "invalid_n": inv_n,
            "duplicate_alias_ignored_n": dup_n,
        }
        tokens_agg[kind] = entry
        tokens_agg[CANONICAL_SDK_TOKEN_NAMES[kind]] = dict(entry)

    att_obs = sum(int(r["attempts"]["observed_n"]) for r in run_summaries)
    att_abs = sum(int(r["attempts"]["absent_n"]) for r in run_summaries)
    att_inv = sum(int(r["attempts"]["invalid_n"]) for r in run_summaries)
    att_totals = [
        int(r["attempts"]["total_attempts"])
        for r in run_summaries
        if r["attempts"]["total_attempts"] is not None
    ]
    att_retries = [
        int(r["attempts"]["retries"])
        for r in run_summaries
        if r["attempts"]["retries"] is not None
    ]
    att_docs_retries = [
        int(r["attempts"]["documents_with_retries"])
        for r in run_summaries
        if r["attempts"]["documents_with_retries"] is not None
    ]
    att_failed = [
        int(r["attempts"]["failed_attempts"])
        for r in run_summaries
        if r["attempts"]["failed_attempts"] is not None
    ]
    tot_attempts = sum(att_totals) if att_obs > 0 else None
    tot_retries = sum(att_retries) if att_obs > 0 else None
    tot_docs_retries = sum(att_docs_retries) if att_obs > 0 else None
    tot_failed_attempts = sum(att_failed) if att_obs > 0 else None
    tot_succeeded_attempts = (
        tot_attempts - tot_failed_attempts
        if tot_attempts is not None and tot_failed_attempts is not None
        else None
    )

    att_fail_status: Counter[str] = Counter()
    att_fail_error: Counter[str] = Counter()
    att_fail_http: Counter[str] = Counter()
    doc_status: Counter[str] = Counter()
    doc_fail_status: Counter[str] = Counter()
    doc_fail_error: Counter[str] = Counter()
    doc_fail_http_all: Counter[str] = Counter()
    doc_fail_http_final: Counter[str] = Counter()
    for r in run_summaries:
        att_fail_status.update(r["attempts"]["failures_by_status"])
        att_fail_error.update(r["attempts"]["failures_by_error_type"])
        att_fail_http.update(r["attempts"]["failures_by_http_code"])
        doc_status.update(r["status_counts"])
        doc_fail_status.update(r["failures_by_status"])
        doc_fail_error.update(r["failures_by_error_type"])
        doc_fail_http_all.update(r["failures_by_http_code"])
        doc_fail_http_final.update(r["document_failures_by_http_code"])

    return sanitize_json_value(
        {
            "unique_documents": unique_documents,
            "total_cases": total_cases,
            "no_document_cases": no_document_cases,
            "repeats": repeats,
            "logical_executions": logical_executions,
            "source_logical_executions": source_logical_executions,
            "reused": bool(reused),
            "calls": 0 if reused else tot_attempts,
            "new_calls": 0 if reused else tot_attempts,
            "metadata_observed_n": sum(int(r["metadata_observed_n"]) for r in run_summaries),
            "metadata_missing_n": sum(int(r["metadata_missing_n"]) for r in run_summaries),
            "latency_ms": {
                "total": lat_total,
                "mean": lat_mean,
                "min": lat_min,
                "max": lat_max,
                "total_ms": lat_total,
                "mean_ms": lat_mean,
                "min_ms": lat_min,
                "max_ms": lat_max,
                "observed_n": lat_obs,
                "missing_n": lat_abs + lat_inv,
                "absent_n": lat_abs,
                "invalid_n": lat_inv,
            },
            "tokens": tokens_agg,
            "attempts": {
                "observed_n": att_obs,
                "missing_n": att_abs + att_inv,
                "absent_n": att_abs,
                "invalid_n": att_inv,
                "total_attempts": tot_attempts,
                "mean_attempts": (tot_attempts / att_obs)
                if att_obs > 0 and tot_attempts is not None
                else None,
                "retries": tot_retries,
                "documents_with_retries": tot_docs_retries,
                "failed_attempts": tot_failed_attempts,
                "succeeded_attempts": tot_succeeded_attempts,
                "failures_by_status": dict(att_fail_status),
                "failures_by_error_type": dict(att_fail_error),
                "failures_by_http_code": dict(att_fail_http),
                "http_code_observed_n": sum(
                    int(r["attempts"]["http_code_observed_n"]) for r in run_summaries
                ),
                "http_code_missing_n": sum(
                    int(r["attempts"]["http_code_missing_n"]) for r in run_summaries
                ),
                "http_code_invalid_n": sum(
                    int(r["attempts"]["http_code_invalid_n"]) for r in run_summaries
                ),
            },
            "status_counts": dict(doc_status),
            "failures_by_status": dict(doc_fail_status),
            "failures_by_error_type": dict(doc_fail_error),
            "failures_by_http_code": dict(doc_fail_http_all),
            "document_failures_by_http_code": dict(doc_fail_http_final),
            "failed_documents_without_http_code_n": sum(
                int(r["failed_documents_without_http_code_n"]) for r in run_summaries
            ),
            "cost_estimate": None,
        }
    )


def summarize_experiment1_telemetry(
    cases: Sequence[Case],
    runs: Sequence[Mapping[str, ExtractedDocumentRecord]],
    baseline_outputs: Mapping[str, ExtractedDocumentRecord],
) -> dict[str, Any]:
    """Resume telemetria do Exp 1 por repetição e para o baseline OCR, preservando N."""
    run_summaries = [
        summarize_run_telemetry(run, cases=cases, reused=False) for run in runs
    ]
    baseline_summary = summarize_run_telemetry(
        baseline_outputs, cases=cases, reused=False
    )
    unique_documents = baseline_summary["unique_documents"]
    total_cases = baseline_summary["total_cases"]
    no_document_cases = baseline_summary["no_document_cases"]
    extractor_totals = _aggregate_run_telemetries(
        run_summaries,
        unique_documents=unique_documents,
        total_cases=total_cases,
        no_document_cases=no_document_cases,
        reused=False,
    )
    return sanitize_json_value(
        {
            "unique_documents": unique_documents,
            "total_cases": total_cases,
            "no_document_cases": no_document_cases,
            "repeats": len(run_summaries),
            "extractor_logical_executions": len(run_summaries) * unique_documents,
            "baseline_logical_executions": unique_documents,
            "reused": False,
            "new_calls": extractor_totals["new_calls"],
            "runs": run_summaries,
            "baseline": baseline_summary,
            "extractor_totals": extractor_totals,
            "cost_estimate": None,
            "repetition_policy": "report separately; never pool repetitions as N",
        }
    )


def summarize_experiment3_telemetry(
    cases: Sequence[Case],
    outputs: Sequence[Mapping[str, ExtractedDocumentRecord]],
) -> dict[str, Any]:
    """Resume telemetria reutilizada no Exp 3 com reused=True e zero chamadas novas."""
    if len(outputs) != 3:
        raise ValueError("Exp 3 reutiliza exatamente as 3 extrações de Exp 1")
    reused_runs = [
        summarize_run_telemetry(run, cases=cases, reused=True) for run in outputs
    ]
    unique_documents = reused_runs[0]["unique_documents"] if reused_runs else 0
    total_cases = len(cases)
    no_document_cases = total_cases - unique_documents
    reused_source_totals = _aggregate_run_telemetries(
        reused_runs,
        unique_documents=unique_documents,
        total_cases=total_cases,
        no_document_cases=no_document_cases,
        reused=True,
    )
    return sanitize_json_value(
        {
            "reused": True,
            "calls": 0,
            "new_calls": 0,
            "new_logical_executions": 0,
            "new_provider_attempts": 0,
            "new_tokens": 0,
            "new_latency_ms": 0.0,
            "unique_documents": unique_documents,
            "total_cases": total_cases,
            "no_document_cases": no_document_cases,
            "repeats": len(reused_runs),
            "logical_executions": 0,
            "source_logical_executions": len(reused_runs) * unique_documents,
            "runs": reused_runs,
            "reused_runs": reused_runs,
            "reused_source_totals": reused_source_totals,
            "cost_estimate": None,
            "accounting_policy": "reused_from_exp1; zero_new_calls; do_not_double_count",
            "repetition_policy": "separate; N unchanged",
        }
    )


def extraction_by_category(
    cases: Sequence[Case],
    outputs: Mapping[str, ExtractedDocumentRecord],
    *,
    equivalent: bool = False,
    metric_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Calcula métricas de extração por categoria curricular usando extraction_metrics."""
    if not cases:
        raise ValueError("Casos não vazios obrigatórios")
    documents = [c for c in cases if c.gold is not None]
    if set(outputs) != {c.case_id for c in documents}:
        raise ValueError("Extrações devem cobrir os mesmos documentos")

    if metric_fn is None:
        from .runner import _extraction_metrics_core as metric_fn

    result: dict[str, dict[str, Any]] = {}
    for cat in _ordered_categories(cases):
        cat_cases = [c for c in cases if _case_category(c) == cat]
        cat_docs = [c for c in cat_cases if c.gold is not None]
        cat_outputs = {c.case_id: outputs[c.case_id] for c in cat_docs}
        metrics = metric_fn(cat_cases, cat_outputs, equivalent=equivalent)
        result[cat] = {
            "category": cat,
            **metrics,
            "total_cases": len(cat_cases),
            "documents_n": len(cat_docs),
            "excluded_no_document_n": len(cat_cases) - len(cat_docs),
            "denominator_unit": "documents_with_gold",
        }
    return result


def experiment1_by_category(
    cases: Sequence[Case],
    runs: Sequence[Mapping[str, ExtractedDocumentRecord]],
    baseline_outputs: Mapping[str, ExtractedDocumentRecord],
    *,
    literal_reports: Sequence[Mapping[str, Any]] | None = None,
    equivalent_reports: Sequence[Mapping[str, Any]] | None = None,
    baseline_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Organiza métricas de extração por categoria para as 3 repetições e o baseline."""
    literal = (
        [dict(r["by_category"]) for r in literal_reports]
        if literal_reports is not None and all("by_category" in r for r in literal_reports)
        else [extraction_by_category(cases, r, equivalent=False) for r in runs]
    )
    equivalent = (
        [dict(r["by_category"]) for r in equivalent_reports]
        if equivalent_reports is not None and all("by_category" in r for r in equivalent_reports)
        else [extraction_by_category(cases, r, equivalent=True) for r in runs]
    )
    baseline = (
        dict(baseline_report["by_category"])
        if baseline_report is not None and "by_category" in baseline_report
        else extraction_by_category(cases, baseline_outputs, equivalent=False)
    )
    return {
        "categories": _ordered_categories(cases),
        "repeats": len(runs),
        "literal": literal,
        "equivalent": equivalent,
        "baseline": baseline,
        "denominator_unit": "documents_with_gold",
        "repetition_policy": "report separately; never pool repetitions as N",
    }


def classification_by_category(
    cases: Sequence[Case],
    rows_or_report: Sequence[Mapping[str, Any]] | Mapping[str, Any],
    *,
    orphans: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Agrupa rows já avaliadas por categoria curricular sem rerodar match_curriculum."""
    if not cases or len({c.case_id for c in cases}) != len(cases):
        raise ValueError("Casos únicos não vazios obrigatórios")
    if isinstance(rows_or_report, Mapping):
        rows = list(rows_or_report["rows"])
        if orphans is None and "DOCUMENTO_NAO_ASSOCIADO" in rows_or_report:
            orphans = list(rows_or_report["DOCUMENTO_NAO_ASSOCIADO"])
    else:
        rows = list(rows_or_report)

    if [r["case_id"] for r in rows] != [c.case_id for c in cases]:
        raise ValueError("Pareamento entre casos e rows divergente")

    orphan_list = list(orphans) if orphans is not None else []
    by_category: dict[str, dict[str, Any]] = {}

    for cat in _ordered_categories(cases):
        pairs = [
            (c, row)
            for c, row in zip(cases, rows, strict=True)
            if _case_category(c) == cat
        ]
        truth = [str(r["expected"]) for _, r in pairs]
        predicted = [str(r["status"]) for _, r in pairs]
        cat_rows = [r for _, r in pairs]

        tp = fp = fn = association_correct = 0
        causes: Counter[str] = Counter()
        reasons: Counter[str] = Counter()
        conditional: list[bool] = []
        cat_doc_ids = {c.case_id for c, _ in pairs if c.gold is not None}

        for c, row in pairs:
            expected_pair = c.case_id if c.gold is not None else None
            assoc_ok = bool(row["association_correct"])
            matched_id = row["automatic"].get("matched_document_id")
            association_correct += int(assoc_ok)
            tp += int(expected_pair is not None and assoc_ok)
            fp += int(matched_id is not None and not assoc_ok)
            fn += int(expected_pair is not None and not assoc_ok)
            if assoc_ok:
                conditional.append(bool(row["correct"]))
            if row.get("error_cause") is not None:
                causes[str(row["error_cause"])] += 1
            reasons[str(row["reason"])] += 1

        doc_pairs = [(c, r) for c, r in pairs if c.gold is not None]
        without_no_doc = (
            classification(
                [str(r["expected"]) for _, r in doc_pairs],
                [str(r["status"]) for _, r in doc_pairs],
            )
            if doc_pairs
            else None
        )
        cat_orphans = [
            o for o in orphan_list if o.get("document_id") in cat_doc_ids
        ]

        by_category[cat] = dict(
            classification(truth, predicted),
            category=cat,
            total_cases=len(pairs),
            with_document_n=len(doc_pairs),
            no_document_n=len(pairs) - len(doc_pairs),
            denominator_unit="curriculum_records_including_no_document",
            rows=cat_rows,
            reasons=dict(reasons),
            association={
                "accuracy": association_correct / len(pairs),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": tp / (tp + fp) if tp + fp else 0,
                "recall": tp / (tp + fn) if tp + fn else 0,
            },
            DOCUMENTO_NAO_ASSOCIADO=cat_orphans,
            error_causes=dict(causes),
            conditional_association_n=len(conditional),
            conditional_class_accuracy=sum(conditional) / len(conditional)
            if conditional
            else None,
            review_stage="automatic_before_human_review",
            without_no_document=without_no_doc,
        )

    return by_category


def experiment2_by_category(
    reports: Mapping[str, Mapping[str, Any]],
    cases: Sequence[Case] | None = None,
) -> dict[str, dict[str, Any]]:
    """Retorna os relatórios por categoria de cada configuração do Exp 2 sem rerodar o motor."""
    out: dict[str, dict[str, Any]] = {}
    for name, report in reports.items():
        if "by_category" in report and cases is None:
            out[name] = dict(report["by_category"])
        elif cases is not None:
            out[name] = classification_by_category(cases, report)
        else:
            raise ValueError(f"Relatório {name!r} sem by_category; informe cases")
    return out


def experiment3_by_category(
    report_or_runs: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    cases: Sequence[Case] | None = None,
) -> dict[str, Any]:
    """Organiza os relatórios por categoria do Exp 3 mantendo as 3 repetições separadas."""
    if isinstance(report_or_runs, Mapping):
        runs = list(report_or_runs["runs"])
        oracle = report_or_runs.get("oracle")
    else:
        runs = list(report_or_runs)
        oracle = None

    if len(runs) != 3:
        raise ValueError("Exp 3 exige exatamente 3 repetições separadas")

    runs_by_cat = []
    for run in runs:
        if "by_category" in run and cases is None:
            runs_by_cat.append(dict(run["by_category"]))
        elif cases is not None:
            runs_by_cat.append(classification_by_category(cases, run))
        else:
            raise ValueError("Run sem by_category; informe cases")

    oracle_by_cat = None
    if oracle is not None:
        if "by_category" in oracle and cases is None:
            oracle_by_cat = dict(oracle["by_category"])
        elif cases is not None:
            oracle_by_cat = classification_by_category(cases, oracle)

    return {
        "repeats": 3,
        "runs": runs_by_cat,
        "oracle": oracle_by_cat,
        "denominator_unit": "curriculum_records_including_no_document",
        "repetition_policy": "separate; N unchanged",
    }
