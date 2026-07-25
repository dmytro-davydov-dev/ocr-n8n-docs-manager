"""RAG Q&A orchestration (ADR-020): query -> retrieval -> prompt
construction -> LLM -> citations -> response. n8n owns scheduling/observing
this as a workflow (ADR-020's "Consequences"); this module is the
backend-owned retrieval/business-logic piece that workflow calls into.

Citations are derived directly from the chunks retrieved and placed in the
prompt (`search_service.hybrid_search`), never parsed out of the LLM's own
output — this keeps every citation independently verifiable (FR-506)
instead of trusting the model to self-report its sources accurately.
"""

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.embedding_provider import EmbeddingProvider
from app.services.llm_provider import LlmProvider, get_llm_provider
from app.services.search_service import hybrid_search

RAG_SYSTEM_PROMPT = (
    "You are a contract-review assistant. Answer the user's question using ONLY the "
    "numbered context passages below, each drawn from an approved contract. If the "
    "passages do not contain the answer, say you don't know rather than guessing. "
    'Respond as JSON: {"answer": "<your answer>"}.'
)


@dataclass(frozen=True)
class Citation:
    document_id: str
    chunk_index: int
    page_number: int
    snippet: str
    score: float


@dataclass(frozen=True)
class ChatAnswer:
    answer: str
    citations: list[Citation]
    model: str


class NoIndexedContent(RuntimeError):
    """No approved, indexed chunk matched the question (FR-501 gate)."""


def _build_context(hits) -> str:
    return "\n\n".join(
        f"[{i + 1}] (document {hit.chunk.document_id}, page {hit.chunk.page_number}): {hit.chunk.text}"
        for i, hit in enumerate(hits)
    )


def answer_question(
    db: Session,
    *,
    question: str,
    limit: int | None = None,
    llm: LlmProvider | None = None,
    embedding_provider: EmbeddingProvider | None = None,
) -> ChatAnswer:
    hits = hybrid_search(
        db, query=question, limit=limit or settings.chat_context_chunks, embedding_provider=embedding_provider
    )
    if not hits:
        raise NoIndexedContent("No indexed, approved content matches this question")

    provider = llm or get_llm_provider()
    user_content = f"Context:\n{_build_context(hits)}\n\nQuestion: {question}"
    result = provider.complete_json(system_prompt=RAG_SYSTEM_PROMPT, user_content=user_content)

    try:
        parsed = json.loads(result.raw_content)
        answer_text = parsed.get("answer") or result.raw_content
    except (json.JSONDecodeError, AttributeError):
        answer_text = result.raw_content

    citations = [
        Citation(
            document_id=hit.chunk.document_id,
            chunk_index=hit.chunk.chunk_index,
            page_number=hit.chunk.page_number,
            snippet=hit.chunk.text[:280],
            score=round(hit.score, 4),
        )
        for hit in hits
    ]
    return ChatAnswer(answer=answer_text, citations=citations, model=result.model_name)
