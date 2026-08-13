"""
Chat routes: POST /api/chat (non-streaming) and POST /api/chat/stream
(Server-Sent Events). Both:
  1. Are rate-limited per user (rate_limit_chat, which wraps
     get_current_user_id so auth always runs first).
  2. Resolve/create the conversation and verify ownership.
  3. Save the user's message to Firestore.
  4. Load bounded conversation history.
  5. Decide whether this question needs live web grounding (should_ground),
     and if so, run ONE Tavily search and inject the results as context —
     this works identically no matter which provider ends up answering,
     unlike relying on a specific provider's own search tool.
  6. Call the AI Model Manager (Gemini -> OpenRouter -> Groq fallback).
  7. Save the assistant's reply (with any citations + timestamp) and bump
     conversation.updatedAt.
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.dependencies.rate_limit import rate_limit_chat
from app.providers.base import ChatMessage, Citation
from app.providers.exceptions import InvalidRequestError
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessageResponse, CitationOut
from app.services import conversation_service as svc
from app.services.ai_model_manager import (
    AllProvidersFailedError,
    StreamInterruptedError,
    get_ai_model_manager,
)
from app.services.grounding import should_ground
from app.services.tavily_search import search_web, build_context_message, results_to_citations
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


def _resolve_conversation(payload: ChatRequest, user_id: str) -> str:
    if payload.conversation_id:
        try:
            svc.get_conversation_or_raise(payload.conversation_id, user_id)
        except svc.ConversationNotFoundError:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        except svc.ConversationAccessDeniedError:
            raise HTTPException(
                status_code=403, detail="You are not authorized to access this conversation."
            )
        return payload.conversation_id
    conversation = svc.create_conversation(user_id, payload.message)
    return conversation["id"]


def _citations_to_dicts(citations: list[Citation]) -> list[dict]:
    return [{"title": c.title, "url": c.url} for c in citations]


async def _maybe_ground(message: str, history: list[ChatMessage]) -> list[Citation]:
    """
    If the message needs live info, runs one Tavily search and appends
    the results to `history` in place as a system-role context message.
    Returns the citations (empty list if grounding wasn't needed, or the
    search returned nothing).
    """
    if not should_ground(message):
        return []

    results = await search_web(message)
    if not results:
        return []

    history.append(ChatMessage(role="system", content=build_context_message(results)))
    return results_to_citations(results)


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, user_id: str = Depends(rate_limit_chat)):
    conversation_id = _resolve_conversation(payload, user_id)
    svc.add_message(conversation_id, user_id, role="user", content=payload.message)
    history: list[ChatMessage] = svc.load_history_for_ai(conversation_id)

    citations = await _maybe_ground(payload.message, history)

    manager = get_ai_model_manager()
    try:
        result = await manager.generate_response(history)
    except InvalidRequestError:
        raise HTTPException(
            status_code=400, detail="Your message could not be processed. Please rephrase it."
        )
    except AllProvidersFailedError:
        logger.error("All AI providers failed for user_id=%s", user_id)
        raise HTTPException(
            status_code=503,
            detail="All AI providers are currently unavailable. Please try again shortly.",
        )

    citation_dicts = _citations_to_dicts(citations)
    saved = svc.add_message(
        conversation_id, user_id, role="assistant",
        content=result.content, model_used=result.model_used,
        provider_used=result.provider_used, citations=citation_dicts,
    )
    svc.touch_conversation(conversation_id)

    return ChatResponse(
        conversation_id=conversation_id,
        message=ChatMessageResponse(
            role="assistant", content=result.content,
            model_used=result.model_used, provider_used=result.provider_used,
            citations=[CitationOut(**c) for c in citation_dicts],
            created_at=saved.get("createdAt"),
        ),
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, user_id: str = Depends(rate_limit_chat)):
    conversation_id = _resolve_conversation(payload, user_id)
    svc.add_message(conversation_id, user_id, role="user", content=payload.message)
    history: list[ChatMessage] = svc.load_history_for_ai(conversation_id)

    # Search happens once, up front, before streaming starts — so
    # citations are known immediately rather than trickling in mid-stream.
    citations = await _maybe_ground(payload.message, history)
    citation_dicts = _citations_to_dicts(citations)

    async def event_generator():
        yield _sse("meta", {"conversation_id": conversation_id})
        if citation_dicts:
            yield _sse("citations", {"citations": citation_dicts})

        manager = get_ai_model_manager()
        accumulated = ""
        provider_used = None

        try:
            async for chunk, provider_name in manager.generate_response_stream(history):
                provider_used = provider_name
                if chunk.delta:
                    accumulated += chunk.delta
                    yield _sse("chunk", {"delta": chunk.delta})
        except InvalidRequestError:
            yield _sse("error", {"message": "Your message could not be processed. Please rephrase it."})
            return
        except AllProvidersFailedError:
            logger.error("All AI providers failed (stream) for user_id=%s", user_id)
            yield _sse(
                "error",
                {"message": "All AI providers are currently unavailable. Please try again shortly."},
            )
            return
        except StreamInterruptedError as e:
            logger.error("Stream interrupted for user_id=%s: %s", user_id, e)
            if accumulated:
                svc.add_message(
                    conversation_id, user_id, role="assistant",
                    content=accumulated, model_used=None,
                    provider_used=provider_used, citations=citation_dicts,
                )
                svc.touch_conversation(conversation_id)
            yield _sse("error", {"message": "The response was interrupted. Please try again."})
            return

        saved = svc.add_message(
            conversation_id, user_id, role="assistant",
            content=accumulated, model_used=None,
            provider_used=provider_used, citations=citation_dicts,
        )
        svc.touch_conversation(conversation_id)
        yield _sse(
            "done",
            {
                "provider_used": provider_used,
                "citations": citation_dicts,
                "created_at": saved.get("createdAt").isoformat() if saved.get("createdAt") else None,
            },
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
