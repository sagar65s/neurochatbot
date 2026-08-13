"""
OpenRouter provider. OpenRouter exposes an OpenAI-compatible REST endpoint,
so rather than pull in the full OpenAI SDK, we call it directly with
httpx. This keeps the provider implementation transparent and easy to
reason about.

Docs: https://openrouter.ai/docs/api/reference

Grounding note: this provider no longer has any special-case search
logic. Grounding (Tavily search) is handled once at the route layer for
all three providers uniformly — see app/services/tavily_search.py. When
relevant, search results arrive here as a normal system-role message
already baked into `messages`.
"""
import json
from typing import AsyncIterator

import httpx

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

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
REQUEST_TIMEOUT_SECONDS = 30.0


class OpenRouterProvider(AIProvider):
    name = "openrouter"

    def __init__(self):
        settings = get_settings()
        self._api_key = settings.openrouter_api_key
        self._model = settings.openrouter_model
        self._frontend_url = settings.frontend_url

    def is_configured(self) -> bool:
        return bool(self._api_key and self._model)

    def _to_openai_messages(self, messages: list[ChatMessage]) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in messages]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self._frontend_url,
            "X-Title": "NeuroChat",
        }

    def _raise_for_status(self, status_code: int, body_preview: str):
        if status_code == 429:
            raise RateLimitError("OpenRouter rate limit exceeded.")
        if status_code in (401, 403):
            raise InvalidRequestError("OpenRouter rejected the request (authentication/config).")
        if status_code == 400:
            raise InvalidRequestError(f"OpenRouter rejected the request: {body_preview[:200]}")
        if status_code >= 500:
            raise ProviderUnavailableError(f"OpenRouter server error (status={status_code}).")
        if status_code != 200:
            raise ProviderUnavailableError(f"OpenRouter unexpected status {status_code}.")

    async def generate_response(self, messages: list[ChatMessage]) -> AIProviderResponse:
        if not self.is_configured():
            raise ProviderConfigError(
                "OpenRouter is not configured. Set OPENROUTER_API_KEY and OPENROUTER_MODEL."
            )

        payload = {"model": self._model, "messages": self._to_openai_messages(messages)}

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(OPENROUTER_URL, json=payload, headers=self._headers())
        except httpx.TimeoutException as e:
            logger.warning("OpenRouter request timed out: %s", e)
            raise ProviderUnavailableError("OpenRouter request timed out.") from e
        except httpx.RequestError as e:
            logger.error("OpenRouter network error: %s", e)
            raise ProviderUnavailableError(f"OpenRouter network error: {e}") from e

        self._raise_for_status(response.status_code, response.text)

        data = response.json()

        if "error" in data:
            err = data["error"]
            message = err.get("message", "Unknown OpenRouter error")
            code = err.get("code")
            if code == 429:
                raise RateLimitError(message)
            raise ProviderUnavailableError(f"OpenRouter error: {message}")

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            logger.error("OpenRouter response missing expected fields: %s", data)
            raise ProviderUnavailableError("OpenRouter returned an unexpected response shape.") from e

        if not content:
            raise ProviderUnavailableError("OpenRouter returned an empty response.")

        return AIProviderResponse(
            content=content,
            model_used=data.get("model", self._model),
            provider_used=self.name,
        )

    async def generate_response_stream(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[StreamChunk]:
        if not self.is_configured():
            raise ProviderConfigError(
                "OpenRouter is not configured. Set OPENROUTER_API_KEY and OPENROUTER_MODEL."
            )

        payload = {
            "model": self._model,
            "messages": self._to_openai_messages(messages),
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                async with client.stream(
                    "POST", OPENROUTER_URL, json=payload, headers=self._headers()
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        self._raise_for_status(response.status_code, body.decode(errors="ignore"))

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[len("data: "):].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        if "error" in chunk:
                            err = chunk["error"]
                            if err.get("code") == 429:
                                raise RateLimitError(err.get("message", "Rate limited"))
                            raise ProviderUnavailableError(f"OpenRouter error: {err.get('message')}")

                        delta = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content")
                        )
                        if delta:
                            yield StreamChunk(delta=delta)
        except httpx.TimeoutException as e:
            raise ProviderUnavailableError("OpenRouter request timed out.") from e
        except httpx.RequestError as e:
            raise ProviderUnavailableError(f"OpenRouter network error: {e}") from e
