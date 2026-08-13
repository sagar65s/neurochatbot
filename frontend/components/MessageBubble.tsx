"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChatMessageItem } from "@/types/chat";
import ProviderBadge from "./ProviderBadge";
import CodeBlock from "./CodeBlock";
import SourcesList from "./SourcesList";

export default function MessageBubble({
  message,
  onRegenerate,
}: {
  message: ChatMessageItem;
  onRegenerate?: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";
  const hasCitations = !isUser && (message.citations?.length ?? 0) > 0;

  async function handleCopy() {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[75%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1.5`}>
        {!isUser && (
          <ProviderBadge
            provider={message.providerUsed}
            model={message.modelUsed}
            grounded={hasCitations}
          />
        )}

        <div
          className={`rounded px-4 py-2.5 text-[15px] leading-relaxed ${
            isUser
              ? "bg-accent text-white"
              : message.error
              ? "border border-red-500/40 bg-red-500/10 text-red-400"
              : "bg-paper-surface2 dark:bg-ink-surface2"
          }`}
        >
          {message.pending ? (
            <TypingDots />
          ) : isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    if (match) {
                      return (
                        <CodeBlock
                          language={match[1]}
                          code={String(children).replace(/\n$/, "")}
                        />
                      );
                    }
                    return (
                      <code className="rounded bg-ink-border/40 px-1.5 py-0.5 font-mono text-[13px]" {...props}>
                        {children}
                      </code>
                    );
                  },
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                }}
              >
                {message.content}
              </ReactMarkdown>
              <SourcesList citations={message.citations} />
            </>
          )}
        </div>

        {!message.pending && (
          <div className="flex items-center gap-3 px-1 text-xs text-ink-muted">
            <span className="text-[11px] text-ink-muted/70">{formatTime(message.createdAt)}</span>
            <button onClick={handleCopy} className="hover:text-accent">
              {copied ? "Copied" : "Copy"}
            </button>
            {!isUser && onRegenerate && (
              <button onClick={onRegenerate} className="hover:text-accent">
                Regenerate
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-muted"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}
