"use client";

import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

export default function CodeBlock({
  language,
  code,
}: {
  language: string;
  code: string;
}) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="my-3 overflow-hidden rounded border border-ink-border">
      <div className="flex items-center justify-between bg-ink-surface2 px-3 py-1.5 font-mono text-xs text-ink-muted">
        <span>{language || "code"}</span>
        <button
          onClick={handleCopy}
          className="rounded px-2 py-0.5 hover:bg-ink-border/50"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <SyntaxHighlighter
        language={language || "text"}
        style={oneDark}
        customStyle={{ margin: 0, fontSize: "13px", padding: "12px" }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
