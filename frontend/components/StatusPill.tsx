import StatusDot, { type StatusTone } from "@/components/StatusDot";
import { cn } from "@/lib/utils";

interface StatusPillProps {
  label: string;
  value: string;
  dot?: StatusTone | null;
  pulse?: boolean;
  className?: string;
}

/**
 * Direction A status pill. Keeps the existing `label · dot · value` shape
 * but drops the UPPERCASE / tracking-widest in favor of sentence case
 * matching the rest of the rework.
 */
export default function StatusPill({
  label,
  value,
  dot,
  pulse,
  className,
}: StatusPillProps) {
  return (
    <span
      className={cn(
        "inline-flex h-7 items-center gap-2 rounded-md border border-border bg-surface px-3 text-xs",
        className,
      )}
    >
      <span className="text-text-mute">{label}</span>
      {dot ? <StatusDot status={dot} pulse={pulse} /> : null}
      <span className="text-text">{value}</span>
    </span>
  );
}
