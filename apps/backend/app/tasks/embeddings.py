"""Phase 5 deliverable (WS-03, RAG-pipeline slice only -- search/chat APIs
are out of this workstream's scope, see WS-03-Document-Processing-and-OCR.md
Out of Scope). Chunks a document's OCR text (ADR-018) and embeds each chunk
via the configured provider (ADR-017).
"""

import logging

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.repositories import chunk_repository, document_repository, ocr_repository
from app.services import embedding_service
from app.services.chunking import chunk_pages
from app.services.embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderUnavailable,
    EmbeddingTransientError,
    get_embedding_provider,
)

logger = logging.getLogger("app.tasks.embeddings")


@celery_app.task(name="documents.generate_embeddings", bind=True, max_retries=3, default_retry_delay=15)
def generate_embeddings(self, document_id: str, provider: EmbeddingProvider | None = None) -> str:
    """Identifiers only in the payload (ADR-008); `provider` is a test-only
    injection seam. Idempotent: chunking is deterministic given the same OCR
    pages/config, so re-running upserts the same chunk_index rather than
    duplicating (ADR-008), and any chunk left over from a prior run with a
    different config is dropped."""
    db = SessionLocal()
    try:
        document = document_repository.get(db, document_id)
        if document is None:
            logger.warning("generate_embeddings: document %s not found", document_id)
            return "not_found"

        if document.status != "complete":
            logger.info(
                "generate_embeddings: document %s not 'complete' (is '%s'), skipping",
                document_id,
                document.status,
            )
            return document.status

        pages = ocr_repository.list_for_document(db, document_id)
        if not pages:
            logger.warning("generate_embeddings: document %s has no OCR pages yet", document_id)
            return "no_ocr_pages"

        try:
            active_provider = provider or get_embedding_provider()
        except EmbeddingProviderUnavailable as exc:
            logger.error("generate_embeddings: %s", exc)
            return "provider_unavailable"

        chunks = chunk_pages(pages)

        for chunk in chunks:
            try:
                result = active_provider.embed(chunk.text)
            except EmbeddingTransientError as exc:
                logger.warning(
                    "generate_embeddings: transient failure for %s chunk %s: %s",
                    document_id,
                    chunk.chunk_index,
                    exc,
                )
                raise self.retry(exc=exc)

            embedding_service.record_chunk(
                db,
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                text=chunk.text,
                token_count=chunk.token_count,
                embedding=result.vector,
                embedding_provider=active_provider.provider_name,
                embedding_model=result.model_name,
            )

        chunk_repository.delete_from_index(db, document_id=document_id, from_chunk_index=len(chunks))
        db.commit()

        embedding_service.record_completion(
            db,
            document_id=document_id,
            chunk_count=len(chunks),
            embedding_provider=active_provider.provider_name,
            embedding_model=active_provider.model_name,
            actor="celery:generate_embeddings",
        )
        return "embedded"
    finally:
        db.close()
