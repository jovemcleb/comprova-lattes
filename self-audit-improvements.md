# Plano de Auto-Verificação e Melhorias (`comprova-lattes`)

## 1. Plano de Auto-Verificação Completa (M1 + M2 + M3)

| ID | Verificação | Alvo | Critério de Aprovação |
| --- | --- | --- | --- |
| **AV-01** | Gate técnico completo | `comprova-lattes-api/` e `comprova-lattes-app/` | `pytest -q` (311+ passed), `ruff check .`, `npm run lint`, `npm run build` |
| **AV-02** | Invariantes científicos (`AD-002`, `AD-009`, `AD-010`) | `matcher/` e `extractor/` | Zero imports de `google-genai` em `matcher/`; zero lógica de decisão em `extractor/`; `Decimal` preservado fim a fim |
| **AV-03** | Alinhamento de contratos (`M1 → M3 → M2`) | `schemas/lattes.py`, `extractor/models.py`, `matcher/models.py` | Campos compatíveis (`event_name`, `activity_title`, `participation_role_raw`, `workload_hours`), ausência como `None` |
| **AV-04** | Revisão de qualidade e casos de borda | `parser/`, `matcher/`, `extractor/` | Sem duplicação de lógica; cobertura de `UNREADABLE`, `INVALID_JSON`, `API_ERROR`, strings vazias e 5 categorias |
| **AV-05** | Atualização documental `.specs/` | `.specs/project/{STATE,ROADMAP}.md`, `.specs/HANDOFF.md` | Registrar estado real implementado de M1 (corrigido), M2 e M3 |

---

## 2. Melhorias Recomendadas no Projeto Principal

### 2.1 Melhorias com Alto Benefício Científico (Alinhadas ao TCC)
1. **Calibração Empírica Automatizada + Congelamento por Hash (`M4`):**
   - *Benefício:* gera a tabela de varredura no Conjunto Piloto (30) e salva os limiares congelados com hash SHA-256 antes de abrir o Conjunto Final (90), eliminando risco de *data leakage* (#45, #62).
   - *Custo:* baixo (1 módulo pequeno em `experiments/calibration.py`).
2. **Comparativo Multi-Métrica no Motor (`LEVENSHTEIN_NORM` vs. `JARO_WINKLER` vs. `TOKEN_HYBRID`):**
   - *Benefício:* `matcher/text.py` já implementa as 3 métricas; incluir a comparação no Experimento 2 atende diretamente ao Comentário #37 do orientador e fortalece o Capítulo 4.
   - *Custo:* muito baixo (apenas parametrização no runner de experimentos).
3. **Relatório de Estabilidade entre Repetições do Gemini (`M3` → `M4`):**
   - *Benefício:* mede automaticamente a concordância campo a campo nas 3 repetições a `temperature=0.0` (#32, #34, #53), quantificando variância residual.
   - *Custo:* baixo.
4. **CLI Unificada do Núcleo (`python -m comprova_lattes`):**
   - *Benefício:* permite executar `parse`, `match`, `extract` e `run-experiments` direto no terminal sem subir PostgreSQL/Redis/Docker, facilitando demonstração na banca e reprodutibilidade (#72).
   - *Custo:* baixo (1 arquivo `cli.py` com `argparse`/`typer` ou stdlib).

### 2.2 Novas Propostas Opcionais (Exigem Aprovação antes de Implementar)
1. **Exportador de Dossiê Auditável (JSON + Markdown/HTML):** gera um parecer legível por registro (dado XML vs. dado extraído vs. escore vs. regra acionada), útil como apêndice da monografia e para comissões avaliadoras.
2. **Exibição de Código de Autenticidade na UI (`AD-013`):** destacar `validation_code` / URL de verificação já capturados na proveniência dentro do painel de revisão humana (sem consulta automática externa, preservando determinismo).

---

## 3. Roteiro Sequencial Recomendado

| Etapa | Responsável | Foco |
| --- | --- | --- |
| **S1 — Auto-Verificação + Specs** | `code-reviewer` (Codex, somente leitura) + atualização `.specs/` | Executar `AV-01` a `AV-05` antes de abrir M4 |
| **S2 — Etapa 4 (`experiments/`)** | `backend-specialist` + `test-engineer` (Codex) | Gerador sintético, degradação visual, OCR baseline, Exp 1–3, Kappa/Bootstrap/McNemar + CLI |
| **S3 — Execução Experimental & TCC** | Usuário + Antigravity | Rodar Piloto → congelar limiares → rodar Final → preencher tabelas reais e alinhar monografia |
| **S4 — Etapa 5 (`api/` + `worker.py`)** | `backend-specialist` + `database-architect` (Codex) | Endpoints FastAPI, Celery/Redis, PostgreSQL e revisão humana `AD-013` |
| **S5 — Etapa 6 (`comprova-lattes-app/`)** | `frontend-specialist` (Codex) | Upload, progresso, trilha por campo e painel de revisão humana |

---

## 4. Checklist de Verificação (Phase X)
- [ ] Auto-verificação (`AV-01` a `AV-04`) aprovada sem regressões.
- [ ] `.specs/` atualizado com status real de M1, M2 e M3 (`AV-05`).
- [ ] Melhorias selecionadas pelo usuário incorporadas antes da Etapa 4 (`experiments/`).
- [ ] Gates finais (`pytest`, `ruff`, `npm run lint`, `npm run build`, `docker compose config --quiet`) verdes.
