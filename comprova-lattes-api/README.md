# Comprova Lattes API & Core (Python 3.11+)

Núcleo científico (P0) e API assíncrona (P2) do projeto de TCC 2.

**Estado atual:** M1–M6 implementados com verificação offline: parser de cinco categorias (AD-012), matcher determinístico, extrator Gemini com SDK simulado, experimentos sintéticos e API/worker com persistência e revisão humana AD-013. O gate M6 histórico tem 390 testes. Gates S2 e limites em [quality.md](../docs/quality.md). DTD oficial, calibração, anotação humana independente e avaliação científica continuam pendentes; PostgreSQL/Redis/Gemini/Tesseract reais não foram exercitados nos testes.

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

Os comandos de instalação/preparação acima não foram reexecutados na rodada S2; dependências existentes foram preservadas. O histórico do ambiente registra restrição no launcher da `.venv`; comandos efetivos e resultados estão em [quality.md](../docs/quality.md). Compose valida-se com `docker compose config --quiet`; isso não comprova serviços iniciados e não foi revalidado em S2.

## Experimentos e fluxo web

```powershell
python -m comprova_lattes.experiments --help
```

Consulte [experiments/README.md](src/comprova_lattes/experiments/README.md) para geração, calibração somente no piloto, congelamento e replay. São 25 casos por família, cinco categorias e cinco operadores; rótulos sintéticos e parâmetros de teste não são resultados científicos.

A API recebe XML e comprovantes em JSON/base64, exige MatcherConfig explícito e persiste o resultado automático separado dos pareceres humanos. TestClient/SQLite e dispatcher/extrator injetáveis verificam esse fluxo offline. O frontend e os contratos de uso estão no [README da interface](../comprova-lattes-app/README.md).
