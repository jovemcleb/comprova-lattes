# Implementação e Integração das Decisões Estatísticas Aprovadas (Exp 1, Exp 2 e Exp 3)

**Data:** 2026-11-15  
**Escopo exclusivo de escrita:** `comprova-lattes-api/src/comprova_lattes/experiments/{statistics.py,runner.py,__main__.py}`, `comprova-lattes-api/tests/{test_approved_statistics.py,test_experiments.py}` e este documento (`.specs/docs/approved-statistics.md`).

---

## 1. Resumo das Decisões e Contratos Implementados

### 1.1. Experimento 2 (`inference` e `paired_comparisons`)
- **Quatro comparações aprovadas com referência `LEVENSHTEIN_NORM`:**
  - `LEVENSHTEIN_NORM:A` (Proposto Levenshtein vs. Baseline Exato)
  - `LEVENSHTEIN_NORM:B` (Proposto Levenshtein vs. Baseline Normalizado)
  - `LEVENSHTEIN_NORM:JARO_WINKLER` (Proposto Levenshtein vs. Variante Jaro-Winkler)
  - `LEVENSHTEIN_NORM:TOKEN_HYBRID` (Proposto Levenshtein vs. Variante Híbrida por Tokens)
- **Teste de McNemar exato binomial bicaudal por família (`mcnemar_exact`):**
  - Unidade pareada: família inteira correta (`all(r["correct"] for r in family_rows)`).
  - Quando não há famílias discordantes (`b + c == 0`), `p_value = 1.0`.
  - Correção de **Holm-Bonferroni (`holm`) aplicada estritamente sobre essas 4 comparações** (`n_comparisons = 4`), sem diluir o ajuste com pares entre baselines (`A:B`, `JARO_WINKLER:TOKEN_HYBRID` etc.).
  - `inference()` exige que todas as 5 variantes (`A`, `B`, `LEVENSHTEIN_NORM`, `JARO_WINKLER`, `TOKEN_HYBRID`) sejam fornecidas juntas e valida o alinhamento estrito de `case_id`, `family_id`, `expected`, `status` e `correct`.
- **Compatibilidade em `paired_comparisons`:**
  - Sem argumentos extras (`paired_comparisons(methods)`), preserva o comportamento genérico de todos os pares (`combinations(methods, 2)`) para compatibilidade de biblioteca.
  - Suporta seleção explícita via `pairs=[...]` ou `reference="LEVENSHTEIN_NORM", comparators=[...]`, rejeitando métodos inexistentes, autopares (`a == b`), pares duplicados/simétricos (`A:B` e `B:A`) e unidades desalinhadas.
- **Metadados de pressupostos e limites (`assumptions_and_limits`, `family_resolution_summary`):**
  - Registra explicitamente `tests_macro_f1_difference: False` (o McNemar por família é complementar e descritivo; não testa diretamente diferenças de Macro-F1).
  - Registra a **perda de resolução** (`partial_correct_families_collapsed_to_false`): uma família com 4/5 casos corretos recebe `False`, igual a 0/5.
  - Registra que a separação determinística de registros-base, emissores e layouts na bancada sintética **não comprova independência estatística** entre famílias nem amostragem populacional (`automatic_independence_claimed: False`, `population_sampling_claimed: False`).
  - Documenta a contagem da bancada final aprovada (`FINAL_WORKBENCH_FAMILIES = 20`, `PILOT_WORKBENCH_FAMILIES = 10` em AD-016) sem tratá-la como limiar recomendável ou garantia científica de validade estatística (`workbench_count_is_validity_guarantee: False`).

### 1.2. Bootstrap Percentil por Família (`cluster_bootstrap` e `mean_cluster_bootstrap`)
- **Parâmetros de protocolo e transparência:**
  - Padrão do protocolo aprovado: `PROTOCOL_BOOTSTRAP_REPLICATES = 2000` e `PROTOCOL_BOOTSTRAP_CONFIDENCE = 0.95` (percentil 95%).
  - `seed: int` é argumento nomeado obrigatório (nunca fixado silenciosamente).
  - Chamadores (como testes rápidos) podem passar `replicates=10` ou outro `confidence`; o retorno grava os valores efetivamente executados (`replicates`, `confidence`) junto de `is_protocol_default` (`True`/`False`) e `parameter_regime` (`"approved_protocol_default"` vs `"custom_caller_override"`), sem fingir 95%/2000 quando o chamador escolheu outro regime.
  - Quando o número de famílias é menor que a contagem da bancada final (`families < FINAL_WORKBENCH_FAMILIES`, onde `FINAL_WORKBENCH_FAMILIES = 20`), não ocorre falha; o relatório inclui `below_final_workbench_family_count: True`, `low_family_count_warning: True` e aviso explícito em `warnings` esclarecendo que 20 é a contagem da bancada sintética final (AD-016), e não um limiar científico nem garantia de validade (`workbench_count_is_validity_guarantee: False`).
  - Todos os intervalos registram `inference_scope: "synthetic_workbench_cluster_resampling; not_population_sampling"`, `automatic_independence_claimed: False` e `population_sampling_claimed: False`.
- **Estatística da média das 3 repetições (`mean_cluster_bootstrap`):**
  - Em cada réplica bootstrap, sorteia-se com reposição um conjunto de famílias inteiras (`groups`), gerando a lista de índices `ix` de tamanho $N$ (nunca $3N$).
  - O mesmo vetor de índices `ix` é avaliado separadamente em cada uma das 3 execuções ($M_1(\text{ix}), M_2(\text{ix}), M_3(\text{ix})$) e a estatística da réplica é a média aritmética $\frac{1}{3}\sum_{r=1}^3 M_r(\text{ix})$.
  - **Não concatena matrizes de confusão** e **não triplica $N$** (`pooled_matrices: False`, `voting_used: False`).

### 1.3. Experimento 1 (`experiment1` e `extraction_inference`)
- `experiment1` preserva todas as chaves existentes e adiciona `mean_3` (média aritmética das métricas das 3 execuções sem inflar $N$), `unstable_document_ids` e `unstable_documents_rate`.
- `extraction_inference` calcula intervalos bootstrap por família para:
  - `repeat_1`, `repeat_2`, `repeat_3` (`is_primary: True`, `role: "primary_per_run"`),
  - `mean_3` (`is_primary: True`, `role: "primary_three_run_mean"`),
  - `baseline` e alias `OCR_regex` (`is_primary: True`, `role: "primary_baseline"`).
- **`all_three` reclassificado como análise secundária descritiva:**
  - Mantido em `intervals["all_three"]` (para compatibilidade estrutural) e em `secondary_descriptive["all_three"]`, com `is_primary: False`, `voting_used: False` e `role: "secondary_descriptive_conservative_stability_only"`.
- **Sem comparações extras de hipótese no Exp 1:**
  - `mcnemar: {}`, `inter_repetition_mcnemar_removed: True`, `mcnemar_policy: "approved_mcnemar_is_exp2_only; no_hypothesis_tests_between_repetitions"`. Não são criadas comparações de hipótese entre `repeat_1..3` ou `all_three`.

### 1.4. Experimento 3 (`experiment3`, `integrated_inference` e CLI `__main__.py`)
- `experiment3` preserva `calls: 0`, `reused: True`, `runs`, `oracle`, `telemetry` e `by_category`, adicionando `mean_3`, `macro_f1_mean`, `macro_f1_range`, `accuracy_mean` e `accuracy_range`.
- `integrated_inference` (com alias `experiment3_inference`) calcula IC bootstrap por família para `repeat_1`, `repeat_2`, `repeat_3`, `mean_3` (média dos 3 Macro-F1 por réplica de família) e `oracle`, validando `type(calls) is int and calls == 0`, `reused is True` e alinhamento de casos/famílias.
- No CLI (`__main__.py`):
  - `exp2` exige `--seed` explícita e usa `2000`/`0.95` por padrão caso `--replicates`/`--confidence` sejam omitidos, ou respeita valores explícitos passados pelo chamador.
  - `exp1` e `exp3` aceitam `--seed` (com `--replicates` e `--confidence` opcionais, assumindo `2000`/`0.95` quando `--seed` é informada) e rejeitam `--replicates`/`--confidence` sem `--seed`, nunca fixando semente silenciosamente.
  - Serialização JSON em `__main__.py` mantém `allow_nan=False` (rejeitando `NaN`/`Infinity` em estatísticas) enquanto sanitiza `raw_metadata` em `ExtractedDocumentRecord` para `None` via `sanitize_json_value`, preservando compatibilidade com `Replay`.

---

## 2. Integração em `tests/test_experiments.py` e Verificação Executada

- **Integração realizada em `comprova-lattes-api/tests/test_experiments.py`:**
  - Atualizada a expectativa legada `stats["mcnemar"]["A:B"]["n"] == 5` em `test_runners_and_propagation` para verificar exatamente os 4 pares aprovados (`LEVENSHTEIN_NORM:A`, `LEVENSHTEIN_NORM:B`, `LEVENSHTEIN_NORM:JARO_WINKLER`, `LEVENSHTEIN_NORM:TOKEN_HYBRID`), a ausência de `"A:B"` em `stats["mcnemar"]` e `n == 5` em todos os pares aprovados, preservando integralmente a separação entre contratos estruturais e avaliação de desempenho feita pelo worker Hydrogen.
- **Comandos executados e resultados reais (`comprova-lattes-api/`):**
  - `.\.venv\Scripts\ruff.exe check .` -> `All checks passed!` (exit 0).
  - `$env:PYTHONPATH="src;.venv\Lib\site-packages"; python -m pytest -q -p no:cacheprovider tests/test_approved_statistics.py` -> **9 passed in 3.76s** (exit 0).
  - `$env:PYTHONPATH="src;.venv\Lib\site-packages"; python -m pytest -q -p no:cacheprovider tests/test_experiments.py` -> **24 passed in 11.82s** (exit 0).
  - `$env:PYTHONPATH="src;.venv\Lib\site-packages"; python -m pytest -q -p no:cacheprovider tests/test_approved_statistics.py tests/test_experiment_reporting.py tests/test_experiment_artifacts.py` -> **24 passed in 23.65s** (`9` em `test_approved_statistics.py` + `8` em `test_experiment_reporting.py` + `7` em `test_experiment_artifacts.py`; exit 0).
  - Total verificado nos 4 módulos (`test_approved_statistics.py`, `test_experiments.py`, `test_experiment_reporting.py`, `test_experiment_artifacts.py`): **48 passed, 0 failed**.
- **Limites e trabalho concorrente:**
  - Esta verificação comprova apenas a conformidade do software e dos contratos estatísticos em testes sintéticos offline; não constitui calibração piloto definitiva, congelamento (`freeze`) oficial, anotação humana nem estudo experimental real.
  - Arquivos de regra de instituição em eventos (`matcher/rules.py`, `tests/test_matcher.py`, `tests/test_performance_reporting_contract.py`) pertencem a tarefa concorrente de outro worker e não foram editados aqui; a validação global conjunta caberá à coordenação após a integração daquela frente.
