"""
Central orchestrator for all AI providers. Handles the fallback chain
(Gemini -> OpenRouter -> Groq by default, configurable via
AI_PROVIDER_ORDER) for both non-streaming and streaming requests.

Grounding (Tavily search) is handled entirely at the route layer before
this manager ever runs — search results, if any, are already baked into
the `messages` list as a system-role message. This manager itself has no
grounding-specific logic, which keeps the fallback chain simple, fast,
and identical in behavior regardless of which provider ends up
answering.

Streaming fallback rule: a provider can only be replaced by the next one
in the chain BEFORE it has yielded any content. Once a provider has
started streaming real tokens to the caller, a failure is reported as
StreamInterruptedError rather than silently retried on another provider.
"""
from typing import AsyncIterator

from app.config.settings import get_settings
from app.providers.base import AIProvider, AIProviderResponse, ChatMessage, StreamChunk
from app.providers.exceptions import (
    InvalidRequestError,
    ProviderConfigError,
    ProviderError,
)
from app.providers.gemini_provider import GeminiProvider
from app.providers.openrouter_provider import OpenRouterProvider
from app.providers.groq_provider import GroqProvider
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AllProvidersFailedError(Exception):
    """Raised when every configured provider in the chain failed."""


class StreamInterruptedError(Exception):
    """A provider failed mid-stream, after already sending content."""


class AIModelManager:
    def __init__(self):
        settings = get_settings()
        self._order = settings.provider_order_list

        self._registry: dict[str, AIProvider] = {
            "gemini": GeminiProvider(),
            "openrouter": OpenRouterProvider(),
            "groq": GroqProvider(),
        }

    def _active_chain(self) -> list[AIProvider]:
        """Providers in configured order, skipping ones with no registry entry."""
        return [
            self._registry[name]
            for name in self._order
            if name in self._registry
        ]

    async def generate_response(self, messages: list[ChatMessage]) -> AIProviderResponse:
        chain = self._active_chain()
        last_error: Exception | None = None

        for provider in chain:
            if not provider.is_configured():
                logger.info("Skipping provider=%s (not configured)", provider.name)
                continue

            try:
                logger.info("Trying provider=%s", provider.name)
                return await provider.generate_response(messages)
            except InvalidRequestError:
                # Not a provider-availability problem — retrying on another
                # provider won't help and could mask a real bug. Fail fast.
                raise
            except ProviderConfigError as e:
                logger.warning("Provider=%s misconfigured: %s", provider.name, e)
                last_error = e
                continue
            except ProviderError as e:
                logger.warning(
                    "Provider=%s failed, trying next in chain: %s", provider.name, e
                )
                last_error = e
                continue

        raise AllProvidersFailedError(
            str(last_error) if last_error else "No AI providers are configured."
        )

    async def generate_response_stream(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[tuple[StreamChunk, str]]:
        """
        Yields (StreamChunk, provider_name) tuples. Raises
        AllProvidersFailedError if every provider fails before yielding
        anything. Raises StreamInterruptedError if a provider fails after
        already streaming some content.
        """
        chain = self._active_chain()
        last_error: Exception | None = None

        for provider in chain:
            if not provider.is_configured():
                logger.info("Skipping provider=%s (not configured)", provider.name)
                continue

            started = False
            try:
                logger.info("Trying provider=%s (stream)", provider.name)
                async for chunk in provider.generate_response_stream(messages):
                    started = True
                    yield chunk, provider.name
                return  # stream completed successfully
            except InvalidRequestError:
                if started:
                    raise StreamInterruptedError(f"{provider.name} failed mid-stream.")
                raise
            except ProviderConfigError as e:
                if started:
                    raise StreamInterruptedError(f"{provider.name} failed mid-stream.")
                logger.warning("Provider=%s misconfigured: %s", provider.name, e)
                last_error = e
                continue
            except ProviderError as e:
                if started:
                    raise StreamInterruptedError(f"{provider.name} failed mid-stream: {e}")
                logger.warning(
                    "Provider=%s failed before streaming, trying next: %s", provider.name, e
                )
                last_error = e
                continue

        raise AllProvidersFailedError(
            str(last_error) if last_error else "No AI providers are configured."
        )


_manager: AIModelManager | None = None


def get_ai_model_manager() -> AIModelManager:
    global _manager
    if _manager is None:
        _manager = AIModelManager()
    return _manager
