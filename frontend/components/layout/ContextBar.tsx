// Sticky bottom-of-app context bar — Bloomberg-footer pattern. Always shows
// the run provenance (seed, sequences, symbol, engine version, mock flag)
// plus a Cmd-K affordance for the command palette.

const FIELDS: { label: string; value: string; tone?: "emerald" | "amber" }[] = [
  { label: "seed", value: "42" },
  { label: "runs", value: "10,000" },
  { label: "symbol", value: "NQ" },
  { label: "engine", value: "v0.1.0" },
  { label: "data", value: "mock", tone: "amber" },
];

export default function ContextBar() {
  return (
    <footer className="flex h-7 shrink-0 items-center justify-between gap-3 border-t border-zinc-800 bg-zinc-950 px-4 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
      <div className="flex items-center gap-3 overflow-x-auto whitespace-nowrap">
        {FIELDS.map((field, i) => (
          <span key={field.label} className="flex items-center gap-1.5">
            {i > 0 ? (
              <span aria-hidden="true" className="text-zinc-700">
                ·
              </span>
            ) : null}
            <span className="text-zinc-600">{field.label}</span>
            <span
              className={
                field.tone === "amber"
                  ? "text-amber-300"
                  : field.tone === "emerald"
                    ? "text-emerald-400"
                    : "text-zinc-200"
              }
            >
              {field.value}
            </span>
          </span>
        ))}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <span className="text-zinc-600">cmd palette</span>
        <kbd className="flex h-4 items-center gap-0.5 rounded-sm border border-zinc-700 bg-zinc-900 px-1 text-[9px] text-zinc-300">
          <span>⌘</span>
          <span>K</span>
        </kbd>
      </div>
    </footer>
  );
}
