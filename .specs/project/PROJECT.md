# Comprova Lattes (TCC 2 - UFRA)

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


**Vision:** Protótipo cientificamente avaliável de validação semiautomatizada do Currículo Lattes, cruzando dados nativos em XML com informações extraídas de documentos comprobatórios via LLM multimodal.
**For:** Comissões avaliadoras, pesquisadores e banca examinadora do TCC 2 (Sistemas de Informação - UFRA).
**Solves:** Reduz a conferência manual de documentos heterogêneos mantendo rastreabilidade por campo e separando estritamente a extração (LLM) da decisão algorítmica.

## Goals

Atualização AD-016 (2026-11-15): aprovado total de **150 cenários sintéticos,
50 piloto + 100 finais**, substituindo os tamanhos propostos historicamente abaixo.
Distribuição por operadores/famílias deve ser reconciliada antes de gerar o estudo.

- **G1 (P0):** Extrair deterministicamente registros das 5 categorias-alvo do XML Lattes — as 3 seções iniciais (`Formação Acadêmica/Titulação`, `Formação Complementar` e `Participação em Eventos`) mais `Apresentação de Trabalho` (`APRESENTACAO_TRABALHO`) e `Organização de Evento` (`ORGANIZACAO_EVENTO`) em `PRODUCAO-TECNICA/DEMAIS-TIPOS-DE-PRODUCAO-TECNICA` (`AD-012`) — com segurança (`defusedxml`), mantendo título, evento e papel separados (`AD-010`) e usando o XSD oficial do Extrator CNPq como referência estrutural principal e a DTD comunitária como comparação histórica (`AD-011`, sem presumir equivalência com a exportação da interface web nem encerrar o requisito de validação DTD do orientador).
- **G2 (P0):** Extrair entidades de PDFs e imagens via `google-genai` (Gemini) em JSON validado por JSON Schema e Pydantic v2, mantendo nome do evento, título específico e papel de participação separados e extraídos apenas quando explícitos (`AD-010`).
- **G3 (P0):** Classificar registros curriculares nas 3 classes (`Validado`, `Divergente` ou `Inconclusivo`) via motor determinístico (normalização, equivalência de siglas, regras temporais, comparação exata de carga horária em `Decimal` conforme `AD-009` e Levenshtein), tratando ausência de comprovante como `Inconclusivo / SEM_COMPROVANTE` (`AD-005`), associação ambígua como `Inconclusivo / ASSOCIACAO_AMBIGUA` com revisão humana posterior às métricas automáticas (`AD-007`) e documentos órfãos fora da matriz $3 \times 3$ como `DOCUMENTO_NAO_ASSOCIADO` (`AD-006`), reportando desempenho observado por classe e Macro-F1 com intervalo de confiança (`AD-008`), sem meta numérica de aprovação fixada sem justificativa. Método e nível do intervalo serão definidos no protocolo experimental.
- **G4 (P0):** Executar 3 experimentos reproduzíveis sobre bancada sintética controlada (proposta inicial de 30 casos piloto + ~90 casos finais; tamanho final, famílias e distribuição entre as 5 categorias permanecem pendentes de aprovação).

## Tech Stack

- **Core & API (`comprova-lattes-api`):** Python 3.11+, `defusedxml`, `pydantic` v2, `google-genai`, `fastapi`, `celery`, `redis`, `sqlalchemy` / `psycopg`.
- **Infraestrutura Local:** Docker Compose (`postgres:16-alpine` + `redis:7-alpine` + workers Celery).
- **Análise Experimental:** `pytest`, `pandas`, `scikit-learn`.
- **Frontend (`comprova-lattes-app`):** React, Vite, TypeScript, Tailwind CSS, React Router, TanStack Query.

## Scope

**Incluído (Ordem de Prioridade do Orientador):**
- **Ampliação aprovada pelo usuário (AD-012):** 5 categorias curriculares no escopo do MVP (`FORMACAO_ACADEMICA`, `FORMACAO_COMPLEMENTAR`, `PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO` e `ORGANIZACAO_EVENTO`), mantendo 3 classes de decisão (`Validado`, `Divergente`, `Inconclusivo`). A inclusão de apresentação de trabalho e organização de evento na produção técnica ocorre em entrega separada das três seções iniciais; a tabela de essencialidade/agregação e a avaliação experimental das novas categorias ainda precisam ser especificadas e aprovadas.
- **P0 (Núcleo & Experimentos):** Módulos Python independentes (`parser`, `extractor`, `matcher`, `experiments`), bancada sintética (proposta de 30 piloto + ~90 finais) e CLI de métricas.
- **P1 (Melhorias Científicas):** Baseline OCR (`Tesseract` + RegEx), Jaro-Winkler/tokens, Kappa de Cohen, bootstrap IC e teste de McNemar (parametrizações estatísticas em proposta).
- **P2 (Serviços & Web):** API FastAPI, fila assíncrona Celery/Redis, persistência PostgreSQL e interface web.

**Fora de escopo:**
- Decisão de validação feita pelo LLM (proibido, `AD-002`).
- Autenticação jurídica/forense de falsificação documental.
- Uso de currículos ou documentos pessoais reais de terceiros na bancada experimental.
- Extração de múltiplas atividades de um mesmo documento no MVP: o fluxo inicial usa um documento por atividade (`AD-004` em `STATE.md`).
- Artigos completos, resumos e trabalhos publicados em anais de eventos (`TRABALHO-EM-EVENTOS`, `AD-012`).

## Constraints

- **Regra de Ouro:** O LLM apenas extrai entidades; somente o motor determinístico classifica.
- **Isolamento de Dados:** Limiares calibrados nos 30 casos piloto e congelados antes dos ~90 casos finais.
- **Não-circularidade:** Documentos sintéticos gerados via templates HTML/DOCX (nunca gerados pelo próprio Gemini que será avaliado).
