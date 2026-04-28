import { cn } from "@/lib/utils";

export type StatusTone = "live" | "idle" | "warn" | "off";

const TONE: Record<StatusTone, string> = {
  live: "bg-pos",
  idle: "bg-text-mute",
  warn: "bg-warn",
  off: "bg-neg",
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
