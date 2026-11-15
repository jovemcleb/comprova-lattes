"""Testes offline de relatórios descritivos de telemetria e métricas por categoria."""

import json
from collections import Counter

import pytest

from comprova_lattes.experiments.__main__ import Replay, _default
from comprova_lattes.experiments.baseline import FIELDS
from comprova_lattes.experiments.reporting import (
    CURRICULUM_CATEGORIES,
    DECISION_CLASSES,
    classification_by_category,
    experiment1_by_category,
    experiment2_by_category,
    experiment3_by_category,
    extraction_by_category,
    summarize_experiment1_telemetry,
    summarize_experiment3_telemetry,
    summarize_run_telemetry,
)
from comprova_lattes.experiments.runner import (
    evaluate,
    experiment1,
    experiment2,
    experiment3,
    extraction_metrics,
)
from comprova_lattes.experiments.synthetic import generate, synthetic_acronyms
from comprova_lattes.matcher.models import (
    ExtractedDocumentRecord,
    MatcherConfig,
    MatcherThresholds,
)


@pytest.fixture(scope="module")
def corpus():
    return generate(seed=93, pilot_families=5, final_families=5)


@pytest.fixture(scope="module")
def pilot_cases(corpus):
    return corpus.select("pilot")


@pytest.fixture
def config(pilot_cases):
    return MatcherConfig(
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


def _dump_strict_json(payload) -> str:
    text = json.dumps(payload, default=_default, sort_keys=True, allow_nan=False)
    assert "NaN" not in text
    assert "Infinity" not in text
    return text


def test_run_telemetry_retries_failures_http_codes_and_alias_deduplication(pilot_cases):
    docs = [c for c in pilot_cases if c.gold is not None][:6]
    cases_slice = [
        *docs,
        next(c for c in pilot_cases if c.gold is None),
    ]
    d0, d1, d2, d3, d4, d5 = (c.case_id for c in docs)

    outputs = {
        # d0: sucesso após retry (503 -> OK), todos os 5 contadores de tokens com aliases duplicados
        d0: docs[0].gold.model_copy(
            update={
                "raw_metadata": {
                    "model": "gemini-3.5-flash-lite",
                    "model_version": "gemini-3.5-flash-lite-001",
                    "prompt_version": "entities-v2",
                    "temperature_policy": "provider_default",
                    "latency_ms": 150.0,
                    "tokens": {
                        "prompt_token_count": 100,
                        "input_tokens": 100,
                        "input_token_count": 999,
                        "candidates_token_count": 40,
                        "output_tokens": 40,
                        "total_token_count": 155,
                        "total_tokens": 155,
                        "thoughts_token_count": 15,
                        "thinking_tokens": 15,
                        "cached_content_token_count": 20,
                        "cache_tokens": 20,
                    },
                    "attempts": [
                        {"number": 1, "error_type": "ServerError", "http_code": 503},
                        {"number": 2, "status": "OK"},
                    ],
                }
            }
        ),
        # d1: sucesso na 1ª tentativa, tokens parciais (sem total_token_count, sem thinking, sem cache)
        # O total NÃO deve ser inferido somando prompt_token_count + candidates_token_count.
        d1: docs[1].gold.model_copy(
            update={
                "raw_metadata": {
                    "model": "gemini-3.5-flash-lite",
                    "model_version": "gemini-3.5-flash-lite-001",
                    "prompt_version": "entities-v2",
                    "temperature_policy": "provider_default",
                    "latency_ms": 50.0,
                    "tokens": {
                        "prompt_token_count": 80,
                        "candidates_token_count": 20,
                    },
                    "attempts": [{"number": 1, "status": "OK"}],
                }
            }
        ),
        # d2: falha API_ERROR após 2 tentativas (503 -> 504); http_code no topo = 504 (igual à tentativa 2)
        d2: ExtractedDocumentRecord(
            document_id=d2,
            extraction_status="API_ERROR",
            raw_metadata={
                "model": "gemini-3.5-flash-lite",
                "latency_ms": 300.0,
                "tokens": None,
                "error_type": "ServerError",
                "http_code": 504,
                "attempts": [
                    {"number": 1, "error_type": "ServerError", "http_code": 503},
                    {"number": 2, "error_type": "ServerError", "http_code": 504},
                ],
            },
        ),
        # d3: falha API_ERROR por timeout sem http_code (None)
        d3: ExtractedDocumentRecord(
            document_id=d3,
            extraction_status="API_ERROR",
            raw_metadata={
                "model": "gemini-3.5-flash-lite",
                "latency_ms": 400.0,
                "tokens": None,
                "error_type": "TimeoutError",
                "http_code": None,
                "attempts": [
                    {"number": 1, "error_type": "TimeoutError", "http_code": None},
                ],
            },
        ),
        # d4: falha INVALID_JSON após chamada HTTP 200 OK
        d4: ExtractedDocumentRecord(
            document_id=d4,
            extraction_status="INVALID_JSON",
            raw_metadata={
                "model": "gemini-3.5-flash-lite",
                "latency_ms": 100.0,
                "error_type": "INVALID_RESPONSE",
                "tokens": {
                    "prompt_token_count": 60,
                    "candidates_token_count": 10,
                    "total_token_count": 70,
                },
                "attempts": [{"number": 1, "status": "OK"}],
            },
        ),
        # d5: falha UNREADABLE sem metadados (como baseline ou simulação enxuta)
        d5: ExtractedDocumentRecord(
            document_id=d5,
            extraction_status="UNREADABLE",
            raw_metadata={},
        ),
    }

    telemetry = summarize_run_telemetry(outputs, cases=cases_slice, reused=False)
    _dump_strict_json(telemetry)

    # Unidades distintas
    assert telemetry["unique_documents"] == 6
    assert telemetry["total_cases"] == 7
    assert telemetry["no_document_cases"] == 1
    assert telemetry["logical_executions"] == 6
    assert telemetry["source_logical_executions"] == 6
    assert telemetry["reused"] is False
    assert telemetry["metadata_observed_n"] == 5
    assert telemetry["metadata_missing_n"] == 1
    assert telemetry["cost_estimate"] is None

    # Latência: 5 observados (150 + 50 + 300 + 400 + 100 = 1000 ms), 1 ausente
    lat = telemetry["latency_ms"]
    assert lat["observed_n"] == 5
    assert lat["missing_n"] == 1
    assert lat["absent_n"] == 1
    assert lat["invalid_n"] == 0
    assert lat["total"] == pytest.approx(1000.0)
    assert lat["mean"] == pytest.approx(200.0)
    assert lat["min"] == pytest.approx(50.0)
    assert lat["max"] == pytest.approx(400.0)

    # Tokens: sem somar aliases duplicados e sem inferir total pela soma parcial de d1
    tok = telemetry["tokens"]
    assert tok["total_inferred_from_parts"] is False
    assert tok["observed_n"] == 3
    assert tok["missing_n"] == 3

    # input: d0 (100), d1 (80), d4 (60) -> total 240, média 80, 3 observados, 3 ausentes
    assert tok["input"]["total"] == 240
    assert tok["input"]["mean"] == pytest.approx(80.0)
    assert tok["input"]["observed_n"] == 3
    assert tok["input"]["missing_n"] == 3
    assert tok["input"]["duplicate_alias_ignored_n"] == 1
    assert tok["prompt_token_count"]["total"] == 240

    # output: d0 (40), d1 (20), d4 (10) -> total 70, 3 observados, 3 ausentes
    assert tok["output"]["total"] == 70
    assert tok["output"]["mean"] == pytest.approx(70 / 3)
    assert tok["output"]["observed_n"] == 3
    assert tok["output"]["missing_n"] == 3
    assert tok["output"]["duplicate_alias_ignored_n"] == 1
    assert tok["candidates_token_count"]["total"] == 70

    # total: apenas d0 (155) e d4 (70) -> total 225 (d1 NÃO foi inferido como 100!)
    assert tok["total"]["total"] == 225
    assert tok["total"]["mean"] == pytest.approx(112.5)
    assert tok["total"]["observed_n"] == 2
    assert tok["total"]["missing_n"] == 4
    assert tok["total"]["duplicate_alias_ignored_n"] == 1
    assert tok["total_token_count"]["total"] == 225

    # thinking: apenas d0 (15) -> 1 observado, 5 ausentes
    assert tok["thinking"]["total"] == 15
    assert tok["thinking"]["mean"] == pytest.approx(15.0)
    assert tok["thinking"]["observed_n"] == 1
    assert tok["thinking"]["missing_n"] == 5
    assert tok["thoughts_token_count"]["total"] == 15

    # cache: apenas d0 (20) -> 1 observado, 5 ausentes
    assert tok["cache"]["total"] == 20
    assert tok["cache"]["mean"] == pytest.approx(20.0)
    assert tok["cache"]["observed_n"] == 1
    assert tok["cache"]["missing_n"] == 5
    assert tok["cached_content_token_count"]["total"] == 20

    # Attempts: 5 documentos com attempts (2 + 1 + 2 + 1 + 1 = 7 tentativas, 2 retries)
    att = telemetry["attempts"]
    assert att["observed_n"] == 5
    assert att["missing_n"] == 1
    assert att["total_attempts"] == 7
    assert att["retries"] == 2
    assert att["documents_with_retries"] == 2
    assert att["failed_attempts"] == 4
    assert att["succeeded_attempts"] == 3
    assert len(att["provider_attempts"]) == 7
    assert att["failures_by_http_code"] == {"503": 2, "504": 1}
    assert att["http_code_observed_n"] == 3
    assert att["http_code_missing_n"] == 1
    assert att["failures_by_error_type"] == {"ServerError": 3, "TimeoutError": 1}

    # Falhas de documento por status e código HTTP (sem duplicar 504 do topo com a tentativa 2)
    assert telemetry["status_counts"] == {
        "OK": 2,
        "API_ERROR": 2,
        "INVALID_JSON": 1,
        "UNREADABLE": 1,
    }
    assert telemetry["failures_by_status"] == {
        "API_ERROR": 2,
        "INVALID_JSON": 1,
        "UNREADABLE": 1,
    }
    assert telemetry["failures_by_error_type"] == {
        "ServerError": 1,
        "TimeoutError": 1,
        "INVALID_RESPONSE": 1,
    }
    assert telemetry["failures_by_http_code"] == {"503": 2, "504": 1}
    assert telemetry["document_failures_by_http_code"] == {"504": 1}
    assert telemetry["failed_documents_without_http_code_n"] == 3


def test_absent_invalid_bool_nan_infinity_never_fabricate_zeros(pilot_cases):
    docs = [c for c in pilot_cases if c.gold is not None][:5]
    ids = [c.case_id for c in docs]

    # 1. Todos os metadados vazios (ex.: OCRRegex ou Replay sem raw_metadata)
    empty_outputs = {c.case_id: c.gold for c in docs}
    empty_summary = summarize_run_telemetry(empty_outputs, cases=docs)
    _dump_strict_json(empty_summary)

    assert empty_summary["metadata_observed_n"] == 0
    assert empty_summary["metadata_missing_n"] == 5
    assert empty_summary["latency_ms"]["total"] is None
    assert empty_summary["latency_ms"]["mean"] is None
    assert empty_summary["latency_ms"]["observed_n"] == 0
    assert empty_summary["latency_ms"]["missing_n"] == 5
    for key in ("input", "output", "total", "thinking", "cache"):
        assert empty_summary["tokens"][key]["total"] is None
        assert empty_summary["tokens"][key]["mean"] is None
        assert empty_summary["tokens"][key]["observed_n"] == 0
        assert empty_summary["tokens"][key]["missing_n"] == 5
    assert empty_summary["attempts"]["total_attempts"] is None
    assert empty_summary["attempts"]["retries"] is None
    assert empty_summary["attempts"]["observed_n"] == 0
    assert empty_summary["attempts"]["missing_n"] == 5
    assert empty_summary["new_calls"] is None

    # 2. Valores inválidos: bool, NaN, Infinity, -Infinity, negativos, float fracionário, strings
    corrupted_outputs = {
        ids[0]: docs[0].gold.model_copy(
            update={
                "raw_metadata": {
                    "latency_ms": True,
                    "tokens": {
                        "prompt_token_count": True,
                        "candidates_token_count": False,
                        "total_token_count": float("nan"),
                        "thoughts_token_count": float("inf"),
                        "cached_content_token_count": -5,
                    },
                    "attempts": True,
                    "http_code": True,
                }
            }
        ),
        ids[1]: docs[1].gold.model_copy(
            update={
                "raw_metadata": {
                    "latency_ms": float("nan"),
                    "tokens": {
                        "prompt_token_count": 12.5,
                        "candidates_token_count": "10",
                        "total_token_count": float("-inf"),
                    },
                    "attempts": ["not-a-dict"],
                    "http_code": float("nan"),
                }
            }
        ),
        ids[2]: docs[2].gold.model_copy(
            update={
                "raw_metadata": {
                    "latency_ms": float("inf"),
                    "tokens": "invalid-tokens-object",
                    "attempts": [
                        {
                            "number": True,
                            "status": "ERROR",
                            "http_code": 999,
                        }
                    ],
                }
            }
        ),
        ids[3]: docs[3].gold.model_copy(
            update={
                "raw_metadata": {
                    "latency_ms": -1.0,
                    "tokens": {},
                    "attempts": [],
                    "http_code": "503",
                }
            }
        ),
        ids[4]: docs[4].gold.model_copy(
            update={
                "raw_metadata": {
                    "latency_ms": float("-inf"),
                    "tokens": None,
                    "attempts": None,
                }
            }
        ),
    }

    corrupted_summary = summarize_run_telemetry(corrupted_outputs, cases=docs)
    _dump_strict_json(corrupted_summary)

    assert corrupted_summary["latency_ms"]["observed_n"] == 0
    assert corrupted_summary["latency_ms"]["invalid_n"] == 5
    assert corrupted_summary["latency_ms"]["missing_n"] == 5
    assert corrupted_summary["latency_ms"]["total"] is None
    assert corrupted_summary["latency_ms"]["mean"] is None

    for key in ("input", "output", "total", "thinking", "cache"):
        assert corrupted_summary["tokens"][key]["observed_n"] == 0
        assert corrupted_summary["tokens"][key]["missing_n"] == 5
        assert corrupted_summary["tokens"][key]["total"] is None
        assert corrupted_summary["tokens"][key]["mean"] is None

    # Apenas ids[2] tinha lista de dicts em attempts, mas com http_code=999 inválido (rejeitado)
    assert corrupted_summary["attempts"]["observed_n"] == 1
    assert corrupted_summary["attempts"]["invalid_n"] == 2
    assert corrupted_summary["attempts"]["absent_n"] == 2
    assert corrupted_summary["attempts"]["missing_n"] == 4
    assert corrupted_summary["attempts"]["http_code_invalid_n"] == 1
    assert corrupted_summary["attempts"]["failures_by_http_code"] == {}
    assert corrupted_summary["failures_by_http_code"] == {}


def test_experiment1_and_experiment3_telemetry_accounting_and_reuse(pilot_cases, config):
    docs = [c for c in pilot_cases if c.gold is not None]
    runs = []
    for rep_idx in range(3):
        run = {}
        for doc_idx, c in enumerate(docs):
            has_retry = rep_idx == 1 and doc_idx == 0
            attempts = (
                [
                    {"number": 1, "error_type": "ServerError", "http_code": 503},
                    {"number": 2, "status": "OK"},
                ]
                if has_retry
                else [{"number": 1, "status": "OK"}]
            )
            run[c.case_id] = c.gold.model_copy(
                update={
                    "raw_metadata": {
                        "model": "gemini-3.5-flash-lite",
                        "latency_ms": float(100 + rep_idx * 10),
                        "tokens": {
                            "prompt_token_count": 50 + rep_idx,
                            "candidates_token_count": 20,
                            "total_token_count": 70 + rep_idx,
                        },
                        "attempts": attempts,
                    }
                }
            )
        runs.append(run)

    ocr_baseline = {c.case_id: c.gold for c in docs}

    exp1 = experiment1(pilot_cases, Replay(runs), Replay([ocr_baseline]))
    _dump_strict_json(exp1)

    t1 = exp1["telemetry"]
    assert exp1["n"] == len(docs) == 20
    assert t1["unique_documents"] == 20
    assert t1["total_cases"] == 25
    assert t1["no_document_cases"] == 5
    assert t1["repeats"] == 3
    assert t1["extractor_logical_executions"] == 60
    assert t1["baseline_logical_executions"] == 20
    assert t1["reused"] is False
    assert t1["new_calls"] == 61
    assert len(t1["runs"]) == 3
    assert t1["runs"][0]["attempts"]["total_attempts"] == 20
    assert t1["runs"][1]["attempts"]["total_attempts"] == 21
    assert t1["runs"][1]["attempts"]["retries"] == 1
    assert t1["runs"][1]["failures_by_http_code"] == {"503": 1}
    assert t1["runs"][2]["attempts"]["total_attempts"] == 20
    assert t1["extractor_totals"]["unique_documents"] == 20
    assert t1["extractor_totals"]["logical_executions"] == 60
    assert t1["extractor_totals"]["attempts"]["total_attempts"] == 61
    assert t1["extractor_totals"]["attempts"]["retries"] == 1
    assert t1["extractor_totals"]["tokens"]["input"]["total"] == 20 * (50 + 51 + 52)
    assert t1["extractor_totals"]["tokens"]["thinking"]["total"] is None
    assert t1["extractor_totals"]["tokens"]["cache"]["total"] is None

    # Baseline OCR não tem tokens nem attempts do provedor LLM -> None, nunca zero fabricado
    assert t1["baseline"]["unique_documents"] == 20
    assert t1["baseline"]["logical_executions"] == 20
    assert t1["baseline"]["latency_ms"]["total"] is None
    assert t1["baseline"]["tokens"]["total"]["total"] is None
    assert t1["baseline"]["attempts"]["total_attempts"] is None

    # Exp 3 reutiliza extrações do Exp 1 com zero novas chamadas e sem duplicar consumo
    # Injetamos também um NaN em raw_metadata para comprovar sanitização JSON no Exp 3
    first_id = docs[0].case_id
    runs_with_nan = [dict(r) for r in runs]
    runs_with_nan[0][first_id] = runs[0][first_id].model_copy(
        update={
            "raw_metadata": {
                **runs[0][first_id].raw_metadata,
                "extra_untrusted_float": float("nan"),
            }
        }
    )

    exp3 = experiment3(pilot_cases, runs_with_nan, config)
    _dump_strict_json(exp3)

    assert exp3["n"] == 25
    assert exp3["calls"] == 0
    assert exp3["reused"] is True
    t3 = exp3["telemetry"]
    assert t3["reused"] is True
    assert t3["calls"] == 0
    assert t3["new_calls"] == 0
    assert t3["new_logical_executions"] == 0
    assert t3["new_provider_attempts"] == 0
    assert t3["new_tokens"] == 0
    assert t3["new_latency_ms"] == 0.0
    assert t3["unique_documents"] == 20
    assert t3["total_cases"] == 25
    assert t3["no_document_cases"] == 5
    assert t3["repeats"] == 3
    assert t3["logical_executions"] == 0
    assert t3["source_logical_executions"] == 60
    assert all(
        r["reused"] is True and r["logical_executions"] == 0 and r["new_calls"] == 0
        for r in t3["reused_runs"]
    )
    assert t3["reused_source_totals"]["reused"] is True
    assert t3["reused_source_totals"]["logical_executions"] == 0
    assert t3["reused_source_totals"]["new_calls"] == 0
    assert t3["reused_source_totals"]["source_logical_executions"] == 60
    assert t3["reused_source_totals"]["attempts"]["total_attempts"] == 61


def test_extraction_by_category_denominators_and_conservation(pilot_cases):
    gold = {c.case_id: c.gold for c in pilot_cases if c.gold is not None}
    mutated = dict(gold)
    # Introduz uma falha API_ERROR e uma divergência em categorias distintas
    fail_case = next(
        c
        for c in pilot_cases
        if c.gold is not None and c.curriculum.records[0].category == "FORMACAO_ACADEMICA"
    )
    wrong_case = next(
        c
        for c in pilot_cases
        if c.gold is not None and c.curriculum.records[0].category == "PARTICIPACAO_EVENTO"
    )
    mutated[fail_case.case_id] = ExtractedDocumentRecord(
        document_id=fail_case.case_id, extraction_status="API_ERROR"
    )
    mutated[wrong_case.case_id] = wrong_case.gold.model_copy(
        update={"holder_name": "NOME ALTERADO NO TESTE"}
    )

    exp1 = experiment1(pilot_cases, Replay([gold, mutated, gold]), Replay([mutated]))
    _dump_strict_json(exp1)

    direct_metric = extraction_metrics(pilot_cases, mutated)
    assert direct_metric["by_category"] == exp1["by_category"]["literal"][1]
    direct_exp1_cat = experiment1_by_category(pilot_cases, [gold, mutated, gold], mutated)
    assert direct_exp1_cat == exp1["by_category"]

    assert exp1["by_category"]["categories"] == list(CURRICULUM_CATEGORIES)
    assert exp1["by_category"]["repeats"] == 3
    assert len(exp1["by_category"]["literal"]) == 3
    assert len(exp1["by_category"]["equivalent"]) == 3

    # Verifica a 2ª repetição (mutated) e o baseline
    for report, by_cat in (
        (exp1["literal"][1], exp1["by_category"]["literal"][1]),
        (exp1["equivalent"][1], exp1["by_category"]["equivalent"][1]),
        (exp1["baseline"], exp1["by_category"]["baseline"]),
    ):
        assert set(by_cat) == set(CURRICULUM_CATEGORIES)
        assert not (set(by_cat) & set(DECISION_CLASSES))

        # Conservação aditiva dos denominadores: 5 categorias * (4 com doc + 1 sem doc) = 20 docs e 25 casos
        assert sum(c["n"] for c in by_cat.values()) == report["n"] == 20
        assert sum(c["documents_n"] for c in by_cat.values()) == 20
        assert sum(c["excluded_no_document_n"] for c in by_cat.values()) == 5
        assert sum(c["total_cases"] for c in by_cat.values()) == 25
        assert sum(c["conditional_n"] for c in by_cat.values()) == report["conditional_n"] == 19

        # Conservação de falhas e de contagens por campo
        agg_failures: Counter[str] = Counter()
        for c in by_cat.values():
            agg_failures.update(c["failures"])
            assert c["n"] == 4
            assert c["total_cases"] == 5
            assert c["documents_n"] == 4
            assert c["excluded_no_document_n"] == 1
            assert c["denominator_unit"] == "documents_with_gold"
            assert c["failure_policy"] == "omission; failed document is incorrect"
        assert dict(agg_failures) == report["failures"] == {"API_ERROR": 1}

        for field in FIELDS:
            for state in ("correct", "incorrect", "omitted", "spurious", "absent_correct"):
                assert sum(
                    c["fields"][field].get(state, 0) for c in by_cat.values()
                ) == report["fields"][field].get(state, 0)

        assert by_cat["FORMACAO_ACADEMICA"]["failures"] == {"API_ERROR": 1}
        assert by_cat["FORMACAO_ACADEMICA"]["conditional_n"] == 3
        assert by_cat["FORMACAO_ACADEMICA"]["all_fields_accuracy"] == pytest.approx(3 / 4)
        assert by_cat["FORMACAO_ACADEMICA"]["conditional_accuracy"] == pytest.approx(1.0)

        assert by_cat["PARTICIPACAO_EVENTO"]["failures"] == {}
        assert by_cat["PARTICIPACAO_EVENTO"]["all_fields_accuracy"] == pytest.approx(3 / 4)
        assert by_cat["PARTICIPACAO_EVENTO"]["fields"]["holder_name"]["incorrect"] == 1


def test_classification_by_category_denominators_conservation_and_no_engine_rerun(
    monkeypatch, pilot_cases, config
):
    import comprova_lattes.experiments.runner as runner_module

    engine_calls = 0
    original_match = runner_module.match_curriculum

    def counted_match(*args, **kwargs):
        nonlocal engine_calls
        engine_calls += 1
        return original_match(*args, **kwargs)

    monkeypatch.setattr(runner_module, "match_curriculum", counted_match)

    gold = {c.case_id: c.gold for c in pilot_cases if c.gold is not None}
    mutated = dict(gold)
    unreadable_case = next(
        c
        for c in pilot_cases
        if c.operator == "identity"
        and c.curriculum.records[0].category == "ORGANIZACAO_EVENTO"
    )
    mutated[unreadable_case.case_id] = ExtractedDocumentRecord(
        document_id=unreadable_case.case_id, extraction_status="UNREADABLE"
    )

    eval_report = evaluate(pilot_cases, mutated, config)
    # evaluate executa match_curriculum exatamente 1 vez por caso (25), sem rerodar para by_category
    assert engine_calls == len(pilot_cases) == 25

    # Chamadas diretas às funções de relatório por categoria não executam match_curriculum
    direct_by_cat = classification_by_category(pilot_cases, eval_report)
    assert engine_calls == 25
    assert direct_by_cat == eval_report["by_category"]

    by_cat = eval_report["by_category"]
    assert set(by_cat) == set(CURRICULUM_CATEGORIES)
    assert not (set(by_cat) & set(DECISION_CLASSES))

    # Denominadores na classificação: inclui casos sem comprovante (5 por categoria = 25 no total)
    assert sum(c["n"] for c in by_cat.values()) == eval_report["n"] == 25
    assert sum(c["total_cases"] for c in by_cat.values()) == 25
    assert sum(c["with_document_n"] for c in by_cat.values()) == 20
    assert sum(c["no_document_n"] for c in by_cat.values()) == 5

    # Soma das matrizes 3x3 por categoria == matriz 3x3 global
    summed_matrix = [[0] * 3 for _ in range(3)]
    agg_reasons: Counter[str] = Counter()
    agg_causes: Counter[str] = Counter()
    agg_orphans = []
    for cat, cat_report in by_cat.items():
        assert cat_report["category"] == cat
        assert tuple(cat_report["labels"]) == DECISION_CLASSES
        assert set(cat_report["per_class"]) == set(DECISION_CLASSES)
        assert cat_report["n"] == 5
        assert cat_report["with_document_n"] == 4
        assert cat_report["no_document_n"] == 1
        assert cat_report["without_no_document"]["n"] == 4
        assert cat_report["denominator_unit"] == "curriculum_records_including_no_document"
        for i in range(3):
            for j in range(3):
                summed_matrix[i][j] += cat_report["matrix"][i][j]
        agg_reasons.update(cat_report["reasons"])
        agg_causes.update(cat_report["error_causes"])
        agg_orphans.extend(cat_report["DOCUMENTO_NAO_ASSOCIADO"])

    assert summed_matrix == eval_report["matrix"]
    assert dict(agg_reasons) == eval_report["reasons"]
    assert dict(agg_causes) == eval_report["error_causes"]
    assert agg_orphans == eval_report["DOCUMENTO_NAO_ASSOCIADO"]
    assert len(by_cat["ORGANIZACAO_EVENTO"]["DOCUMENTO_NAO_ASSOCIADO"]) == 1
    assert sum(c["association"]["tp"] for c in by_cat.values()) == eval_report["association"]["tp"]
    assert sum(c["association"]["fp"] for c in by_cat.values()) == eval_report["association"]["fp"]
    assert sum(c["association"]["fn"] for c in by_cat.values()) == eval_report["association"]["fn"]

    # Exp 2 e Exp 3 preservam relatórios por categoria e 3 repetições separadas sem triplicar N
    exp2 = experiment2(pilot_cases, config)
    calls_after_exp2 = engine_calls
    exp2_cats = experiment2_by_category(exp2)
    assert engine_calls == calls_after_exp2
    assert set(exp2_cats) == {"A", "B", "LEVENSHTEIN_NORM", "JARO_WINKLER", "TOKEN_HYBRID"}
    for mode_name, mode_cats in exp2_cats.items():
        assert set(mode_cats) == set(CURRICULUM_CATEGORIES)
        assert sum(c["n"] for c in mode_cats.values()) == exp2[mode_name]["n"] == 25

    exp3 = experiment3(pilot_cases, [gold, mutated, gold], config)
    calls_after_exp3 = engine_calls
    exp3_cats = experiment3_by_category(exp3)
    assert engine_calls == calls_after_exp3
    assert exp3_cats == exp3["by_category"]
    assert exp3["n"] == 25
    assert len(exp3["by_category"]["runs"]) == 3
    assert "all_three" not in exp3["by_category"]
    assert "majority_vote" not in exp3["by_category"]
    assert (
        exp3["by_category"]["runs"][0]["ORGANIZACAO_EVENTO"]["macro_f1"]
        > exp3["by_category"]["runs"][1]["ORGANIZACAO_EVENTO"]["macro_f1"]
    )
    assert set(exp3["by_category"]["oracle"]) == set(CURRICULUM_CATEGORIES)
    _dump_strict_json({"eval": eval_report, "exp2": exp2, "exp3": exp3})


def test_explicit_zero_is_observed_unlike_missing_none_and_top_level_http_code_fallback(
    pilot_cases,
):
    docs = [c for c in pilot_cases if c.gold is not None][:2]
    d0, d1 = docs[0].case_id, docs[1].case_id
    outputs = {
        # d0: zero explícito observado em latency_ms, thoughts_token_count e cached_content_token_count
        d0: docs[0].gold.model_copy(
            update={
                "raw_metadata": {
                    "latency_ms": 0.0,
                    "tokens": {
                        "prompt_token_count": 10,
                        "candidates_token_count": 5,
                        "total_token_count": 15,
                        "thoughts_token_count": 0,
                        "cached_content_token_count": 0,
                    },
                    "attempts": [{"number": 1, "status": "OK"}],
                }
            }
        ),
        # d1: falha com http_code no topo mas sem lista attempts, e tokens ausentes
        d1: ExtractedDocumentRecord(
            document_id=d1,
            extraction_status="API_ERROR",
            raw_metadata={
                "error_type": "ClientError",
                "http_code": 429,
            },
        ),
    }

    summary = summarize_run_telemetry(outputs, cases=docs)
    _dump_strict_json(summary)

    # Zero explícito em d0 é observado (total=0, mean=0.0, observed_n=1, missing_n=1 de d1)
    assert summary["latency_ms"]["observed_n"] == 1
    assert summary["latency_ms"]["missing_n"] == 1
    assert summary["latency_ms"]["total"] == 0.0
    assert summary["latency_ms"]["mean"] == 0.0

    assert summary["tokens"]["thinking"]["observed_n"] == 1
    assert summary["tokens"]["thinking"]["missing_n"] == 1
    assert summary["tokens"]["thinking"]["total"] == 0
    assert summary["tokens"]["thinking"]["mean"] == 0.0

    assert summary["tokens"]["cache"]["observed_n"] == 1
    assert summary["tokens"]["cache"]["missing_n"] == 1
    assert summary["tokens"]["cache"]["total"] == 0
    assert summary["tokens"]["cache"]["mean"] == 0.0

    # Fallback de http_code de topo quando attempts está ausente em d1
    assert summary["attempts"]["observed_n"] == 1
    assert summary["attempts"]["missing_n"] == 1
    assert summary["attempts"]["total_attempts"] == 1
    assert summary["attempts"]["failures_by_http_code"] == {}
    assert summary["document_failures_by_http_code"] == {"429": 1}
    assert summary["failures_by_http_code"] == {"429": 1}


def test_category_with_only_no_document_cases_in_extraction_and_classification(
    pilot_cases, config
):
    no_doc_acad = next(
        c
        for c in pilot_cases
        if c.gold is None and c.curriculum.records[0].category == "FORMACAO_ACADEMICA"
    )
    doc_event = next(
        c
        for c in pilot_cases
        if c.gold is not None and c.curriculum.records[0].category == "PARTICIPACAO_EVENTO"
    )
    subset = [no_doc_acad, doc_event]
    outputs = {doc_event.case_id: doc_event.gold}

    ext = extraction_metrics(subset, outputs)
    _dump_strict_json(ext)
    assert ext["n"] == 1
    assert set(ext["by_category"]) == {"FORMACAO_ACADEMICA", "PARTICIPACAO_EVENTO"}
    assert ext["by_category"]["FORMACAO_ACADEMICA"]["total_cases"] == 1
    assert ext["by_category"]["FORMACAO_ACADEMICA"]["n"] == 0
    assert ext["by_category"]["FORMACAO_ACADEMICA"]["documents_n"] == 0
    assert ext["by_category"]["FORMACAO_ACADEMICA"]["excluded_no_document_n"] == 1
    assert ext["by_category"]["FORMACAO_ACADEMICA"]["conditional_accuracy"] is None
    assert ext["by_category"]["PARTICIPACAO_EVENTO"]["total_cases"] == 1
    assert ext["by_category"]["PARTICIPACAO_EVENTO"]["n"] == 1
    assert ext["by_category"]["PARTICIPACAO_EVENTO"]["documents_n"] == 1
    assert ext["by_category"]["PARTICIPACAO_EVENTO"]["excluded_no_document_n"] == 0

    cls_report = evaluate(subset, outputs, config)
    _dump_strict_json(cls_report)
    assert cls_report["n"] == 2
    assert cls_report["by_category"]["FORMACAO_ACADEMICA"]["n"] == 1
    assert cls_report["by_category"]["FORMACAO_ACADEMICA"]["with_document_n"] == 0
    assert cls_report["by_category"]["FORMACAO_ACADEMICA"]["no_document_n"] == 1
    assert cls_report["by_category"]["FORMACAO_ACADEMICA"]["without_no_document"] is None
    assert cls_report["by_category"]["PARTICIPACAO_EVENTO"]["n"] == 1
    assert cls_report["by_category"]["PARTICIPACAO_EVENTO"]["with_document_n"] == 1
    assert cls_report["by_category"]["PARTICIPACAO_EVENTO"]["no_document_n"] == 0
    assert cls_report["by_category"]["PARTICIPACAO_EVENTO"]["without_no_document"]["n"] == 1


def test_reporting_validation_guards(pilot_cases):
    with pytest.raises(ValueError, match="Casos"):
        extraction_by_category([], {})
    with pytest.raises(ValueError, match="Casos"):
        classification_by_category([], [])
    with pytest.raises(ValueError, match="3 extrações"):
        summarize_experiment3_telemetry(pilot_cases, [{}])
    with pytest.raises(ValueError, match="3 repetições"):
        experiment3_by_category([{}, {}])
    assert summarize_experiment1_telemetry(pilot_cases, [], {
        c.case_id: c.gold for c in pilot_cases if c.gold is not None
    })["repeats"] == 0
