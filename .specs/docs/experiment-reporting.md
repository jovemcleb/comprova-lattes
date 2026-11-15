# Relatórios Descritivos de Telemetria e Métricas por Categoria Curricular

## 1. Objetivo e Escopo

Este documento descreve os contratos, nomes de chaves, unidades, denominadores e limites metodológicos implementados em `comprova_lattes/experiments/reporting.py` e integrados em `comprova_lattes/experiments/runner.py`.

- **Natureza exclusivamente descritiva e offline:** os relatórios resumem os metadados brutos (`raw_metadata`) efetivamente registrados em `ExtractedDocumentRecord` e desagregam as métricas de extração e classificação pelas cinco categorias curriculares aprovadas (`AD-012`), sem alterar `statistics.py`, `freeze.py`, limiares do motor, definição de precisão/revocação/F1, política de falhas ou testes inferenciais (`McNemar`, `cluster_bootstrap`, correção de `Holm`).
- **Compatibilidade retroativa:** todas as chaves preexistentes de `extraction_metrics`, `experiment1`, `evaluate`, `experiment2` e `experiment3` são preservadas integralmente.

---

## 2. Unidades Contábeis e Reutilização (Exp 1 vs. Exp 3)

Os relatórios de telemetria distinguem explicitamente quatro conceitos para impedir inflação amostral ou dupla contagem de consumo:

| Chave | Semântica |
| --- | --- |
| `total_cases` | Total de casos curriculares avaliados na partição/recorte (inclui casos `no_document` / `SEM_COMPROVANTE`). |
| `no_document_cases` | Casos curriculares sem documento comprobatório (`gold is None` e `document is None`). |
| `unique_documents` | Documentos comprobatórios únicos com gabarito (`N` documental de extração; ex.: 40 no piloto e 80 no final). Nunca é multiplicado pelo número de repetições (`repeats`). |
| `repeats` | Número de repetições independentes do extrator avaliado (`3` no protocolo do Exp 1 e Exp 3). |
| `logical_executions` | Execuções lógicas de `extract(document_id, data, mime_type)` realizadas na etapa. Em cada repetição do Exp 1 vale `unique_documents`; em `extractor_totals` do Exp 1 vale `repeats * unique_documents`; no Exp 3 vale `0` (`reused = True`). |
| `source_logical_executions` | Execuções lógicas de origem dos registros inspecionados (`unique_documents` por repetição; `repeats * unique_documents` no agregado), permitindo auditar a cobertura no Exp 3 sem somar novas execuções. |
| `attempts.total_attempts` | Soma das tentativas de transporte/provedor registradas em `raw_metadata["attempts"]` (`>= logical_executions` quando há *retries*; `None` quando `attempts` não está disponível nos metadados). |
| `attempts.retries` | Soma de `max(0, len(attempts) - 1)` por documento com lista `attempts` observada (`None` quando ausente). |
| `reused` | `False` no Exp 1; `True` no Exp 3 (`experiment3["reused"]` e `experiment3["telemetry"]["reused"]`). |
| `calls` / `new_calls` | No Exp 1 reflete as chamadas observadas (`total_attempts` quando presente ou `None` quando ausente); no Exp 3 é fixado em `0` (`new_calls = 0`, `new_logical_executions = 0`, `new_provider_attempts = 0`, `new_tokens = 0`, `new_latency_ms = 0.0`). |

---

## 3. Telemetria de Extração (`raw_metadata`)

Em `extractor/gemini.py`, `GeminiExtractor.extract` preenche `raw_metadata` com:
- `latency_ms`: tempo decorrido em milissegundos (`float >= 0.0`).
- `tokens`: resultado de `response.usage_metadata.model_dump(exclude_none=True)` (`google.genai.types.GenerateContentResponseUsageMetadata`) ou `None`.
- `attempts`: lista de dicionários por tentativa (`{"number": attempt, "status": "OK"}` em sucesso; `{"number": attempt, "error_type": type(exc).__name__, "http_code": code}` em falha).
- `error_type` e `http_code`: registrados no nível do documento quando a extração falha.

### 3.1 Regras de validação e ausência (nunca fabricar zero)

1. **Ausência ou valor inválido nunca vira zero:** quando `observed_n == 0` para `latency_ms`, qualquer contador de `tokens` ou `attempts`, os campos de soma/média (`total`, `mean`, `min`, `max`, `total_attempts`, `retries`) retornam `None`, acompanhados de `observed_n`, `missing_n`, `absent_n` e `invalid_n`.
2. **Rejeição de tipos inválidos e não finitos:** valores `bool` (`True`/`False`, mesmo sendo subclasse de `int` em Python), `NaN`, `Infinity`, `-Infinity`, números negativos, strings ou coleções malformadas são rejeitados e contabilizados em `invalid_n` (que compõe `missing_n = absent_n + invalid_n`).
3. **Serialização JSON estrita (`allow_nan=False`):** `sanitize_json_value` garante que nenhum `NaN` ou `Infinity` (inclusive em `extraction_metadata` do Exp 3) viole a serialização JSON.
4. **Sem estimativa monetária:** `cost_estimate` permanece `None` (nenhuma métrica monetária é calculada sem tabela de preços verificada).

### 3.2 Contadores de `tokens` e nomes reais do SDK

Cada dimensão de token é exposta simultaneamente pelo nome semântico (`input`, `output`, `total`, `thinking`, `cache`) e pelo nome real do `GenerateContentResponseUsageMetadata` do `google-genai`:

| Chave semântica | Chave canônica SDK (`extractor/gemini.py`) | Aliases aceitos na leitura (ordem de prioridade, sem soma entre aliases) |
| --- | --- | --- |
| `input` | `prompt_token_count` | `prompt_token_count`, `input_token_count`, `input_tokens`, `prompt_tokens`, `input` |
| `output` | `candidates_token_count` | `candidates_token_count`, `output_token_count`, `output_tokens`, `candidate_token_count`, `candidates_tokens`, `completion_token_count`, `output` |
| `total` | `total_token_count` | `total_token_count`, `total_tokens`, `total` |
| `thinking` | `thoughts_token_count` | `thoughts_token_count`, `thinking_token_count`, `thinking_tokens`, `thoughts_tokens`, `thought_token_count`, `thinking` |
| `cache` | `cached_content_token_count` | `cached_content_token_count`, `cached_token_count`, `cache_token_count`, `cached_tokens`, `cache_tokens`, `cache` |

- **Deduplicação de aliases:** se um mesmo documento contiver mais de um alias da mesma dimensão (ex.: `prompt_token_count` e `input_tokens`), apenas o primeiro alias na ordem canônica é lido e `duplicate_alias_ignored_n` é incrementado. Aliases nunca são somados entre si.
- **Proibição de inferir `total` por soma parcial:** `tokens["total_inferred_from_parts"]` é sempre `False`. Se `total_token_count` (ou alias de total) estiver ausente num documento, `total` é contado como ausente (`missing_n += 1`), mesmo que `prompt_token_count` e `candidates_token_count` estejam presentes.

### 3.3 Tentativas (`attempts`), *retries* e falhas por status / código HTTP

- `attempts.provider_attempts`: lista linear normalizada de tentativas (`document_id`, `number`, `status`, `error_type`, `http_code`).
- `attempts.by_document`: mapa `document_id -> list[attempt]`.
- `status_counts` e `failures_by_status`: contagens por `ExtractedDocumentRecord.extraction_status` (`OK`, `API_ERROR`, `INVALID_JSON`, `UNREADABLE`).
- `failures_by_error_type`: contagens de `raw_metadata["error_type"]` em documentos falhos (`ServerError`, `TimeoutError`, `INVALID_RESPONSE`, etc.).
- `failures_by_http_code`: contagens por código HTTP (`"503"`, `"504"`, etc.) observadas nas tentativas falhas em `attempts` (ou no `http_code` de topo quando `attempts` está ausente), **sem duplicar** o código HTTP da última tentativa com o `raw_metadata["http_code"]` copiado no topo por `GeminiExtractor.extract`.
- `document_failures_by_http_code` e `failed_documents_without_http_code_n`: código HTTP final por documento falho (máximo 1 por documento) e contagem de documentos falhos sem código HTTP (ex.: `TimeoutError`, `INVALID_JSON`, `UNREADABLE`).

---

## 4. Relatórios por Categoria Curricular (`by_category`)

As cinco categorias curriculares do MVP (`AD-012`) são mantidas na ordem canônica de `CURRICULUM_CATEGORIES`:
1. `FORMACAO_ACADEMICA`
2. `FORMACAO_COMPLEMENTAR`
3. `PARTICIPACAO_EVENTO`
4. `APRESENTACAO_TRABALHO`
5. `ORGANIZACAO_EVENTO`

Categorias curriculares nunca são misturadas com as três classes de decisão do motor (`DECISION_CLASSES`: `VALIDADO`, `DIVERGENTE`, `INCONCLUSIVO`).

### 4.1 Extração por categoria (`extraction_metrics`, `experiment1`)

- Calculada por `extraction_by_category` invocando `_extraction_metrics_core` sobre o subconjunto de cada categoria, preservando a mesma definição de `precision`, `recall`, `f1`, `accuracy`, `all_fields_accuracy`, `conditional_accuracy` e `failure_policy = "omission; failed document is incorrect"`.
- **Denominador na extração (`denominator_unit = "documents_with_gold"`):**
  - `n` / `documents_n`: número de casos da categoria que possuem comprovante (`gold is not None`).
  - `excluded_no_document_n`: casos da categoria sem comprovante (`no_document`), que ficam fora da avaliação de extração documental.
  - `total_cases`: `documents_n + excluded_no_document_n`.
- Em `experiment1`:
  - Cada repetição em `literal[0..2]` e `equivalent[0..2]` e o `baseline` possuem a chave `by_category`.
  - O topo de `experiment1` também expõe `by_category: {"categories": [...], "repeats": 3, "literal": [...], "equivalent": [...], "baseline": {...}, "denominator_unit": "documents_with_gold", "repetition_policy": "report separately; never pool repetitions as N"}`.

### 4.2 Classificação por categoria (`evaluate`, `experiment2`, `experiment3`)

- Calculada por `classification_by_category` agrupando diretamente as `rows` e `DOCUMENTO_NAO_ASSOCIADO` já produzidos em `evaluate` e aplicando `statistics.classification(truth, predicted)`, **sem chamar `evaluate` recursivamente e sem reexecutar `match_curriculum`**.
- **Denominador na classificação (`denominator_unit = "curriculum_records_including_no_document"`):**
  - `n` / `total_cases`: todos os registros curriculares da categoria, **incluindo** os casos sem comprovante (`no_document_n`, cujo esperado é `INCONCLUSIVO` / `SEM_COMPROVANTE`).
  - `with_document_n`: casos da categoria com comprovante (`gold is not None`).
  - `no_document_n`: casos da categoria sem comprovante (`gold is None`).
  - `without_no_document`: sub-relatório `classification(...)` restrito aos `with_document_n` casos com comprovante da categoria.
- Conservação aditiva: a soma das matrizes 3×3 (`matrix`), contagens de associação (`tp`, `fp`, `fn`), `reasons`, `error_causes` e `DOCUMENTO_NAO_ASSOCIADO` entre as categorias é idêntica ao relatório global de `evaluate`.
- Em `experiment2`, cada configuração (`A`, `B`, `LEVENSHTEIN_NORM`, `JARO_WINKLER`, `TOKEN_HYBRID`) contém `by_category` (e pode ser consultada via `experiment2_by_category`).
- Em `experiment3`, cada uma das 3 repetições em `runs[0..2]` e `oracle` contém `by_category`, e o topo expõe `by_category: {"repeats": 3, "runs": [...], "oracle": {...}, "denominator_unit": "curriculum_records_including_no_document", "repetition_policy": "separate; N unchanged"}`, mantendo as 3 repetições estritamente separadas sem voto majoritário, sem `all_three` adicional e sem triplicar `N`.

---

## 5. Limites Metodológicos

- Testes automatizados em `tests/test_experiment_reporting.py` usam metadados simulados e extrações injetadas (`Replay`) para verificar contratos de software offline; **não constituem resultado experimental oficial** nem substituem a execução com Gemini/Tesseract reais após congelamento (`freeze`).
- Decisões científicas pendentes (anotação humana independente e Kappa, calibração final de limiares, ampliação de operadores e protocolo de agregação inferencial entre repetições) permanecem inalteradas.
