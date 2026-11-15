# Plano M4/M5: Bancada Sintética, Baselines e Experimentos (`comprova_lattes.experiments`)

## 1. Arquitetura e Escopo do Pacote `comprova_lattes.experiments`

| Módulo | Responsabilidade | Restrições / Tecnologias |
| --- | --- | --- |
| `models.py` | Contratos Pydantic v2 (`SyntheticCase`, `BenchmarkManifest`, `AnnotationRecord`, `KappaReport`, `FieldExtractionMetrics`, `Experiment1Report`, `AssociationMetrics`, `ClassificationMetrics`, `BootstrapCI`, `McNemarResult`, `Experiment2Report`, `Experiment3Report`, `FreezeManifest`) | `extra="forbid"`, `frozen=True`, `Decimal` para horas (`AD-009`) |
| `generator.py` & `degradation.py` | Gerador determinístico 100% sintético com semente fixa nas **5 categorias** (`AD-012`), gerando XMLs Lattes válidos, templates HTML e bytes válidos `application/pdf` e `image/png` (via stdlib `zlib`/`struct`, sem novas dependências e **zero LLM** `#46` / **zero dado real** `#49`), com degradação visual (rotação, ruído, *blur*, carimbo) e partição estrita por família (`pilot` N=30 vs. `final` N=90) com IDs neutros | Zero vazamento de rótulos em nomes de arquivo ou metadados |
| `ocr_baseline.py` | Baseline clássico OCR + RegEx (`#29`) com protocolo `OcrBackend` injetável (e adaptador opcional CLI `tesseract`), preservando prefixos de papel (`Ouvinte`, `Palestrante`, `Apresentador`, `Organizador`), horas em `Decimal`, anos, instituição, sigla, evento e título | Retorna `ExtractedDocumentRecord` compatível com `M2` |
| `statistics.py` | **Kappa de Cohen** pré-consenso (`#47`, `OPEN-04`, `sklearn.metrics.cohen_kappa_score`/fórmula pura + concordância bruta + matriz de discordância); **Bootstrap por cluster (`family_id`)** com semente fixa e IC 95% (`#45`, `AD-008`, sem meta fixa `0,85`); **McNemar pareado** (`scipy.stats.binomtest` exato + $\chi^2$ assintótico com correção de continuidade + correção de Holm-Bonferroni `#67`) | Apenas pacotes já presentes na `.venv` (`numpy`, `scipy`, `scikit-learn`, `pandas`) |
| `calibration.py` | Busca em grade (*grid search*) dos limiares exclusivamente no `pilot` + geração de `FreezeManifest` com hashes SHA-256 (prompt, schema, tabela de siglas, regex, limiares e semente do gerador) antes do `final` | Impede *data leakage* entre calibração e avaliação final |
| `runner.py` & `cli.py` | **Exp. 1:** avaliação por campo (`correto`, `incorreto`, `omitido`, `espurio`, `ausente_correto`), horas em `Decimal`, taxas de falha (`API_ERROR`, `INVALID_JSON`, `UNREADABLE`) e estabilidade das **3 repetições** (`#32, #34, #53`, contando 3 repetições idênticas uma vez e usando a 1ª execução pré-designada em caso de divergência); **Exp. 2:** `M2` sobre gabarito perfeito comparando `BASELINE_EXACT`, `BASELINE_NORMALIZED` (`#16`) e `PROPOSED` em `LEVENSHTEIN_NORM`, `JARO_WINKLER` e `TOKEN_HYBRID` (`#37`); **Exp. 3:** pipeline integrado `M1 → M3 → M2` reaproveitando extrações do Exp. 1, métricas automáticas **antes** da revisão humana (`AD-007`, `AD-013`), matriz $3 \times 3$, decomposição de `Inconclusivo` com/sem `SEM_COMPROVANTE` (`AD-005`), associação separada (`#65`), `DOCUMENTO_NAO_ASSOCIADO` fora da $3 \times 3$ (`AD-006`) e taxonomia de erro propagado | Execução offline reproduzível por CLI (`python -m comprova_lattes.experiments.cli`) |

---

## 2. Tarefas e Atribuição de Agentes

| ID | Tarefa | Agente / Executor | Verificação |
| --- | --- | --- | --- |
| **T1** | Implementar contratos `models.py` e gerador determinístico `generator.py` + `degradation.py` | `backend-specialist` (Codex) | Determinismo por semente, 5 categorias e 0 famílias compartilhadas entre `pilot` e `final` |
| **T2** | Implementar `ocr_baseline.py` (RegEx + `OcrBackend` injetável) | `backend-specialist` (Codex) | Preservação de papéis e `Decimal`, zero descarte indevido |
| **T3** | Implementar `statistics.py` (Kappa, Bootstrap por família, McNemar exato + Holm) e `calibration.py` (`FreezeManifest`) | `backend-specialist` (Codex) | Oráculos numéricos verificados em `pytest` |
| **T4** | Implementar `runner.py` (Exp. 1, 2 e 3) e `cli.py` | `backend-specialist` (Codex) | Execução ponta a ponta com mocks offline e exportação CSV/JSON |
| **T5** | Criar suíte `tests/test_experiments*.py` e atualizar `STATE.md`, `ROADMAP.md` e `HANDOFF.md` | `test-engineer` (Codex) | `pytest -q` + `ruff check .` 100% aprovados |

---

## 3. Comando de Delegação ao Codex (`simple-orchestrator`)

```powershell
& "$env:LOCALAPPDATA\Programs\simple-orchestrator\simple-orchestrator.exe" delegate `
  --run-key "tcc-e4-m4-experiments-20261113" `
  --task-id "e4-experiments" `
  --attempt-id "att-01" `
  --maestra-provider "antigravity" `
  --maestra-session "a1db91ea-25b8-4e05-bafb-dcaa92656f15" `
  --worker-provider "codex" `
  --worker-chat-title "E4 - Implementacao M4 e M5 Experiments" `
  --workspace "c:\Users\elivanilso.junior\Music\TCc2\comprova-lattes" `
  --target "comprova-lattes-api/src/comprova_lattes/experiments/, comprova-lattes-api/tests/, .specs/project/STATE.md, .specs/project/ROADMAP.md, .specs/HANDOFF.md" `
  --change "Implementar o pacote comprova_lattes.experiments (M4 e M5) completo: gerador sintetico deterministico (5 categorias, XML + PDF/PNG validos via stdlib + degradacao visual, particao por familia piloto/final sem vazamento), baseline OCR+RegEx injetavel, calibracao e congelamento por SHA-256, estatistica (Kappa de Cohen, IC bootstrap por familia, McNemar pareado exato com Holm), runner e CLI dos Experimentos 1, 2 e 3, e testes automatizados." `
  --constraints "Escrita restrita a experiments/, tests/ e .specs/{project/STATE.md,project/ROADMAP.md,HANDOFF.md}; NAO alterar parser/, matcher/ ou extractor/; NAO instalar novos pacotes; NAO fazer chamadas reais pagas ao Gemini; NAO usar meta arbitraria 0.85 (AD-008); NAO executar git commit/push." `
  --acceptance "Pacote experiments/ implementado e coberto por testes unitarios e integrados: (1) geracao deterministica com semente fixa e isolamento estrito de familias entre piloto e final; (2) PDF e PNG sinteticos validos + degradacao; (3) baseline OCR+RegEx injetavel; (4) Exp 1 (por campo, falhas e estabilidade de 3 repeticoes sem triplicar N), Exp 2 (Baselines A/B + Levenshtein/Jaro-Winkler/Tokens), Exp 3 (matriz 3x3 antes da revisao humana, associacao separada, DOCUMENTO_NAO_ASSOCIADO fora da 3x3, propagacao de erro); (5) Kappa, bootstrap por familia e McNemar exato usando apenas dependencias ja instaladas (scipy/sklearn/numpy); (6) calibracao no piloto e freeze-manifest com hashes SHA-256; (7) pytest e ruff 100% aprovados." `
  --prompt "Leia .specs/features/experimental-protocol/proposal.md, .specs/codebase/PROFESSOR-REQUIREMENTS.md, .specs/project/STATE.md e inspecione schemas/lattes.py, matcher/{models,engine,text}.py e extractor/{models,gemini}.py. Implemente comprova-lattes-api/src/comprova_lattes/experiments/ de forma enxuta, modular e 100% deterministica usando apenas a stdlib e pacotes ja instalados na .venv (numpy, scipy, scikit-learn, pandas, pydantic). Adicione testes abrangentes em tests/test_experiments*.py, atualize STATE/ROADMAP/HANDOFF e execute pytest e ruff ao final." `
  --auto-ack
```

---

## 4. Checklist de Verificação (Phase X)
- [ ] Plano `m4-experiments-plan.md` criado na raiz do projeto.
- [ ] Delegação `e4-experiments` executada e concluída pelo Codex com `ok: true`.
- [ ] Verificação local independente aprovada (`pytest -q` e `ruff check .` sem erros).
- [ ] `STATE.md`, `ROADMAP.md` e `HANDOFF.md` atualizados refletindo o estado real de M4/M5.
