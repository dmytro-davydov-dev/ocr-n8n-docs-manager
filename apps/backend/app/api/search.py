from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.search import ChatCitationOut, ChatRequest, ChatResponseOut, SearchResultOut
from app.services import rag_service, search_service

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[SearchResultOut])
def search(
    q: str = Query(..., min_length=1, alias="q"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[SearchResultOut]:
    """FR-503/504/505: hybrid keyword + semantic search over approved contracts."""
    hits = search_service.hybrid_search(db, query=q, limit=limit)
    return [
        SearchResultOut(
            document_id=hit.chunk.document_id,
            chunk_index=hit.chunk.chunk_index,
            page_number=hit.chunk.page_number,
            snippet=hit.chunk.text[:280],
            keyword_score=round(hit.keyword_score, 4),
            vector_score=round(hit.vector_score, 4),
            score=round(hit.score, 4),
        )
        for hit in hits
    ]


@router.post("/chat", response_model=ChatResponseOut)
def chat(body: ChatRequest, db: Session = Depends(get_db)) -> ChatResponseOut:
    """FR-506: AI Q&A grounded in approved contracts, with verifiable citations (ADR-020)."""
    try:
        result = rag_service.answer_question(db, question=body.question)
    except rag_service.NoIndexedContent as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ChatResponseOut(
        answer=result.answer,
        citations=[ChatCitationOut.model_validate(citation) for citation in result.citations],
        model=result.model,
    )
