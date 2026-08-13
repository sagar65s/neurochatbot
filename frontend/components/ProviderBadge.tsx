import { ProviderName } from "@/types/chat";

const PROVIDER_COLORS: Record<ProviderName, string> = {
  gemini: "bg-provider-gemini",
  openrouter: "bg-provider-openrouter",
  groq: "bg-provider-groq",
  stub: "bg-provider-stub",
};

export default function ProviderBadge({
  provider,
  model,
  grounded,
}: {
  provider?: ProviderName;
  model?: string;
  grounded?: boolean;
}) {
  if (!provider) return null;

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-ink-border/60 px-2 py-0.5 font-mono text-[11px] text-ink-muted dark:border-ink-border">
      <span className={`h-1.5 w-1.5 rounded-full ${PROVIDER_COLORS[provider]}`} />
      {provider}
      {model ? <span className="text-ink-muted/70">· {model}</span> : null}
      {grounded && (
        <span
          className="ml-0.5 flex items-center gap-0.5 text-provider-gemini"
          title="Grounded with Google Search"
        >
          <SearchIcon /> grounded
        </span>
      )}
    </span>
  );
}

function SearchIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" strokeLinecap="round" />
    </svg>
  );
}
