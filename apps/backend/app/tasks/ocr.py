"""Phase 2 deliverable (WS-03): the OCR pipeline. Rasterizes each PDF page
and runs the configured OcrEngine (ADR-010) over it, persisting page-level
results (ADR-011) via the service layer as they complete.
"""

import logging

from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

from app.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.storage import storage
from app.repositories import document_repository
from app.services import ocr_service
from app.services.ocr_engine import OcrEngine, OcrEngineUnavailable, get_ocr_engine

logger = logging.getLogger("app.tasks.ocr")


@celery_app.task(
    name="documents.run_ocr",
    bind=True,
    max_retries=settings.ocr_max_retries,
    default_retry_delay=15,
    soft_time_limit=settings.ocr_soft_time_limit_seconds,
    time_limit=settings.ocr_time_limit_seconds,
)
def run_ocr(self, document_id: str, engine: OcrEngine | None = None) -> str:
    """Identifiers only in the payload (ADR-008); `engine` is a test-only
    injection seam and is never passed when the task is dispatched over
    the broker. Idempotent: only acts on documents in 'processing'; each
    page write is an upsert, so a retried/duplicated run overwrites rather
    than duplicates prior pages (ADR-008, ADR-011)."""
    db = SessionLocal()
    document = None
    try:
        document = document_repository.get(db, document_id)
        if document is None:
            logger.warning("run_ocr: document %s not found", document_id)
            return "not_found"

        if document.status == "complete":
            return "complete"
        if document.status != "processing":
            logger.info(
                "run_ocr: document %s not in 'processing' (is '%s'), skipping",
                document_id,
                document.status,
            )
            return document.status

        try:
            content = storage.read(document.storage_path)
        except OSError as exc:
            logger.warning("run_ocr: transient storage read failure for %s: %s", document_id, exc)
            try:
                raise self.retry(exc=exc)
            except MaxRetriesExceededError:
                logger.error(
                    "run_ocr: storage read failed for %s after %s retries, marking failed",
                    document_id,
                    self.max_retries,
                )
                document_repository.update_status(
                    db,
                    document,
                    new_status="failed",
                    actor="celery:run_ocr",
                    error_message=f"Storage read failed after {self.max_retries} retries: {exc}",
                )
                return "failed"

        try:
            active_engine = engine or get_ocr_engine()
        except OcrEngineUnavailable as exc:
            document_repository.update_status(
                db, document, new_status="failed", actor="celery:run_ocr", error_message=str(exc)
            )
            return "failed"

        try:
            import fitz  # PyMuPDF
        except ImportError:
            document_repository.update_status(
                db,
                document,
                new_status="failed",
                actor="celery:run_ocr",
                error_message="PDF rasterization dependency (PyMuPDF) is not installed",
            )
            return "failed"

        try:
            pdf = fitz.open(stream=content, filetype="pdf")
        except Exception as exc:
            document_repository.update_status(
                db,
                document,
                new_status="failed",
                actor="celery:run_ocr",
                error_message=f"Failed to open PDF for OCR: {exc}",
            )
            return "failed"

        try:
            zoom = settings.ocr_rasterize_dpi / 72
            matrix = fitz.Matrix(zoom, zoom)
            for page_index in range(pdf.page_count):
                page = pdf.load_page(page_index)
                pixmap = page.get_pixmap(matrix=matrix)
                image_bytes = pixmap.tobytes("png")

                try:
                    result = active_engine.recognize_page(image_bytes)
                except Exception as exc:
                    logger.warning(
                        "run_ocr: transient engine failure for %s page %s: %s",
                        document_id,
                        page_index + 1,
                        exc,
                    )
                    try:
                        raise self.retry(exc=exc)
                    except MaxRetriesExceededError:
                        logger.error(
                            "run_ocr: engine failed for %s page %s after %s retries, marking failed",
                            document_id,
                            page_index + 1,
                            self.max_retries,
                        )
                        document_repository.update_status(
                            db,
                            document,
                            new_status="failed",
                            actor="celery:run_ocr",
                            error_message=(
                                f"OCR engine failed on page {page_index + 1} after "
                                f"{self.max_retries} retries: {exc}"
                            ),
                        )
                        return "failed"

                ocr_service.record_page(
                    db,
                    document_id=document_id,
                    page_number=page_index + 1,
                    result=result,
                    engine_name=active_engine.engine_name,
                    engine_version=active_engine.engine_version,
                    actor="celery:run_ocr",
                )
        finally:
            pdf.close()

        document_repository.update_status(db, document, new_status="complete", actor="celery:run_ocr")
        return "complete"
    except SoftTimeLimitExceeded:
        logger.error("run_ocr: soft time limit exceeded for %s", document_id)
        if document is not None and document.status == "processing":
            document_repository.update_status(
                db,
                document,
                new_status="failed",
                actor="celery:run_ocr",
                error_message=(
                    f"run_ocr exceeded its {settings.ocr_soft_time_limit_seconds}s time limit"
                ),
            )
        return "failed"
    finally:
        db.close()
