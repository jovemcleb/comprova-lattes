from celery import Celery

from comprova_lattes.config import settings

celery_app = Celery(
    "comprova_lattes",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Belem",
    enable_utc=True,
)


@celery_app.task(name="comprova_lattes.ping")
def ping_task() -> dict[str, str]:
    """Tarefa base de diagnóstico para validar conexão do worker Celery com o Redis."""
    return {"status": "pong"}


@celery_app.task(name="comprova_lattes.process_validation")
def process_validation_task(validation_id: str) -> dict[str, str]:
    """Executa M1 → M3 → M2; entregas duplicadas não sobrescrevem o snapshot."""
    from comprova_lattes.api.db import get_session_factory
    from comprova_lattes.api.service import process_validation

    return process_validation(validation_id, get_session_factory())
