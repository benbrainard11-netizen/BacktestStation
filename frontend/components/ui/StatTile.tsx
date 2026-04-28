import { cn } from "@/lib/utils";

export type StatTone = "pos" | "neg" | "warn" | "neutral";

interface StatTileProps {
  /** Top-left small label, sentence case. */
  label: string;
  /** Big tabular value. */
  value: React.ReactNode;
  /** Dim sub-label below the value. Optional. */
  sub?: React.ReactNode;
  tone?: StatTone;
  /** Optional sparkline node (e.g. <Sparkline values={...} />) rendered top-right. */
  spark?: React.ReactNode;
  /** Optional click handler — recolors hover state and adds cursor-pointer. */
  onClick?: () => void;
  /** When provided, renders as a Link-style anchor. */
  href?: string;
  className?: string;
}

const TONE: Record<StatTone, string> = {
  pos: "text-pos",
  neg: "text-neg",
  warn: "text-warn",
  neutral: "text-text",
};

/**
 * Direction A KPI tile. Label top-left, optional sparkline top-right, big
 * 28px tabular value, dim sub-label. Border + surface only. Click target if
 * `onClick` or `href` provided.
 */
export default function StatTile({
  label,
  value,
  sub,
  tone = "neutral",
  spark,
  onClick,
  href,
  className,
}: StatTileProps) {
  const Wrapper: React.ElementType = href ? "a" : onClick ? "button" : "div";
  const interactive = Boolean(href || onClick);
  return (
    <Wrapper
      href={href}
      onClick={onClick}
      className={cn(
        "block w-full rounded-lg border border-border bg-surface px-[18px] py-4 text-left",
        interactive && "transition-colors hover:bg-surface-alt cursor-pointer",
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <p className="m-0 text-xs text-text-mute">{label}</p>
        {spark ? <div className="shrink-0">{spark}</div> : null}
      </div>
      <p
        className={cn(
          "mb-0 mt-2 text-[28px] font-normal leading-none tracking-[-0.02em] tabular-nums",
          TONE[tone],
        )}
      >
        {value}
      </p>
      {sub ? (
        <p className="m-0 mt-1 text-xs text-text-dim">{sub}</p>
      ) : null}
    </Wrapper>
  );
}
