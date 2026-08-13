"""
Groq provider using the official `groq` Python SDK (OpenAI-shaped client).

IMPORTANT: Groq deprecates model IDs periodically. GROQ_MODEL is fully
configurable and intentionally has no hardcoded default. Check
https://console.groq.com/docs/models before setting it.

Grounding note: this provider no longer has any special-case search or
caution-note logic. Grounding (Tavily search) is handled once at the
route layer for all three providers uniformly — see
app/services/tavily_search.py. When relevant, search results arrive here
as a normal system-role message already baked into `messages`, so Groq
answers using that context like any other instruction.
"""
from typing import AsyncIterator

from groq import Groq
from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    RateLimitError as GroqRateLimitError,
)

from app.config.settings import get_settings
from app.providers.base import AIProvider, AIProviderResponse, ChatMessage, StreamChunk
from app.providers.exceptions import (
    InvalidRequestError,
    ProviderConfigError,
    ProviderUnavailableError,
    RateLimitError,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class GroqProvider(AIProvider):
    name = "groq"

    def __init__(self):
        settings = get_settings()
        self._api_key = settings.groq_api_key
        self._model = settings.groq_model
        self._client: Groq | None = None

    def is_configured(self) -> bool:
        return bool(self._api_key and self._model)

    def _get_client(self) -> Groq:
        if self._client is None:
            self._client = Groq(api_key=self._api_key)
        return self._client

    def _to_groq_messages(self, messages: list[ChatMessage]) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in messages]

    def _map_error(self, e: Exception) -> Exception:
        if isinstance(e, GroqRateLimitError):
            return RateLimitError("Groq rate limit exceeded.")
        if isinstance(e, AuthenticationError):
            return InvalidRequestError("Groq rejected the request (authentication).")
        if isinstance(e, BadRequestError):
            return InvalidRequestError(f"Groq rejected the request: {e}")
        if isinstance(e, APITimeoutError):
            return ProviderUnavailableError("Groq request timed out.")
        if isinstance(e, APIConnectionError):
            return ProviderUnavailableError(f"Groq network error: {e}")
        if isinstance(e, APIStatusError):
            if e.status_code >= 500:
                return ProviderUnavailableError(f"Groq server error (status={e.status_code}).")
            return InvalidRequestError(f"Groq rejected the request (status={e.status_code}).")
        return ProviderUnavailableError(f"Groq unavailable: {e}")

    async def generate_response(self, messages: list[ChatMessage]) -> AIProviderResponse:
        if not self.is_configured():
            raise ProviderConfigError("Groq is not configured. Set GROQ_API_KEY and GROQ_MODEL.")

        client = self._get_client()
        try:
            completion = client.chat.completions.create(
                model=self._model, messages=self._to_groq_messages(messages),
            )
        except Exception as e:
            raise self._map_error(e) from e

        try:
            content = completion.choices[0].message.content
        except (IndexError, AttributeError) as e:
            raise ProviderUnavailableError("Groq returned an unexpected response shape.") from e

        if not content:
            raise ProviderUnavailableError("Groq returned an empty response.")

        return AIProviderResponse(
            content=content,
            model_used=getattr(completion, "model", self._model),
            provider_used=self.name,
        )

    async def generate_response_stream(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[StreamChunk]:
        if not self.is_configured():
            raise ProviderConfigError("Groq is not configured. Set GROQ_API_KEY and GROQ_MODEL.")

        client = self._get_client()
        try:
            stream = client.chat.completions.create(
                model=self._model,
                messages=self._to_groq_messages(messages),
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield StreamChunk(delta=delta)
        except Exception as e:
            raise self._map_error(e) from e
