import { cn } from "@/lib/utils";

export type StatusTone = "live" | "idle" | "warn" | "off";

const TONE: Record<StatusTone, string> = {
  live: "bg-emerald-400",
  idle: "bg-zinc-500",
  warn: "bg-amber-400",
  off: "bg-rose-400",
};

interface StatusDotProps {
  status: StatusTone;
  pulse?: boolean;
  className?: string;
}

export default function StatusDot({ status, pulse, className }: StatusDotProps) {
  return (
    <span
      className={cn(
        "inline-block h-1.5 w-1.5 shrink-0 rounded-full",
        TONE[status],
        pulse && "animate-pulse",
        className,
      )}
      aria-hidden="true"
    />
  );
}
