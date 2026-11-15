# Plano M6 Backend: API FastAPI, Worker Celery e Revisão Humana Auditável (`AD-013`)

## 1. Arquitetura e Restrições Técnicas

- **Entrada JSON sem `python-multipart`:** `python-multipart` não está instalado na `.venv` e `AGENTS.md` veda instalar novas dependências sem autorização explícita. Portanto, os endpoints de upload recebem **payloads JSON tipados** (`xml_content`/`xml_base64` e lista de documentos com `document_id`, `filename`, `mime_type`, `content_base64`).
- **Independência Offline:** produção utiliza `settings.database_url` (PostgreSQL 16) e Celery/Redis (`worker.py`); testes automatizados rodam 100% offline usando SQLite em memória (`StaticPool`) e extrator/dispatcher injetáveis.
- **Preservação Estrita `AD-013`:** todo `INCONCLUSIVO` possui `review_required=True`, e `VALIDADO`/`DIVERGENTE` também aceitam revisão solicitada. O parecer humano exige `reviewer`, `status` e `justification` não vazia, valida IDs de documentos contra o lote da sessão e **nunca sobrescreve** o resultado automático original (`RecordVerdict`), reportando métricas/contagens automáticas separadas das pós-revisão (`AD-007`, `AD-013`).

---

## 2. Escopo dos Módulos (`comprova_lattes.api` e `worker.py`)

| Arquivo | Responsabilidade |
| --- | --- |
| `api/schemas.py` | Contratos Pydantic v2 (`DocumentUploadInput`, `ValidationCreateRequest`, `HumanReviewRequest`, `ValidationSummaryResponse`, `ValidationDetailResponse`) com contagens automáticas separadas das pós-revisão |
| `api/db.py` & `api/models.py` | Camada SQLAlchemy 2.0 (sessões de validação, XML/documentos, veredictos automáticos e histórico/registro de revisão humana `AD-013`) compatível com PostgreSQL e SQLite em memória |
| `worker.py` | Preserva `ping_task` e implementa `process_validation_task` (`comprova_lattes.process_validation`) executando `M1 → M3 → M2` e persistindo resultado |
| `api/main.py` | Preserva `GET /health`, habilita `CORSMiddleware` para `comprova-lattes-app` e expõe `POST /validations`, `GET /validations`, `GET /validations/{validation_id}` e `POST /validations/{validation_id}/records/{record_index}/review` |
| `tests/test_api.py` | Suíte offline via `TestClient` cobrindo `/health`, pipeline `M1 → M3 → M2`, revisão humana `AD-013` em inconclusivos e validados/divergentes, erros de entrada e tarefa Celery |

---

## 3. Tarefas e Verificação

| ID | Tarefa | Responsável | Critério de Aceite |
| --- | --- | --- | --- |
| **T1** | Criar `api/schemas.py`, `api/db.py` e modelos ORM SQLAlchemy | `backend-specialist` (Codex) | Sessão e revisão humana `AD-013` persistidas sem alterar resultado automático |
| **T2** | Implementar endpoints FastAPI + CORS em `api/main.py` e tarefa em `worker.py` | `backend-specialist` (Codex) | Endpoints operacionais via JSON (`base64`/texto) + `TestClient` offline |
| **T3** | Criar `tests/test_api.py` e atualizar `STATE.md`, `ROADMAP.md` e `HANDOFF.md` | `test-engineer` (Codex) | `pytest -q` + `ruff check .` 100% aprovados |

---

## 4. Comando de Delegação ao Codex (`simple-orchestrator`)

```powershell
& "$env:LOCALAPPDATA\Programs\simple-orchestrator\simple-orchestrator.exe" delegate `
  --run-key "tcc-e5-m6-api-20261113" `
  --task-id "e5-api" `
  --attempt-id "att-01" `
  --maestra-provider "antigravity" `
  --maestra-session "a1db91ea-25b8-4e05-bafb-dcaa92656f15" `
  --worker-provider "codex" `
  --worker-chat-title "E5 - Implementacao M6 API Worker e Revisao Humana" `
  --workspace "c:\Users\elivanilso.junior\Music\TCc2\comprova-lattes" `
  --target "comprova-lattes-api/src/comprova_lattes/api/, comprova-lattes-api/src/comprova_lattes/worker.py, comprova-lattes-api/tests/, .specs/project/STATE.md, .specs/project/ROADMAP.md, .specs/HANDOFF.md" `
  --change "Implementar a camada M6 de backend (API FastAPI, persistencia SQLAlchemy, tarefa Celery em worker.py e fluxo completo de revisao humana auditavel AD-013) com testes automatizados offline." `
  --constraints "Escrita restrita a api/, worker.py, tests/ e .specs/{project/STATE.md,project/ROADMAP.md,HANDOFF.md}; NAO alterar parser/, matcher/, extractor/ ou experiments/; NAO instalar novos pacotes (atencao: python-multipart NAO esta instalado, portanto use payloads JSON com base64/texto nos endpoints FastAPI em vez de UploadFile/Form); NAO exigir Postgres/Redis/Gemini ativos nos testes pytest (usar SQLite em memoria e extrator/dispatcher injetaveis); NAO executar git commit/push." `
  --acceptance "API FastAPI e worker Celery implementados e testados cobrindo: (1) GET /health preservado e CORS configurado; (2) POST /validations, GET /validations, GET /validations/{id} integrando M1->M3->M2 com persistencia SQLAlchemy; (3) POST /validations/{id}/records/{record_index}/review implementando AD-013 (revisao de inconclusivos e revisao solicitada de validados/divergentes, justificativa obrigatoria, validacao de documentos candidatos, preservacao estrita do resultado automatico original e sumarios automatico vs revisado separados); (4) tarefa Celery em worker.py; (5) pytest e ruff 100% aprovados offline." `
  --prompt "Leia .specs/project/STATE.md (especialmente AD-003, AD-007, AD-013), .specs/codebase/ARCHITECTURE.md e inspecione api/main.py, worker.py, config.py, parser/xml_parser.py, matcher/{models,engine}.py e extractor/gemini.py. Implemente os endpoints FastAPI, persistencia SQLAlchemy e tarefa Celery respeitando estritamente AD-013 e sem usar UploadFile/Form (pois python-multipart nao esta instalado). Crie testes abrangentes em tests/test_api.py usando TestClient, SQLite em memoria e extrator fake/mock, atualize STATE/ROADMAP/HANDOFF e execute pytest e ruff ao final." `
  --auto-ack
```

---

## 5. Checklist de Verificação (Phase X)
- [ ] Plano `m6-backend-plan.md` criado na raiz do projeto.
- [ ] Delegação `e5-api` concluída pelo Codex com `ok: true`.
- [ ] Gates independentes (`pytest -q` e `ruff check .`) aprovados.
