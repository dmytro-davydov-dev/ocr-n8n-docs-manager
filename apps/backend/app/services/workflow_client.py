import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("app.workflow_client")


def trigger_document_workflow(document_id: str) -> bool:
    """Best-effort trigger of the n8n ingestion workflow (FR-105, ADR-009).

    Idempotent on the n8n side by contract (n8n keys its workflow run on
    `document_id`). A failure here must not fail the upload — the document
    stays in `uploaded` and processing can be retried/observed separately;
    it is logged so operators can see missed triggers.
    """
    if not settings.n8n_webhook_url:
        logger.warning("N8N_WEBHOOK_URL not configured; skipping workflow trigger for %s", document_id)
        return False

    try:
        response = httpx.post(
            settings.n8n_webhook_url,
            json={"document_id": document_id},
            timeout=settings.n8n_webhook_timeout_seconds,
        )
        response.raise_for_status()
        return True
    except httpx.HTTPError:
        logger.exception("Failed to trigger n8n workflow for document %s", document_id)
        return False
