import { cn } from "@/lib/utils";

export type RowTone = "pos" | "neg" | "warn" | "neutral";

interface RowProps {
  label: React.ReactNode;
  value: React.ReactNode;
  tone?: RowTone;
  className?: string;
  /** Hide the bottom 1px border (used when stacking last row in a group). */
  noBorder?: boolean;
}

const TONE: Record<RowTone, string> = {
  pos: "text-pos",
  neg: "text-neg",
  warn: "text-warn",
  neutral: "text-text",
};

/**
 * Direction A KV row. Label on the left (text-dim, 13px), value on the
 * right (tabular-nums, 14px, optionally toned). 1px bottom border, 10px
 * vertical padding. Stacks cleanly in 1- or N-column grids.
 */
export default function Row({
  label,
  value,
  tone = "neutral",
  className,
  noBorder,
}: RowProps) {
  return (
    <div
      className={cn(
        "flex items-baseline justify-between gap-3 py-2.5",
        noBorder ? "" : "border-b border-border last:border-b-0",
        className,
      )}
    >
      <span className="text-[13px] text-text-dim">{label}</span>
      <span
        className={cn(
          "text-[14px] tabular-nums",
          TONE[tone],
        )}
      >
        {value}
      </span>
    </div>
  );
}
