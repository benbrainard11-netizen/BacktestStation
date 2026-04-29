import { cn } from "@/lib/utils";

interface PhaseSectionProps {
  /** Used as the anchor id (e.g. "idea" → `#phase-idea`). */
  id: string;
  /** Phase number for the leading badge. */
  number: number;
  title: string;
  subtitle?: string;
  /** Right-aligned actions (e.g. "+ new version" button). */
  actions?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}

/**
 * Workflow-phase section wrapper for the strategy detail page. Each
 * phase (Idea / Build / Backtest / Validate / Live) gets one section,
 * vertically stacked. Content slots cleanly under a number+label
 * header so the user can scan phase-to-phase as they scroll.
 */
export default function PhaseSection({
  id,
  number,
  title,
  subtitle,
  actions,
  className,
  children,
}: PhaseSectionProps) {
  return (
    <section
      id={`phase-${id}`}
      className={cn("scroll-mt-24 flex flex-col gap-3", className)}
    >
      <header className="flex items-baseline justify-between gap-3 border-b border-border pb-2">
        <div className="flex items-baseline gap-3">
          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-border bg-surface tabular-nums text-xs text-text-dim">
            {number}
          </span>
          <h2 className="m-0 text-[16px] font-medium tracking-[-0.01em] text-text">
            {title}
          </h2>
          {subtitle ? (
            <span className="text-xs text-text-mute">{subtitle}</span>
          ) : null}
        </div>
        {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
      </header>
      <div className="flex flex-col gap-3">{children}</div>
    </section>
  );
}
