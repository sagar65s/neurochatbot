"""
Pydantic request/response models for the chat endpoints.
"""
from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str | None = Field(
        default=None,
        description="Existing conversation ID, or null to start a new one.",
    )
    message: str = Field(..., min_length=1, max_length=8000)


class CitationOut(BaseModel):
    title: str
    url: str


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    model_used: str | None = None
    provider_used: str | None = None
    citations: list[CitationOut] = Field(default_factory=list)
    created_at: datetime | None = None


class ChatResponse(BaseModel):
    conversation_id: str | None
    message: ChatMessageResponse
