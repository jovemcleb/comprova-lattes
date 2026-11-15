# Roadmap — Comprova Lattes (TCC 2)

## Reorganização aprovada e implementada — AD-016 (2026-11-15)

150 cenários: **10 famílias piloto de cinco casos (50)** e **20 famílias finais
 de cinco casos (100)**. Cada família mantém um registro-base/categoria e os cinco
operadores existentes; categorias balanceadas separadamente por partição.
Emissores exclusivos, ordem dos campos, margens e espaçamento variam deterministicamente.
A mudança não comprova independência estatística. Não executar estudo oficial nem
reutilizar corpus/manifestos antigos. Ampliação de operadores e revisão das métricas
continuam pendentes; não foram implicitamente concluídas por esta reorganização.

**Atualizar depois na monografia:** substituir 2/4 famílias de 25 por 10/20 de cinco;
explicar definição da família, balanceamento por categoria e diversidade de layouts;
atualizar quadro de composição e figuras; revisar unidade de reamostragem e limitações.
Continuam 40 documentos piloto e 80 finais; três repetições seriam 120 + 240 chamadas,
sem contar retries, reaproveitando extrações na etapa integrada. Sem resultados novos.


**AD-016 (2026-11-15):** aprovado 50 piloto + 100 finais, todos sintéticos;
substitui propostas de 30/~90 abaixo. Ampliação da bancada e protocolo ainda pendentes.

**Atualização 2026-11-15 (Templates pt-BR em rascunho):** `experiments/synthetic.py`
passa a emitir cabeçalhos e frases neutras fixas por categoria (cinco categorias) e
rótulos em português do contrato (`Titular`, `Atividade`, `Evento`, `Papel`,
`Instituição emissora`, `Sigla da instituição`, `Identificação da instituição`,
`Ano de início`, `Ano de conclusão`, `Ano da atividade`, `Carga horária`), sem criar
fatos nem alterar valores `gold` ou o trecho literal AD-014. A composição textual foi
assistida por agente da família Gemini (`TEMPLATE_PROVENANCE`) e permanece como
rascunho dependente de aprovação humana antes do congelamento (`freeze`), sem alegar
independência metodológica frente ao extrator. Integração com `baseline.py` (OCR+RegEx)
em adaptação concorrente; estudos oficiais M3/M4/M5 continuam pendentes.

**Atualização 2026-11-15:** AD-014 (equivalência institucional documental) e AD-015
(`gemini-3.5-flash-lite`) implementadas. Gate atual: 412 testes, Ruff e configuração
Compose aprovados. Primeira sondagem de extração real concluída; não equivale à
avaliação oficial M3/M4. Evidência e limites em STATE e
[relatório](../../docs/gemini-model-probe-20261115.md). Histórico abaixo preservado.

**Current Milestone:** M6 — backend verificado offline; interface implementada com lint/build aprovados

**S2 (2026-11-13):** S2: bloqueio ORGANIZACAO_EVENTO corrigido com autorização em 2026-11-13. Quando event_name=None, evento recebe NOT_APPLICABLE/STRUCTURAL_NOT_APPLICABLE e titulo é essencial, mesmo ausente; com evento preenchido o comportamento anterior permanece. Regressão parametrizada cobre evento documental ausente/presente e título documental ausente. Todos os testes existentes de matcher e experiments preservados; pilot/final aprovados. Gate completo: 396 passed em 24,09 s; Ruff, npm run lint e npm run build com exit 0. Sem instalação, commit/push ou serviços externos; integração real, DTD e estudo oficial continuam pendentes.
**Status:** API, persistência, worker e revisão AD-013 implementados; gate backend histórico de 390 testes e Ruff offline. Frontend implementado com lint/build exit 0 e smoke checks Node/React SSR; integração real pendente. M4/M5 sem estudo oficial; M1 aberto pelo requisito DTD, M2 sem calibração científica e M3 sem avaliação no serviço real. Gate e limites atuais em STATE/HANDOFF.

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
- **Testes (`pytest`)** — `VERIFIED OFFLINE`: regressões M1 existentes incluídas no gate S1 de 344 testes, incluindo IDs determinísticos únicos, contêineres repetidos e fallbacks de títulos, resumo, status e ano. Parser preservado nesta tarefa. Histórico de 130 testes e seis fixtures XSD em `docs/m1-linux-verification.md`; XSD não foi revalidado nesta execução.

---

## M2 (P0-C) — Motor Determinístico & Tabela de Decisão (IMPLEMENTED / VERIFIED OFFLINE)

**Goal:** Associar e classificar registros das 5 categorias curriculares nas 3 classes (`Validado`, `Divergente`, `Inconclusivo`) de forma 100% determinística e auditável, independente da API do Gemini.

- **Associação, Órfãos e Ambiguidade (`AD-004` a `AD-007`)** — `IMPLEMENTED`: atribuição global um-para-um de soma máxima, candidatos dentro da margem configurada, ausência de comprovante e órfãos separados da matriz. Âncoras título/evento exigem conteúdo após normalização. Falhas M3 não disputam pares; registros sem par sinalizam falha/ilegibilidade do lote com IDs/status nos diagnósticos, sem presumir associação. Contratos, backend e interface de revisão separados do automático; integração real pendente.
- **Normalização, Similaridade e Regras por Campo (`AD-009`, `AD-010`)** — `IMPLEMENTED`: normalização, siglas explícitas, Levenshtein, Jaro-Winkler e tokens, essencialidade/agregação por categoria, papéis coexistentes e horas estruturais. Decimal compara valores diretamente e calcula magnitude exata em contexto local, independente da precisão/faixa de expoentes do chamador. Ano inicial divergente é comparado quando ambos informados, mesmo com ano final igual; intervalo de atividade em andamento preservado. Implementação não constitui calibração ou aprovação científica de regras ainda pendentes.
- **Baselines Comparativos & Trilha de Auditoria** — `IMPLEMENTED`: Exato, Normalizado e Proposto, com escore, regra, magnitude e motivo por campo; serialização JSON verificada. Limiares dos testes são sintéticos; calibração piloto e avaliação final permanecem pendentes.

---

## M3 (P0-B) — Extração Multimodal com Gemini (IMPLEMENTED / VERIFIED OFFLINE)

**Goal:** Extrair entidades de PDFs e imagens usando `google-genai` com saída validada por JSON Schema e Pydantic.

- **Pipeline Multimodal (`AD-004`, `AD-010`)** — `IMPLEMENTED / VERIFIED OFFLINE`: PDF, PNG, JPEG e WebP via `google-genai`, JSON Schema e validação Pydantic local; entidades separadas, ausência como `None`, horas em Decimal. Múltiplas atividades rejeitadas pelo contrato. SDK simulado nos testes, sem chamadas ao serviço real.
- **Rastreabilidade** — `IMPLEMENTED`: modelo solicitado/versão retornada, prompt/versão/schema, temperatura zero, data, hash do documento, latência e tokens quando disponíveis. Modelo experimental e protocolo de repetições ainda pendentes.
- **Tratamento de Erros (`AD-002`)** — `IMPLEMENTED / VERIFIED OFFLINE`: `API_ERROR`, `INVALID_JSON` e `UNREADABLE`; integração M3 → M2 para sucesso, precisão Decimal, conflito de ano inicial, falhas isoladas e lotes mistos. Confiança/categoria sugeridas não participam da decisão. Nenhuma métrica de extração real produzida.

---

## M4 (P0-Exp) — Bancada Sintética & Experimentos 1, 2 e 3 (IMPLEMENTED OFFLINE / STUDY PENDING)

**Goal:** Gerar dados sintéticos controlados e calcular todas as métricas automaticamente via CLI, sem meta arbitrária de Macro-F1 (`AD-008`).

- **Gerador Sintético stdlib** — `IMPLEMENTED OFFLINE`: 5 categorias, XML e PDF/PNG raster válidos, degradação determinística e partição estrita por família/emissor/template. Tamanhos por número de famílias explícitos (25 casos/família); distribuição científica definitiva ainda pendente. Sem alegação de conformidade XSD/DTD.
- **Runner dos 3 Experimentos + CLI** — `IMPLEMENTED OFFLINE`: extração injetável/replay, três repetições sem inflar N; motor com gabarito vs A/B e três métricas; integrado reutiliza saídas e mede automático pré-revisão. Um registro por XML; bancada de competição multirregistro ainda não implementada.
- **Relatórios e congelamento (`AD-006`, `AD-008`)** — `IMPLEMENTED OFFLINE`: JSON com matriz 3×3, métricas por classe, associação e órfãos separados, falhas/estabilidade/propagação; calibração só piloto e SHA-256 de artefatos e corpus. Bootstrap por família; avaliação oficial e cegamento cronológico continuam responsabilidades do protocolo.

---

## M5 (P1) — Melhorias Científicas Recomendadas (IMPLEMENTED OFFLINE / STUDY PENDING)

**Goal:** Elevar o rigor estatístico e comparativo da monografia.

- **Baseline OCR Clássico** — `IMPLEMENTED / INJECTABLE`: OCR+RegEx recebe bytes/MIME; Tesseract real não instalado nem executado nesta tarefa.
- **Métricas & Estatística** — `IMPLEMENTED OFFLINE`: Kappa pré-consenso, IC percentil por família, McNemar pareado exato binomial e Holm; comparação Jaro-Winkler/tokens. Parâmetros explícitos, nenhuma meta de F1. Anotações humanas, calibração definitiva e avaliação real pendentes.

---

## M6 (P2) — API FastAPI, Filas Celery & Interface Web (BACKEND VERIFIED OFFLINE / UI IMPLEMENTED / REAL INTEGRATION PENDING)

**Goal:** Integrar os módulos validados à API assíncrona e ao frontend React (`comprova-lattes-app`).

- **Endpoints FastAPI + Worker Celery** — `IMPLEMENTED / VERIFIED OFFLINE`: health/CORS, criação JSON com XML texto/base64 e documentos base64, listagem paginada, consulta, persistência SQLAlchemy e tarefa M1 → M3 → M2. Configuração do matcher obrigatória, sem limiar científico implícito. SQLite em memória e extrator/dispatcher injetáveis; serviços reais não exercitados.
- **Revisão humana AD-013** — `IMPLEMENTED / VERIFIED OFFLINE`: inconclusivos e revisão solicitada das demais classes, justificativa obrigatória, documentos restritos ao lote, correção/rejeição de associação e histórico com revisor/data/parecer. Snapshot automático preservado e contagens automáticas/pós-revisão separadas. Identidade do revisor declarada, sem autenticação; recuperação de jobs interrompidos e migrações pendentes.
- **Telas React (`comprova-lattes-app`)** — `IMPLEMENTED / LINT + BUILD VERIFIED`: histórico/health, criação com XML binário ou texto, múltiplos comprovantes e MatcherConfig explícito; acompanhamento com polling, auditoria M1 → M3 → M2, candidatos/órfãos/diagnósticos e revisão humana AD-013 com histórico e sumários separados. Camadas types/lib/hooks/components/pages; smoke checks de serviços e renderização SSR aprovados. Integração interativa com serviços reais ainda pendente, sem afirmar avaliação científica ou operação de infraestrutura.
