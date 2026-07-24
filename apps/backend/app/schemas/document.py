from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


def _to_camel(field_name: str) -> str:
    first, *rest = field_name.split("_")
    return first + "".join(word.capitalize() for word in rest)


class DocumentSummary(BaseModel):
    """Mirrors `DocumentSummary` in packages/api-client/src/index.ts — the
    OpenAPI contract that WS-01's frontend is generated/mocked against."""

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True, from_attributes=True)

    id: str
    filename: str
    size_bytes: int
    status: Literal["uploaded", "queued", "processing", "complete", "failed"]
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None


class DocumentStatusUpdate(BaseModel):
    """Body for the internal status-callback endpoint n8n uses to report
    processing progress (WS-04 -> WS-02, ADR-009)."""

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    status: Literal["uploaded", "queued", "processing", "complete", "failed"]
    error_message: str | None = None
