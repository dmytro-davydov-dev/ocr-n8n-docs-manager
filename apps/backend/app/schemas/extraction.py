from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(field_name: str) -> str:
    first, *rest = field_name.split("_")
    return first + "".join(word.capitalize() for word in rest)


class ExtractedContractFields(BaseModel):
    """FR-302/303: the deterministic schema an LLM's JSON output must
    validate against before it is considered a successful extraction."""

    parties: list[str] = Field(default_factory=list)
    effective_date: str | None = None
    termination_date: str | None = None
    monetary_values: list[str] = Field(default_factory=list)
    key_clauses: list[str] = Field(default_factory=list)
    obligations: list[str] = Field(default_factory=list)


class ExtractionOut(BaseModel):
    """FR-307: extraction results retrievable through the API. FR-306/308:
    prompt and model version travel with every result."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        from_attributes=True,
        protected_namespaces=(),
    )

    document_id: str
    content: dict
    confidence_score: float
    prompt_id: str
    prompt_version: str
    model_provider: str
    model_name: str
    processing_timestamp: datetime
