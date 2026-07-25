"""Hybrid search over indexed contract chunks (ADR-019).

Combines a lexical signal (substring/term-frequency match, portable across
Postgres and the SQLite test database) with a vector-similarity signal
(cosine similarity over the JSON-stored embeddings — see app/models/chunk.py
for why these aren't a native pgvector column yet) into one configurable
ranking, per FR-503/504/505.

FR-501 ("Approved contracts are indexed") is enforced here, not at
embedding time: `generate_embeddings` chunks/embeds a document as soon as
OCR/extraction finish (WS-03's pipeline), independent of review status, so
`searchable_chunks` is the single gate that decides what's actually
retrievable — only chunks belonging to a document with an `approved` review
are ever returned.
"""

import math
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.review import Review
from app.services.embedding_provider import EmbeddingProvider, get_embedding_provider


@dataclass(frozen=True)
class SearchHit:
    chunk: Chunk
    keyword_score: float
    vector_score: float
    score: float


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _keyword_score(text: str, query: str) -> float:
    terms = [t for t in query.lower().split() if t]
    if not terms:
        return 0.0
    text_lower = text.lower()
    hits = sum(text_lower.count(term) for term in terms)
    return min(hits / len(terms), 5.0) / 5.0


def searchable_chunks(db: Session) -> list[Chunk]:
    """Chunks belonging to documents whose review has been approved (FR-501)."""
    stmt = (
        select(Chunk)
        .join(Document, Chunk.document_id == Document.id)
        .join(Review, Review.document_id == Document.id)
        .where(Review.status == "approved")
    )
    return list(db.scalars(stmt).all())


def hybrid_search(
    db: Session,
    *,
    query: str,
    limit: int | None = None,
    embedding_provider: EmbeddingProvider | None = None,
) -> list[SearchHit]:
    chunks = searchable_chunks(db)
    if not chunks:
        return []

    provider = embedding_provider or get_embedding_provider()
    query_vector = provider.embed(query).vector

    hits: list[SearchHit] = []
    for chunk in chunks:
        keyword_score = _keyword_score(chunk.text, query)
        vector_score = _cosine_similarity(query_vector, chunk.embedding)
        score = settings.search_keyword_weight * keyword_score + settings.search_vector_weight * vector_score
        if keyword_score > 0 or vector_score > 0:
            hits.append(
                SearchHit(chunk=chunk, keyword_score=keyword_score, vector_score=vector_score, score=score)
            )

    hits.sort(key=lambda hit: hit.score, reverse=True)
    return hits[: limit or settings.search_default_limit]
