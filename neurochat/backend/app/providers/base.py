"""
Common interface every AI provider must implement. Grounding (Tavily
search) is now handled entirely at the route/service layer — search
results get injected into the conversation as a plain context message
before it ever reaches a provider. This means providers stay simple and
provider-agnostic: none of them need special grounding logic, tool
wiring, or retry loops. It also makes grounding work identically no
matter which provider in the fallback chain ends up answering.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class Citation:
    title: str
    url: str


@dataclass
class AIProviderResponse:
    content: str
    model_used: str
    provider_used: str
    citations: list[Citation] = field(default_factory=list)


@dataclass
class StreamChunk:
    delta: str = ""


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether this provider has the API key/config it needs to run."""
        raise NotImplementedError

    @abstractmethod
    async def generate_response(self, messages: list[ChatMessage]) -> AIProviderResponse:
        """
        Send messages to the provider and return its reply.
        Must raise one of app.providers.exceptions on failure — never a
        raw SDK exception — so the manager can reason about it.
        """
        raise NotImplementedError

    async def generate_response_stream(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[StreamChunk]:
        """
        Default fallback implementation: calls the non-streaming method and
        yields its full content as one chunk. Providers that support real
        token streaming override this for a genuinely progressive UI.
        """
        result = await self.generate_response(messages)
        yield StreamChunk(delta=result.content)
