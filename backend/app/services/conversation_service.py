"""
All Firestore reads/writes for conversations and messages go through this
module. Ownership checks live here so both the chat route and the
conversations CRUD routes enforce the exact same rule: a conversation can
only be touched by the Firebase user who owns it.
"""
from firebase_admin import firestore

from app.config.settings import get_settings
from app.firebase.admin import get_firestore_client
from app.providers.base import ChatMessage
from app.utils.logging import get_logger
from app.utils.tokens import estimate_tokens

logger = get_logger(__name__)


class ConversationNotFoundError(Exception):
    pass


class ConversationAccessDeniedError(Exception):
    pass


def _conversations_ref():
    return get_firestore_client().collection("conversations")


def derive_title(message: str) -> str:
    """
    Local, non-AI title generation. Takes the first few words of the
    first user message rather than calling a model just for this.
    """
    words = message.strip().split()
    if not words:
        return "New chat"
    short = " ".join(words[:6])
    return short if len(short) < len(message.strip()) else short


def create_conversation(user_id: str, first_message: str) -> dict:
    ref = _conversations_ref().document()
    data = {
        "id": ref.id,
        "userId": user_id,
        "title": derive_title(first_message),
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }
    ref.set(data)
    snapshot = ref.get()
    return snapshot.to_dict()


def get_conversation_or_raise(conversation_id: str, user_id: str) -> dict:
    ref = _conversations_ref().document(conversation_id)
    snapshot = ref.get()
    if not snapshot.exists:
        raise ConversationNotFoundError(conversation_id)

    data = snapshot.to_dict()
    if data.get("userId") != user_id:
        raise ConversationAccessDeniedError(conversation_id)

    return data


def list_conversations(user_id: str) -> list[dict]:
    query = (
        _conversations_ref()
        .where("userId", "==", user_id)
        .order_by("updatedAt", direction=firestore.Query.DESCENDING)
    )
    return [doc.to_dict() for doc in query.stream()]


def rename_conversation(conversation_id: str, user_id: str, new_title: str) -> dict:
    get_conversation_or_raise(conversation_id, user_id)  # ownership check
    ref = _conversations_ref().document(conversation_id)
    ref.update({"title": new_title, "updatedAt": firestore.SERVER_TIMESTAMP})
    return ref.get().to_dict()


def touch_conversation(conversation_id: str) -> None:
    _conversations_ref().document(conversation_id).update(
        {"updatedAt": firestore.SERVER_TIMESTAMP}
    )


def delete_conversation(conversation_id: str, user_id: str) -> None:
    get_conversation_or_raise(conversation_id, user_id)  # ownership check
    conv_ref = _conversations_ref().document(conversation_id)

    messages_ref = conv_ref.collection("messages")
    batch_size = 100
    while True:
        docs = list(messages_ref.limit(batch_size).stream())
        if not docs:
            break
        batch = get_firestore_client().batch()
        for doc in docs:
            batch.delete(doc.reference)
        batch.commit()
        if len(docs) < batch_size:
            break

    conv_ref.delete()


def add_message(
    conversation_id: str,
    user_id: str,
    role: str,
    content: str,
    model_used: str | None = None,
    provider_used: str | None = None,
    citations: list[dict] | None = None,
) -> dict:
    ref = _conversations_ref().document(conversation_id).collection("messages").document()
    data = {
        "id": ref.id,
        "conversationId": conversation_id,
        "userId": user_id,
        "role": role,
        "content": content,
        "modelUsed": model_used,
        "providerUsed": provider_used,
        "citations": citations or [],
        "createdAt": firestore.SERVER_TIMESTAMP,
    }
    ref.set(data)
    return ref.get().to_dict()


def list_messages(conversation_id: str, user_id: str) -> list[dict]:
    get_conversation_or_raise(conversation_id, user_id)  # ownership check
    query = (
        _conversations_ref()
        .document(conversation_id)
        .collection("messages")
        .order_by("createdAt", direction=firestore.Query.ASCENDING)
    )
    return [doc.to_dict() for doc in query.stream()]


def load_history_for_ai(conversation_id: str) -> list[ChatMessage]:
    """
    Context management strategy:
      - Fetch at most `max_history_messages` most-recent messages.
      - Walk them newest-to-oldest accumulating an estimated token count;
        stop adding older messages once `max_context_tokens` is reached.
      - Prepend a system prompt if one is configured.

    Never truncates a single message's own content — if one message alone
    exceeds the budget it's still included whole.
    """
    settings = get_settings()

    query = (
        _conversations_ref()
        .document(conversation_id)
        .collection("messages")
        .order_by("createdAt", direction=firestore.Query.DESCENDING)
        .limit(settings.max_history_messages)
    )
    docs = [doc.to_dict() for doc in query.stream()]  # newest first

    selected: list[dict] = []
    token_budget = settings.max_context_tokens
    tokens_used = 0

    for msg in docs:
        msg_tokens = estimate_tokens(msg["content"])
        if selected and tokens_used + msg_tokens > token_budget:
            break
        selected.append(msg)
        tokens_used += msg_tokens

    selected.reverse()  # back to chronological order

    history = [ChatMessage(role=m["role"], content=m["content"]) for m in selected]

    if settings.system_prompt:
        history.insert(0, ChatMessage(role="system", content=settings.system_prompt))

    logger.info(
        "Loaded %d/%d messages (~%d tokens) for conversation_id=%s",
        len(selected), len(docs), tokens_used, conversation_id,
    )

    return history
