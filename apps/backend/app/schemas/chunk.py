from datetime import datetime

from pydantic import BaseModel, ConfigDict


def _to_camel(field_name: str) -> str:
    first, *rest = field_name.split("_")
    return first + "".join(word.capitalize() for word in rest)


class ChunkOut(BaseModel):
    """RAG chunk + embedding metadata (ADR-016/017/018)."""

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True, from_attributes=True)

    document_id: str
    chunk_index: int
    page_number: int
    start_offset: int
    end_offset: int
    text: str
    token_count: int
    embedding_provider: str
    embedding_model: str
    updated_at: datetime
