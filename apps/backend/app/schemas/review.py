from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


def _to_camel(field_name: str) -> str:
    first, *rest = field_name.split("_")
    return first + "".join(word.capitalize() for word in rest)


class ReviewSummary(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True, from_attributes=True)

    id: str
    document_id: str
    status: Literal["draft_review", "in_review", "approved", "rejected", "archived"]
    version: int
    content: dict[str, Any]
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class ReviewCreateRequest(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    content: dict[str, Any] = {}


class ReviewSaveDraftRequest(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    content: dict[str, Any]
    expected_version: int


class ReviewTransitionRequest(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    expected_version: int


class ReviewRejectRequest(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    expected_version: int
    reason: str


class ReviewRevisionSummary(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True, from_attributes=True)

    id: str
    version: int
    status: Literal["draft_review", "in_review", "approved", "rejected", "archived"]
    content: dict[str, Any]
    actor: str
    created_at: datetime
