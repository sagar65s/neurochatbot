"""
Gemini provider using Google's current recommended SDK: google-genai
(`from google import genai`). The old `google.generativeai` package is
deprecated and NOT used here.

Model name is fully configurable via GEMINI_MODEL — do not hardcode a
specific model, since Google periodically retires older ones. Get the
current list of supported model names from:
https://ai.google.dev/gemini-api/docs/models

NOTE on grounding: this provider does NOT use Gemini's built-in
google_search tool anymore. That was tried and turned out to be
inconsistent (search would sometimes run but return no citations, and
was Gemini-only anyway). Grounding is now handled uniformly for all
three providers at the route layer via Tavily search — see
app/services/tavily_search.py. Search results, when relevant, arrive
here as a normal system-role message already baked into `messages`, so
this provider just answers normally with no special-case logic, no
retries, and no added latency for grounded requests.
"""
from typing import AsyncIterator

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

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


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self):
        settings = get_settings()
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_model
        self._client: genai.Client | None = None

    def is_configured(self) -> bool:
        return bool(self._api_key and self._model)

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _to_gemini_contents(self, messages: list[ChatMessage]):
        """
        google-genai expects a list of content turns. We map our internal
        role names to Gemini's expected roles ("model" instead of
        "assistant"). System-role messages (including any Tavily search
        context) are folded into system_instruction rather than
        interleaved into contents.
        """
        contents = []
        for m in messages:
            if m.role == "system":
                continue
            role = "model" if m.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m.content}]})
        return contents

    def _system_instruction(self, messages: list[ChatMessage]) -> str | None:
        system_msgs = [m.content for m in messages if m.role == "system"]
        return "\n\n".join(system_msgs) if system_msgs else None

    def _build_config(self, messages: list[ChatMessage]) -> types.GenerateContentConfig:
        system_instruction = self._system_instruction(messages)
        kwargs = {}
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        return types.GenerateContentConfig(**kwargs)

    def _map_error(self, e: Exception) -> Exception:
        if isinstance(e, genai_errors.ClientError):
            status_code = getattr(e, "code", None)
            if status_code == 429:
                return RateLimitError("Gemini rate limit exceeded.")
            if status_code in (400, 401, 403):
                return InvalidRequestError(f"Gemini rejected the request: {e}")
            return ProviderUnavailableError(f"Gemini client error: {e}")
        if isinstance(e, genai_errors.ServerError):
            return ProviderUnavailableError(f"Gemini server error: {e}")
        return ProviderUnavailableError(f"Gemini unavailable: {e}")

    async def generate_response(self, messages: list[ChatMessage]) -> AIProviderResponse:
        if not self.is_configured():
            raise ProviderConfigError(
                "Gemini is not configured. Set GEMINI_API_KEY and GEMINI_MODEL."
            )

        client = self._get_client()
        contents = self._to_gemini_contents(messages)
        config = self._build_config(messages)

        try:
            response = client.models.generate_content(
                model=self._model, contents=contents, config=config,
            )
        except Exception as e:
            raise self._map_error(e) from e

        text = getattr(response, "text", None)
        if not text:
            raise ProviderUnavailableError("Gemini returned an empty response.")

        return AIProviderResponse(content=text, model_used=self._model, provider_used=self.name)

    async def generate_response_stream(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[StreamChunk]:
        if not self.is_configured():
            raise ProviderConfigError(
                "Gemini is not configured. Set GEMINI_API_KEY and GEMINI_MODEL."
            )

        client = self._get_client()
        contents = self._to_gemini_contents(messages)
        config = self._build_config(messages)

        try:
            stream = await client.aio.models.generate_content_stream(
                model=self._model, contents=contents, config=config,
            )
            async for chunk in stream:
                text = getattr(chunk, "text", None)
                if text:
                    yield StreamChunk(delta=text)
        except Exception as e:
            raise self._map_error(e) from e
