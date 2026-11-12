from fastapi import FastAPI

from comprova_lattes import __version__
from comprova_lattes.config import settings

app = FastAPI(
    title="Comprova Lattes API",
    version=__version__,
    description="API de validação semiautomatizada do Currículo Lattes (TCC 2 - UFRA)",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "version": __version__,
        "environment": settings.environment,
        "gemini_model": settings.gemini_model,
    }
