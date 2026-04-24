import StatusDot, { type StatusTone } from "@/components/StatusDot";
import { cn } from "@/lib/utils";

interface StatusPillProps {
  label: string;
  value: string;
  dot?: StatusTone | null;
  pulse?: boolean;
  className?: string;
}

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
        "inline-flex h-7 items-center gap-2 border border-zinc-800 bg-zinc-950 px-3 font-mono text-[10px] uppercase tracking-widest",
        className,
      )}
    >
      <span className="text-zinc-500">{label}</span>
      {dot ? <StatusDot status={dot} pulse={pulse} /> : null}
      <span className="text-zinc-200">{value}</span>
    </span>
  );
}
