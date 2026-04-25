import { cn } from "@/lib/utils";

interface PanelProps {
  title: string;
  meta?: string;
  className?: string;
  /**
   * Visual emphasis. "default" = the standard dimensional panel used
   * everywhere; "hero" = stronger ambient shadow + radial vignette,
   * intended for the top-of-page summary panel.
   */
  tone?: "default" | "hero";
  children: React.ReactNode;
}

export default function Panel({
  title,
  meta,
  className,
  tone = "default",
  children,
}: PanelProps) {
  return (
    <section
      className={cn(
        "panel-enter rounded-md border border-zinc-800 bg-zinc-950",
        tone === "hero"
          ? "bg-depth-radial shadow-hero"
          : "shadow-dim",
        "transition-shadow duration-200",
        className,
      )}
    >
      <header className="flex items-center justify-between border-b border-zinc-800/80 px-4 py-2">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
          {title}
        </h3>
        {meta ? (
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
            {meta}
          </span>
        ) : null}
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}
