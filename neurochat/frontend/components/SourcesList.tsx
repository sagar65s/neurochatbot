import { Citation } from "@/types/chat";

export default function SourcesList({ citations }: { citations?: Citation[] }) {
  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-2 rounded border border-ink-border/60 bg-ink-surface2/40 px-3 py-2">
      <p className="mb-1.5 flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wide text-ink-muted">
        <SearchIcon /> Sources
      </p>
      <ol className="space-y-1">
        {citations.map((c, i) => (
          <li key={`${c.url}-${i}`} className="truncate text-[13px]">
            <span className="mr-1.5 text-ink-muted">{i + 1}.</span>
            <a
              href={c.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent hover:underline"
              title={c.url}
            >
              {c.title}
            </a>
          </li>
        ))}
      </ol>
    </div>
  );
}

function SearchIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" strokeLinecap="round" />
    </svg>
  );
}
