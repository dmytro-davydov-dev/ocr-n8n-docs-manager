from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "contract_review",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# ADR-008 named "worker crash during processing" as a risk to mitigate with
# "late acknowledgement where appropriate" -- this was never actually
# configured. Celery's default is to ack a task as soon as it's *received*,
# before it runs. If the worker child is killed mid-task (observed in
# practice: the OOM killer SIGKILLing a ForkPoolWorker mid-OCR -- SIGKILL
# can't be caught in Python, so no task-level try/except can ever run for
# this), the message is already gone from the broker with acks_late off:
# Celery surfaces a WorkerLostError in its own logs, but nothing ever
# re-attempts the task, so the document is stranded in whatever status it
# was last written to with zero further activity (indistinguishable from a
# hang, but not fixable by the task-level MaxRetriesExceededError/
# SoftTimeLimitExceeded handling in app/tasks/*, since the process never got
# a chance to run any of that code). late-ack + reject_on_worker_lost
# requeues the message for another attempt instead of silently dropping it.
# Safe here because every pipeline task is already idempotent (re-checks the
# document's current status before acting -- ADR-008/009). prefetch=1 is the
# standard pairing so one worker doesn't hoard several long-running unacked
# OCR tasks while others sit idle.
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(name="health.ping")
def ping() -> str:
    return "pong"


# Import task modules so they register with celery_app (ADR-008). Deferred
# to the bottom of the module to avoid a circular import: app/tasks/*
# imports celery_app itself to get the @celery_app.task decorator.
from app.tasks import embeddings, extraction, file_validation, ocr  # noqa: E402,F401
