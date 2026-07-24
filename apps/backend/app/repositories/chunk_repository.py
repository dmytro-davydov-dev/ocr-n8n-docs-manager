from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk


def upsert_chunk(
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
) -> Chunk:
    """Idempotent write, mirroring ocr_repository.upsert_page: safe under
    Celery's at-least-once delivery (ADR-008)."""
    existing = db.scalar(
        select(Chunk).where(Chunk.document_id == document_id, Chunk.chunk_index == chunk_index)
    )

    if existing is not None:
        existing.page_number = page_number
        existing.start_offset = start_offset
        existing.end_offset = end_offset
        existing.text = text
        existing.token_count = token_count
        existing.embedding = embedding
        existing.embedding_provider = embedding_provider
        existing.embedding_model = embedding_model
        db.add(existing)
        db.flush()
        return existing

    chunk = Chunk(
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
    db.add(chunk)
    db.flush()
    return chunk


def list_for_document(db: Session, document_id: str) -> list[Chunk]:
    stmt = select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index.asc())
    return list(db.scalars(stmt).all())


def delete_from_index(db: Session, *, document_id: str, from_chunk_index: int) -> None:
    """Drop any chunks at/after `from_chunk_index`: if re-chunking (e.g. a
    config change) now produces fewer chunks than a prior run, the tail of
    the previous run must not linger as stale, unreferenced chunks."""
    db.execute(
        delete(Chunk).where(Chunk.document_id == document_id, Chunk.chunk_index >= from_chunk_index)
    )
