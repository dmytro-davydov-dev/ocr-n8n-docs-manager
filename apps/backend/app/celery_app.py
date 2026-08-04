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

# worker_max_tasks_per_child: recycles a pool worker after N tasks instead of
# reusing it forever. Not load-bearing for the default OCR_ENGINE=tesseract
# path -- TesseractOcrEngine showed zero RSS growth over repeated calls
# (apps/backend/tests/test_ocr_engine.py), so there's no per-process leak
# left to recycle away there. It stays load-bearing for OCR_ENGINE=paddleocr,
# which remains a supported (if fragile, per ADR-010's addendum) config: its
# confirmed upstream native-allocator leak lives inside PaddlePaddle's C++
# runtime, below what gc.collect() (app/tasks/ocr.py) can reach, so a
# paddleocr-backed worker still accumulates RSS across tasks even after that
# mitigation. Recycling every 50 tasks bounds that accumulation to "50 tasks'
# worth of growth" instead of "until WORKER_MEMORY_LIMIT kills it", without
# meaningfully hurting steady-state throughput (PaddleOCR's own model-load
# cost, paid once per process, amortizes over 50 tasks; tesseract's is
# negligible either way). See docs/architecture/Progress.md.
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)


@celery_app.task(name="health.ping")
def ping() -> str:
    return "pong"


# Import task modules so they register with celery_app (ADR-008). Deferred
# to the bottom of the module to avoid a circular import: app/tasks/*
# imports celery_app itself to get the @celery_app.task decorator.
from app.tasks import embeddings, extraction, file_validation, ocr  # noqa: E402,F401
