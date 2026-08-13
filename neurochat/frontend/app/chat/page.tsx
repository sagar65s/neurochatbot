"use client";

import { useEffect, useRef, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import Sidebar from "@/components/Sidebar";
import MessageBubble from "@/components/MessageBubble";
import ChatInput from "@/components/ChatInput";
import ThemeToggle from "@/components/ThemeToggle";
import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";
import { ChatMessageItem, ConversationSummary } from "@/types/chat";
import {
  streamChatMessage,
  fetchConversations,
  fetchMessages,
  renameConversationApi,
  deleteConversationApi,
} from "@/lib/api";
import { makeId } from "@/lib/mockChat";

function ChatContent() {
  const { user, loading: authLoading, logOut } = useAuth();
  const router = useRouter();

  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationsLoading, setConversationsLoading] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messagesByConv, setMessagesByConv] = useState<Record<string, ChatMessageItem[]>>({});
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [sending, setSending] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeMessages = activeId ? messagesByConv[activeId] ?? [] : [];

  // Load conversation list once authenticated.
  useEffect(() => {
    if (authLoading || !user) return;
    (async () => {
      setConversationsLoading(true);
      try {
        const convs = await fetchConversations();
        setConversations(convs);
      } catch (err) {
        console.error("Failed to load conversations", err);
      } finally {
        setConversationsLoading(false);
      }
    })();
  }, [authLoading, user]);

  // Load messages when switching to a conversation we haven't fetched yet.
  useEffect(() => {
    if (!activeId || messagesByConv[activeId]) return;
    (async () => {
      setMessagesLoading(true);
      try {
        const msgs = await fetchMessages(activeId);
        setMessagesByConv((prev) => ({ ...prev, [activeId]: msgs }));
      } catch (err) {
        console.error("Failed to load messages", err);
      } finally {
        setMessagesLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

  // Auto-scroll to the latest message, including during streaming (content
  // length changes trigger this effect too via the dependency below).
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [activeMessages.length, activeMessages[activeMessages.length - 1]?.content]);

  function handleNewChat() {
    setActiveId(null);
  }

  function handleSelect(id: string) {
    setActiveId(id);
  }

  async function handleDelete(id: string) {
    const prevConversations = conversations;
    setConversations((prev) => prev.filter((c) => c.id !== id));
    setMessagesByConv((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    if (activeId === id) setActiveId(null);

    try {
      await deleteConversationApi(id);
    } catch (err) {
      console.error("Failed to delete conversation", err);
      setConversations(prevConversations); // revert on failure
    }
  }

  async function handleRename(id: string, title: string) {
    const prevConversations = conversations;
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)));
    try {
      await renameConversationApi(id, title);
    } catch (err) {
      console.error("Failed to rename conversation", err);
      setConversations(prevConversations);
    }
  }

  async function handleSend(text: string, regenerateFromId?: string) {
    let convId = activeId;
    const isNewConversation = !convId;

    const userMessage: ChatMessageItem = {
      id: makeId(),
      role: "user",
      content: text,
      createdAt: Date.now(),
    };

    const pendingId = makeId();
    const pendingMessage: ChatMessageItem = {
      id: pendingId,
      role: "assistant",
      content: "",
      createdAt: Date.now(),
      pending: true,
    };

    if (convId) {
      setMessagesByConv((prev) => {
        const existing = prev[convId!] ?? [];
        const withoutRegenTarget = regenerateFromId
          ? existing.filter((m) => m.id !== regenerateFromId)
          : existing;
        return {
          ...prev,
          [convId!]: [...withoutRegenTarget, ...(regenerateFromId ? [] : [userMessage]), pendingMessage],
        };
      });
    }

    setSending(true);
    let streamedAny = false;

    await streamChatMessage(text, isNewConversation ? null : convId, {
      onMeta: (conversationId) => {
        convId = conversationId;
        if (isNewConversation) {
          setConversations((prev) => [
            { id: conversationId, title: text.split(/\s+/).slice(0, 6).join(" "), updatedAt: Date.now() },
            ...prev,
          ]);
          setActiveId(conversationId);
          setMessagesByConv((prev) => ({ ...prev, [conversationId]: [userMessage, pendingMessage] }));
        }
      },
      onDelta: (delta) => {
        streamedAny = true;
        setMessagesByConv((prev) => ({
          ...prev,
          [convId!]: (prev[convId!] ?? []).map((m) =>
            m.id === pendingId ? { ...m, content: m.content + delta, pending: false } : m
          ),
        }));
      },
      onCitations: (citations) => {
        setMessagesByConv((prev) => ({
          ...prev,
          [convId!]: (prev[convId!] ?? []).map((m) =>
            m.id === pendingId ? { ...m, citations } : m
          ),
        }));
      },
      onDone: (providerUsed, citations) => {
        setMessagesByConv((prev) => ({
          ...prev,
          [convId!]: (prev[convId!] ?? []).map((m) =>
            m.id === pendingId
              ? { ...m, providerUsed, citations: citations?.length ? citations : m.citations, pending: false }
              : m
          ),
        }));
        setConversations((prev) =>
          [...prev]
            .map((c) => (c.id === convId ? { ...c, updatedAt: Date.now() } : c))
            .sort((a, b) => b.updatedAt - a.updatedAt)
        );
        setSending(false);
      },
      onError: (message) => {
        if (convId) {
          setMessagesByConv((prev) => ({
            ...prev,
            [convId!]: (prev[convId!] ?? []).map((m) =>
              m.id === pendingId
                ? { ...m, content: streamedAny ? m.content : message, error: true, pending: false }
                : m
            ),
          }));
        }
        setSending(false);
      },
    });
  }

  function handleRegenerate(assistantMessageId: string) {
    if (!activeId) return;
    const msgs = messagesByConv[activeId] ?? [];
    const idx = msgs.findIndex((m) => m.id === assistantMessageId);
    const priorUser = [...msgs.slice(0, idx)].reverse().find((m) => m.role === "user");
    if (!priorUser) return;
    handleSend(priorUser.content, assistantMessageId);
  }

  async function handleLogout() {
    await logOut();
    router.push("/login");
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={handleSelect}
        onNewChat={handleNewChat}
        onDelete={handleDelete}
        onRename={handleRename}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((c) => !c)}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-paper-border px-3 py-3 dark:border-ink-border sm:px-4">
          <div className="flex min-w-0 items-center gap-2">
            <button
              onClick={() => setMobileOpen(true)}
              className="rounded p-1.5 hover:bg-paper-surface2 dark:hover:bg-ink-surface2 md:hidden"
              aria-label="Open menu"
            >
              <MenuIcon />
            </button>
            <h1 className="truncate font-semibold">
              {activeId ? conversations.find((c) => c.id === activeId)?.title ?? "Chat" : "New chat"}
            </h1>
          </div>
          <div className="flex shrink-0 items-center gap-2 text-sm sm:gap-3">
            <ThemeToggle />
            <span className="hidden text-ink-muted lg:inline">{user?.email}</span>
            <button
              onClick={handleLogout}
              className="rounded border border-paper-border px-2.5 py-1 text-xs sm:px-3 sm:text-sm dark:border-ink-border"
            >
              Log out
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-3 py-6 sm:px-4">
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {conversationsLoading && (
              <p className="text-center text-sm text-ink-muted">Loading conversations...</p>
            )}
            {!conversationsLoading && activeId && messagesLoading && (
              <p className="text-center text-sm text-ink-muted">Loading messages...</p>
            )}
            {!conversationsLoading && !messagesLoading && activeMessages.length === 0 && (
              <div className="flex h-[50vh] flex-col items-center justify-center px-4 text-center text-ink-muted">
                <p className="text-lg font-medium text-inherit">Start a conversation</p>
                <p className="mt-1 text-sm">
                  Ask anything — questions about current events or today's news are automatically
                  grounded with Google Search.
                </p>
              </div>
            )}
            {activeMessages.map((m) => (
              <MessageBubble
                key={m.id}
                message={m}
                onRegenerate={
                  m.role === "assistant" && !m.pending ? () => handleRegenerate(m.id) : undefined
                }
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <ChatInput onSend={(text) => handleSend(text)} disabled={sending} />
      </div>
    </div>
  );
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
    </svg>
  );
}

export default function ChatPage() {
  return (
    <ProtectedRoute>
      <ChatContent />
    </ProtectedRoute>
  );
}
