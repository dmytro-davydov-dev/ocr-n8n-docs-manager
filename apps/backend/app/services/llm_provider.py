"""Provider-agnostic LLM abstraction (ADR-012).

ADR-012's decision is to target OpenAI-compatible APIs and let additional
providers (Anthropic via a compatible gateway, Azure OpenAI, Ollama, vLLM)
be used by pointing the *same* client at a different base URL/model —
"configured without changing business logic". `get_llm_provider()` is the
single place that knows which concrete implementation is active; callers
depend only on the `LlmProvider` protocol.
"""

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import settings

logger = logging.getLogger("app.llm_provider")


@dataclass(frozen=True)
class LlmCompletionResult:
    raw_content: str
    model_name: str


class LlmProvider(Protocol):
    provider_name: str
    model_name: str

    def complete_json(self, *, system_prompt: str, user_content: str) -> LlmCompletionResult: ...


class LlmProviderUnavailable(RuntimeError):
    """Terminal, operator-actionable: bad/missing provider configuration
    (ADR-008 — do not blindly retry deterministic config errors)."""


class LlmTransientError(RuntimeError):
    """Network/provider errors worth retrying (ADR-008)."""


class OpenAiCompatibleLlmProvider:
    """Talks to any OpenAI-compatible `/chat/completions` endpoint. Swapping
    OpenAI <-> Ollama <-> vLLM <-> Azure OpenAI is a matter of `LLM_BASE_URL`
    / `LLM_MODEL` / `LLM_API_KEY`, never a code change."""

    provider_name = "openai_compatible"

    def __init__(self) -> None:
        if not settings.llm_base_url:
            raise LlmProviderUnavailable(
                "LLM_PROVIDER=openai_compatible but LLM_BASE_URL is not configured"
            )
        self.model_name = settings.llm_model
        self._base_url = settings.llm_base_url.rstrip("/")
        self._api_key = settings.llm_api_key
        self._timeout = settings.llm_timeout_seconds

    def complete_json(self, *, system_prompt: str, user_content: str) -> LlmCompletionResult:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LlmTransientError(f"LLM request failed: {exc}") from exc

        body = response.json()
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LlmTransientError(f"Unexpected LLM response shape: {body}") from exc

        return LlmCompletionResult(raw_content=content, model_name=self.model_name)


class NullLlmProvider:
    """No-op provider for LLM_PROVIDER=null — lets the worker boot and the
    task be exercised without live model credentials. Must be explicitly
    configured, never a silent fallback for a missing base URL."""

    provider_name = "null"
    model_name = "null"

    def complete_json(self, *, system_prompt: str, user_content: str) -> LlmCompletionResult:
        return LlmCompletionResult(raw_content=json.dumps({}), model_name=self.model_name)


_PROVIDERS = {
    "openai_compatible": OpenAiCompatibleLlmProvider,
    "null": NullLlmProvider,
}


@lru_cache(maxsize=1)
def get_llm_provider() -> LlmProvider:
    provider_cls = _PROVIDERS.get(settings.llm_provider)
    if provider_cls is None:
        raise LlmProviderUnavailable(
            f"Unknown LLM_PROVIDER '{settings.llm_provider}'. Valid values: {sorted(_PROVIDERS)}"
        )
    return provider_cls()
