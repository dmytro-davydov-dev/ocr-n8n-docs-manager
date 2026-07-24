from sqlalchemy.orm import Session

from app.repositories import audit_repository, chunk_repository


def record_chunk(
    db: Session,
    *,
    document_id: str,
    chunk_index: int,
    page_number: int,
    start_offset: int,
    end_offset: int,
    text: str,
    token_count: int,
    embedding: list[float],
    embedding_provider: str,
    embedding_model: str,
) -> None:
    """Idempotent per-chunk write, committed immediately so partial progress
    survives a mid-run failure/retry (ADR-008)."""
    chunk_repository.upsert_chunk(
        db,
        document_id=document_id,
        chunk_index=chunk_index,
        page_number=page_number,
        start_offset=start_offset,
        end_offset=end_offset,
        text=text,
        token_count=token_count,
        embedding=embedding,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
    )
    db.commit()


def record_completion(
    db: Session,
    *,
    document_id: str,
    chunk_count: int,
    embedding_provider: str,
    embedding_model: str,
    actor: str,
) -> None:
    """One audit entry per embedding run rather than one per chunk -- chunk
    counts can run into the hundreds, and the per-chunk write is already
    traceable via the chunk rows themselves (ADR-015)."""
    audit_repository.record(
        db,
        entity_type="document",
        entity_id=document_id,
        action="embeddings_generated",
        actor=actor,
        details={
            "chunk_count": chunk_count,
            "embedding_provider": embedding_provider,
            "embedding_model": embedding_model,
        },
    )
    db.commit()
