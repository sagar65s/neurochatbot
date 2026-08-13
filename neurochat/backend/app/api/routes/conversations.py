from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.auth import get_current_user_id
from app.schemas.conversation import (
    ConversationListResponse,
    ConversationSummary,
    MessageListResponse,
    MessageOut,
    RenameConversationRequest,
)
from app.services import conversation_service as svc
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/api/conversations", response_model=ConversationListResponse)
async def get_conversations(user_id: str = Depends(get_current_user_id)):
    conversations = svc.list_conversations(user_id)
    return ConversationListResponse(
        conversations=[
            ConversationSummary(
                id=c["id"],
                title=c.get("title", "New chat"),
                created_at=c.get("createdAt"),
                updated_at=c.get("updatedAt"),
            )
            for c in conversations
        ]
    )


@router.get("/api/conversations/{conversation_id}", response_model=ConversationSummary)
async def get_conversation(conversation_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        c = svc.get_conversation_or_raise(conversation_id, user_id)
    except svc.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    except svc.ConversationAccessDeniedError:
        raise HTTPException(status_code=403, detail="You are not authorized to access this conversation.")

    return ConversationSummary(
        id=c["id"], title=c.get("title", "New chat"),
        created_at=c.get("createdAt"), updated_at=c.get("updatedAt"),
    )


@router.patch("/api/conversations/{conversation_id}", response_model=ConversationSummary)
async def rename_conversation(
    conversation_id: str,
    payload: RenameConversationRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        c = svc.rename_conversation(conversation_id, user_id, payload.title)
    except svc.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    except svc.ConversationAccessDeniedError:
        raise HTTPException(status_code=403, detail="You are not authorized to access this conversation.")

    return ConversationSummary(
        id=c["id"], title=c.get("title", "New chat"),
        created_at=c.get("createdAt"), updated_at=c.get("updatedAt"),
    )


@router.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        svc.delete_conversation(conversation_id, user_id)
    except svc.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    except svc.ConversationAccessDeniedError:
        raise HTTPException(status_code=403, detail="You are not authorized to access this conversation.")

    return {"deleted": True}


@router.get(
    "/api/conversations/{conversation_id}/messages", response_model=MessageListResponse
)
async def get_messages(conversation_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        messages = svc.list_messages(conversation_id, user_id)
    except svc.ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    except svc.ConversationAccessDeniedError:
        raise HTTPException(status_code=403, detail="You are not authorized to access this conversation.")

    return MessageListResponse(
        messages=[
            MessageOut(
                id=m["id"],
                role=m["role"],
                content=m["content"],
                model_used=m.get("modelUsed"),
                provider_used=m.get("providerUsed"),
                citations=m.get("citations") or [],
                created_at=m.get("createdAt"),
            )
            for m in messages
        ]
    )
