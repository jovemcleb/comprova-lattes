# Comprova Lattes — TCC 2 (BSI / UFRA)

Sistema semiautomatizado para validação do Currículo Lattes por meio do cruzamento determinístico entre dados nativos em XML e entidades extraídas de documentos comprobatórios (PDF/Imagem) via LLM multimodal (Google Gemini).

**Autores:** Caleb Cardoso Lima & Elivanilso Vidal Almeida Junior
**Orientador:** Prof. Dr. Fabrício Almeida Araújo

---

## Estado atual — 2026-11-13

**Atualização 2026-11-15:** modelo aprovado `gemini-3.5-flash-lite`, extração com
JSON Schema corrigido, relação nome/sigla documentada por campo e controle de
timeout/tentativas. Gate atual: 412 testes backend, Ruff e configuração Compose
aprovados. Sondagem real em cinco comprovantes sintéticos concluída; resultados e
limitações em [relatório](docs/gemini-model-probe-20261115.md). O estudo oficial e
a validação ponta a ponta dos serviços continuam pendentes. Histórico abaixo.

M1–M6 possuem implementação: parser seguro de cinco categorias, motor determinístico, extrator multimodal, bancada sintética/CLI, API assíncrona e interface de revisão humana AD-013. O gate histórico M6 reúne 390 testes backend e lint/build frontend; a rodada S2 e seus limites estão em [docs/quality.md](docs/quality.md). Testes offline usam SDK/extratores simulados e SQLite em memória. A exigência DTD do orientador, equivalência com XML da interface, calibração e estudo experimental oficial permanecem pendentes. PostgreSQL, Redis, Gemini e Tesseract reais não foram exercitados nesses gates.

O núcleo de parsing/testes funciona sem PostgreSQL, Redis ou Gemini. Gramáticas baixadas e legado do Drive são referências locais excluídas do Git; proveniência e instruções em [references/xml-grammars/README.md](references/xml-grammars/README.md).

## Mapa de Contexto (Para Desenvolvedores e Agentes de IA)

Este repositório utiliza o fluxo **Spec-Driven (`@tlc-spec-driven`)** com documentos curtos em `.specs/` para sincronizar contexto entre a dupla e agentes de IA:

- **[PROJECT.md](.specs/project/PROJECT.md)**: Visão geral, metas científicas (`G1`–`G4`), stack tecnológica e restrições.
- **[ROADMAP.md](.specs/project/ROADMAP.md)**: Plano incremental dividido nos marcos **M0 a M6** (priorizando `P0` → `P1` → `P2`).
- **[STATE.md](.specs/project/STATE.md)**: Decisões arquiteturais (`AD-001` a `AD-013`), minuta para a CTES (`ADMIN-01`) e **decisões em aberto (`OPEN-01` a `OPEN-04`)**.
- **[ARCHITECTURE.md](.specs/codebase/ARCHITECTURE.md)**: Diagrama em camadas e responsabilidade de cada módulo Python.
- **[PROFESSOR-REQUIREMENTS.md](.specs/codebase/PROFESSOR-REQUIREMENTS.md)**: Checklist técnico de código e experimentos extraído dos 88 comentários do orientador.
- **[MONOGRAPH-GUIDE.md](.specs/codebase/MONOGRAPH-GUIDE.md)**: Guia de revisão da monografia (capítulos, ABNT/UFRA, citações a trocar/incluir e trâmite CTES).
- **[COMENTARIOS-PROFESSOR-ORIGINAIS.md](docs/COMENTARIOS-PROFESSOR-ORIGINAIS.md)**: Transcrição integral dos 88 comentários do Prof. Dr. Fabrício no Word.
- **[CONVENTIONS.md](.specs/codebase/CONVENTIONS.md)**: Estrutura de pastas e padrões de código Python.

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

Consulte o [README da API](comprova-lattes-api/README.md) para instruções de execução local com `venv`/`pytest`.

A [interface React/Vite](comprova-lattes-app/README.md) permite anexar comprovantes incrementalmente e preencher um exemplo operacional explícito de MatcherConfig. Esse exemplo não representa calibração aprovada. A [CLI experimental](comprova-lattes-api/src/comprova_lattes/experiments/README.md) gera documentos fictícios e reproduz os três experimentos offline.
