# Comprova Lattes API & Core (Python 3.11+)

Núcleo científico (P0) e API assíncrona (P2) do projeto de TCC 2.

**Estado atual:** schemas e parser M1 implementados para cinco categorias (AD-012); motor, extrator, experimentos e fluxo de revisão humana ainda são planejados. API/worker possuem estrutura base; integração científica não está implementada. Gates e limites em [quality.md](../docs/quality.md).

## Estrutura de Módulos

- `src/comprova_lattes/parser/`: Parsing determinístico do XML Lattes com `defusedxml`.
- `src/comprova_lattes/extractor/`: Extração multimodal com `google-genai` validada por Pydantic/JSON Schema.
- `src/comprova_lattes/matcher/`: Motor determinístico de associação e classificação (`Validado`, `Divergente`, `Inconclusivo`).
- `src/comprova_lattes/experiments/`: Scripts da bancada experimental sintética e cálculo de métricas.
- `src/comprova_lattes/api/`: Endpoints FastAPI.
- `src/comprova_lattes/worker.py`: Configuração do Celery + Redis.

## 1. Subindo via Docker Compose (PostgreSQL + Redis + API + Celery)

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

- **Healthcheck API:** `http://localhost:8000/health`
- **Docs Swagger:** `http://localhost:8000/docs`
- **PostgreSQL:** `localhost:5432` (`comprova_lattes`)
- **Redis:** `localhost:6379`

## 2. Rodando Localmente (Para Desenvolvimento do Núcleo P0 e Testes)

Para executar parser e testes do núcleo, não é necessário iniciar PostgreSQL/Redis nem configurar Gemini. Depois de instalar Python 3.11+:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

python -m pytest
python -m ruff check .
```

Teste observado: 130 aprovados localmente e Ruff sem erros. Compose valida-se com `docker compose config --quiet`; isso não comprova serviços iniciados. Os comandos de instalação/preparação acima não foram reexecutados nesta atualização documental.
