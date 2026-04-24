import { cn } from "@/lib/utils";
import type { ConfidenceInterval } from "@/lib/prop-simulator/types";

type Format = "percent" | "currency" | "days" | "raw";
type Tone = "neutral" | "positive" | "negative" | "auto";

interface ConfidenceIntervalValueProps {
  interval: ConfidenceInterval;
  format?: Format;
  tone?: Tone;
  className?: string;
}

function formatValue(value: number, format: Format): string {
  switch (format) {
    case "percent":
      return `${(value * 100).toFixed(1)}%`;
    case "currency": {
      const sign = value < 0 ? "-" : value > 0 ? "+" : "";
      return `${sign}$${Math.abs(value).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
    }
    case "days":
      return `${value.toFixed(1)}d`;
    case "raw":
      return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
  }
}

function resolveTone(tone: Tone, value: number): string {
  if (tone === "positive") return "text-emerald-400";
  if (tone === "negative") return "text-rose-400";
  if (tone === "auto") {
    if (value > 0) return "text-emerald-400";
    if (value < 0) return "text-rose-400";
    return "text-zinc-100";
  }
  return "text-zinc-100";
}

export default function ConfidenceIntervalValue({
  interval,
  format = "percent",
  tone = "neutral",
  className,
}: ConfidenceIntervalValueProps) {
  const valueClass = resolveTone(tone, interval.value);
  return (
    <span className={cn("font-mono tabular-nums", className)}>
      <span className={cn("text-base", valueClass)}>
        {formatValue(interval.value, format)}
      </span>
      <span className="ml-2 text-[10px] uppercase tracking-widest text-zinc-500">
        {formatValue(interval.low, format)} – {formatValue(interval.high, format)}
      </span>
    </span>
  );
}
