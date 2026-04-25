"use client";

import { useState } from "react";

import { cn } from "@/lib/utils";
import { useDelta } from "@/lib/hooks/useDelta";
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

type DeltaFormat = "percent" | "currency" | "days";

interface StatBlockProps {
  label: string;
  value: string;
  delta: number | null;
  deltaFormat: DeltaFormat;
  tone?: "neutral" | "positive" | "negative";
}

const TONE_CLASS: Record<NonNullable<StatBlockProps["tone"]>, string> = {
  positive: "text-emerald-400",
  negative: "text-rose-400",
  neutral: "text-zinc-100",
};

function formatDelta(delta: number, format: DeltaFormat): string {
  const sign = delta > 0 ? "+" : "";
  switch (format) {
    case "percent":
      return `${sign}${(delta * 100).toFixed(1)}%`;
    case "currency": {
      return `${sign}$${Math.abs(Math.round(delta)).toLocaleString("en-US")}`.replace(
        "$",
        delta < 0 ? "-$" : delta > 0 ? "+$" : "$",
      );
    }
    case "days":
      return `${sign}${delta.toFixed(1)}d`;
  }
}

function DeltaChip({ delta, format }: { delta: number | null; format: DeltaFormat }) {
  if (delta === null) return null;
  const tone = delta > 0 ? "emerald" : "rose";
  const toneClass =
    tone === "emerald"
      ? "border-emerald-900/70 bg-emerald-950/40 text-emerald-300"
      : "border-rose-900/70 bg-rose-950/40 text-rose-300";
  return (
    <span
      key={Math.random()}
      className={cn(
        "panel-enter pointer-events-none ml-1 inline-flex items-center rounded-sm border px-1 py-px font-mono text-[9px] tabular-nums leading-none",
        toneClass,
      )}
    >
      {formatDelta(delta, format)}
    </span>
  );
}

function StatBlock({
  label,
  value,
  delta,
  deltaFormat,
  tone = "neutral",
}: StatBlockProps) {
  return (
    <div className="flex flex-col gap-1.5 rounded-md border border-zinc-800/80 bg-zinc-950/40 px-3 py-2.5 shadow-edge-top">
      <span className="flex items-center font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
        <DeltaChip delta={delta} format={deltaFormat} />
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

  // Tween every numeric stat — initialValue=0 means each one counts up from
  // zero on first mount, then transitions smoothly between rows on slider
  // changes thereafter.
  const passRate = useTween(row.pass_rate, 600, 0);
  const payoutRate = useTween(row.payout_rate, 600, 0);
  const evAfterFees = useTween(row.ev_after_fees, 600, 0);
  const avgDays = useTween(row.avg_days_to_pass, 600, 0);
  const ddUsage = useTween(row.average_dd_usage_percent, 600, 0);

  const passDelta = useDelta(row.pass_rate);
  const payoutDelta = useDelta(row.payout_rate);
  const evDelta = useDelta(row.ev_after_fees);
  const daysDelta = useDelta(row.avg_days_to_pass);
  const ddDelta = useDelta(row.average_dd_usage_percent);

  const evTone =
    row.ev_after_fees > 0
      ? "positive"
      : row.ev_after_fees < 0
        ? "negative"
        : "neutral";

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-6">
        <StatBlock
          label="Paths"
          value="10,000"
          delta={null}
          deltaFormat="percent"
        />
        <StatBlock
          label="Pass"
          value={formatPercent(passRate)}
          delta={passDelta}
          deltaFormat="percent"
        />
        <StatBlock
          label="Payout"
          value={formatPercent(payoutRate)}
          delta={payoutDelta}
          deltaFormat="percent"
        />
        <StatBlock
          label="EV after fees"
          value={formatCurrencySigned(Math.round(evAfterFees))}
          delta={evDelta}
          deltaFormat="currency"
          tone={evTone}
        />
        <StatBlock
          label="Avg days to pass"
          value={formatDays(avgDays)}
          delta={daysDelta}
          deltaFormat="days"
        />
        <StatBlock
          label="DD usage"
          value={formatPercent(ddUsage)}
          delta={ddDelta}
          deltaFormat="percent"
        />
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
