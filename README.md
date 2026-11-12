# Comprova Lattes — TCC 2 (BSI / UFRA)

Sistema semiautomatizado para validação do Currículo Lattes por meio do cruzamento determinístico entre dados nativos em XML e entidades extraídas de documentos comprobatórios (PDF/Imagem) via LLM multimodal (Google Gemini).

**Autores:** Caleb Cardoso Lima & Elivanilso Vidal Almeida Junior  
**Orientador:** Prof. Dr. Fabrício Almeida Araújo

---

## Mapa de Contexto (Para Desenvolvedores e Agentes de IA)

Este repositório utiliza o fluxo **Spec-Driven (`@tlc-spec-driven`)** com documentos curtos em `.specs/` para sincronizar contexto entre a dupla e agentes de IA:

- **[PROJECT.md](file:///c:/Users/Caleb/dev/ufra-projects/tcc/.specs/project/PROJECT.md)**: Visão geral, metas científicas (G1–G4), stack tecnológica e restrições.
- **[ROADMAP.md](file:///c:/Users/Caleb/dev/ufra-projects/tcc/.specs/project/ROADMAP.md)**: Plano incremental dividido nos marcos **M0 a M6** (priorizando P0 → P1 → P2).
- **[STATE.md](file:///c:/Users/Caleb/dev/ufra-projects/tcc/.specs/project/STATE.md)**: Decisões arquiteturais tomadas (`AD-001` a `AD-003`) e **decisões/perguntas em aberto (`OPEN-01` a `OPEN-04`)** para alinhamento da dupla.
- **[ARCHITECTURE.md](file:///c:/Users/Caleb/dev/ufra-projects/tcc/.specs/codebase/ARCHITECTURE.md)**: Diagrama em camadas e responsabilidade de cada módulo Python.
- **[PROFESSOR-REQUIREMENTS.md](file:///c:/Users/Caleb/dev/ufra-projects/tcc/.specs/codebase/PROFESSOR-REQUIREMENTS.md)**: Checklist técnico extraído diretamente dos comentários do orientador.
- **[CONVENTIONS.md](file:///c:/Users/Caleb/dev/ufra-projects/tcc/.specs/codebase/CONVENTIONS.md)**: Estrutura de pastas e padrões de código Python.

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

Consulte o [README da API](file:///c:/Users/Caleb/dev/ufra-projects/tcc/comprova-lattes-api/README.md) para instruções de execução local com `venv`/`pytest`.
