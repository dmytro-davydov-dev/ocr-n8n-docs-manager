from datetime import datetime

from pydantic import BaseModel, ConfigDict


def _to_camel(field_name: str) -> str:
    first, *rest = field_name.split("_")
    return first + "".join(word.capitalize() for word in rest)


class OcrPageOut(BaseModel):
    """Mirrors `OcrPage` in packages/api-client/src/index.ts (ADR-011)."""

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True, from_attributes=True)

    document_id: str
    page_number: int
    extracted_text: str
    confidence_score: float
    processing_timestamp: datetime
    ocr_engine_version: str
