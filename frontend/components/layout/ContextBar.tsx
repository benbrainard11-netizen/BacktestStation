// Sticky bottom-of-app context bar — Bloomberg-footer pattern. Always shows
// the run provenance plus a Cmd-K affordance for the command palette.

const FIELDS: { label: string; value: string; tone?: "pos" | "warn" }[] = [
  { label: "seed", value: "42" },
  { label: "runs", value: "10,000" },
  { label: "symbol", value: "NQ" },
  { label: "engine", value: "v0.1.0" },
  { label: "data", value: "mock", tone: "warn" },
];

export default function ContextBar() {
  return (
    <footer className="flex h-7 shrink-0 items-center justify-between gap-3 border-t border-border bg-surface px-4 text-xs text-text-mute">
      <div className="flex items-center gap-3 overflow-x-auto whitespace-nowrap">
        {FIELDS.map((field, i) => (
          <span key={field.label} className="flex items-center gap-1.5">
            {i > 0 ? (
              <span aria-hidden="true" className="text-text-mute/60">
                ·
              </span>
            ) : null}
            <span>{field.label}</span>
            <span
              className={
                field.tone === "warn"
                  ? "text-warn"
                  : field.tone === "pos"
                    ? "text-pos"
                    : "text-text"
              }
            >
              {field.value}
            </span>
          </span>
        ))}
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <span className="hidden items-center gap-1.5 sm:flex">
          <span>help</span>
          <kbd className="flex h-4 items-center justify-center rounded border border-border bg-surface-alt px-1 text-[10px] text-text-dim">
            ?
          </kbd>
        </span>
        <span className="flex items-center gap-1.5">
          <span>cmd</span>
          <kbd className="flex h-4 items-center gap-0.5 rounded border border-border bg-surface-alt px-1 text-[10px] text-text-dim">
            <span>⌘</span>
            <span>K</span>
          </kbd>
        </span>
      </div>
    </footer>
  );
}
