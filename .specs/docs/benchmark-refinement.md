# Refinamento da Bancada Sintética e Diagnóstico de Veredictos (`AD-014` e `legitimate`)

> **Status:** Separação aprovada pelo usuário entre testes unitários de contrato e contrato de avaliação de desempenho aplicada, e **política condicional de instituição em eventos (`EVENT_CATEGORIES`) implementada mediante aprovação explícita (2026-11-15)**; **não aprova** os templates em rascunho (`TEMPLATE_PROVENANCE["status"] == "draft_pending_human_validation"`), **não executa** calibração oficial, **não gera** corpus final oficial e **não altera** limiares ou gabaritos (`expected`/`gold`).

---

## 1. Escopo e invariantes preservados

- **Base de referência:** commit `8a168e2` e alterações locais posteriores.
- **Arquivos alterados no refinamento e na separação de testes:** `comprova-lattes-api/src/comprova_lattes/experiments/synthetic.py`, `comprova-lattes-api/tests/test_synthetic_leakage.py`, `comprova-lattes-api/tests/test_certificate_templates.py`, `comprova-lattes-api/tests/test_experiments.py`, `comprova-lattes-api/tests/test_performance_reporting_contract.py` e este documento (`.specs/docs/benchmark-refinement.md`).
- **Invariantes preservados:**
  - Partição `150 = 50 piloto (10 famílias × 5) + 100 finais (20 famílias × 5)`, com equilíbrio exato entre as 5 categorias e os 5 operadores por partição.
  - Piloto invariável quando `final_families` varia.
  - Semântica original de `gold` (valores literais impressos no documento) e `expected` (`identity`/`legitimate` → `VALIDADO`, `factual_mutation` → `DIVERGENTE`, `omission`/`no_document` → `INCONCLUSIVO`).
  - Nenhuma alteração em `matcher/` (regras, escores ou essencialidade), `experiments/runner.py`, `experiments/statistics.py`, limiares do teste (`config`), `STATE.md`, `ROADMAP.md`, `HANDOFF.md`, `README*`, `pyproject.toml` ou interface web.

---

## 2. Refinamentos implementados em `experiments/synthetic.py`

### 2.1 Distribuição de sigla e evidência (`AD-014`) entre operadores

- A presença de `issuer_acronym` e `issuer_name_acronym_evidence` passou a ser derivada exclusivamente do índice da família por regra prévia independente de classe e operador: `has_ad014 = (index % 2 == 0)`.
- Quando `has_ad014` é verdadeiro e existe documento (`operator != "no_document"`), a relação sigla/evidência é aplicada coerentemente a `identity`, `legitimate`, `factual_mutation` e `omission`; em `no_document`, `gold` e `document` permanecem `None`.
- No recorte aprovado (`10` famílias piloto + `20` finais):
  - **Piloto (`50` casos, `40` documentos):** `5/10` casos com AD-014 em cada um dos 4 operadores com documento (`1` por par `(categoria, operador)`).
  - **Final (`100` casos, `80` documentos):** `10/20` casos com AD-014 em cada um dos 4 operadores com documento (`2` por par `(categoria, operador)`).
  - Todas as variantes documentais da mesma família compartilham a mesma presença/ausência de AD-014, eliminando a exclusividade estrutural anterior em `legitimate`.

### 2.2 Coerência na mutação institucional (`ORGANIZACAO_EVENTO`)

- Em `factual_mutation` da categoria `ORGANIZACAO_EVENTO`, `issuer_institution` é mutada para `INSTITUTO FICTICIO <alt_inst>` (via `alternative_identity(seed, fid, "issuer_institution")`).
- Quando `has_ad014` está ativo nessa família, `issuer_acronym` é emitida como `IF<alt_inst>` e `issuer_name_acronym_evidence` como `INSTITUTO FICTICIO <alt_inst> - IF<alt_inst>`, refletindo estritamente a instituição **documental** mutada sem copiar a sigla do XML (`fid`) nem contradizer o trecho literal.

### 2.3 Remoção do `X` inicial e divisão de características em `legitimate`

- Removida a alteração artificial `"X" + values["activity_title"][1:]`.
- Substituída por `_apply_legitimate_variation(values, index)`, que alterna deterministicamente por `index % 3` (coprimo a `index % 2` e `index % 5`) três variações realmente equivalentes sob `normalize_text`:
  - `0` (**espaços**): espaços duplos (`"  "`) entre palavras de titular, atividade, evento (quando presente) e instituição.
  - `1` (**caixa**): capitalização em título nas palavras antes do identificador hex (ex.: `"Pessoa Ficticia <FID>"`).
  - `2` (**pontuação**): separadores equivalentes antes do identificador (`", "` em titular e instituição, `" - "` em atividade e `": "` em evento quando presente).
- Nenhum status (`VALIDADO`, `DIVERGENTE`, `INCONCLUSIVO`), nome de operador ou pista técnica é impresso nas imagens.

---

## 3. Diagnóstico das 2 falhas em `test_synthetic_categories_and_operator_verdicts`

O teste `test_synthetic_categories_and_operator_verdicts[pilot]` e `[final]` em `comprova-lattes-api/tests/test_experiments.py` utiliza limiares sintéticos fixos **não calibrados**:
- `association=0.3`, `ambiguity_margin=0.01`
- `holder_low=0.4`, `holder_high=0.95`
- `title_low=0.4`, `title_high=0.95`
- `institution_low=0.4`, `institution_high=0.95`

Com `seed=93` (`5` famílias piloto + `5` famílias finais = `25` casos por partição), o motor proposto (`LEVENSHTEIN_NORM`) obtém `macro_f1 = 0.8849206349206349` em ambas as partições, com exatamente **2 divergências por partição** (ambas em `factual_mutation`, com associação correta `association_correct=True`):

### 3.1 Falha por caso e por campo (observado diretamente)

| Partição | Caso (`case_id` / `family_id`) | Categoria (`factual_mutation`) | Campo mutado | `lattes_normalized` vs. `document_normalized` | Regra & Score (`LEVENSHTEIN_NORM`) | Desfecho do campo | `essential_fields` da categoria | Veredicto observado (`reason_code`) | Esperado |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pilot` | `340402dd3533a8bbc17c` / `f2ca9f34dce7` | `APRESENTACAO_TRABALHO` | `titular` | `'pessoa ficticia f2ca9f34dce7'` vs. `'pessoa ficticia 61826877d0b5'` | `SIMILARITY`: `0.6071428571428572` | `INCONCLUSIVE_BORDERLINE` (`0.4 <= 0.6071 < 0.95`) | `['ano', 'evento', 'papel_participacao', 'titular', 'titulo']` | `INCONCLUSIVO` (`EVIDENCIA_INSUFICIENTE`) | `DIVERGENTE` |
| `pilot` | `3a9914e74fbaf0f7095f` / `38ec113f8d9e` | `ORGANIZACAO_EVENTO` | `instituicao` | `'instituto ficticio 38ec113f8d9e'` vs. `'instituto ficticio bd490217124e'` | `SIMILARITY`: `0.6451612903225806` | `INCONCLUSIVE_BORDERLINE` (`0.4 <= 0.6452 < 0.95`) | `['ano', 'papel_participacao', 'titular', 'titulo']` | **`VALIDADO`** (`VALIDADO_CORRESPONDENCIA_COMPLETA`) | `DIVERGENTE` |
| `final` | `74b62526dafb960c5b07` / `ed082f2663fe` | `APRESENTACAO_TRABALHO` | `titular` | `'pessoa ficticia ed082f2663fe'` vs. `'pessoa ficticia ff5905dadb09'` | `SIMILARITY`: `0.5714285714285714` | `INCONCLUSIVE_BORDERLINE` (`0.4 <= 0.5714 < 0.95`) | `['ano', 'evento', 'papel_participacao', 'titular', 'titulo']` | `INCONCLUSIVO` (`EVIDENCIA_INSUFICIENTE`) | `DIVERGENTE` |
| `final` | `b280019df0eb6527a91e` / `3de9e933d202` | `ORGANIZACAO_EVENTO` | `instituicao` | `'instituto ficticio 3de9e933d202'` vs. `'instituto ficticio 785cfcc430c4'` | `SIMILARITY`: `0.6129032258064516` | `INCONCLUSIVE_BORDERLINE` (`0.4 <= 0.6129 < 0.95`) | `['ano', 'papel_participacao', 'titular', 'titulo']` | **`VALIDADO`** (`VALIDADO_CORRESPONDENCIA_COMPLETA`) | `DIVERGENTE` |

*(Observação sobre todos os demais campos desses 4 casos: os campos não mutados obtiveram `MATCH` — `NORMALIZED_MATCH`, `ACRONYM_EQUIVALENCE`, `YEAR_EXACT`, `ROLE_COMPATIBLE` — ou `NOT_APPLICABLE` / `STRUCTURAL_NOT_APPLICABLE` em `carga` e `evento` de `ORGANIZACAO_EVENTO`.)*

### 3.2 Causa raiz combinada e impacto após remoção do `X`

1. **Prefixo neutro compartilhado + `low=0.4` arbitrário:**
   - A substituição de nomes explícitos (`OUTRA ...`) por identificadores neutros (`PESSOA FICTICIA <12-hex>` e `INSTITUTO FICTICIO <12-hex>`) faz com que pares factuais distintos compartilhem ~57%–65% de similaridade por Levenshtein normalizado (`16/28` e `19/31` caracteres do prefixo fixo mais colisões hexadecimais).
   - Com os limiares arbitrários do teste (`holder_low=0.4`, `institution_low=0.4`), esses escores caem na faixa intermediária `[0.4, 0.95)` (`INCONCLUSIVE_BORDERLINE`) em vez de `CONFLICT`.
2. **Essencialidade de `instituicao` em `EVENT_CATEGORIES` (`matcher/rules.py:300-322`):**
   - Em `essential_fields(record)`, `instituicao` é essencial para `FORMACAO_ACADEMICA` e `FORMACAO_COMPLEMENTAR`, mas **não** está incluída em `essential_fields` para `EVENT_CATEGORIES` (`PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO`, `ORGANIZACAO_EVENTO`).
   - Consequentemente, quando `instituicao` recebe `INCONCLUSIVE_BORDERLINE` em `ORGANIZACAO_EVENTO`, `classify()` (`matcher/engine.py:31-45`) não vê `CONFLICT` e vê todos os campos essenciais com `MATCH`, produzindo **`VALIDADO`** mesmo diante de mutação factual da instituição promotora.
3. **Efeito comparativo frente ao Baseline `B` (`BASELINE_NORMALIZED`) após remoção do `X`:**
   - Antes da remoção do `X`, o `Baseline B` errava os 5 casos `legitimate` (`macro_f1 = 0.7778`), permitindo que `proposed > reports["B"]["macro_f1"]` passasse (`0.8849 > 0.7778`) e a falha aparecesse apenas na linha 228 (`assert row["status"] == "DIVERGENTE"`).
   - Após remover o `X` inicial, todas as variações `legitimate` (espaços, caixa, pontuação) tornam-se idênticas após `normalize_text`, levando `BASELINE_NORMALIZED` a **`macro_f1 = 1.0`** (`0` erros, pois `B` atribui `score = 0.0 < low` a qualquer divergência pós-normalização e não tem faixa cinzenta). Como `LEVENSHTEIN_NORM` (assim como `JARO_WINKLER` e `TOKEN_HYBRID`) mantém `macro_f1 = 0.8849`, o teste falha agora na linha 199 (`assert proposed["macro_f1"] > reports["B"]["macro_f1"]`, `0.8849 > 1.0` falso) — além de continuar incompatível com linhas 219–226 (que pressupunham AD-014 exclusiva de `legitimate`), linha 228 e linhas 232/235 (`macro_f1 == 1`).
   - Enquanto isso, o `Baseline A` (`BASELINE_EXACT`) obtém `macro_f1 = 0.8222` (falha nos 5 casos `legitimate` por erro de associação `SEM_COMPROVANTE`, pois todos os campos textuais variam em caixa/espaços/pontuação).

---

## 4. Separação aprovada: contrato unitário vs. contrato de avaliação de desempenho

Com aprovação explícita do usuário, a verificação determinística de software foi separada da avaliação de desempenho do motor sem alterar `matcher/`, limiares, `expected`/`gold` nem ocultar falhas:

1. **Testes unitários de contrato (`tests/test_experiments.py` + `test_synthetic_leakage.py` + `test_certificate_templates.py`):**
   - `test_synthetic_categories_and_operator_verdicts[pilot/final]` e `test_synthetic_unit_contracts_with_distributed_ad014[pilot/final]` foram refatorados para verificar invariantes estruturais (5 categorias, `start_year`/`end_year`, `event_name`, papel de apresentação, alfabeto raster), associação 1-para-1, classes determinísticas (`identity`/`legitimate` → `VALIDADO`, `omission`/`no_document` → `INCONCLUSIVO`), aplicação local de `AD-014` (`DOCUMENT_ACRONYM_EQUIVALENCE` quando presente e instituição não mutada, inclusive sem `acronym_table` na partição final) e famílias **sem sigla** (`issuer_name_acronym_evidence is None`).
   - Removidas as suposições indevidas de `macro_f1 == 1`, superioridade de `LEVENSHTEIN_NORM` sobre o `Baseline B` com limiares não calibrados e presença obrigatória de `AD-014` em todo caso `legitimate`.
2. **Contrato de avaliação de desempenho (`tests/test_performance_reporting_contract.py`):**
   - Verifica `classification`, `evaluate` e `experiment2` contra resultados esperados calculados manualmente em exemplos pequenos e independentes (cobrindo erros de regra, associação e extração frente a oráculo).
   - Garante que `factual_mutation` permanece integral em `rows` (`expected == "DIVERGENTE"`), matriz $3 \times 3$, `per_class`, `accuracy`, `macro_f1`, `without_no_document`, `by_category` e `error_causes`, sem congelar `0.8849` como meta, sem ranquear métodos como critério de aprovação e sem `xfail`/`skip`.
3. **Diferença entre check de software verde e motor calibrado/perfeito:**
   - **Suíte verde significa apenas integridade de software:** confirma que gerador, associação, regras implementadas e agregação de métricas funcionam conforme especificado e reportam erros fielmente.
   - **Suíte verde NÃO significa motor calibrado ou livre de erros:** o motor atual, com limiares não calibrados e regras vigentes, continua imperfeito. Em particular, em `ORGANIZACAO_EVENTO` (e demais `EVENT_CATEGORIES`), como `instituicao` ainda não integra `essential_fields` (`matcher/rules.py:300-322`), uma instituição emissora em faixa limítrofe (`INCONCLUSIVE_BORDERLINE`) produz **`VALIDADO`** (`VALIDADO_CORRESPONDENCIA_COMPLETA`) apesar da mutação factual, enquanto a decisão sobre essencialidade institucional permanece pendente. Da mesma forma, `titular` limítrofe em `APRESENTACAO_TRABALHO` retorna `INCONCLUSIVO`. Esses erros continuam registrados integralmente como `error_cause == "rule"` nas métricas do `Experiment 2`.
4. **Decisões metodológicas ainda pendentes antes da calibração piloto:**
   - Decidir se `instituicao` deve compor `essential_fields` em `EVENT_CATEGORIES` (ou em `ORGANIZACAO_EVENTO`, evitando que `INCONCLUSIVE_BORDERLINE` em instituição vire `VALIDADO`).
   - Calibrar `holder_low` e `institution_low` exclusivamente no piloto (`50` casos) após validação humana dos templates em português.
   - Avaliar se o operador `legitimate` deve manter apenas variações equivalentes de caixa/pontuação/espaços ou também incluir casos com sigla isolada (sem nome completo no campo principal) caso se deseje diferenciar o motor proposto do `BASELINE_NORMALIZED` pela resolução de siglas (`ACRONYM_EQUIVALENCE` / `DOCUMENT_ACRONYM_EQUIVALENCE`).

---

## 5. Pendências abertas (este documento não aprova o benchmark)

- Aprovação humana explícita dos templates em português (`TEMPLATE_PROVENANCE`).
- Calibração piloto, congelamento (`freeze`), geração/hash do conjunto final oficial, anotações humanas independentes A/B e consenso.
- As execuções de verificação pós-edição (`pytest` focal e `ruff check .`) constam exclusivamente no registro de entrega da tarefa correspondente.

---

## 6. Política aprovada de instituição em eventos (`EVENT_CATEGORIES`, 2026-11-15)

### 6.1 Regra implementada (`matcher/rules.py`)

Com aprovação explícita do usuário, `essential_fields(record)` passou a incluir `"instituicao"` condicionalmente nas três categorias de eventos (`PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO`, `ORGANIZACAO_EVENTO`) sempre que o XML declarar `institution` ou `institution_acronym` com conteúdo não vazio após `normalize_text`:

1. **XML declara instituição ou sigla (`_first_normalized` não nulo):**
   - Comprovante coerente (igualdade normalizada, similaridade $\ge \tau_{\text{inst\_alto}}$, `DOCUMENT_ACRONYM_EQUIVALENCE` local `AD-014` ou fallback em `acronym_table` via `ACRONYM_EQUIVALENCE`) produz `MATCH` e permite `VALIDADO`.
   - Comprovante sem instituição (`MISSING_DOCUMENT` / `MISSING_DOCUMENT_VALUE`), em faixa limítrofe (`INCONCLUSIVE_BORDERLINE` / `SIMILARITY`) ou com sigla isolada desconhecida (`INCONCLUSIVE_BORDERLINE` / `UNKNOWN_INSTITUTION_ACRONYM`) **impede `VALIDADO`** e resulta em `INCONCLUSIVO` (`EVIDENCIA_INSUFICIENTE`, `review_required=True`).
   - Conflito factual em instituição (`CONFLICT` por similaridade $< \tau_{\text{inst\_baixo}}$ ou `DISTINCT_KNOWN_INSTITUTIONS`) ou conflito decisivo em qualquer outro campo (`titular`, `titulo`, `evento`, `ano`, `carga`) preserva prioridade estrita em `classify()` e resulta em `DIVERGENTE` (`CONFLITO_ATRIBUTO_DECISIVO`), mesmo quando `instituicao` estiver ausente ou incerta.
2. **XML não declara instituição nem sigla (ambos `None` ou vazios/pontuação após `normalize_text`):**
   - `"instituicao"` **não** entra em `essential_fields(record)`, evitando exigir correspondência impossível ou inferência.
   - `compare_institution` preserva a evidência de ausência (`MISSING_LATTES` quando o documento informa instituição ou sigla isolada desconhecida; `MISSING_BOTH` quando ambos omitem), **sem** inventar `CONFLICT` nem converter `MISSING_LATTES` em `UNKNOWN_INSTITUTION_ACRONYM`.

### 6.2 Impacto observado e custo de inconclusivos

- **Eliminação de falsos `VALIDADO`:** no fixture independente de `tests/test_performance_reporting_contract.py` (`case-2`, `ORGANIZACAO_EVENTO` com instituição limítrofe) e nos casos `ORGANIZACAO_EVENTO` de `factual_mutation` com `seed=93` (`3a9914e74fbaf0f7095f` no piloto e `b280019df0eb6527a91e` no final), o veredito deixa de ser `VALIDADO` e passa a `INCONCLUSIVO` (`EVIDENCIA_INSUFICIENTE`), preservando `expected == "DIVERGENTE"` e `error_cause == "rule"`. No recorte `seed=93` (`5+5` famílias, `LEVENSHTEIN_NORM`, limiares não calibrados do teste), `macro_f1` observada passa de `0.8849206349206349` para `0.8863636363636364`, enquanto os erros de `titular` limítrofe em `APRESENTACAO_TRABALHO` permanecem `INCONCLUSIVO`.
- **Custo esperado em `INCONCLUSIVO`:** exigir comprovação institucional quando declarada no XML transfere para `INCONCLUSIVO` (`review_required=True`) certificados de eventos que omitam a entidade emissora, tragam apenas sigla isolada sem `AD-014`/dicionário ou caiam na faixa cinzenta $[\tau_{\text{inst\_baixo}}, \tau_{\text{inst\_alto}})$. Isso protege contra validação indevida sem evidência, ao custo de elevar a fila de revisão humana (`AD-013`) e reduzir a taxa de confirmação automática quando comprovantes de eventos forem omissos ou abreviados sem contexto, até calibração piloto adequada dos limiares.
