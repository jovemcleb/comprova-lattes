# Comprova Lattes API & Core (Python 3.11+)

Núcleo científico (P0) e API assíncrona (P2) do projeto de TCC 2.

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

Você pode subir apenas o banco e o Redis no Docker e rodar o Python na máquina local:

```powershell
docker compose up -d postgres redis

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

pytest
```
