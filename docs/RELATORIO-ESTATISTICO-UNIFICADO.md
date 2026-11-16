# Relatório Estatístico Unificado — Bancada Experimental Completa (`comprova-lattes`)

Documento consolidado automaticamente a partir dos artefatos JSON verificados em disco nas **4 baterias experimentais independentes** (`seed = 42 v2`, `seed = 101`, `seed = 202`, `seed = 303`), mais os registros históricos da bateria inicial (`seed = 42 v1`) e do teste de rajada (`burst3w`).

## 1. Inventário Forense Global e Isolamento entre Baterias

- **Universo total auditado nas 4 baterias principais:** **`600` cenários sintéticos únicos** (`120` famílias únicas; `480` documentos PDF/PNG únicos com comprovante e `120` cenários `no_document`).
- **Execuções multimodais reais (`gemini-3.5-flash-lite`):** `4 × (80 final + 40 piloto) × 3 repetições = 1.440` extrações válidas nas 4 baterias principais (plus `360` da Bateria Base `v1` = **`1.800` extrações reais concluintes** com `0` falhas não recuperadas no estado final).
- **Execuções baseline clássicas (`Tesseract OCR v5.4.0.20240606 + OCRRegex`):** `4 × 120 = 480` extrações locais determinísticas.
- **Parâmetros inferenciais aplicados em todas as baterias:** Bootstrap de *clusters* por família (`B = 2.000` reamostragens, `IC = 95%`, `seed = 42`); teste complementar de McNemar exato binomial bicaudal por acerto integral da família com correção de Holm-Bonferroni (`4` comparações vs. `LEVENSHTEIN_NORM`).

| Bateria | Seed | Casos (Piloto / Final) | Docs (Piloto / Final) | Famílias | Sobreposições (`case/fam/doc`) | `bundle_sha256` (pré-freeze) | `freeze.json` SHA-256 | Drift / Template |
| --- | :---: | :---: | :---: | :---: | :---: | --- | --- | --- |
| Base v2 (`seed=42`) | `42` | `150` (`50/100`) | `120` (`40/80`) | `30` | `0/0/0` | `2b2de7b726de45b8…` | `018c7ea9af07e859…` | `drift=False` / `draft_pending_human_validation` |
| Chave 1 (`seed=101`) | `101` | `150` (`50/100`) | `120` (`40/80`) | `30` | `0/0/0` | `ec4ee975c64b8706…` | `bc365b493f96fe97…` | `drift=False` / `draft_pending_human_validation` |
| Chave 2 (`seed=202`) | `202` | `150` (`50/100`) | `120` (`40/80`) | `30` | `0/0/0` | `2341cbfbbbbf86da…` | `eb6c2153fc8587eb…` | `drift=False` / `draft_pending_human_validation` |
| Chave 3 (`seed=303`) | `303` | `150` (`50/100`) | `120` (`40/80`) | `30` | `0/0/0` | `021ce665e7e9353e…` | `5ae1cbf7bd1430b3…` | `drift=False` / `draft_pending_human_validation` |

> **Hashes completos dos manifestos `freeze.json`:**
> - Bateria Base v2 (`seed=42`, 2 chaves alternadas): `018c7ea9af07e859a77c15e331692f89fd905ccc70279a99ac00ebded3cfa436` (prompt `entities-v2`, rasterizador `pillow-aileron-gray-v1`, `code=b319587eb603dcd9…`)
> - Bateria Chave 1 (`seed=101`): `bc365b493f96fe97a255bbdd9554430041691d1ec4a51a25c2b0b5862bf10f9c` (prompt `entities-v2`, rasterizador `pillow-aileron-gray-v1`, `code=b319587eb603dcd9…`)
> - Bateria Chave 2 (`seed=202`): `eb6c2153fc8587eba5806d4a7c22cce16bdf9c286c2e333305151f36f87b6313` (prompt `entities-v2`, rasterizador `pillow-aileron-gray-v1`, `code=b319587eb603dcd9…`)
> - Bateria Chave 3 (`seed=303`): `5ae1cbf7bd1430b31ecf12e9491292536c32d1b0367b9bf0c4b7ce137bf784f8` (prompt `entities-v2`, rasterizador `pillow-aileron-gray-v1`, `code=b319587eb603dcd9…`)

## 2. Síntese Consolidada Multi-Bateria (Médias e Amplitudes entre Chaves/Seeds)

| Recorte Consolidado | Exp 1 Gemini Literal (Min–Máx) | Exp 1 Equiv. Norm. | Exp 1 OCR Baseline | Exp 2 `A` / `B` / `JW` Macro-F1 | Exp 2 `LEV` (Min–Máx) / `TOK` | Exp 3 Macro-F1 (Min–Máx) | Exp 3 Acurácia | Exp 3 Oráculo |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **3 Chaves Teamwork (`101, 202, 303`) — FINAL (`N=300`)** | 84.72% (`84.17%–85.42%`) | 96.39% | 29.17% | 0.8222 / 1.0000 / 0.9264 | **0.9872** (`0.9743–1.0000`) / 1.0000 | **0.9787** (`0.9627–0.9917`) | **98.11%** | 0.9872 |
| **4 Baterias Principais (`42, 101, 202, 303`) — FINAL (`N=400`)** | 85.10% (`84.17%–86.25%`) | 96.77% | 29.38% | 0.8222 / 1.0000 / 0.9384 | **0.9904** (`0.9743–1.0000`) / 1.0000 | **0.9840** (`0.9627–1.0000`) | **98.58%** | 0.9904 |
| **3 Chaves Teamwork (`101, 202, 303`) — PILOTO (`N=150`)** | 85.83% (`85.00%–86.67%`) | 97.78% | 30.83% | 0.8222 / 1.0000 / 0.9470 | **1.0000** (`1.0000–1.0000`) / 1.0000 | **0.9981** (`0.9944–1.0000`) | **99.78%** | 1.0000 |
| **4 Baterias Principais (`42, 101, 202, 303`) — PILOTO (`N=200`)** | 85.83% (`85.00%–86.67%`) | 97.92% | 31.87% | 0.8222 / 1.0000 / 0.9470 | **1.0000** (`1.0000–1.0000`) / 1.0000 | **0.9958** (`0.9889–1.0000`) | **99.50%** | 1.0000 |

> **Nota de auditoria documental:** em `experiments_runs/battery_key_1/battery_report.md` (linha 89), a prosa conclusiva mencionou `"23.75%"` para o baseline OCR, porém a tabela na linha 26 e o arquivo fonte oficial `exp1-final.json` comprovam que o valor real é **`31,25%`** (`25/80` documentos corretos), valor preservado neste relatório unificado.

## 3. Calibração Empírica no Conjunto Piloto (`N = 50` por bateria, regra `first tie wins`)

| Bateria | Cand. 0 (`A`) | Cand. 1 (`B`) | Cand. 2 (`C`) | Cand. 3 (`D`) | Índice Selecionado | Configuração Congelada (`assoc`, `δ`, `titular`, `título`, `instituição`) |
| --- | :---: | :---: | :---: | :---: | :---: | --- |
| Base v2 (`seed=42`) | `0.9743` | `0.9743` | `1.0000` | `1.0000` | **`2`** | `assoc=0.65, δ=0.02, tit=[0.60,0.85], tít=[0.60,0.85], inst=[0.60,0.85]` |
| Chave 1 (`seed=101`) | `0.9743` | `0.9743` | `1.0000` | `1.0000` | **`2`** | `assoc=0.65, δ=0.02, tit=[0.60,0.85], tít=[0.60,0.85], inst=[0.60,0.85]` |
| Chave 2 (`seed=202`) | `0.9743` | `0.9743` | `1.0000` | `1.0000` | **`2`** | `assoc=0.65, δ=0.02, tit=[0.60,0.85], tít=[0.60,0.85], inst=[0.60,0.85]` |
| Chave 3 (`seed=303`) | `1.0000` | `1.0000` | `1.0000` | `1.0000` | **`0`** | `assoc=0.55, δ=0.02, tit=[0.50,0.75], tít=[0.50,0.70], inst=[0.50,0.70]` |

<details><summary>Ver definição completa dos 4 candidatos avaliados no Piloto</summary>

- **Candidato 0:** `assoc=0.55, δ=0.02, tit=[0.50,0.75], tít=[0.50,0.70], inst=[0.50,0.70]` (`mode=PROPOSED`, `metric=LEVENSHTEIN_NORM`)
- **Candidato 1:** `assoc=0.60, δ=0.02, tit=[0.50,0.80], tít=[0.50,0.78], inst=[0.50,0.75]` (`mode=PROPOSED`, `metric=LEVENSHTEIN_NORM`)
- **Candidato 2:** `assoc=0.65, δ=0.02, tit=[0.60,0.85], tít=[0.60,0.85], inst=[0.60,0.85]` (`mode=PROPOSED`, `metric=LEVENSHTEIN_NORM`)
- **Candidato 3:** `assoc=0.75, δ=0.02, tit=[0.75,0.92], tít=[0.75,0.90], inst=[0.75,0.90]` (`mode=PROPOSED`, `metric=LEVENSHTEIN_NORM`)

</details>

## 4. Experimento 1 — Extração Documental Multimodal (`gemini-3.5-flash-lite` 3× vs. `Tesseract OCR + RegEx`)

### 4.1 Partição Final (`n = 80` documentos/bateria × 3 repetições = `240` execuções/bateria)

| Bateria | Rep 1 Lit. | Rep 2 Lit. | Rep 3 Lit. | **Gemini `mean_3` Lit. `[IC 95%]`** | **Gemini `mean_3` Equiv.** | `all_three` Estab. `[IC 95%]` | Instáveis | **Baseline OCR `[IC 95%]`** (Falhas / Condicional) |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | --- |
| Base v2 (`seed=42`) | 86.25% | 87.50% | 85.00% | **86.25%** (0.8625 `[0.8083; 0.9167]`) | **97.92%** | 0.8375 `[0.7750; 0.9000]` | `5/80` (`6.25%`) | 30.00% (0.3000 `[0.2250; 0.3750]`) / falhas=`{'INVALID_JSON': 24}`, cond=`42.86%` |
| Chave 1 (`seed=101`) | 85.00% | 85.00% | 82.50% | **84.17%** (0.8417 `[0.7667; 0.9083]`) | **96.25%** | 0.8250 `[0.7497; 0.9000]` | `4/80` (`5.00%`) | 31.25% (0.3125 `[0.2250; 0.4000]`) / falhas=`{'INVALID_JSON': 19}`, cond=`40.98%` |
| Chave 2 (`seed=202`) | 83.75% | 86.25% | 86.25% | **85.42%** (0.8542 `[0.7833; 0.9208]`) | **97.08%** | 0.8250 `[0.7250; 0.9125]` | `6/80` (`7.50%`) | 26.25% (0.2625 `[0.1875; 0.3375]`) / falhas=`{'INVALID_JSON': 26}`, cond=`38.89%` |
| Chave 3 (`seed=303`) | 82.50% | 85.00% | 86.25% | **84.58%** (0.8458 `[0.7833; 0.9125]`) | **95.83%** | 0.8250 `[0.7500; 0.9000]` | `4/80` (`5.00%`) | 30.00% (0.3000 `[0.2250; 0.3750]`) / falhas=`{'INVALID_JSON': 27}`, cond=`45.28%` |
| *Histórico Base v1* (`seed=42`, 1 chave) | 85.00% | 86.25% | 88.75% | 86.67% (0.8667 `[0.8125; 0.9208]`) | 99.17% | 0.8375 `[0.7625; 0.9000]` | `5/80` | iguais (`30.00%`) |
| *Histórico Rajada 3w* (`burst3w`, sem cadência) | 63.75% | 42.50% | 28.75% | 45.00% (`47.5% API_ERROR HTTP 429`) | 51.67% | 0.2000 `[0.0750; 0.3500]` | `51/80` | iguais (`30.00%`) |

### 4.2 Partição Piloto (`n = 40` documentos/bateria × 3 repetições = `120` execuções/bateria)

| Bateria | Rep 1 Lit. | Rep 2 Lit. | Rep 3 Lit. | **Gemini `mean_3` Lit. `[IC 95%]`** | **Gemini `mean_3` Equiv.** | `all_three` Estab. `[IC 95%]` | Instáveis | **Baseline OCR `[IC 95%]`** (Falhas / Condicional) |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | --- |
| Base v2 (`seed=42`) | 85.00% | 85.00% | 87.50% | **85.83%** (0.8583 `[0.7833; 0.9333]`) | **98.33%** | 0.8500 `[0.7750; 0.9250]` | `2/40` (`5.00%`) | 35.00% (0.3500 `[0.2500; 0.4500]`) / falhas=`{'INVALID_JSON': 12}`, cond=`50.00%` |
| Chave 1 (`seed=101`) | 87.50% | 87.50% | 85.00% | **86.67%** (0.8667 `[0.7833; 0.9500]`) | **98.33%** | 0.8500 `[0.7500; 0.9500]` | `2/40` (`5.00%`) | 35.00% (0.3500 `[0.2250; 0.4750]`) / falhas=`{'INVALID_JSON': 10}`, cond=`46.67%` |
| Chave 2 (`seed=202`) | 87.50% | 85.00% | 85.00% | **85.83%** (0.8583 `[0.7917; 0.9250]`) | **98.33%** | 0.8250 `[0.7500; 0.9000]` | `3/40` (`7.50%`) | 25.00% (0.2500 `[0.1250; 0.3750]`) / falhas=`{'INVALID_JSON': 16}`, cond=`41.67%` |
| Chave 3 (`seed=303`) | 87.50% | 85.00% | 82.50% | **85.00%** (0.8500 `[0.7833; 0.9167]`) | **96.67%** | 0.8250 `[0.7500; 0.9000]` | `3/40` (`7.50%`) | 32.50% (0.3250 `[0.2250; 0.4250]`) / falhas=`{'INVALID_JSON': 10}`, cond=`43.33%` |
| *Histórico Base v1* (`seed=42`, 1 chave) | 85.00% | 85.00% | 87.50% | 85.83% (0.8583 `[0.7833; 0.9333]`) | 98.33% | 0.8500 `[0.7750; 0.9250]` | `2/40` | iguais (`35.00%`) |

### 4.3 Desempenho por Campo (`11` Campos Extraídos — Média `mean_3` no Conjunto Final)

#### Bateria Base v2 (`seed=42`, 2 chaves alternadas) — Final (`n = 80` docs)

| Campo | Precision | Recall | F1 | Accuracy Literal | Estabilidade (`3` reps) |
| --- | :---: | :---: | :---: | :---: | :---: |
| `activity_title` | 0.8958 | 0.8958 | 0.8958 | 0.8958 | 96.25% |
| `activity_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `end_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `event_name` | 0.8438 | 0.8438 | 0.8438 | 0.9375 | 100.00% |
| `holder_name` | 0.8444 | 0.8444 | 0.8444 | 0.8833 | 98.75% |
| `issuer_acronym` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `issuer_institution` | 0.9000 | 0.9000 | 0.9000 | 0.9000 | 100.00% |
| `issuer_name_acronym_evidence` | 0.8583 | 0.8583 | 0.8583 | 0.9292 | 98.75% |
| `participation_role_raw` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `start_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `workload_hours` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |

#### Bateria Chave 1 (`seed=101`) — Final (`n = 80` docs)

| Campo | Precision | Recall | F1 | Accuracy Literal | Estabilidade (`3` reps) |
| --- | :---: | :---: | :---: | :---: | :---: |
| `activity_title` | 0.8866 | 0.8792 | 0.8828 | 0.8792 | 98.75% |
| `activity_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `end_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `event_name` | 0.8267 | 0.8438 | 0.8351 | 0.9292 | 98.75% |
| `holder_name` | 0.8556 | 0.8556 | 0.8556 | 0.8917 | 98.75% |
| `issuer_acronym` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `issuer_institution` | 0.9000 | 0.9000 | 0.9000 | 0.9000 | 100.00% |
| `issuer_name_acronym_evidence` | 0.8417 | 0.8417 | 0.8417 | 0.9208 | 96.25% |
| `participation_role_raw` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `start_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `workload_hours` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |

#### Bateria Chave 2 (`seed=202`) — Final (`n = 80` docs)

| Campo | Precision | Recall | F1 | Accuracy Literal | Estabilidade (`3` reps) |
| --- | :---: | :---: | :---: | :---: | :---: |
| `activity_title` | 0.8987 | 0.8875 | 0.8931 | 0.8875 | 95.00% |
| `activity_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `end_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `event_name` | 0.8235 | 0.8750 | 0.8485 | 0.9250 | 95.00% |
| `holder_name` | 0.8556 | 0.8556 | 0.8556 | 0.8917 | 98.75% |
| `issuer_acronym` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `issuer_institution` | 0.8958 | 0.8958 | 0.8958 | 0.8958 | 97.50% |
| `issuer_name_acronym_evidence` | 0.9000 | 0.9000 | 0.9000 | 0.9500 | 100.00% |
| `participation_role_raw` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `start_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `workload_hours` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |

#### Bateria Chave 3 (`seed=303`) — Final (`n = 80` docs)

| Campo | Precision | Recall | F1 | Accuracy Literal | Estabilidade (`3` reps) |
| --- | :---: | :---: | :---: | :---: | :---: |
| `activity_title` | 0.9099 | 0.8833 | 0.8964 | 0.8833 | 96.25% |
| `activity_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `end_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `event_name` | 0.8083 | 0.8750 | 0.8402 | 0.9167 | 96.25% |
| `holder_name` | 0.8667 | 0.8667 | 0.8667 | 0.9000 | 100.00% |
| `issuer_acronym` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `issuer_institution` | 0.9000 | 0.9000 | 0.9000 | 0.9000 | 100.00% |
| `issuer_name_acronym_evidence` | 0.8500 | 0.8500 | 0.8500 | 0.9250 | 97.50% |
| `participation_role_raw` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `start_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `workload_hours` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |

<details><summary>Ver desempenho dos 11 campos no Conjunto Piloto (todas as 4 baterias)</summary>

#### Bateria Base v2 (`seed=42`, 2 chaves alternadas) — Piloto (`n = 40` docs)

| Campo | Precision | Recall | F1 | Accuracy Literal | Estabilidade (`3` reps) |
| --- | :---: | :---: | :---: | :---: | :---: |
| `activity_title` | 0.8812 | 0.8667 | 0.8738 | 0.8667 | 95.00% |
| `activity_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `end_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `event_name` | 0.8407 | 0.8750 | 0.8573 | 0.9333 | 97.50% |
| `holder_name` | 0.8444 | 0.8444 | 0.8444 | 0.8833 | 97.50% |
| `issuer_acronym` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `issuer_institution` | 0.8833 | 0.8833 | 0.8833 | 0.8833 | 97.50% |
| `issuer_name_acronym_evidence` | 0.8667 | 0.8667 | 0.8667 | 0.9333 | 97.50% |
| `participation_role_raw` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `start_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `workload_hours` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |

#### Bateria Chave 1 (`seed=101`) — Piloto (`n = 40` docs)

| Campo | Precision | Recall | F1 | Accuracy Literal | Estabilidade (`3` reps) |
| --- | :---: | :---: | :---: | :---: | :---: |
| `activity_title` | 0.9000 | 0.9000 | 0.9000 | 0.9000 | 100.00% |
| `activity_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `end_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `event_name` | 0.9375 | 0.9375 | 0.9375 | 0.9750 | 100.00% |
| `holder_name` | 0.8333 | 0.8333 | 0.8333 | 0.8750 | 100.00% |
| `issuer_acronym` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `issuer_institution` | 0.9000 | 0.9000 | 0.9000 | 0.9000 | 100.00% |
| `issuer_name_acronym_evidence` | 0.8667 | 0.8667 | 0.8667 | 0.9333 | 95.00% |
| `participation_role_raw` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `start_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `workload_hours` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |

#### Bateria Chave 2 (`seed=202`) — Piloto (`n = 40` docs)

| Campo | Precision | Recall | F1 | Accuracy Literal | Estabilidade (`3` reps) |
| --- | :---: | :---: | :---: | :---: | :---: |
| `activity_title` | 0.8908 | 0.8833 | 0.8870 | 0.8833 | 95.00% |
| `activity_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `end_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `event_name` | 0.8578 | 0.8750 | 0.8662 | 0.9417 | 97.50% |
| `holder_name` | 0.8333 | 0.8333 | 0.8333 | 0.8750 | 100.00% |
| `issuer_acronym` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `issuer_institution` | 0.9000 | 0.9000 | 0.9000 | 0.9000 | 97.50% |
| `issuer_name_acronym_evidence` | 0.9000 | 0.9000 | 0.9000 | 0.9500 | 100.00% |
| `participation_role_raw` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `start_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `workload_hours` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |

#### Bateria Chave 3 (`seed=303`) — Piloto (`n = 40` docs)

| Campo | Precision | Recall | F1 | Accuracy Literal | Estabilidade (`3` reps) |
| --- | :---: | :---: | :---: | :---: | :---: |
| `activity_title` | 0.8983 | 0.8833 | 0.8907 | 0.8833 | 97.50% |
| `activity_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `end_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `event_name` | 0.8254 | 0.8750 | 0.8490 | 0.9250 | 95.00% |
| `holder_name` | 0.8444 | 0.8444 | 0.8444 | 0.8833 | 97.50% |
| `issuer_acronym` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `issuer_institution` | 0.9000 | 0.9000 | 0.9000 | 0.9000 | 100.00% |
| `issuer_name_acronym_evidence` | 0.8833 | 0.8833 | 0.8833 | 0.9417 | 97.50% |
| `participation_role_raw` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `start_year` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |
| `workload_hours` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 100.00% |

</details>

### 4.4 Desagregação do Experimento 1 por Categoria Curricular (`by_category`)

#### Final (`16` docs/categoria)

| Bateria | Categoria | Docs `n` | Gemini `mean_3` Literal | Gemini `mean_3` Equiv. | Baseline `OCR+RegEx` | Falhas OCR |
| --- | --- | :---: | :---: | :---: | :---: | --- |
| Base v2 (`seed=42`) | `FORMACAO_ACADEMICA` | `16` | **85.42%** | **97.92%** | 31.25% | `{'INVALID_JSON': 2}` |
| Base v2 (`seed=42`) | `FORMACAO_COMPLEMENTAR` | `16` | **89.58%** | **95.83%** | 25.00% | `{'INVALID_JSON': 6}` |
| Base v2 (`seed=42`) | `PARTICIPACAO_EVENTO` | `16` | **81.25%** | **100.00%** | 18.75% | `{'INVALID_JSON': 7}` |
| Base v2 (`seed=42`) | `APRESENTACAO_TRABALHO` | `16` | **83.33%** | **95.83%** | 43.75% | `{'INVALID_JSON': 6}` |
| Base v2 (`seed=42`) | `ORGANIZACAO_EVENTO` | `16` | **91.67%** | **100.00%** | 31.25% | `{'INVALID_JSON': 3}` |
| Chave 1 (`seed=101`) | `FORMACAO_ACADEMICA` | `16` | **87.50%** | **100.00%** | 31.25% | `{'INVALID_JSON': 5}` |
| Chave 1 (`seed=101`) | `FORMACAO_COMPLEMENTAR` | `16` | **91.67%** | **97.92%** | 31.25% | `{'INVALID_JSON': 5}` |
| Chave 1 (`seed=101`) | `PARTICIPACAO_EVENTO` | `16` | **81.25%** | **97.92%** | 25.00% | `{'INVALID_JSON': 4}` |
| Chave 1 (`seed=101`) | `APRESENTACAO_TRABALHO` | `16` | **87.50%** | **100.00%** | 37.50% | `{'INVALID_JSON': 2}` |
| Chave 1 (`seed=101`) | `ORGANIZACAO_EVENTO` | `16` | **72.92%** | **85.42%** | 31.25% | `{'INVALID_JSON': 3}` |
| Chave 2 (`seed=202`) | `FORMACAO_ACADEMICA` | `16` | **87.50%** | **100.00%** | 25.00% | `{'INVALID_JSON': 5}` |
| Chave 2 (`seed=202`) | `FORMACAO_COMPLEMENTAR` | `16` | **89.58%** | **100.00%** | 25.00% | `{'INVALID_JSON': 3}` |
| Chave 2 (`seed=202`) | `PARTICIPACAO_EVENTO` | `16` | **83.33%** | **100.00%** | 18.75% | `{'INVALID_JSON': 7}` |
| Chave 2 (`seed=202`) | `APRESENTACAO_TRABALHO` | `16` | **85.42%** | **97.92%** | 37.50% | `{'INVALID_JSON': 6}` |
| Chave 2 (`seed=202`) | `ORGANIZACAO_EVENTO` | `16` | **81.25%** | **87.50%** | 25.00% | `{'INVALID_JSON': 5}` |
| Chave 3 (`seed=303`) | `FORMACAO_ACADEMICA` | `16` | **87.50%** | **100.00%** | 37.50% | `{'INVALID_JSON': 6}` |
| Chave 3 (`seed=303`) | `FORMACAO_COMPLEMENTAR` | `16` | **93.75%** | **100.00%** | 31.25% | `{'INVALID_JSON': 6}` |
| Chave 3 (`seed=303`) | `PARTICIPACAO_EVENTO` | `16` | **83.33%** | **95.83%** | 12.50% | `{'INVALID_JSON': 5}` |
| Chave 3 (`seed=303`) | `APRESENTACAO_TRABALHO` | `16` | **87.50%** | **100.00%** | 31.25% | `{'INVALID_JSON': 6}` |
| Chave 3 (`seed=303`) | `ORGANIZACAO_EVENTO` | `16` | **70.83%** | **83.33%** | 37.50% | `{'INVALID_JSON': 4}` |

#### Piloto (`8` docs/categoria)

| Bateria | Categoria | Docs `n` | Gemini `mean_3` Literal | Gemini `mean_3` Equiv. | Baseline `OCR+RegEx` | Falhas OCR |
| --- | --- | :---: | :---: | :---: | :---: | --- |
| Base v2 (`seed=42`) | `FORMACAO_ACADEMICA` | `8` | **87.50%** | **100.00%** | 37.50% | `{'INVALID_JSON': 3}` |
| Base v2 (`seed=42`) | `FORMACAO_COMPLEMENTAR` | `8` | **87.50%** | **100.00%** | 37.50% | `{'INVALID_JSON': 2}` |
| Base v2 (`seed=42`) | `PARTICIPACAO_EVENTO` | `8` | **87.50%** | **100.00%** | 25.00% | `{'INVALID_JSON': 2}` |
| Base v2 (`seed=42`) | `APRESENTACAO_TRABALHO` | `8` | **87.50%** | **100.00%** | 37.50% | `{'INVALID_JSON': 1}` |
| Base v2 (`seed=42`) | `ORGANIZACAO_EVENTO` | `8` | **79.17%** | **91.67%** | 37.50% | `{'INVALID_JSON': 4}` |
| Chave 1 (`seed=101`) | `FORMACAO_ACADEMICA` | `8` | **87.50%** | **100.00%** | 37.50% | `{}` |
| Chave 1 (`seed=101`) | `FORMACAO_COMPLEMENTAR` | `8` | **87.50%** | **100.00%** | 25.00% | `{'INVALID_JSON': 3}` |
| Chave 1 (`seed=101`) | `PARTICIPACAO_EVENTO` | `8` | **83.33%** | **91.67%** | 50.00% | `{'INVALID_JSON': 2}` |
| Chave 1 (`seed=101`) | `APRESENTACAO_TRABALHO` | `8` | **87.50%** | **100.00%** | 25.00% | `{'INVALID_JSON': 2}` |
| Chave 1 (`seed=101`) | `ORGANIZACAO_EVENTO` | `8` | **87.50%** | **100.00%** | 37.50% | `{'INVALID_JSON': 3}` |
| Chave 2 (`seed=202`) | `FORMACAO_ACADEMICA` | `8` | **87.50%** | **100.00%** | 37.50% | `{'INVALID_JSON': 3}` |
| Chave 2 (`seed=202`) | `FORMACAO_COMPLEMENTAR` | `8` | **83.33%** | **95.83%** | 12.50% | `{'INVALID_JSON': 6}` |
| Chave 2 (`seed=202`) | `PARTICIPACAO_EVENTO` | `8` | **87.50%** | **100.00%** | 25.00% | `{'INVALID_JSON': 2}` |
| Chave 2 (`seed=202`) | `APRESENTACAO_TRABALHO` | `8` | **87.50%** | **100.00%** | 37.50% | `{'INVALID_JSON': 3}` |
| Chave 2 (`seed=202`) | `ORGANIZACAO_EVENTO` | `8` | **83.33%** | **95.83%** | 12.50% | `{'INVALID_JSON': 2}` |
| Chave 3 (`seed=303`) | `FORMACAO_ACADEMICA` | `8` | **83.33%** | **95.83%** | 37.50% | `{'INVALID_JSON': 2}` |
| Chave 3 (`seed=303`) | `FORMACAO_COMPLEMENTAR` | `8` | **87.50%** | **100.00%** | 25.00% | `{'INVALID_JSON': 2}` |
| Chave 3 (`seed=303`) | `PARTICIPACAO_EVENTO` | `8` | **87.50%** | **95.83%** | 12.50% | `{'INVALID_JSON': 3}` |
| Chave 3 (`seed=303`) | `APRESENTACAO_TRABALHO` | `8` | **87.50%** | **100.00%** | 50.00% | `{'INVALID_JSON': 1}` |
| Chave 3 (`seed=303`) | `ORGANIZACAO_EVENTO` | `8` | **79.17%** | **91.67%** | 37.50% | `{'INVALID_JSON': 2}` |

### 4.5 Telemetria Completa de Rede, Tempos (`latency_ms`), Retries e Tokens

| Bateria | Partição | Rep 1 Lat. Média (ms) | Rep 2 Lat. Média (ms) | Rep 3 Lat. Média (ms) | **Latência Média Geral `[Mín – Máx]` (ms)** | Tentativas / Retries (`HTTP`) | Tokens Totais (`Input` + `Output`) |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | --- |
| Base v2 (`seed=42`) | `final` | 4412.3 | 7490.4 | 1621.6 | **4508.1** (`1012.6 – 76108.0`) | `254` / `14` (`{'429': 3, '503': 4}`) | `297,497` (`257,436` + `40,061`) |
| Base v2 (`seed=42`) | `pilot` | 2035.1 | 1332.3 | 1473.8 | **1613.7** (`964.0 – 6157.9`) | `140` / `20` (`{'429': 19, '503': 1}`) | `149,662` (`129,600` + `20,062`) |
| Chave 1 (`seed=101`) | `final` | 2335.1 | 1438.8 | 1755.6 | **1843.2** (`971.6 – 32684.1`) | `245` / `5` (`{'503': 4}`) | `298,415` (`258,612` + `39,803`) |
| Chave 1 (`seed=101`) | `pilot` | 2357.5 | 1610.3 | 1418.2 | **1795.3** (`967.8 – 14952.4`) | `121` / `1` (`{'503': 1}`) | `148,608` (`128,775` + `19,833`) |
| Chave 2 (`seed=202`) | `final` | 1957.3 | 1576.5 | 1550.9 | **1694.9** (`1025.4 – 7529.4`) | `243` / `3` (`{'429': 1, '503': 2}`) | `297,556` (`257,943` + `39,613`) |
| Chave 2 (`seed=202`) | `pilot` | 2113.8 | 1752.6 | 1347.1 | **1737.8** (`1013.2 – 14304.9`) | `121` / `1` (`{'503': 1}`) | `148,683` (`128,862` + `19,821`) |
| Chave 3 (`seed=303`) | `final` | 2718.5 | 1659.7 | 1553.7 | **1977.3** (`1153.8 – 28905.1`) | `240` / `0` (`{}`) | `297,762` (`257,904` + `39,858`) |
| Chave 3 (`seed=303`) | `pilot` | 2192.7 | 1723.4 | 2225.2 | **2047.1** (`1149.5 – 25340.4`) | `120` / `0` (`{}`) | `149,163` (`129,051` + `20,112`) |
| *Histórico Base v1* (`seed=42`) | `final` | 6585.2 | 1842.7 | 1892.4 | 3440.1 (`955.0 – 75569.0`) | `263` / `23` (`{'429': 21, '503': 2}`) | `297,354` (`257,436` + `39,918`) |
| *Histórico Base v1* (`seed=42`) | `pilot` | 3248.2 | 3942.1 | 3954.4 | 3714.9 (`1034.4 – 46359.7`) | `122` / `2` (`{'503': 2}`) | `149,662` (`129,600` + `20,062`) |

## 5. Experimento 2 — Motor Determinístico M2 sobre o Gabarito (`exp2`)

### 5.1 Partição Final (`N = 100` cenários, `20` famílias/bateria)

| Bateria | Variante | Acurácia | Macro-F1 `[IC 95% Bootstrap]` | F1 `VAL / DIV / INC` | Associação (`Acc / Prec / Rec`) | Órfãos | Matriz 3×3 | Famílias `100%` |
| --- | --- | :---: | :---: | :---: | :---: | :---: | --- | :---: |
| Base v2 (`seed=42`) | `A` | 80.00% | 0.8222 `[0.8222; 0.8222]` | `0.6667 / 1.0000 / 0.8000` | `80.00% / 1.0000 / 0.7500` | `20` | `[[20, 0, 20], [0, 20, 0], [0, 0, 40]]` | `0/20` (0.00%) |
| Base v2 (`seed=42`) | `B` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [0, 20, 0], [0, 0, 40]]` | `20/20` (100.00%) |
| Base v2 (`seed=42`) | `LEVENSHTEIN_NORM` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [0, 20, 0], [0, 0, 40]]` | `20/20` (100.00%) |
| Base v2 (`seed=42`) | `JARO_WINKLER` | 98.00% | 0.9743 `[0.9328; 1.0000]` | `1.0000 / 0.9474 / 0.9756` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [0, 18, 2], [0, 0, 40]]` | `18/20` (90.00%) |
| Base v2 (`seed=42`) | `TOKEN_HYBRID` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [0, 20, 0], [0, 0, 40]]` | `20/20` (100.00%) |
| Chave 1 (`seed=101`) | `A` | 80.00% | 0.8222 `[0.8222; 0.8222]` | `0.6667 / 1.0000 / 0.8000` | `80.00% / 1.0000 / 0.7500` | `20` | `[[20, 0, 20], [0, 20, 0], [0, 0, 40]]` | `0/20` (0.00%) |
| Chave 1 (`seed=101`) | `B` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [0, 20, 0], [0, 0, 40]]` | `20/20` (100.00%) |
| Chave 1 (`seed=101`) | `LEVENSHTEIN_NORM` | 99.00% | 0.9873 `[0.9609; 1.0000]` | `1.0000 / 0.9744 / 0.9877` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [0, 19, 1], [0, 0, 40]]` | `19/20` (95.00%) |
| Chave 1 (`seed=101`) | `JARO_WINKLER` | 97.00% | 0.9607 `[0.9171; 1.0000]` | `0.9877 / 0.9189 / 0.9756` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [1, 17, 2], [0, 0, 40]]` | `17/20` (85.00%) |
| Chave 1 (`seed=101`) | `TOKEN_HYBRID` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [0, 20, 0], [0, 0, 40]]` | `20/20` (100.00%) |
| Chave 2 (`seed=202`) | `A` | 80.00% | 0.8222 `[0.8222; 0.8222]` | `0.6667 / 1.0000 / 0.8000` | `80.00% / 1.0000 / 0.7500` | `20` | `[[20, 0, 20], [0, 20, 0], [0, 0, 40]]` | `0/20` (0.00%) |
| Chave 2 (`seed=202`) | `B` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [0, 20, 0], [0, 0, 40]]` | `20/20` (100.00%) |
| Chave 2 (`seed=202`) | `LEVENSHTEIN_NORM` | 98.00% | 0.9743 `[0.9328; 1.0000]` | `1.0000 / 0.9474 / 0.9756` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [0, 18, 2], [0, 0, 40]]` | `18/20` (90.00%) |
| Chave 2 (`seed=202`) | `JARO_WINKLER` | 95.00% | 0.9322 `[0.8677; 0.9743]` | `0.9756 / 0.8571 / 0.9639` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [2, 15, 3], [0, 0, 40]]` | `15/20` (75.00%) |
| Chave 2 (`seed=202`) | `TOKEN_HYBRID` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [0, 20, 0], [0, 0, 40]]` | `20/20` (100.00%) |
| Chave 3 (`seed=303`) | `A` | 80.00% | 0.8222 `[0.8222; 0.8222]` | `0.6667 / 1.0000 / 0.8000` | `80.00% / 1.0000 / 0.7500` | `20` | `[[20, 0, 20], [0, 20, 0], [0, 0, 40]]` | `0/20` (0.00%) |
| Chave 3 (`seed=303`) | `B` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [0, 20, 0], [0, 0, 40]]` | `20/20` (100.00%) |
| Chave 3 (`seed=303`) | `LEVENSHTEIN_NORM` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [0, 20, 0], [0, 0, 40]]` | `20/20` (100.00%) |
| Chave 3 (`seed=303`) | `JARO_WINKLER` | 92.00% | 0.8864 `[0.8137; 0.9471]` | `1.0000 / 0.7500 / 0.9091` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [0, 12, 8], [0, 0, 40]]` | `12/20` (60.00%) |
| Chave 3 (`seed=303`) | `TOKEN_HYBRID` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[40, 0, 0], [0, 20, 0], [0, 0, 40]]` | `20/20` (100.00%) |

### 5.2 Partição Piloto (`N = 50` cenários, `10` famílias/bateria)

| Bateria | Variante | Acurácia | Macro-F1 `[IC 95% Bootstrap]` | F1 `VAL / DIV / INC` | Associação (`Acc / Prec / Rec`) | Órfãos | Matriz 3×3 | Famílias `100%` |
| --- | --- | :---: | :---: | :---: | :---: | :---: | --- | :---: |
| Base v2 (`seed=42`) | `A` | 80.00% | 0.8222 `[0.8222; 0.8222]` | `0.6667 / 1.0000 / 0.8000` | `80.00% / 1.0000 / 0.7500` | `10` | `[[10, 0, 10], [0, 10, 0], [0, 0, 20]]` | `0/10` (0.00%) |
| Base v2 (`seed=42`) | `B` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `10/10` (100.00%) |
| Base v2 (`seed=42`) | `LEVENSHTEIN_NORM` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `10/10` (100.00%) |
| Base v2 (`seed=42`) | `JARO_WINKLER` | 96.00% | 0.9471 `[0.8519; 1.0000]` | `1.0000 / 0.8889 / 0.9524` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 8, 2], [0, 0, 20]]` | `8/10` (80.00%) |
| Base v2 (`seed=42`) | `TOKEN_HYBRID` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `10/10` (100.00%) |
| Chave 1 (`seed=101`) | `A` | 80.00% | 0.8222 `[0.8222; 0.8222]` | `0.6667 / 1.0000 / 0.8000` | `80.00% / 1.0000 / 0.7500` | `10` | `[[10, 0, 10], [0, 10, 0], [0, 0, 20]]` | `0/10` (0.00%) |
| Chave 1 (`seed=101`) | `B` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `10/10` (100.00%) |
| Chave 1 (`seed=101`) | `LEVENSHTEIN_NORM` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `10/10` (100.00%) |
| Chave 1 (`seed=101`) | `JARO_WINKLER` | 96.00% | 0.9467 `[0.8518; 1.0000]` | `0.9756 / 0.8889 / 0.9756` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [1, 8, 1], [0, 0, 20]]` | `8/10` (80.00%) |
| Chave 1 (`seed=101`) | `TOKEN_HYBRID` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `10/10` (100.00%) |
| Chave 2 (`seed=202`) | `A` | 80.00% | 0.8222 `[0.8222; 0.8222]` | `0.6667 / 1.0000 / 0.8000` | `80.00% / 1.0000 / 0.7500` | `10` | `[[10, 0, 10], [0, 10, 0], [0, 0, 20]]` | `0/10` (0.00%) |
| Chave 2 (`seed=202`) | `B` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `10/10` (100.00%) |
| Chave 2 (`seed=202`) | `LEVENSHTEIN_NORM` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `10/10` (100.00%) |
| Chave 2 (`seed=202`) | `JARO_WINKLER` | 96.00% | 0.9471 `[0.8519; 1.0000]` | `1.0000 / 0.8889 / 0.9524` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 8, 2], [0, 0, 20]]` | `8/10` (80.00%) |
| Chave 2 (`seed=202`) | `TOKEN_HYBRID` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `10/10` (100.00%) |
| Chave 3 (`seed=303`) | `A` | 80.00% | 0.8222 `[0.8222; 0.8222]` | `0.6667 / 1.0000 / 0.8000` | `80.00% / 1.0000 / 0.7500` | `10` | `[[10, 0, 10], [0, 10, 0], [0, 0, 20]]` | `0/10` (0.00%) |
| Chave 3 (`seed=303`) | `B` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `10/10` (100.00%) |
| Chave 3 (`seed=303`) | `LEVENSHTEIN_NORM` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `10/10` (100.00%) |
| Chave 3 (`seed=303`) | `JARO_WINKLER` | 96.00% | 0.9471 `[0.8519; 1.0000]` | `1.0000 / 0.8889 / 0.9524` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 8, 2], [0, 0, 20]]` | `8/10` (80.00%) |
| Chave 3 (`seed=303`) | `TOKEN_HYBRID` | 100.00% | 1.0000 `[1.0000; 1.0000]` | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `0` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `10/10` (100.00%) |

### 5.3 Teste de McNemar Exato Binomial Pareado por Família + Ajuste de Holm-Bonferroni (`vs LEVENSHTEIN_NORM`)

#### Partição Final (`20` famílias/bateria)

| Bateria | Comparação | Concord. Correta | Discordantes `b` (Ref+/Comp-) | Discordantes `c` (Ref-/Comp+) | `p_value` | `p_holm` | Signif. (`α=0,05`) |
| --- | --- | :---: | :---: | :---: | :---: | :---: | :---: |
| Base v2 (`seed=42`) | `LEVENSHTEIN_NORM:A` | `0/20` | `20` | `0` | `1.90735e-06` | `7.62939e-06` | **Sim (`p < 0,05`)** |
| Base v2 (`seed=42`) | `LEVENSHTEIN_NORM:B` | `20/20` | `0` | `0` | `1` | `1` | Não |
| Base v2 (`seed=42`) | `LEVENSHTEIN_NORM:JARO_WINKLER` | `18/20` | `2` | `0` | `0.5` | `1` | Não |
| Base v2 (`seed=42`) | `LEVENSHTEIN_NORM:TOKEN_HYBRID` | `20/20` | `0` | `0` | `1` | `1` | Não |
| Chave 1 (`seed=101`) | `LEVENSHTEIN_NORM:A` | `0/20` | `19` | `0` | `3.8147e-06` | `1.52588e-05` | **Sim (`p < 0,05`)** |
| Chave 1 (`seed=101`) | `LEVENSHTEIN_NORM:B` | `19/20` | `0` | `1` | `1` | `1` | Não |
| Chave 1 (`seed=101`) | `LEVENSHTEIN_NORM:JARO_WINKLER` | `17/20` | `2` | `0` | `0.5` | `1` | Não |
| Chave 1 (`seed=101`) | `LEVENSHTEIN_NORM:TOKEN_HYBRID` | `19/20` | `0` | `1` | `1` | `1` | Não |
| Chave 2 (`seed=202`) | `LEVENSHTEIN_NORM:A` | `0/20` | `18` | `0` | `7.62939e-06` | `3.05176e-05` | **Sim (`p < 0,05`)** |
| Chave 2 (`seed=202`) | `LEVENSHTEIN_NORM:B` | `18/20` | `0` | `2` | `0.5` | `1` | Não |
| Chave 2 (`seed=202`) | `LEVENSHTEIN_NORM:JARO_WINKLER` | `15/20` | `3` | `0` | `0.25` | `0.75` | Não |
| Chave 2 (`seed=202`) | `LEVENSHTEIN_NORM:TOKEN_HYBRID` | `18/20` | `0` | `2` | `0.5` | `1` | Não |
| Chave 3 (`seed=303`) | `LEVENSHTEIN_NORM:A` | `0/20` | `20` | `0` | `1.90735e-06` | `7.62939e-06` | **Sim (`p < 0,05`)** |
| Chave 3 (`seed=303`) | `LEVENSHTEIN_NORM:B` | `20/20` | `0` | `0` | `1` | `1` | Não |
| Chave 3 (`seed=303`) | `LEVENSHTEIN_NORM:JARO_WINKLER` | `12/20` | `8` | `0` | `0.0078125` | `0.0234375` | **Sim (`p < 0,05`)** |
| Chave 3 (`seed=303`) | `LEVENSHTEIN_NORM:TOKEN_HYBRID` | `20/20` | `0` | `0` | `1` | `1` | Não |

#### Partição Piloto (`10` famílias/bateria)

| Bateria | Comparação | Concord. Correta | Discordantes `b` (Ref+/Comp-) | Discordantes `c` (Ref-/Comp+) | `p_value` | `p_holm` | Signif. (`α=0,05`) |
| --- | --- | :---: | :---: | :---: | :---: | :---: | :---: |
| Base v2 (`seed=42`) | `LEVENSHTEIN_NORM:A` | `0/10` | `10` | `0` | `0.00195312` | `0.0078125` | **Sim (`p < 0,05`)** |
| Base v2 (`seed=42`) | `LEVENSHTEIN_NORM:B` | `10/10` | `0` | `0` | `1` | `1` | Não |
| Base v2 (`seed=42`) | `LEVENSHTEIN_NORM:JARO_WINKLER` | `8/10` | `2` | `0` | `0.5` | `1` | Não |
| Base v2 (`seed=42`) | `LEVENSHTEIN_NORM:TOKEN_HYBRID` | `10/10` | `0` | `0` | `1` | `1` | Não |
| Chave 1 (`seed=101`) | `LEVENSHTEIN_NORM:A` | `0/10` | `10` | `0` | `0.00195312` | `0.0078125` | **Sim (`p < 0,05`)** |
| Chave 1 (`seed=101`) | `LEVENSHTEIN_NORM:B` | `10/10` | `0` | `0` | `1` | `1` | Não |
| Chave 1 (`seed=101`) | `LEVENSHTEIN_NORM:JARO_WINKLER` | `8/10` | `2` | `0` | `0.5` | `1` | Não |
| Chave 1 (`seed=101`) | `LEVENSHTEIN_NORM:TOKEN_HYBRID` | `10/10` | `0` | `0` | `1` | `1` | Não |
| Chave 2 (`seed=202`) | `LEVENSHTEIN_NORM:A` | `0/10` | `10` | `0` | `0.00195312` | `0.0078125` | **Sim (`p < 0,05`)** |
| Chave 2 (`seed=202`) | `LEVENSHTEIN_NORM:B` | `10/10` | `0` | `0` | `1` | `1` | Não |
| Chave 2 (`seed=202`) | `LEVENSHTEIN_NORM:JARO_WINKLER` | `8/10` | `2` | `0` | `0.5` | `1` | Não |
| Chave 2 (`seed=202`) | `LEVENSHTEIN_NORM:TOKEN_HYBRID` | `10/10` | `0` | `0` | `1` | `1` | Não |
| Chave 3 (`seed=303`) | `LEVENSHTEIN_NORM:A` | `0/10` | `10` | `0` | `0.00195312` | `0.0078125` | **Sim (`p < 0,05`)** |
| Chave 3 (`seed=303`) | `LEVENSHTEIN_NORM:B` | `10/10` | `0` | `0` | `1` | `1` | Não |
| Chave 3 (`seed=303`) | `LEVENSHTEIN_NORM:JARO_WINKLER` | `8/10` | `2` | `0` | `0.5` | `1` | Não |
| Chave 3 (`seed=303`) | `LEVENSHTEIN_NORM:TOKEN_HYBRID` | `10/10` | `0` | `0` | `1` | `1` | Não |

### 5.4 Desagregação do Experimento 2 por Categoria Curricular (`Final`, `20` casos/categoria)

| Bateria | Categoria | `A` (`EXACT`) Macro-F1 | `B` (`NORM`) Macro-F1 | `LEVENSHTEIN_NORM` Macro-F1 | `JARO_WINKLER` Macro-F1 | `TOKEN_HYBRID` Macro-F1 |
| --- | --- | :---: | :---: | :---: | :---: | :---: |
| Base v2 (`seed=42`) | `FORMACAO_ACADEMICA` | 0.8222 | 1.0000 | **1.0000** | 1.0000 | 1.0000 |
| Base v2 (`seed=42`) | `FORMACAO_COMPLEMENTAR` | 0.8222 | 1.0000 | **1.0000** | 1.0000 | 1.0000 |
| Base v2 (`seed=42`) | `PARTICIPACAO_EVENTO` | 0.8222 | 1.0000 | **1.0000** | 1.0000 | 1.0000 |
| Base v2 (`seed=42`) | `APRESENTACAO_TRABALHO` | 0.8222 | 1.0000 | **1.0000** | 0.9328 | 1.0000 |
| Base v2 (`seed=42`) | `ORGANIZACAO_EVENTO` | 0.8222 | 1.0000 | **1.0000** | 0.9328 | 1.0000 |
| Chave 1 (`seed=101`) | `FORMACAO_ACADEMICA` | 0.8222 | 1.0000 | **1.0000** | 1.0000 | 1.0000 |
| Chave 1 (`seed=101`) | `FORMACAO_COMPLEMENTAR` | 0.8222 | 1.0000 | **1.0000** | 1.0000 | 1.0000 |
| Chave 1 (`seed=101`) | `PARTICIPACAO_EVENTO` | 0.8222 | 1.0000 | **1.0000** | 1.0000 | 1.0000 |
| Chave 1 (`seed=101`) | `APRESENTACAO_TRABALHO` | 0.8222 | 1.0000 | **1.0000** | 0.9328 | 1.0000 |
| Chave 1 (`seed=101`) | `ORGANIZACAO_EVENTO` | 0.8222 | 1.0000 | **0.9328** | 0.8497 | 1.0000 |
| Chave 2 (`seed=202`) | `FORMACAO_ACADEMICA` | 0.8222 | 1.0000 | **1.0000** | 1.0000 | 1.0000 |
| Chave 2 (`seed=202`) | `FORMACAO_COMPLEMENTAR` | 0.8222 | 1.0000 | **1.0000** | 1.0000 | 1.0000 |
| Chave 2 (`seed=202`) | `PARTICIPACAO_EVENTO` | 0.8222 | 1.0000 | **1.0000** | 1.0000 | 1.0000 |
| Chave 2 (`seed=202`) | `APRESENTACAO_TRABALHO` | 0.8222 | 1.0000 | **0.9328** | 0.8497 | 1.0000 |
| Chave 2 (`seed=202`) | `ORGANIZACAO_EVENTO` | 0.8222 | 1.0000 | **0.9328** | 0.7434 | 1.0000 |
| Chave 3 (`seed=303`) | `FORMACAO_ACADEMICA` | 0.8222 | 1.0000 | **1.0000** | 1.0000 | 1.0000 |
| Chave 3 (`seed=303`) | `FORMACAO_COMPLEMENTAR` | 0.8222 | 1.0000 | **1.0000** | 1.0000 | 1.0000 |
| Chave 3 (`seed=303`) | `PARTICIPACAO_EVENTO` | 0.8222 | 1.0000 | **1.0000** | 1.0000 | 1.0000 |
| Chave 3 (`seed=303`) | `APRESENTACAO_TRABALHO` | 0.8222 | 1.0000 | **1.0000** | 0.6000 | 1.0000 |
| Chave 3 (`seed=303`) | `ORGANIZACAO_EVENTO` | 0.8222 | 1.0000 | **1.0000** | 0.6000 | 1.0000 |

## 6. Experimento 3 — Pipeline Integrado Fim a Fim (`M1 → M3 Gemini → M2`, `calls = 0`, `reused = True`)

### 6.1 Partição Final (`N = 100`/bateria)

| Bateria | Execução | Macro-F1 `[IC 95% Bootstrap]` | Acurácia | F1 `VAL / DIV / INC` | Associação (`Acc / Prec / Rec`) | Matriz 3×3 (`VAL/DIV/INC`) | Causas de Erro | Oráculo Macro-F1 |
| --- | --- | :---: | :---: | :---: | :---: | --- | --- | :---: |
| Base v2 (`seed=42`) | `Rep 1` | 1.0000 `[1.0000; 1.0000]` | 100.00% | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `[[40, 0, 0], [0, 20, 0], [0, 0, 40]]` | `{}` | 1.0000 |
| Base v2 (`seed=42`) | `Rep 2` | 1.0000 `[1.0000; 1.0000]` | 100.00% | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `[[40, 0, 0], [0, 20, 0], [0, 0, 40]]` | `{}` | 1.0000 |
| Base v2 (`seed=42`) | `Rep 3` | 1.0000 `[1.0000; 1.0000]` | 100.00% | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `[[40, 0, 0], [0, 20, 0], [0, 0, 40]]` | `{}` | 1.0000 |
| Base v2 (`seed=42`) | **`Média (mean_3)`** | **1.0000 `[1.0000; 1.0000]`** | **100.00%** | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | — | `calls=0, reused=True` | **1.0000 `[1.0000; 1.0000]`** |
| Chave 1 (`seed=101`) | `Rep 1` | 0.9873 `[0.9609; 1.0000]` | 99.00% | `1.0000 / 0.9744 / 0.9877` | `100.00% / 1.0000 / 1.0000` | `[[40, 0, 0], [0, 19, 1], [0, 0, 40]]` | `{'rule': 1}` | 0.9873 |
| Chave 1 (`seed=101`) | `Rep 2` | 0.9791 `[0.9367; 1.0000]` | 98.00% | `0.9873 / 0.9744 / 0.9756` | `99.00% / 1.0000 / 0.9875` | `[[39, 0, 1], [0, 19, 1], [0, 0, 40]]` | `{'association': 1, 'rule': 1}` | 0.9873 |
| Chave 1 (`seed=101`) | `Rep 3` | 0.9791 `[0.9367; 1.0000]` | 98.00% | `0.9873 / 0.9744 / 0.9756` | `99.00% / 1.0000 / 0.9875` | `[[39, 0, 1], [0, 19, 1], [0, 0, 40]]` | `{'association': 1, 'rule': 1}` | 0.9873 |
| Chave 1 (`seed=101`) | **`Média (mean_3)`** | **0.9818 `[0.9448; 1.0000]`** | **98.33%** | `0.9916 / 0.9744 / 0.9796` | `99.33% / 1.0000 / 0.9917` | — | `calls=0, reused=True` | **0.9873 `[0.9609; 1.0000]`** |
| Chave 2 (`seed=202`) | `Rep 1` | 0.9662 `[0.9249; 1.0000]` | 97.00% | `0.9873 / 0.9474 / 0.9639` | `99.00% / 1.0000 / 0.9875` | `[[39, 0, 1], [0, 18, 2], [0, 0, 40]]` | `{'association': 1, 'rule': 2}` | 0.9743 |
| Chave 2 (`seed=202`) | `Rep 2` | 0.9609 `[0.9179; 1.0000]` | 97.00% | `1.0000 / 0.9189 / 0.9639` | `99.00% / 1.0000 / 0.9875` | `[[40, 0, 0], [0, 17, 3], [0, 0, 40]]` | `{'association': 1, 'rule': 2}` | 0.9743 |
| Chave 2 (`seed=202`) | `Rep 3` | 0.9609 `[0.9179; 1.0000]` | 97.00% | `1.0000 / 0.9189 / 0.9639` | `99.00% / 1.0000 / 0.9875` | `[[40, 0, 0], [0, 17, 3], [0, 0, 40]]` | `{'association': 1, 'rule': 2}` | 0.9743 |
| Chave 2 (`seed=202`) | **`Média (mean_3)`** | **0.9627 `[0.9202; 1.0000]`** | **97.00%** | `0.9958 / 0.9284 / 0.9639` | `99.00% / 1.0000 / 0.9875` | — | `calls=0, reused=True` | **0.9743 `[0.9328; 1.0000]`** |
| Chave 3 (`seed=303`) | `Rep 1` | 0.9917 `[0.9750; 1.0000]` | 99.00% | `0.9873 / 1.0000 / 0.9877` | `97.00% / 1.0000 / 0.9625` | `[[39, 0, 1], [0, 20, 0], [0, 0, 40]]` | `{'association': 1}` | 1.0000 |
| Chave 3 (`seed=303`) | `Rep 2` | 0.9917 `[0.9750; 1.0000]` | 99.00% | `0.9873 / 1.0000 / 0.9877` | `98.00% / 1.0000 / 0.9750` | `[[39, 0, 1], [0, 20, 0], [0, 0, 40]]` | `{'association': 1}` | 1.0000 |
| Chave 3 (`seed=303`) | `Rep 3` | 0.9917 `[0.9750; 1.0000]` | 99.00% | `0.9873 / 1.0000 / 0.9877` | `98.00% / 1.0000 / 0.9750` | `[[39, 0, 1], [0, 20, 0], [0, 0, 40]]` | `{'association': 1}` | 1.0000 |
| Chave 3 (`seed=303`) | **`Média (mean_3)`** | **0.9917 `[0.9750; 1.0000]`** | **99.00%** | `0.9873 / 1.0000 / 0.9877` | `97.67% / 1.0000 / 0.9708` | — | `calls=0, reused=True` | **1.0000 `[1.0000; 1.0000]`** |

### 6.2 Partição Piloto (`N = 50`/bateria)

| Bateria | Execução | Macro-F1 `[IC 95% Bootstrap]` | Acurácia | F1 `VAL / DIV / INC` | Associação (`Acc / Prec / Rec`) | Matriz 3×3 (`VAL/DIV/INC`) | Causas de Erro | Oráculo Macro-F1 |
| --- | --- | :---: | :---: | :---: | :---: | --- | --- | :---: |
| Base v2 (`seed=42`) | `Rep 1` | 0.9833 `[0.9497; 1.0000]` | 98.00% | `0.9744 / 1.0000 / 0.9756` | `98.00% / 1.0000 / 0.9750` | `[[19, 0, 1], [0, 10, 0], [0, 0, 20]]` | `{'association': 1}` | 1.0000 |
| Base v2 (`seed=42`) | `Rep 2` | 0.9833 `[0.9497; 1.0000]` | 98.00% | `0.9744 / 1.0000 / 0.9756` | `98.00% / 1.0000 / 0.9750` | `[[19, 0, 1], [0, 10, 0], [0, 0, 20]]` | `{'association': 1}` | 1.0000 |
| Base v2 (`seed=42`) | `Rep 3` | 1.0000 `[1.0000; 1.0000]` | 100.00% | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `{}` | 1.0000 |
| Base v2 (`seed=42`) | **`Média (mean_3)`** | **0.9889 `[0.9665; 1.0000]`** | **98.67%** | `0.9829 / 1.0000 / 0.9837` | `98.67% / 1.0000 / 0.9833` | — | `calls=0, reused=True` | **1.0000 `[1.0000; 1.0000]`** |
| Chave 1 (`seed=101`) | `Rep 1` | 1.0000 `[1.0000; 1.0000]` | 100.00% | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `{}` | 1.0000 |
| Chave 1 (`seed=101`) | `Rep 2` | 1.0000 `[1.0000; 1.0000]` | 100.00% | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `{}` | 1.0000 |
| Chave 1 (`seed=101`) | `Rep 3` | 1.0000 `[1.0000; 1.0000]` | 100.00% | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `{}` | 1.0000 |
| Chave 1 (`seed=101`) | **`Média (mean_3)`** | **1.0000 `[1.0000; 1.0000]`** | **100.00%** | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | — | `calls=0, reused=True` | **1.0000 `[1.0000; 1.0000]`** |
| Chave 2 (`seed=202`) | `Rep 1` | 1.0000 `[1.0000; 1.0000]` | 100.00% | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `{}` | 1.0000 |
| Chave 2 (`seed=202`) | `Rep 2` | 0.9833 `[0.9497; 1.0000]` | 98.00% | `0.9744 / 1.0000 / 0.9756` | `98.00% / 1.0000 / 0.9750` | `[[19, 0, 1], [0, 10, 0], [0, 0, 20]]` | `{'association': 1}` | 1.0000 |
| Chave 2 (`seed=202`) | `Rep 3` | 1.0000 `[1.0000; 1.0000]` | 100.00% | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `{}` | 1.0000 |
| Chave 2 (`seed=202`) | **`Média (mean_3)`** | **0.9944 `[0.9832; 1.0000]`** | **99.33%** | `0.9915 / 1.0000 / 0.9919` | `99.33% / 1.0000 / 0.9917` | — | `calls=0, reused=True` | **1.0000 `[1.0000; 1.0000]`** |
| Chave 3 (`seed=303`) | `Rep 1` | 1.0000 `[1.0000; 1.0000]` | 100.00% | `1.0000 / 1.0000 / 1.0000` | `100.00% / 1.0000 / 1.0000` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `{}` | 1.0000 |
| Chave 3 (`seed=303`) | `Rep 2` | 1.0000 `[1.0000; 1.0000]` | 100.00% | `1.0000 / 1.0000 / 1.0000` | `98.00% / 1.0000 / 0.9750` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `{}` | 1.0000 |
| Chave 3 (`seed=303`) | `Rep 3` | 1.0000 `[1.0000; 1.0000]` | 100.00% | `1.0000 / 1.0000 / 1.0000` | `98.00% / 1.0000 / 0.9750` | `[[20, 0, 0], [0, 10, 0], [0, 0, 20]]` | `{}` | 1.0000 |
| Chave 3 (`seed=303`) | **`Média (mean_3)`** | **1.0000 `[1.0000; 1.0000]`** | **100.00%** | `1.0000 / 1.0000 / 1.0000` | `98.67% / 1.0000 / 0.9833` | — | `calls=0, reused=True` | **1.0000 `[1.0000; 1.0000]`** |

### 6.3 Desagregação do Experimento 3 por Categoria Curricular (`by_category`)

#### Final (`20` casos/categoria)

| Bateria | Categoria | `n` | Rep 1 Macro-F1 | Rep 2 Macro-F1 | Rep 3 Macro-F1 | **Média 3 Reps** | Oráculo Macro-F1 |
| --- | --- | :---: | :---: | :---: | :---: | :---: | :---: |
| Base v2 (`seed=42`) | `FORMACAO_ACADEMICA` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Base v2 (`seed=42`) | `FORMACAO_COMPLEMENTAR` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Base v2 (`seed=42`) | `PARTICIPACAO_EVENTO` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Base v2 (`seed=42`) | `APRESENTACAO_TRABALHO` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Base v2 (`seed=42`) | `ORGANIZACAO_EVENTO` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 1 (`seed=101`) | `FORMACAO_ACADEMICA` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 1 (`seed=101`) | `FORMACAO_COMPLEMENTAR` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 1 (`seed=101`) | `PARTICIPACAO_EVENTO` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 1 (`seed=101`) | `APRESENTACAO_TRABALHO` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 1 (`seed=101`) | `ORGANIZACAO_EVENTO` | `20` | 0.9328 | 0.8931 | 0.8931 | **0.9063** | 0.9328 |
| Chave 2 (`seed=202`) | `FORMACAO_ACADEMICA` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 2 (`seed=202`) | `FORMACAO_COMPLEMENTAR` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 2 (`seed=202`) | `PARTICIPACAO_EVENTO` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 2 (`seed=202`) | `APRESENTACAO_TRABALHO` | `20` | 0.9328 | 0.9328 | 0.9328 | **0.9328** | 0.9328 |
| Chave 2 (`seed=202`) | `ORGANIZACAO_EVENTO` | `20` | 0.8931 | 0.8519 | 0.8519 | **0.8656** | 0.9328 |
| Chave 3 (`seed=303`) | `FORMACAO_ACADEMICA` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 3 (`seed=303`) | `FORMACAO_COMPLEMENTAR` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 3 (`seed=303`) | `PARTICIPACAO_EVENTO` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 3 (`seed=303`) | `APRESENTACAO_TRABALHO` | `20` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 3 (`seed=303`) | `ORGANIZACAO_EVENTO` | `20` | 0.9582 | 0.9582 | 0.9582 | **0.9582** | 1.0000 |

#### Piloto (`10` casos/categoria)

| Bateria | Categoria | `n` | Rep 1 Macro-F1 | Rep 2 Macro-F1 | Rep 3 Macro-F1 | **Média 3 Reps** | Oráculo Macro-F1 |
| --- | --- | :---: | :---: | :---: | :---: | :---: | :---: |
| Base v2 (`seed=42`) | `FORMACAO_ACADEMICA` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Base v2 (`seed=42`) | `FORMACAO_COMPLEMENTAR` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Base v2 (`seed=42`) | `PARTICIPACAO_EVENTO` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Base v2 (`seed=42`) | `APRESENTACAO_TRABALHO` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Base v2 (`seed=42`) | `ORGANIZACAO_EVENTO` | `10` | 0.9153 | 0.9153 | 1.0000 | **0.9436** | 1.0000 |
| Chave 1 (`seed=101`) | `FORMACAO_ACADEMICA` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 1 (`seed=101`) | `FORMACAO_COMPLEMENTAR` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 1 (`seed=101`) | `PARTICIPACAO_EVENTO` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 1 (`seed=101`) | `APRESENTACAO_TRABALHO` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 1 (`seed=101`) | `ORGANIZACAO_EVENTO` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 2 (`seed=202`) | `FORMACAO_ACADEMICA` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 2 (`seed=202`) | `FORMACAO_COMPLEMENTAR` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 2 (`seed=202`) | `PARTICIPACAO_EVENTO` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 2 (`seed=202`) | `APRESENTACAO_TRABALHO` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 2 (`seed=202`) | `ORGANIZACAO_EVENTO` | `10` | 1.0000 | 0.9153 | 1.0000 | **0.9718** | 1.0000 |
| Chave 3 (`seed=303`) | `FORMACAO_ACADEMICA` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 3 (`seed=303`) | `FORMACAO_COMPLEMENTAR` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 3 (`seed=303`) | `PARTICIPACAO_EVENTO` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 3 (`seed=303`) | `APRESENTACAO_TRABALHO` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |
| Chave 3 (`seed=303`) | `ORGANIZACAO_EVENTO` | `10` | 1.0000 | 1.0000 | 1.0000 | **1.0000** | 1.0000 |

## 7. Notas Técnicas e Metodológicas Consolidando o Estado Atual

1. **Gabarito Determinístico por Construção (`case.gold` e `case.expected`):** todas as métricas das 4 baterias acima foram calculadas deterministicamente sobre os casos gerados por `synthetic.py`, selados por SHA-256 nos manifestos `freeze.json` antes das execuções experimentais.
2. **Estabilidade Arquitetural (LLM desacoplado):** mesmo quando a extração literal no Exp 1 oscilou entre **82,50% e 88,75%** (por variações cosméticas de espaços ou formatação), a normalização canônica `N(s)` e a equivalência explícita de siglas no Módulo M2 elevaram o desempenho fim a fim no **Exp 3** para **Macro-F1 entre `0,9627` e `1,0000`** no conjunto final (`97,00%` a `100,00%` de acurácia global), igualando ou aproximando em <0,012 o Oráculo determinístico.
3. **Superioridade do Proposto e de `LEVENSHTEIN_NORM` sobre `BASELINE_EXACT` (`A`) e `JARO_WINKLER`:** em todas as 4 baterias finais (`400` cenários), `LEVENSHTEIN_NORM` superou `BASELINE_EXACT` (`0,8222`) com `p_holm` significativo em 100% dos testes (`7,63e-06` em todas as 4 baterias). Adicionalmente, `JARO_WINKLER` sofreu degradação em mutações de instituição por atribuir peso excessivo a prefixos comuns (`0,8864` a `0,9743` vs. `0,9743` a `1,0000` de `LEVENSHTEIN_NORM`).
4. **Resiliência HTTP em Produção (`httpx2.ReadTimeout`):** os testes reais com timeout de `30 s` expuseram que `google-genai` usa o cliente interno `httpx2`, corrigido localmente em `src/comprova_lattes/extractor/gemini.py` e coberto por novos testes em `tests/test_extractor.py` (`72 passed` nos testes de extrator/artefatos + `ruff check .` aprovado após a edição; resselo refletido na Bateria Base v2).
5. **Compatibilidade de OCR entre Sistemas Operacionais (`tests/test_ocr_quality.py`):** 2 asserções de texto literal de `case-001` no piloto permanecem vinculadas ao reconhecimento de string do Tesseract `5.5.0` em container Linux Docker (no Tesseract `5.4.0.20240606` nativo do Windows, o mesmo PDF é lido como `Ano deinício: 2031` sem o erro `20381`), conforme documentado em `.specs/docs/human-annotation.md` e `.specs/project/STATE.md`.

