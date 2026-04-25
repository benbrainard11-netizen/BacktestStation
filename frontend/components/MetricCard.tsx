import { Info } from "lucide-react";

import { cn } from "@/lib/utils";

export type Tone = "positive" | "negative" | "neutral";

interface MetricCardProps {
  label: string;
  value: string;
  valueTone?: Tone;
  delta?: string;
  deltaTone?: Tone;
}

const VALUE_TONE: Record<Tone, string> = {
  positive: "text-emerald-400",
  negative: "text-rose-400",
  neutral: "text-zinc-100",
};

const DELTA_TONE: Record<Tone, string> = {
  positive: "text-emerald-400",
  negative: "text-rose-400",
  neutral: "text-zinc-500",
};

export default function MetricCard({
  label,
  value,
  valueTone = "neutral",
  delta,
  deltaTone = "neutral",
}: MetricCardProps) {
  return (
    <div
      className={cn(
        "panel-enter group flex min-w-0 flex-col gap-3",
        "rounded-md border border-zinc-800 bg-zinc-950 px-4 py-3",
        "transform-gpu shadow-dim",
        "transition-[transform,border-color,box-shadow] duration-200",
        "[transition-timing-function:cubic-bezier(0.16,1,0.3,1)]",
        "hover:-translate-y-0.5 hover:border-zinc-700 hover:shadow-dim-hover",
      )}
    >
      <div className="flex items-center gap-1.5 text-zinc-500">
        <span className="font-mono text-[10px] uppercase tracking-widest">
          {label}
        </span>
        <Info
          className="h-3 w-3 shrink-0 text-zinc-700 transition-colors group-hover:text-zinc-600"
          strokeWidth={1.5}
          aria-hidden="true"
        />
      </div>
      <p
        className={cn(
          "font-mono text-2xl leading-none tracking-tight tabular-nums",
          VALUE_TONE[valueTone],
        )}
      >
        {value}
      </p>
      {delta ? (
        <p className="font-mono text-[11px] leading-none">
          <span className={DELTA_TONE[deltaTone]}>{delta.split(" ")[0]}</span>
          <span className="ml-1 text-zinc-600">
            {delta.split(" ").slice(1).join(" ")}
          </span>
        </p>
      ) : null}
    </div>
  );
}
