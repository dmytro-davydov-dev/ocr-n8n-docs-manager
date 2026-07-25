from pydantic import BaseModel, ConfigDict, Field


def _to_camel(field_name: str) -> str:
    first, *rest = field_name.split("_")
    return first + "".join(word.capitalize() for word in rest)


class SearchResultOut(BaseModel):
    """One ranked chunk from hybrid retrieval (ADR-019, FR-503/504/505)."""

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    document_id: str
    chunk_index: int
    page_number: int
    snippet: str
    keyword_score: float
    vector_score: float
    score: float


class ChatCitationOut(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True, from_attributes=True)

    document_id: str
    chunk_index: int
    page_number: int
    snippet: str
    score: float


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)


class ChatResponseOut(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    answer: str
    citations: list[ChatCitationOut]
    model: str
