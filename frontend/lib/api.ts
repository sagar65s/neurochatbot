import { auth } from "@/lib/firebase";
import { ChatMessageItem, Citation, ConversationSummary, ProviderName } from "@/types/chat";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function getAuthHeader(): Promise<Record<string, string>> {
  const idToken = auth.currentUser ? await auth.currentUser.getIdToken() : null;
  return idToken ? { Authorization: `Bearer ${idToken}` } : {};
}

async function authorizedFetch(path: string, options: RequestInit = {}) {
  const authHeader = await getAuthHeader();

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...authHeader,
    ...(options.headers || {}),
  };

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError("Can't reach the server. Check your connection and try again.", 0);
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(mapErrorMessage(res.status, body.detail), res.status);
  }

  if (res.status === 204) return null;
  return res.json();
}

function mapErrorMessage(status: number, detail?: string): string {
  if (status === 401) return "Your session expired. Please log in again.";
  if (status === 400) return detail || "Your message could not be processed. Please rephrase it.";
  if (status === 403) return "You are not authorized to access this conversation.";
  if (status === 404) return "That conversation no longer exists.";
  if (status === 413) return "Your message is too long.";
  if (status === 429) return "You're sending messages too quickly. Please wait a moment and try again.";
  if (status === 503) return "All AI providers are currently unavailable. Please try again shortly.";
  if (status === 0) return detail || "Can't reach the server.";
  return detail || "Something went wrong. Please try again.";
}

export async function checkHealth() {
  const res = await fetch(`${API_BASE_URL}/api/health`);
  return res.json();
}

// Non-streaming — kept for cases where streaming isn't desired (e.g. tests).
export async function sendChatMessage(
  message: string,
  conversationId: string | null
): Promise<{
  conversationId: string | null;
  content: string;
  modelUsed?: string;
  providerUsed?: ProviderName;
  citations?: Citation[];
}> {
  const data = await authorizedFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  return {
    conversationId: data.conversation_id,
    content: data.message.content,
    modelUsed: data.message.model_used ?? undefined,
    providerUsed: (data.message.provider_used as ProviderName) ?? undefined,
    citations: data.message.citations ?? [],
  };
}

export interface StreamCallbacks {
  onMeta?: (conversationId: string) => void;
  onDelta: (delta: string) => void;
  onCitations?: (citations: Citation[]) => void;
  onDone: (providerUsed?: ProviderName, citations?: Citation[]) => void;
  onError: (message: string) => void;
}

/**
 * Streams a chat response via Server-Sent Events. Uses fetch + a manual
 * reader instead of EventSource because EventSource cannot send an
 * Authorization header.
 */
export async function streamChatMessage(
  message: string,
  conversationId: string | null,
  callbacks: StreamCallbacks
): Promise<void> {
  const authHeader = await getAuthHeader();

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader },
      body: JSON.stringify({ message, conversation_id: conversationId }),
    });
  } catch {
    callbacks.onError("Can't reach the server. Check your connection and try again.");
    return;
  }

  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => ({}));
    callbacks.onError(mapErrorMessage(response.status, body.detail));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by a blank line.
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const rawEvent of events) {
      const lines = rawEvent.split("\n");
      const eventLine = lines.find((l) => l.startsWith("event: "));
      const dataLine = lines.find((l) => l.startsWith("data: "));
      if (!eventLine || !dataLine) continue;

      const eventType = eventLine.replace("event: ", "").trim();
      const data = JSON.parse(dataLine.replace("data: ", ""));

      if (eventType === "meta") callbacks.onMeta?.(data.conversation_id);
      else if (eventType === "chunk") callbacks.onDelta(data.delta);
      else if (eventType === "citations") callbacks.onCitations?.(data.citations);
      else if (eventType === "done") callbacks.onDone(data.provider_used, data.citations);
      else if (eventType === "error") callbacks.onError(data.message);
    }
  }
}

export async function fetchConversations(): Promise<ConversationSummary[]> {
  const data = await authorizedFetch("/api/conversations");
  return data.conversations.map((c: any) => ({
    id: c.id,
    title: c.title,
    updatedAt: c.updated_at ? new Date(c.updated_at).getTime() : Date.now(),
  }));
}

export async function fetchMessages(conversationId: string): Promise<ChatMessageItem[]> {
  const data = await authorizedFetch(`/api/conversations/${conversationId}/messages`);
  return data.messages.map((m: any) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    modelUsed: m.model_used ?? undefined,
    providerUsed: m.provider_used ?? undefined,
    citations: m.citations ?? [],
    createdAt: m.created_at ? new Date(m.created_at).getTime() : Date.now(),
  }));
}

export async function renameConversationApi(conversationId: string, title: string) {
  return authorizedFetch(`/api/conversations/${conversationId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

export async function deleteConversationApi(conversationId: string) {
  return authorizedFetch(`/api/conversations/${conversationId}`, {
    method: "DELETE",
  });
}
