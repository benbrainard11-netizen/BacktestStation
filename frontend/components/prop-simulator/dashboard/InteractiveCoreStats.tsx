"use client";

import { useState } from "react";

import { cn } from "@/lib/utils";
import { useTween } from "@/lib/hooks/useTween";
import type { RiskSweepRow } from "@/lib/prop-simulator/types";
import {
  failureReasonLabel,
  formatCurrencySigned,
  formatDays,
  formatPercent,
} from "@/lib/prop-simulator/format";

interface InteractiveCoreStatsProps {
  sweep: RiskSweepRow[];
  defaultIndex?: number;
}

interface StatBlockProps {
  label: string;
  value: string;
  tone?: "neutral" | "positive" | "negative";
}

const TONE_CLASS: Record<NonNullable<StatBlockProps["tone"]>, string> = {
  positive: "text-emerald-400",
  negative: "text-rose-400",
  neutral: "text-zinc-100",
};

function StatBlock({ label, value, tone = "neutral" }: StatBlockProps) {
  return (
    <div className="flex flex-col gap-1.5 rounded-md border border-zinc-800/80 bg-zinc-950/40 px-3 py-2.5 shadow-edge-top">
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <span
        className={cn(
          "font-mono text-xl leading-none tracking-tight tabular-nums transition-colors",
          TONE_CLASS[tone],
        )}
      >
        {value}
      </span>
    </div>
  );
}

export default function InteractiveCoreStats({
  sweep,
  defaultIndex = 1,
}: InteractiveCoreStatsProps) {
  const [index, setIndex] = useState(defaultIndex);
  const safeIndex = Math.min(Math.max(0, index), sweep.length - 1);
  const row = sweep[safeIndex];

  // Tween every numeric stat smoothly to the target row's values. Format
  // the live tweened number for display so the slider feels analog.
  const passRate = useTween(row.pass_rate);
  const payoutRate = useTween(row.payout_rate);
  const evAfterFees = useTween(row.ev_after_fees);
  const avgDays = useTween(row.avg_days_to_pass);
  const ddUsage = useTween(row.average_dd_usage_percent);

  const evTone =
    row.ev_after_fees > 0
      ? "positive"
      : row.ev_after_fees < 0
        ? "negative"
        : "neutral";

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-6">
        <StatBlock label="Paths" value="10,000" />
        <StatBlock label="Pass" value={formatPercent(passRate)} />
        <StatBlock label="Payout" value={formatPercent(payoutRate)} />
        <StatBlock
          label="EV after fees"
          value={formatCurrencySigned(Math.round(evAfterFees))}
          tone={evTone}
        />
        <StatBlock label="Avg days to pass" value={formatDays(avgDays)} />
        <StatBlock label="DD usage" value={formatPercent(ddUsage)} />
      </div>

      <div className="flex flex-col gap-2 rounded-md border border-zinc-800/80 bg-zinc-950/30 px-3 py-3 shadow-edge-top">
        <div className="flex items-center justify-between gap-3">
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Risk per trade
          </span>
          <span className="font-mono text-sm tabular-nums text-zinc-100">
            ${row.risk_per_trade.toLocaleString()}
            <span className="ml-1 text-[10px] uppercase tracking-widest text-zinc-500">
              / trade
            </span>
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={sweep.length - 1}
          step={1}
          value={safeIndex}
          onChange={(e) => setIndex(Number(e.target.value))}
          className="terminal-slider"
          aria-label="Risk per trade"
        />
        <div className="flex justify-between font-mono text-[9px] uppercase tracking-widest text-zinc-600">
          {sweep.map((r, i) => (
            <button
              key={r.risk_per_trade}
              type="button"
              onClick={() => setIndex(i)}
              className={cn(
                "transition-colors hover:text-zinc-300",
                i === safeIndex && "text-zinc-200",
              )}
            >
              ${r.risk_per_trade}
            </button>
          ))}
        </div>
        <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-zinc-600">
          Main fail at this level · {failureReasonLabel(row.main_failure_reason)}
        </p>
      </div>
    </div>
  );
}
