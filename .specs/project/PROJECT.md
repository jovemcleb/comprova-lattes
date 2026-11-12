# Comprova Lattes (TCC 2 - UFRA)

**Vision:** Protótipo cientificamente avaliável de validação semiautomatizada do Currículo Lattes, cruzando dados nativos em XML com informações extraídas de documentos comprobatórios via LLM multimodal.
**For:** Comissões avaliadoras, pesquisadores e banca examinadora do TCC 2 (Sistemas de Informação - UFRA).
**Solves:** Reduz a conferência manual de documentos heterogêneos mantendo rastreabilidade por campo e separando estritamente a extração (LLM) da decisão algorítmica.

## Goals

- **G1 (P0):** Extrair deterministicamente 3 seções do XML Lattes (`Formação Acadêmica/Titulação`, `Formação Complementar` e `Participação em Eventos`) com segurança (`defusedxml` + validação DTD).
- **G2 (P0):** Extrair entidades de PDFs e imagens via `google-genai` (Gemini) em JSON validado por JSON Schema e Pydantic v2.
- **G3 (P0):** Classificar registros em `Validado`, `Divergente` ou `Inconclusivo` via motor determinístico (normalização, equivalência de siglas, regras temporais/numéricas e Levenshtein), alcançando meta experimental de $\text{Macro-F1} \ge 0{,}85$.
- **G4 (P0):** Executar 3 experimentos reproduzíveis sobre bancada sintética controlada (30 casos piloto + ~90 casos finais).

## Tech Stack

- **Core & API (`comprova-lattes-api`):** Python 3.11+, `defusedxml`, `pydantic` v2, `google-genai`, `fastapi`, `celery`, `redis`, `sqlalchemy` / `psycopg`.
- **Infraestrutura Local:** Docker Compose (`postgres:16-alpine` + `redis:7-alpine` + workers Celery).
- **Análise Experimental:** `pytest`, `pandas`, `scikit-learn`.
- **Frontend (`comprova-lattes-app`):** React, Vite, TypeScript, Tailwind CSS, React Router, TanStack Query.

## Scope

**Incluído (Ordem de Prioridade do Orientador):**
- **P0 (Núcleo & Experimentos):** Módulos Python independentes (`parser`, `extractor`, `matcher`, `experiments`), bancada sintética (30 piloto + 90 finais) e CLI de métricas.
- **P1 (Melhorias Científicas):** Baseline OCR (`Tesseract` + RegEx), Jaro-Winkler/tokens, Kappa de Cohen, bootstrap IC e teste de McNemar.
- **P2 (Serviços & Web):** API FastAPI, fila assíncrona Celery/Redis, persistência PostgreSQL e interface web.

**Fora de escopo:**
- Decisão de validação feita pelo LLM (proibido).
- Autenticação jurídica/forense de falsificação documental.
- Uso de currículos ou documentos pessoais reais de terceiros na bancada experimental.

## Constraints

- **Regra de Ouro:** O LLM apenas extrai entidades; somente o motor determinístico classifica.
- **Isolamento de Dados:** Limiares calibrados nos 30 casos piloto e congelados antes dos ~90 casos finais.
- **Não-circularidade:** Documentos sintéticos gerados via templates HTML/DOCX (nunca gerados pelo próprio Gemini que será avaliado).
