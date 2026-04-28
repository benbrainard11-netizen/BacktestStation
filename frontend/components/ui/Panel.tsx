import { cn } from "@/lib/utils";

export interface PanelProps {
  /** Sentence-case title — never UPPERCASE in Direction A. */
  title?: string;
  /** Optional right-aligned meta. Accepts a string or any node (e.g. a <Pill />). */
  meta?: React.ReactNode;
  /** When false, body has no padding (e.g. for tables that own their padding). */
  padded?: boolean;
  className?: string;
  bodyClassName?: string;
  children: React.ReactNode;
}

/**
 * Direction A panel. Border + surface only — no shadow. 1px borders, 8px
 * radius, sentence-case 13px title. Headerless variant supported by
 * omitting `title`.
 */
export default function Panel({
  title,
  meta,
  padded = true,
  className,
  bodyClassName,
  children,
}: PanelProps) {
  return (
    <section
      className={cn(
        "rounded-lg border border-border bg-surface",
        className,
      )}
    >
      {title ? (
        <header className="flex items-baseline justify-between border-b border-border px-[18px] py-[14px]">
          <h3 className="m-0 text-[13px] font-medium tracking-[-0.005em] text-text">
            {title}
          </h3>
          {meta ? (
            typeof meta === "string" ? (
              <span className="text-xs text-text-mute">{meta}</span>
            ) : (
              meta
            )
          ) : null}
        </header>
      ) : null}
      <div className={cn(padded ? "px-[18px] py-4" : "", bodyClassName)}>
        {children}
      </div>
    </section>
  );
}
