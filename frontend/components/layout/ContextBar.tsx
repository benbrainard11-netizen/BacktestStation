// Sticky bottom-of-app context bar — minimal status + Cmd-K affordance.

const APP_VERSION = "0.1.0";

export default function ContextBar() {
  return (
    <footer className="flex h-7 shrink-0 items-center justify-between gap-3 border-t border-border bg-surface px-4 text-xs text-text-mute">
      <div className="flex items-center gap-1.5">
        <span>engine</span>
        <span className="text-text">v{APP_VERSION}</span>
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
