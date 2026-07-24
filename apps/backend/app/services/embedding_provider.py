"""Provider-agnostic embedding abstraction (ADR-017). Same shape as
app/services/llm_provider.py: one OpenAI-compatible HTTP client, swapped by
config (`EMBEDDING_BASE_URL`/`EMBEDDING_MODEL`/`EMBEDDING_API_KEY`), plus a
`NullEmbeddingProvider` for environments without live credentials.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    model_name: str


class EmbeddingProvider(Protocol):
    provider_name: str
    model_name: str

    def embed(self, text: str) -> EmbeddingResult: ...


class EmbeddingProviderUnavailable(RuntimeError):
    """Terminal, operator-actionable: bad/missing provider configuration."""


class EmbeddingTransientError(RuntimeError):
    """Network/provider errors worth retrying (ADR-008)."""


class OpenAiCompatibleEmbeddingProvider:
    provider_name = "openai_compatible"

    def __init__(self) -> None:
        if not settings.embedding_base_url:
            raise EmbeddingProviderUnavailable(
                "EMBEDDING_PROVIDER=openai_compatible but EMBEDDING_BASE_URL is not configured"
            )
        self.model_name = settings.embedding_model
        self._base_url = settings.embedding_base_url.rstrip("/")
        self._api_key = settings.embedding_api_key
        self._timeout = settings.embedding_timeout_seconds

    def embed(self, text: str) -> EmbeddingResult:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            response = httpx.post(
                f"{self._base_url}/embeddings",
                headers=headers,
                json={"model": self.model_name, "input": text},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmbeddingTransientError(f"Embedding request failed: {exc}") from exc

        body = response.json()
        try:
            vector = body["data"][0]["embedding"]
        except (KeyError, IndexError) as exc:
            raise EmbeddingTransientError(f"Unexpected embedding response shape: {body}") from exc

        return EmbeddingResult(vector=vector, model_name=self.model_name)


class NullEmbeddingProvider:
    """No-op provider for EMBEDDING_PROVIDER=null."""

    provider_name = "null"
    model_name = "null"

    def embed(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(vector=[], model_name=self.model_name)


_PROVIDERS = {
    "openai_compatible": OpenAiCompatibleEmbeddingProvider,
    "null": NullEmbeddingProvider,
}


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    provider_cls = _PROVIDERS.get(settings.embedding_provider)
    if provider_cls is None:
        raise EmbeddingProviderUnavailable(
            f"Unknown EMBEDDING_PROVIDER '{settings.embedding_provider}'. Valid values: {sorted(_PROVIDERS)}"
        )
    return provider_cls()
