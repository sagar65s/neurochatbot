from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.chat import CitationOut


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


class RenameConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    model_used: str | None = None
    provider_used: str | None = None
    citations: list[CitationOut] = Field(default_factory=list)
    created_at: datetime | None = None


class MessageListResponse(BaseModel):
    messages: list[MessageOut]
