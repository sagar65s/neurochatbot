"use client";

import { ConversationSummary } from "@/types/chat";

export default function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNewChat,
  onDelete,
  onRename,
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
}: {
  conversations: ConversationSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}) {
  const content = (
    <div className="flex h-full w-64 flex-col bg-paper-surface dark:bg-ink-surface">
      <div className="flex items-center justify-between px-3 py-3">
        <span className="font-semibold">NeuroChat</span>
        <button
          onClick={onToggleCollapse}
          className="hidden rounded p-1.5 hover:bg-paper-surface2 dark:hover:bg-ink-surface2 md:block"
          aria-label="Collapse sidebar"
        >
          <PanelIcon />
        </button>
        <button
          onClick={onCloseMobile}
          className="rounded p-1.5 hover:bg-paper-surface2 dark:hover:bg-ink-surface2 md:hidden"
          aria-label="Close menu"
        >
          <CloseIcon />
        </button>
      </div>

      <div className="px-3">
        <button
          onClick={() => {
            onNewChat();
            onCloseMobile();
          }}
          className="flex w-full items-center gap-2 rounded border border-paper-border px-3 py-2 text-sm hover:bg-paper-surface2 dark:border-ink-border dark:hover:bg-ink-surface2"
        >
          <PlusIcon /> New chat
        </button>
      </div>

      <div className="mt-3 flex-1 space-y-0.5 overflow-y-auto px-2 pb-3">
        {conversations.length === 0 && (
          <p className="px-2 py-4 text-center text-xs text-ink-muted">
            No conversations yet — start one above.
          </p>
        )}
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`group flex items-center justify-between rounded px-2.5 py-2 text-sm cursor-pointer ${
              c.id === activeId
                ? "bg-paper-surface2 dark:bg-ink-surface2"
                : "hover:bg-paper-surface2/60 dark:hover:bg-ink-surface2/60"
            }`}
            onClick={() => {
              onSelect(c.id);
              onCloseMobile();
            }}
          >
            <span className="truncate">{c.title}</span>
            <div className="hidden shrink-0 gap-1 group-hover:flex">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  const title = window.prompt("Rename conversation", c.title);
                  if (title) onRename(c.id, title);
                }}
                className="rounded p-1 text-ink-muted hover:text-accent"
                aria-label="Rename"
              >
                <EditIcon />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(c.id);
                }}
                className="rounded p-1 text-ink-muted hover:text-red-400"
                aria-label="Delete"
              >
                <TrashIcon />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop: static column, collapsible */}
      <div
        className={`hidden shrink-0 border-r border-paper-border dark:border-ink-border md:block ${
          collapsed ? "w-14" : "w-64"
        }`}
      >
        {collapsed ? (
          <div className="flex h-full flex-col items-center bg-paper-surface py-3 dark:bg-ink-surface">
            <button
              onClick={onToggleCollapse}
              className="mb-3 rounded p-2 hover:bg-paper-surface2 dark:hover:bg-ink-surface2"
              aria-label="Expand sidebar"
            >
              <PanelIcon />
            </button>
            <button
              onClick={onNewChat}
              className="rounded p-2 hover:bg-paper-surface2 dark:hover:bg-ink-surface2"
              aria-label="New chat"
            >
              <PlusIcon />
            </button>
          </div>
        ) : (
          content
        )}
      </div>

      {/* Mobile: overlay drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <div className="absolute inset-y-0 left-0 z-50 shadow-xl">{content}</div>
        </div>
      )}
    </>
  );
}

function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}
function PanelIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M9 4v16" />
    </svg>
  );
}
function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
    </svg>
  );
}
function EditIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  );
}
function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6" />
    </svg>
  );
}
