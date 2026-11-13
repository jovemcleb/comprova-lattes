# Roadmap — Comprova Lattes (TCC 2)

**Current Milestone:** M1 — Parser XML Lattes Seguro
**Status:** Em andamento — implementação das 5 categorias e gate local verificados (AD-012); referência estrutural XSD/DTD definida (`AD-011`), com requisito DTD do orientador ainda pendente. M2 e protocolo experimental em planejamento/proposta.

---

## M0 — Setup Base & Contexto Compartilhado (COMPLETE)

**Goal:** Limpar boilerplate Node.js antigo, estruturar repositório Python + Docker Compose (PostgreSQL + Redis + Celery) e documentar contexto enxuto para colaboração e agentes.

- **Documentação Spec-Driven** — `COMPLETE`: `.specs/project/` e `.specs/codebase/` com arquivos curtos e objetivos.
- **Infraestrutura Base (`comprova-lattes-api`)** — `COMPLETE`: `compose.yaml` (Postgres + Redis + API + Celery Worker), `pyproject.toml` e pacote base Python.

---

## M1 (P0-A) — Parser XML Lattes Seguro (IN PROGRESS)

**Goal:** Extrair deterministicamente os registros do XML Lattes para JSON canônico nas 5 categorias aprovadas (`AD-012`).

- **Leitura Segura (`defusedxml`) & Referência Estrutural (`AD-011`)** — `IMPLEMENTED / IN PROGRESS`: UTF-8/ISO-8859-1, bloqueio de entidades/DTD e limites de recursos. XSD oficial do Extrator CNPq adotado como referência estrutural principal e DTD comunitária como comparação histórica (com fixtures conformes separadas das de robustez), sem presumir equivalência integral com a exportação da interface web (UI). Substituição/atendimento do requisito de validação DTD do professor (#25) ainda pendente de justificativa e confirmação com o orientador; bloqueio de DTD não é validação de conformidade.
- **Mapeamento de 5 Categorias (`AD-010`, `AD-012`)** — `IMPLEMENTED / VERIFIED LOCAL`: `FORMACAO_ACADEMICA`, `FORMACAO_COMPLEMENTAR` e `PARTICIPACAO_EVENTO` implementadas, com ampliação também implementada para `APRESENTACAO_TRABALHO` (`APRESENTACAO-DE-TRABALHO`) e `ORGANIZACAO_EVENTO` (`ORGANIZACAO-DE-EVENTO`) em `PRODUCAO-TECNICA/DEMAIS-TIPOS-DE-PRODUCAO-TECNICA`, mantendo título, nome do evento, natureza e papel separados sem inferências indevidas (artigos e anais permanecem fora de escopo).
- **Testes (`pytest`)** — `VERIFIED`: 130 testes e Ruff aprovados independentemente em Python 3.14 local; Linux/Python 3.12 com 130 testes e Ruff relatados pelo Hydrogen. Seis fixtures conformes/técnicas revalidadas independentemente contra XSD offline. Evidências em `docs/m1-linux-verification.md`.

---

## M2 (P0-C) — Motor Determinístico & Tabela de Decisão (PLANNED)

**Goal:** Associar e classificar registros das 5 categorias curriculares nas 3 classes (`Validado`, `Divergente`, `Inconclusivo`) de forma 100% determinística e auditável, independente da API do Gemini.

- **Associação, Órfãos e Ambiguidade (`AD-004` a `AD-007`)** — `PLANNED`: Um documento por atividade no MVP (`AD-004`); registro sem comprovante como `Inconclusivo / SEM_COMPROVANTE` (`AD-005`); documento sem registro reportado fora da matriz $3 \times 3$ como `DOCUMENTO_NAO_ASSOCIADO` (`AD-006`); associação ambígua como `Inconclusivo / ASSOCIACAO_AMBIGUA` com revisão humana separada e métricas automáticas calculadas antes da intervenção humana (`AD-007`). AD-013 amplia revisão a todos os inconclusivos e permite revisão das demais classes por solicitação, com parecer/revisor/data/justificativa separados do automático; fluxo ainda não implementado. Limiares quantitativos e resolução de disputas entre registros permanecem em aberto.
- **Normalização, Similaridade e Regras por Campo (`AD-009`, `AD-010`)** — `PLANNED`: Caixa, acentuação, pontuação, Levenshtein normalizado, tabela explícita de siglas (ex.: `UFRA` ↔ `Universidade Federal Rural da Amazônia`), comparação exata de carga horária em `Decimal` (`40 == 40.0`; `40` vs `45` conflito no campo em par associado, `AD-009`) e separação entre título específico, nome do evento e papel explícito (`AD-010`). Essencialidade e agregação final por categoria, título omitido e coexistência de papéis (ex.: ouvinte vs. apresentador/organizador) permanecem pendentes de aprovação.
- **Baselines Comparativos & Trilha de Auditoria** — `PLANNED`: Baseline A (Exato), Baseline B (Normalizado) e Método Proposto, com retorno detalhado por campo (escore, regra acionada, magnitude numérica e motivo).

---

## M3 (P0-B) — Extração Multimodal com Gemini (PLANNED)

**Goal:** Extrair entidades de PDFs e imagens usando `google-genai` com saída validada por JSON Schema e Pydantic.

- **Pipeline Multimodal (`AD-004`, `AD-010`)** — `PLANNED`: Envio de PDF/imagem (1 documento por atividade no MVP), diferenciação entre campo ausente (`null`) e extraído, mantendo nome do evento, título do trabalho/palestra e papel explícito de participação em campos separados.
- **Rastreabilidade Experimental** — `PLANNED`: Log de modelo, versão, temperatura, prompt (zero-shot/few-shot), latência e consumo de tokens.
- **Tratamento de Erros (`AD-002`)** — `PLANNED`: Separação entre erro de API, JSON inválido e documento ilegível (`confianca_extracao` e `categoria_sugerida` não entram na decisão).

---

## M4 (P0-Exp) — Bancada Sintética & Experimentos 1, 2 e 3 (PLANNED)

**Goal:** Gerar dados sintéticos controlados e calcular todas as métricas automaticamente via CLI, sem meta arbitrária de Macro-F1 (`AD-008`).

- **Gerador Sintético (Templates HTML/DOCX)** — `PLANNED`: Proposta inicial de 30 cenários piloto (12 Validados, 10 Divergentes, 8 Inconclusivos) + ~90 cenários finais; tamanho definitivo, definição de famílias e distribuição entre as 5 categorias (`AD-012`) e as 3 classes permanecem pendentes de aprovação.
- **Runner dos 3 Experimentos** — `PLANNED`: Exp 1 (Extração LLM, proposta de 3 repetições), Exp 2 (Motor com gabarito perfeito vs Baselines A/B), Exp 3 (Fluxo integrado, métricas automáticas antes da revisão humana conforme `AD-007`).
- **Relatórios Automáticos (`AD-006`, `AD-008`)** — `PLANNED`: Matriz de confusão $3 \times 3$ dos registros curriculares, Acurácia, Precisão, Recall, F1 por classe e Macro-F1 observado com intervalo de confiança em CSV/JSON, além de métricas de associação e reporte separado de `DOCUMENTO_NAO_ASSOCIADO`.

---

## M5 (P1) — Melhorias Científicas Recomendadas (PLANNED)

**Goal:** Elevar o rigor estatístico e comparativo da monografia.

- **Baseline OCR Clássico** — `PLANNED`: `Tesseract` + RegEx nos mesmos documentos.
- **Métricas & Estatística** — `PLANNED`: Jaro-Winkler/tokens, Kappa de Cohen nos gabaritos, IC via bootstrap e teste de McNemar (unidade de reamostragem, nível do IC e regra de agregação das repetições continuam propostas sem aprovação).

---

## M6 (P2) — API FastAPI, Filas Celery & Interface Web (PLANNED)

**Goal:** Integrar os módulos validados à API assíncrona e ao frontend React (`comprova-lattes-app`).

- **Endpoints FastAPI + Worker Celery** — `PLANNED`: Upload de XML/documentos, disparo de jobs no Redis/Celery e persistência no PostgreSQL.
- **Telas React (`comprova-lattes-app`)** — `PLANNED`: Nova validação, acompanhamento de progresso e visualização rastreável por campo.
