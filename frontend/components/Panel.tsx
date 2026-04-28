import { cn } from "@/lib/utils";

interface PanelProps {
  title: string;
  meta?: string;
  className?: string;
  /**
   * Visual emphasis. "default" / "hero" tone props are kept for legacy
   * callsites; both render the Direction A panel — border + surface, no
   * shadow. New code should import `@/components/ui/Panel` directly.
   */
  tone?: "default" | "hero";
  children: React.ReactNode;
}

/**
 * Legacy Panel shim. After the Direction A rework, this re-renders as the
 * new ui/Panel so every existing page picks up the calmer aesthetic
 * automatically. Kept under the original path so existing imports still
 * work without per-file edits.
 */
export default function Panel({
  title,
  meta,
  className,
  children,
}: PanelProps) {
  return (
    <section
      className={cn(
        "rounded-lg border border-border bg-surface",
        className,
      )}
    >
      <header className="flex items-baseline justify-between border-b border-border px-[18px] py-[14px]">
        <h3 className="m-0 text-[13px] font-medium tracking-[-0.005em] text-text">
          {title}
        </h3>
        {meta ? (
          <span className="text-xs text-text-mute">{meta}</span>
        ) : null}
      </header>
      <div className="px-[18px] py-4">{children}</div>
    </section>
  );
}
