from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "contract_review",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)


@celery_app.task(name="health.ping")
def ping() -> str:
    return "pong"


# Import task modules so they register with celery_app (ADR-008). Deferred
# to the bottom of the module to avoid a circular import: app/tasks/*
# imports celery_app itself to get the @celery_app.task decorator.
from app.tasks import embeddings, extraction, file_validation, ocr  # noqa: E402,F401
