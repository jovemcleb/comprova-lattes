# Roadmap — Comprova Lattes (TCC 2)

**Current Milestone:** M0 — Setup Base & Contexto Compartilhado
**Status:** Complete (Pronto para iniciar M1)

---

## M0 — Setup Base & Contexto Compartilhado (COMPLETE)

**Goal:** Limpar boilerplate Node.js antigo, estruturar repositório Python + Docker Compose (PostgreSQL + Redis + Celery) e documentar contexto enxuto para colaboração e agentes.

- **Documentação Spec-Driven** — `COMPLETE`: `.specs/project/` e `.specs/codebase/` com arquivos curtos e objetivos.
- **Infraestrutura Base (`comprova-lattes-api`)** — `COMPLETE`: `compose.yaml` (Postgres + Redis + API + Celery Worker), `pyproject.toml` e pacote base Python.

---

## M1 (P0-A) — Parser XML Lattes Seguro (PLANNED)

**Goal:** Extrair deterministicamente os registros do XML Lattes para JSON canônico.

- **Leitura Segura (`defusedxml`)** — `PLANNED`: Suporte a `UTF-8` e `ISO-8859-1`, bloqueio de XXE/entidades externas e validação contra DTD.
- **Mapeamento de 3 Seções** — `PLANNED`: Formação Acadêmica/Titulação, Formação Complementar e Participação em Eventos.
- **Testes Unitários (`pytest`)** — `PLANNED`: Cobertura para XMLs malformados, atributos ausentes e estruturas inesperadas.

---

## M2 (P0-C) — Motor Determinístico & Tabela de Decisão (PLANNED)

**Goal:** Associar e classificar registros (`Validado`, `Divergente`, `Inconclusivo`) de forma 100% determinística e auditável, independente da API do Gemini.

- **Normalização & Similaridade** — `PLANNED`: Caixa, acentuação, pontuação, Levenshtein normalizado e tabela explícita de siglas (ex.: `UFRA` ↔ `Universidade Federal Rural da Amazônia`).
- **Baselines Comparativos** — `PLANNED`: Baseline A (Exato), Baseline B (Normalizado) e Método Proposto.
- **Trilha de Auditoria** — `PLANNED`: Retorno detalhado por campo com score, regra acionada e motivo.

---

## M3 (P0-B) — Extração Multimodal com Gemini (PLANNED)

**Goal:** Extrair entidades de PDFs e imagens usando `google-genai` com saída validada por JSON Schema e Pydantic.

- **Pipeline Multimodal** — `PLANNED`: Envio de PDF/imagem, diferenciação entre campo ausente (`null`) e extraído.
- **Rastreabilidade Experimental** — `PLANNED`: Log de modelo, versão, temperatura, prompt (zero-shot/few-shot), latência e consumo de tokens.
- **Tratamento de Erros** — `PLANNED`: Separação entre erro de API, JSON inválido e documento ilegível (`confianca_extracao` não entra na decisão).

---

## M4 (P0-Exp) — Bancada Sintética & Experimentos 1, 2 e 3 (PLANNED)

**Goal:** Gerar dados sintéticos controlados e calcular todas as métricas automaticamente via CLI.

- **Gerador Sintético (Templates HTML/DOCX)** — `PLANNED`: 30 cenários piloto (12 Validados, 10 Divergentes, 8 Inconclusivos) + ~90 cenários finais com 5 operadores de mutação.
- **Runner dos 3 Experimentos** — `PLANNED`: Exp 1 (Extração LLM, 3 repetições), Exp 2 (Motor com gabarito perfeito vs Baselines A/B), Exp 3 (Fluxo integrado).
- **Relatórios Automáticos** — `PLANNED`: Matriz de confusão $3 \times 3$, Acurácia, Precisão, Recall, F1 por classe e Macro-F1 em CSV/JSON.

---

## M5 (P1) — Melhorias Científicas Recomendadas (PLANNED)

**Goal:** Elevar o rigor estatístico e comparativo da monografia.

- **Baseline OCR Clássico** — `PLANNED`: `Tesseract` + RegEx nos mesmos documentos.
- **Métricas & Estatística** — `PLANNED`: Jaro-Winkler/tokens, Kappa de Cohen nos gabaritos, IC via bootstrap e teste de McNemar.

---

## M6 (P2) — API FastAPI, Filas Celery & Interface Web (PLANNED)

**Goal:** Integrar os módulos validados à API assíncrona e ao frontend React (`comprova-lattes-app`).

- **Endpoints FastAPI + Worker Celery** — `PLANNED`: Upload de XML/documentos, disparo de jobs no Redis/Celery e persistência no PostgreSQL.
- **Telas React (`comprova-lattes-app`)** — `PLANNED`: Nova validação, acompanhamento de progresso e visualização rastreável por campo.
