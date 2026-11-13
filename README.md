# Comprova Lattes — TCC 2 (BSI / UFRA)

Sistema semiautomatizado para validação do Currículo Lattes por meio do cruzamento determinístico entre dados nativos em XML e entidades extraídas de documentos comprobatórios (PDF/Imagem) via LLM multimodal (Google Gemini).

**Autores:** Caleb Cardoso Lima & Elivanilso Vidal Almeida Junior
**Orientador:** Prof. Dr. Fabrício Almeida Araújo

---

## Estado atual — 2026-11-13

Schemas e parser seguro de cinco categorias implementados no M1. Gate independente: **130 testes e Ruff aprovados localmente**, seis fixtures validadas offline contra o XSD do Extrator CNPq. A exigência DTD do orientador e equivalência com XML da interface permanecem pendentes. Motor, extrator, experimentos e fluxo web de revisão humana ainda não estão implementados. Evidências em [docs/quality.md](docs/quality.md).

O núcleo de parsing/testes funciona sem PostgreSQL, Redis ou Gemini. Gramáticas baixadas e legado do Drive são referências locais excluídas do Git; proveniência e instruções em [references/xml-grammars/README.md](references/xml-grammars/README.md).

## Mapa de Contexto (Para Desenvolvedores e Agentes de IA)

Este repositório utiliza o fluxo **Spec-Driven (`@tlc-spec-driven`)** com documentos curtos em `.specs/` para sincronizar contexto entre a dupla e agentes de IA:

- **[PROJECT.md](../../../../Caleb/dev/ufra-projects/tcc/.specs/project/PROJECT.md)**: Visão geral, metas científicas (`G1`–`G4`), stack tecnológica e restrições.
- **[ROADMAP.md](../../../../Caleb/dev/ufra-projects/tcc/.specs/project/ROADMAP.md)**: Plano incremental dividido nos marcos **M0 a M6** (priorizando `P0` → `P1` → `P2`).
- **[STATE.md](../../../../Caleb/dev/ufra-projects/tcc/.specs/project/STATE.md)**: Decisões arquiteturais (`AD-001` a `AD-013`), minuta para a CTES (`ADMIN-01`) e **decisões em aberto (`OPEN-01` a `OPEN-04`)**.
- **[ARCHITECTURE.md](../../../../Caleb/dev/ufra-projects/tcc/.specs/codebase/ARCHITECTURE.md)**: Diagrama em camadas e responsabilidade de cada módulo Python.
- **[PROFESSOR-REQUIREMENTS.md](../../../../Caleb/dev/ufra-projects/tcc/.specs/codebase/PROFESSOR-REQUIREMENTS.md)**: Checklist técnico de código e experimentos extraído dos 88 comentários do orientador.
- **[MONOGRAPH-GUIDE.md](../../../../Caleb/dev/ufra-projects/tcc/.specs/codebase/MONOGRAPH-GUIDE.md)**: Guia de revisão da monografia (capítulos, ABNT/UFRA, citações a trocar/incluir e trâmite CTES).
- **[COMENTARIOS-PROFESSOR-ORIGINAIS.md](../../../../Caleb/dev/ufra-projects/tcc/docs/COMENTARIOS-PROFESSOR-ORIGINAIS.md)**: Transcrição integral dos 88 comentários do Prof. Dr. Fabrício no Word.
- **[CONVENTIONS.md](../../../../Caleb/dev/ufra-projects/tcc/.specs/codebase/CONVENTIONS.md)**: Estrutura de pastas e padrões de código Python.

---

## Como Iniciar o Ambiente Base (API + Banco + Celery)

A infraestrutura base (PostgreSQL 16 + Redis 7 + FastAPI + Celery Worker) fica em `comprova-lattes-api/`:

```powershell
cd comprova-lattes-api
Copy-Item .env.example .env

# Subir apenas Banco e Redis (para rodar Python localmente):
docker compose up -d postgres redis

# Ou subir tudo (Banco + Redis + API FastAPI + Celery Worker):
docker compose up --build -d
```

Consulte o [README da API](../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/README.md) para instruções de execução local com `venv`/`pytest`.
