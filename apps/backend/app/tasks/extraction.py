"""Phase 3 deliverable (WS-03): AI extraction. Turns a document's OCR text
into schema-validated structured JSON via the configured LLM provider
(ADR-012), recording the prompt/model version with the result (ADR-013).
"""

import json
import logging

from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
from pydantic import ValidationError

from app.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.repositories import document_repository, extraction_repository, ocr_repository
from app.schemas.extraction import ExtractedContractFields
from app.services import extraction_service
from app.services.llm_provider import (
    LlmProvider,
    LlmProviderUnavailable,
    LlmTransientError,
    get_llm_provider,
)
from app.services.prompts import load_contract_extraction_prompt

logger = logging.getLogger("app.tasks.extraction")


@celery_app.task(
    name="documents.extract_fields",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    soft_time_limit=settings.extract_fields_soft_time_limit_seconds,
    time_limit=settings.extract_fields_time_limit_seconds,
)
def extract_fields(self, document_id: str, provider: LlmProvider | None = None) -> str:
    """Identifiers only in the payload (ADR-008); `provider` is a test-only
    injection seam. Idempotent: only acts on documents that are 'complete'
    (OCR finished) and skips if already extracted with the current prompt
    version -- re-running after a prompt bump is a deliberate reprocess,
    which upserts rather than duplicates (ADR-008/013)."""
    db = SessionLocal()
    try:
        document = document_repository.get(db, document_id)
        if document is None:
            logger.warning("extract_fields: document %s not found", document_id)
            return "not_found"

        if document.status != "complete":
            logger.info(
                "extract_fields: document %s not 'complete' (is '%s'), skipping",
                document_id,
                document.status,
            )
            return document.status

        pages = ocr_repository.list_for_document(db, document_id)
        if not pages:
            logger.warning("extract_fields: document %s has no OCR pages yet", document_id)
            return "no_ocr_pages"

        prompt = load_contract_extraction_prompt()
        existing = extraction_repository.get_for_document(db, document_id)
        if (
            existing is not None
            and existing.prompt_id == prompt.prompt_id
            and existing.prompt_version == prompt.prompt_version
        ):
            return "already_extracted"

        try:
            active_provider = provider or get_llm_provider()
        except LlmProviderUnavailable as exc:
            logger.error("extract_fields: %s", exc)
            return "provider_unavailable"

        full_text = "\n\n".join(f"[Page {p.page_number}]\n{p.extracted_text}" for p in pages)

        try:
            completion = active_provider.complete_json(
                system_prompt=prompt.system_prompt, user_content=full_text
            )
        except LlmTransientError as exc:
            logger.warning("extract_fields: transient LLM failure for %s: %s", document_id, exc)
            try:
                raise self.retry(exc=exc)
            except MaxRetriesExceededError:
                # Note: document.status stays 'complete' here by design -- it
                # tracks the OCR stage only (see ALLOWED_TRANSITIONS, which
                # has no 'complete' -> 'failed' edge). Record the terminal
                # failure the same way a schema-validation failure is
                # recorded below, so it's visible via the audit trail /
                # extraction API instead of silently vanishing.
                logger.error(
                    "extract_fields: LLM failed for %s after %s retries, giving up",
                    document_id,
                    self.max_retries,
                )
                extraction_service.record_extraction_failure(
                    db,
                    document_id=document_id,
                    reason=f"LLM extraction failed after {self.max_retries} retries: {exc}",
                    actor="celery:extract_fields",
                )
                return "extraction_failed"

        try:
            parsed = json.loads(completion.raw_content)
            fields = ExtractedContractFields.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as exc:
            # FR-303/304: a schema-invalid response is deterministic for the
            # same input+prompt -- log and stop rather than retry blindly.
            logger.warning("extract_fields: validation failed for %s: %s", document_id, exc)
            extraction_service.record_extraction_failure(
                db, document_id=document_id, reason=str(exc), actor="celery:extract_fields"
            )
            return "validation_failed"

        # No OpenAI-compatible API returns a per-extraction confidence score,
        # so OCR page confidence stands in as a defensible proxy: extraction
        # quality is bounded by the quality of the text it was extracted from.
        page_confidences = [p.confidence_score for p in pages]
        confidence = sum(page_confidences) / len(page_confidences) if page_confidences else 0.0

        extraction_service.record_extraction(
            db,
            document_id=document_id,
            content=fields.model_dump(),
            confidence_score=confidence,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.prompt_version,
            model_provider=active_provider.provider_name,
            model_name=completion.model_name,
            actor="celery:extract_fields",
        )
        return "extracted"
    except SoftTimeLimitExceeded:
        logger.error("extract_fields: soft time limit exceeded for %s", document_id)
        extraction_service.record_extraction_failure(
            db,
            document_id=document_id,
            reason=f"extract_fields exceeded its {settings.extract_fields_soft_time_limit_seconds}s time limit",
            actor="celery:extract_fields",
        )
        return "extraction_failed"
    finally:
        db.close()
