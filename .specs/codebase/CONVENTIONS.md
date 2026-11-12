# Convenções de Código e Estrutura

## Estrutura do Repositório

```text
tcc/
├── .specs/                     # Contexto para humanos e agentes (@tlc-spec-driven)
│   ├── project/
│   │   ├── PROJECT.md          # Visão, metas e escopo
│   │   ├── ROADMAP.md          # Marcos M0 a M6
│   │   └── STATE.md            # Decisões (AD) e questões em aberto (OPEN)
│   └── codebase/
│       ├── ARCHITECTURE.md     # Diagrama e divisão de módulos
│       ├── PROFESSOR-REQUIREMENTS.md # Checklist das exigências do orientador
│       └── CONVENTIONS.md      # Este arquivo
├── comprova-lattes-api/        # Backend Python 3.11+, Núcleo P0, FastAPI e Celery
│   ├── compose.yaml            # PostgreSQL 16 + Redis 7 + API + Celery Worker
│   ├── Dockerfile              # Imagem Python 3.12-slim para API e Worker
│   ├── pyproject.toml          # Dependências e configuração pytest/ruff
│   ├── src/comprova_lattes/    # Pacote principal Python
│   └── tests/                  # Testes automatizados (pytest)
└── comprova-lattes-app/        # Frontend React + Vite + TypeScript + Tailwind
```

## Padrões Python (`comprova-lattes-api`)

- **Versão:** Python 3.11+ (Docker padronizado em `python:3.12-slim`).
- **Tipagem:** Type hints obrigatórios em todas as assinaturas públicas; validação de dados com `Pydantic v2`.
- **Segurança XML:** Sempre importar `defusedxml.ElementTree` (nunca `xml.etree.ElementTree` para leitura de arquivos externos).
- **Testabilidade:** Funções do motor determinístico e do parser devem ser puras (recebem objetos/arquivos e retornam modelos Pydantic), sem depender de banco de dados ou Redis para rodar nos testes e nos scripts de experimento.
- **Idioma:** Nomes de variáveis/funções em inglês ou português consistente nos schemas de domínio acadêmico (`nome_titular`, `carga_horaria`, `instituicao_emissora`, conforme definido na seção 6.3 do TCC). Documentação e justificativas de auditoria em português.
