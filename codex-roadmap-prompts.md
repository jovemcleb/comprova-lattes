# Plano de Continuidade e Prompts de Orquestração (`Codex` via `simple-orchestrator`)

## 1. Diagnóstico da Arquitetura Atual (`comprova-lattes`)

| Camada / Marco | Localização | Estado Verificado | Dependências / Bloqueios |
| --- | --- | --- | --- |
| **M0 — Setup Base** | `compose.yaml`, `pyproject.toml`, `.specs/` | **Concluído** | — |
| **M1 — Parser XML** | `comprova-lattes-api/src/comprova_lattes/{schemas,parser}/` | **Implementado e verificado** (130 testes `pytest`, `ruff` OK; 5 categorias `AD-012`; `defusedxml` + XSD offline `AD-011`) | Pendência externa: confirmar requisito DTD com orientador (#25) |
| **M2 — Matcher** | `comprova-lattes-api/src/comprova_lattes/matcher/__init__.py` | **Vazio (planejado)** | Decisões abertas: essencialidade/agregação por categoria, título omitido, coexistência de papéis (`D-M2-*`) |
| **M3 — Extractor** | `comprova-lattes-api/src/comprova_lattes/extractor/__init__.py` | **Vazio (planejado)** | Schema alinhado ao M2 (`ExtractedDocumentRecord`); modelo/prompt (`OPEN-03`) |
| **M4/M5 — Experimentos** | `comprova-lattes-api/src/comprova_lattes/experiments/__init__.py` | **Vazio (planejado)** | Fechar desenho piloto/final (30/~90), partição por família, IC bootstrap e McNemar |
| **M6 — API & Worker** | `api/main.py` (`/health`), `worker.py` (`ping_task`) | **Esqueleto base** | Depende de M1–M3 e contrato de revisão humana (`AD-013`) |
| **M6 — Frontend** | `comprova-lattes-app/src/App.tsx` (`/` e `/validacoes/nova`) | **Esqueleto base** (`npm run lint/build` OK) | Depende dos endpoints da API M6 |

**Invariantes Inegociáveis em Todas as Etapas:**
1. `matcher/` **nunca** importa ou chama `google-genai`; `confianca_extracao` e `categoria_sugerida` não entram na decisão (`AD-002`).
2. `parser/`, `matcher/` e `experiments/` executam offline sem PostgreSQL, Redis ou chamadas pagas ao Gemini.
3. Um documento por atividade no MVP (`AD-004`); sem comprovante = `Inconclusivo / SEM_COMPROVANTE` (`AD-005`); órfão fora da matriz $3 \times 3$ = `DOCUMENTO_NAO_ASSOCIADO` (`AD-006`); ambiguidade = `Inconclusivo / ASSOCIACAO_AMBIGUA` (`AD-007`); carga horária exata em `Decimal` (`AD-009`); evento, título e papel separados (`AD-010`).

---

## 2. Grafo de Execução e Responsabilidades

```text
[E1: Auditoria & Fechamento de Contratos (Somente Leitura)]
        │
        ▼ (Aprovação do usuário sobre pendências M2/M4)
[E2: M2 Motor Determinístico (matcher/)] ──► [E3: M3 Extrator Gemini (extractor/)]
        │                                               │
        └───────────────────────┬───────────────────────┘
                                ▼
                [E4: M4/M5 Bancada & Experimentos (experiments/)]
                                │
                                ▼
        [E5: M6 API FastAPI + Worker Celery + Revisão Humana (AD-013)]
                                │
                                ▼
                [E6: M6 Frontend React (comprova-lattes-app/)]
```

---

## 3. Prompts Prontos por Etapa (`simple-orchestrator delegate`)

> **Sessão Antigravity atual:** `a1db91ea-25b8-4e05-bafb-dcaa92656f15`
> **Regra:** Execute uma etapa por vez, valide o critério de aceite e só libere escrita após aprovação explícita do usuário.

### Etapa 1 — Auditoria Completa e Fechamento de Decisões (Somente Leitura)
- **Objetivo:** Verificar alinhamento entre código M1, specs M2/M3/M4 e listar todas as decisões pendentes para aprovação antes de codificar.
```powershell
& "$env:LOCALAPPDATA\Programs\simple-orchestrator\simple-orchestrator.exe" delegate `
  --run-key "tcc-e1-audit-20261113" `
  --task-id "e1-audit" `
  --attempt-id "att-01" `
  --maestra-provider "antigravity" `
  --maestra-session "a1db91ea-25b8-4e05-bafb-dcaa92656f15" `
  --worker-provider "codex" `
  --worker-chat-title "E1 - Auditoria e Decisoes Abertas" `
  --workspace "c:\Users\elivanilso.junior\Music\TCc2\comprova-lattes" `
  --target "AGENTS.md, .specs/, docs/, comprova-lattes-api/, comprova-lattes-app/" `
  --change "Auditar todo o repositorio em somente leitura, confirmar aderencia de M1 as specs e consolidar a lista objetiva de decisoes pendentes para M2, M3 e M4." `
  --constraints "Somente leitura; NAO criar, editar ou remover arquivos; NAO executar git commit/push; NAO chamar APIs pagas." `
  --acceptance "Relatorio estruturado com: (1) status verificado de M1 e testes; (2) lacunas entre specs e codigo; (3) questionario objetivo das decisoes pendentes (tabela de essencialidade M2, titulo omitido, coexistencia de papeis, desenho da bancada M4 e estatistica M5) com recomendacao tecnica." `
  --prompt "Leia AGENTS.md, .specs/project/{PROJECT,ROADMAP,STATE}.md, .specs/HANDOFF.md, .specs/features/m2-matcher/{proposal,event-role-contract}.md e .specs/features/experimental-protocol/proposal.md. Inspecione comprova-lattes-api/src/ e tests/ sem editar nada." `
  --auto-ack
```

### Etapa 2 — M2: Motor Determinístico (`matcher/`)
- **Pré-requisito:** Decisões de essencialidade/agregação por categoria aprovadas pelo usuário na Etapa 1.
- **Agente / Escopo:** `backend-specialist` → `comprova-lattes-api/src/comprova_lattes/matcher/` + `tests/test_matcher*.py`.
```powershell
& "$env:LOCALAPPDATA\Programs\simple-orchestrator\simple-orchestrator.exe" delegate `
  --run-key "tcc-e2-m2-matcher" `
  --task-id "e2-matcher" `
  --attempt-id "att-01" `
  --maestra-provider "antigravity" `
  --maestra-session "a1db91ea-25b8-4e05-bafb-dcaa92656f15" `
  --worker-provider "codex" `
  --worker-chat-title "E2 - Implementacao M2 Matcher" `
  --workspace "c:\Users\elivanilso.junior\Music\TCc2\comprova-lattes" `
  --target "comprova-lattes-api/src/comprova_lattes/matcher/, comprova-lattes-api/tests/" `
  --change "Implementar o motor deterministico M2 completo: contratos Pydantic, normalizacao, tabela de siglas, metricas (Levenshtein com guarda de string vazia, Jaro-Winkler, tokens), Etapa 1 (associacao/orfaos/ambiguidade), Etapa 2 (tabela de decisao por categoria e baselines A/B) e testes unitarios." `
  --constraints "Escrita restrita a matcher/ e tests/; PROIBIDO importar google-genai; nenhum limiar final hardcoded (parametros configuraveis com metadata de calibracao); manter funcoes puras sem Postgres/Redis; rodar pytest e ruff." `
  --acceptance "Modulos de matcher/ implementados com type hints, testes sinteticos cobrindo as 5 categorias, AD-004..AD-012, baselines A/B, e gate local 100% aprovado (pytest e ruff)." `
  --prompt "Siga .specs/features/m2-matcher/proposal.md, event-role-contract.md, .specs/codebase/CONVENTIONS.md e as decisoes aprovadas em .specs/project/STATE.md. Ao concluir, execute .venv\Scripts\python.exe -m pytest -q e .venv\Scripts\python.exe -m ruff check ." `
  --auto-ack
```

### Etapa 3 — M3: Extrator Multimodal (`extractor/`)
- **Pré-requisito:** Contrato `ExtractedDocumentRecord` fechado na Etapa 2.
- **Agente / Escopo:** `backend-specialist` → `comprova-lattes-api/src/comprova_lattes/extractor/` + `tests/test_extractor*.py`.
```powershell
& "$env:LOCALAPPDATA\Programs\simple-orchestrator\simple-orchestrator.exe" delegate `
  --run-key "tcc-e3-m3-extractor" `
  --task-id "e3-extractor" `
  --attempt-id "att-01" `
  --maestra-provider "antigravity" `
  --maestra-session "a1db91ea-25b8-4e05-bafb-dcaa92656f15" `
  --worker-provider "codex" `
  --worker-chat-title "E3 - Implementacao M3 Extractor" `
  --workspace "c:\Users\elivanilso.junior\Music\TCc2\comprova-lattes" `
  --target "comprova-lattes-api/src/comprova_lattes/extractor/, comprova-lattes-api/tests/" `
  --change "Implementar modulo extractor/ com SDK google-genai para PDF/imagem, schema JSON/Pydantic v2 alinhado a ExtractedDocumentRecord (event_name, activity_title, participation_role_raw separados), temperatura 0.0, registro de metadados de reprodutibilidade e separacao de erros (API_ERROR, INVALID_JSON, UNREADABLE)." `
  --constraints "Escrita restrita a extractor/ e tests/; NAO fazer chamadas reais pagas ao Gemini nos testes (usar mocks/fakes); nao acoplar regras de decisao no extrator (AD-002)." `
  --acceptance "Pipeline extractor/ implementado, testes com mocks cobrindo sucesso, JSON invalido, documento ilegivel e erro de API, e pytest + ruff aprovados." `
  --prompt "Alinhe a saida do extrator ao contrato ExtractedDocumentRecord em matcher/. Garanta que campos ausentes retornem null/None e que temperatura, modelo, versao, tokens e latencia sejam registrados. Rode pytest e ruff ao final." `
  --auto-ack
```

### Etapa 4 — M4/M5: Bancada Sintética, Baseline OCR e Experimentos (`experiments/`)
- **Pré-requisito:** Etapas 2 e 3 concluídas; desenho piloto/final e estatística aprovados.
- **Agente / Escopo:** `backend-specialist` + `test-engineer` → `comprova-lattes-api/src/comprova_lattes/experiments/` + `tests/test_experiments*.py`.
```powershell
& "$env:LOCALAPPDATA\Programs\simple-orchestrator\simple-orchestrator.exe" delegate `
  --run-key "tcc-e4-experiments" `
  --task-id "e4-experiments" `
  --attempt-id "att-01" `
  --maestra-provider "antigravity" `
  --maestra-session "a1db91ea-25b8-4e05-bafb-dcaa92656f15" `
  --worker-provider "codex" `
  --worker-chat-title "E4 - Bancada Sintetica e Experimentos" `
  --workspace "c:\Users\elivanilso.junior\Music\TCc2\comprova-lattes" `
  --target "comprova-lattes-api/src/comprova_lattes/experiments/, comprova-lattes-api/tests/" `
  --change "Implementar gerador deterministico de bancada sintetica (HTML/DOCX -> PDF/imagem + degradacao visual, sem usar LLM), particionamento por familia (piloto vs final), baseline OCR (Tesseract + RegEx), runner CLI dos Experimentos 1, 2 e 3, matriz 3x3, metricas de associacao, Kappa de Cohen, IC bootstrap e teste de McNemar." `
  --constraints "Escrita restrita a experiments/ e tests/; NAO usar documentos reais; NAO gerar documentos via Gemini; garantir isolamento estrito entre piloto e final e relatar DOCUMENTO_NAO_ASSOCIADO fora da matriz 3x3." `
  --acceptance "CLI reproduzivel gerando manifesto, metricas em CSV/JSON sem meta arbitraria (AD-008), testes automatizados validando determinismo, isolamento de particoes e calculos estatisticos, com pytest e ruff aprovados." `
  --prompt "Siga .specs/features/experimental-protocol/proposal.md e PROFESSOR-REQUIREMENTS.md. Execute pytest e ruff apos finalizar." `
  --auto-ack
```

### Etapa 5 — M6: API FastAPI, Worker Celery e Revisão Humana (`AD-013`)
- **Pré-requisito:** Núcleo P0 (`parser`, `matcher`, `extractor`) validado.
- **Agente / Escopo:** `backend-specialist` + `database-architect` → `comprova-lattes-api/src/comprova_lattes/{api,worker.py,db}/` + `tests/`.
```powershell
& "$env:LOCALAPPDATA\Programs\simple-orchestrator\simple-orchestrator.exe" delegate `
  --run-key "tcc-e5-api-worker" `
  --task-id "e5-api" `
  --attempt-id "att-01" `
  --maestra-provider "antigravity" `
  --maestra-session "a1db91ea-25b8-4e05-bafb-dcaa92656f15" `
  --worker-provider "codex" `
  --worker-chat-title "E5 - API FastAPI Worker e Revisao Humana" `
  --workspace "c:\Users\elivanilso.junior\Music\TCc2\comprova-lattes" `
  --target "comprova-lattes-api/src/comprova_lattes/, comprova-lattes-api/tests/" `
  --change "Implementar endpoints FastAPI (upload XML + documentos, consulta de status/resultado por campo, fluxo de revisao humana auditavel AD-013), tarefas Celery em worker.py e modelos SQLAlchemy preservando resultado automatico original separado do parecer manual." `
  --constraints "Preservar execucao offline dos testes do nucleo; testes de API devem usar TestClient/dependencias isoladas quando Postgres/Redis nao estiverem ativos; validar XML com parser seguro M1." `
  --acceptance "Endpoints documentados no OpenAPI, worker Celery integrado ao nucleo, trilha de revisao humana AD-013 persistida separadamente e gate local (pytest, ruff, docker compose config --quiet) aprovado." `
  --prompt "Implemente a camada P2 conectando parser, extractor e matcher aos endpoints FastAPI e ao worker Celery, respeitando AD-013. Rode pytest, ruff e docker compose config --quiet." `
  --auto-ack
```

### Etapa 6 — M6: Frontend React (`comprova-lattes-app/`)
- **Pré-requisito:** Contratos de API da Etapa 5 definidos.
- **Agente / Escopo:** `frontend-specialist` → `comprova-lattes-app/src/`.
```powershell
& "$env:LOCALAPPDATA\Programs\simple-orchestrator\simple-orchestrator.exe" delegate `
  --run-key "tcc-e6-frontend" `
  --task-id "e6-frontend" `
  --attempt-id "att-01" `
  --maestra-provider "antigravity" `
  --maestra-session "a1db91ea-25b8-4e05-bafb-dcaa92656f15" `
  --worker-provider "codex" `
  --worker-chat-title "E6 - Frontend React Comprova Lattes" `
  --workspace "c:\Users\elivanilso.junior\Music\TCc2\comprova-lattes" `
  --target "comprova-lattes-app/src/" `
  --change "Implementar telas React/TypeScript/Tailwind para nova validacao (upload XML + comprovantes), acompanhamento de progresso, visualizacao rastreavel por campo (XML vs documento) e painel de revisao humana (AD-013) exibindo resultado automatico preservado e justificativa manual." `
  --constraints "Preservar stack existente (React 19, Vite, Tailwind v4, React Router, TanStack Query) e package-lock.json; nao instalar novas dependencias sem aprovacao." `
  --acceptance "Fluxo completo integrado aos contratos da API, estados de erro/carregamento tratados e npm run lint + npm run build aprovados sem erros TypeScript." `
  --prompt "Implemente as rotas e componentes em comprova-lattes-app/src/ usando TanStack Query e Tailwind. Ao final execute npm run lint e npm run build." `
  --auto-ack
```

---

## 4. Checklist de Verificação Final (Phase X)
- [ ] **Etapa 1** concluída em somente leitura e decisões `M2/M4` aprovadas pelo usuário.
- [ ] **Etapas 2–4 (Núcleo P0):** `pytest -q` e `ruff check .` aprovados sem depender de Postgres/Redis/Gemini real.
- [ ] **Etapa 5 (API/Worker):** `pytest -q`, `ruff check .` e `docker compose config --quiet` aprovados.
- [ ] **Etapa 6 (Frontend):** `npm run lint` e `npm run build` aprovados.
- [ ] `.specs/project/{ROADMAP,STATE}.md` e `.specs/HANDOFF.md` atualizados ao fim de cada marco.
