# Plano Completo de Desenvolvimento e Alinhamento TCC (`comprova-lattes`)

## 1. Alinhamento Crítico: Monografia (TCC 2) ↔ Código e Specs

| Ponto | Texto Atual do TCC | Estado Real / Regra Aprovada (`STATE.md`) | Ação Necessária |
| --- | --- | --- | --- |
| Meta `Macro-F1 >= 0,85` | Citada no Resumo, 1.3.2, 3.4, Tab. 5 e Conclusão | **Removida (`AD-008`, #66)**; reportar observado + IC | Atualizar texto do TCC após experimentos |
| Papéis (`event-role-contract`) | Quadro 4 classifica ouvinte vs. palestrante como `Divergente` | `AD-010` e `matcher/` tratam como `Inconclusivo` (coexistência) | Alinhar Quadro 4 ao comportamento do M2 |
| `DocumentoExtraidoSchema` | `categoria_inferida` obrigatório + `carga_horaria: float` | `AD-002` proíbe uso decisório; `AD-009` usa `Decimal` | Alinhar M3 a `ExtractedDocumentRecord` (`Decimal`) |
| Seções em `PRODUCAO-TECNICA` | Quadro 2 cita `SOFTWARE`, `PRODUTO-TECNOLOGICO`, etc. | `AD-012` implementa `APRESENTACAO-DE-TRABALHO` e `ORGANIZACAO-DE-EVENTO` | Atualizar Quadro 2 e Tabela 1 (5 categorias) |
| Infraestrutura (`GCS`) | Cita Google Cloud Storage no Resumo e §3.3/4.1 | Não existe GCS no `compose.yaml` ou `pyproject.toml` | Remover GCS do texto ou implementar |
| Baselines e Estatística | Só `Exact Match` e sem 3 repetições/OCR/Kappa/IC/McNemar | Exigidos em `PROFESSOR-REQUIREMENTS.md` (#16, #29, #37, #45, #47, #67) | Implementar em M4/M5 e atualizar Cap. 3–4 |
| Validação XSD/DTD | Texto afirma validação XSD/DTD em runtime no M1 | `defusedxml` bloqueia DTD; XSD validado offline (`AD-011`) | Confirmar alternativa XSD com orientador (#25) |

---

## 2. Etapas Restantes de Desenvolvimento (via `simple-orchestrator` → Codex)

### Etapa 3 — M3: Extrator Multimodal (`extractor/`)
- **Responsável:** `backend-specialist` (Codex)
- **Alvo:** `comprova-lattes-api/src/comprova_lattes/extractor/`, `tests/test_extractor*.py`
- **Entregas:**
  1. Cliente `google-genai` (`temperature=0.0`, `response_mime_type="application/json"`, `response_schema`).
  2. Conversão direta para `ExtractedDocumentRecord` (`matcher/models.py`), preservando `event_name`, `activity_title`, `participation_role_raw` separados e `workload_hours` em `Decimal` (sem `float`).
  3. Registro de metadados de reprodutibilidade (modelo, versão, temperatura, prompt, latência, tokens) e separação de falhas (`OK`, `UNREADABLE`, `INVALID_JSON`, `API_ERROR`).
  4. Testes unitários 100% offline com mocks (sem chamadas pagas).
- **Verificação:** `pytest -q` + `ruff check .` aprovados.

### Etapa 4 — M4/M5: Bancada Sintética, Baselines e Experimentos (`experiments/`)
- **Responsável:** `backend-specialist` + `test-engineer` (Codex)
- **Alvo:** `comprova-lattes-api/src/comprova_lattes/experiments/`, `tests/test_experiments*.py`
- **Entregas:**
  1. Gerador determinístico de bancada sintética (HTML/DOCX → PDF/imagem + script de degradação visual: rotação, ruído, blur, carimbo; sem uso de LLM).
  2. Partição por família sem vazamento: Conjunto Piloto (calibração) isolado do Conjunto Final (teste cego), cobrindo as 5 categorias e operadores de variação/mutação.
  3. Baseline OCR (`Tesseract` + RegEx) para Exp. 1; Baselines A (`Exact Match`), B (`Normalizado`) e métricas Jaro-Winkler/Tokens para Exp. 2.
  4. Runner CLI para Experimentos 1 (3 repetições Gemini), 2 e 3, exportando matriz $3 \times 3$, `DOCUMENTO_NAO_ASSOCIADO` separado, Kappa de Cohen, IC por bootstrap e teste de McNemar em CSV/JSON.
- **Verificação:** `pytest -q` + `ruff check .` aprovados; execução seca offline validada.

### Etapa 5 — M6: API FastAPI, Worker Celery e Revisão Humana (`AD-013`)
- **Responsável:** `backend-specialist` + `database-architect` (Codex)
- **Alvo:** `comprova-lattes-api/src/comprova_lattes/{api,worker.py,db}/`, `tests/`
- **Entregas:**
  1. Modelos SQLAlchemy/PostgreSQL e endpoints FastAPI para upload de XML + comprovantes, consulta de status e detalhamento rastreável por campo.
  2. Fluxo de revisão humana auditável (`AD-013`): encaminhamento de `Inconclusivo`, revisão opcional de `Validado`/`Divergente`, preservação do resultado automático original e registro separado de revisor/data/parecer/justificativa.
  3. Integração Celery/Redis em `worker.py` sem quebrar a execução offline do núcleo (`parser`, `matcher`, `experiments`).
- **Verificação:** `pytest -q`, `ruff check .` e `docker compose config --quiet` aprovados.

### Etapa 6 — M6: Frontend React (`comprova-lattes-app/`)
- **Responsável:** `frontend-specialist` (Codex)
- **Alvo:** `comprova-lattes-app/src/`
- **Entregas:**
  1. Tela de nova validação (upload XML + PDFs/imagens) com TanStack Query.
  2. Painel de acompanhamento e auditoria por campo (XML vs. extraído vs. evidência/escore).
  3. Interface de revisão humana (`AD-013`) para confirmar/corrigir associação e registrar parecer manual com justificativa.
- **Verificação:** `npm run lint` e `npm run build` aprovados.

---

## 3. Checklist de Verificação Final (Phase X)
- [ ] **E3 (`extractor/`):** mocks aprovados, `Decimal` preservado, zero decisão no LLM.
- [ ] **E4 (`experiments/`):** piloto isolado do final, CSV/JSON reproduzíveis, métricas completas (#16, #29, #37, #45, #47, #67).
- [ ] **E5 (`api/` + `worker.py`):** revisão humana `AD-013` preservando automático + `pytest`/`ruff`/`compose` OK.
- [ ] **E6 (`comprova-lattes-app/`):** `npm run lint` + `npm run build` OK.
- [ ] **Monografia (TCC 2):** atualizar placeholders `{...}` com resultados reais e corrigir os 7 pontos de alinhamento da Seção 1.
