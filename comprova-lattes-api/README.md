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

## 1. Subindo via Docker Compose (PostgreSQL + Redis + API + Celery + OCR)

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
```

Se as portas padrão já estiverem ocupadas por outro projeto, defina
`POSTGRES_PORT=55432` e `REDIS_PORT=56379` no `.env` antes de subir os serviços.
Essas variáveis alteram apenas as portas publicadas no computador; API e worker
continuam acessando `postgres:5432` e `redis:6379` dentro da rede Docker.
O serviço `api` tem healthcheck HTTP: container iniciado não garante aplicação
disponível. Confira `docker compose ps` e `http://localhost:8000/health`.

- **Healthcheck API:** `http://localhost:8000/health`
- **Docs Swagger:** `http://localhost:8000/docs`
- **OCR da revisão:** `http://127.0.0.1:8766/health` (Tesseract português no container)
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
## Configuração Gemini atual

Modelo aprovado: `gemini-3.5-flash-lite` (AD-015). Copie `.env.example` para
`.env` e preencha `GEMINI_API_KEY` localmente, sem publicar a chave. Preserve um
`.env` existente. Não é necessário instalar outro SDK além de `google-genai`,
já declarado em `pyproject.toml`.

`GEMINI_TIMEOUT_MS=120000` limita cada tentativa; `GEMINI_MAX_ATTEMPTS=2` inclui
a inicial. Erros temporários usam espera progressiva e tentativas são registradas
sem mensagens sensíveis. Gemini 3+ omite temperatura; o valor legado
`GEMINI_TEMPERATURE=0.0` não significa temperatura efetivamente controlada.

Extração usa `generateContent`, JSON Schema e validação Pydantic local. Sucesso
com cinco certificados fictícios não equivale a avaliação científica final.
Resultados e limitações: [sondagem de modelos](../docs/gemini-model-probe-20261115.md).


## OCR iniciado junto com a API

`docker compose up --build -d` também inicia `ocr`, sem precisar do terceiro terminal.
A imagem `Dockerfile.ocr` instala Tesseract + idioma português e dependências `.[ocr]`.
O OCR não recebe `.env`, chave Gemini, credenciais ou volumes de documentos. A porta
é publicada somente em `127.0.0.1:8766`, mantendo a URL usada pelo frontend.
O container usa `--container-bind --host 0.0.0.0` internamente; sem essa opção explícita,
a CLI continua aceitando apenas loopback. CORS e verificação de Host continuam locais.

Se você já iniciou o OCR pelo Python, encerre aquele terminal com Ctrl+C antes de
subir o container: ambos usam a porta8766. Para conferir:

```powershell
docker compose ps ocr
docker compose logs --tail 50 ocr
```

O healthcheck exige Tesseract/idioma disponíveis. `docker compose up --build -d ocr`
inicia somente o OCR, sem banco/Redis/API. O frontend continua com `npm run dev`.
Ambiente Linux do container pode reconhecer caracteres diferentemente do Windows;
registre versões de Tesseract/Pillow/PDFium no ambiente experimental antes do freeze.
