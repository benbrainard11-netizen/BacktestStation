import { cn } from "@/lib/utils";

export type PillTone = "pos" | "neg" | "warn" | "neutral" | "accent";

interface PillProps {
  tone?: PillTone;
  /** Hide the leading dot. */
  noDot?: boolean;
  className?: string;
  children: React.ReactNode;
}

/**
 * Direction A pill. Border + tinted background + 6×6 dot. 12px sentence-case.
 * Tone drives all three: dot color, border (~20% alpha), bg (~8% alpha).
 */
export default function Pill({
  tone = "neutral",
  noDot,
  className,
  children,
}: PillProps) {
  const c = TONE[tone];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-[2px] text-xs leading-none",
        c.text,
        c.border,
        c.bg,
        className,
      )}
    >
      {noDot ? null : (
        <span className={cn("h-1.5 w-1.5 rounded-full", c.dot)} />
      )}
      <span>{children}</span>
    </span>
  );
}

const TONE: Record<
  PillTone,
  { text: string; border: string; bg: string; dot: string }
> = {
  pos: {
    text: "text-pos",
    border: "border-pos/30",
    bg: "bg-pos/10",
    dot: "bg-pos",
  },
  neg: {
    text: "text-neg",
    border: "border-neg/30",
    bg: "bg-neg/10",
    dot: "bg-neg",
  },
  warn: {
    text: "text-warn",
    border: "border-warn/30",
    bg: "bg-warn/10",
    dot: "bg-warn",
  },
  accent: {
    text: "text-accent",
    border: "border-accent/30",
    bg: "bg-accent/10",
    dot: "bg-accent",
  },
  neutral: {
    text: "text-text-dim",
    border: "border-border",
    bg: "bg-transparent",
    dot: "bg-text-mute",
  },
};
