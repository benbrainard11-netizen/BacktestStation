"use client";

import { useState } from "react";

import Panel from "@/components/Panel";
import OutcomeDistributionChart from "@/components/prop-simulator/OutcomeDistributionChart";
import { cn } from "@/lib/utils";
import type {
  DistributionMetric,
  OutcomeDistribution,
} from "@/lib/prop-simulator/types";

interface OutcomeDistributionPanelProps {
  distributions: OutcomeDistribution[];
  defaultMetric?: DistributionMetric;
  meta?: string;
}

const METRIC_TAB_LABEL: Record<DistributionMetric, string> = {
  final_balance: "Final balance",
  ev_after_fees: "EV after fees",
  max_drawdown: "Max drawdown",
};

const PANEL_TITLE: Record<DistributionMetric, string> = {
  final_balance: "Final balance distribution",
  ev_after_fees: "EV after fees distribution",
  max_drawdown: "Max drawdown distribution",
};

function formatStat(metric: DistributionMetric, value: number): string {
  switch (metric) {
    case "final_balance":
      return `$${Math.round(value).toLocaleString("en-US")}`;
    case "ev_after_fees": {
      const sign = value < 0 ? "-" : value > 0 ? "+" : "";
      return `${sign}$${Math.abs(value).toLocaleString("en-US", {
        maximumFractionDigits: 0,
      })}`;
    }
    case "max_drawdown":
      return `$${Math.round(value).toLocaleString("en-US")}`;
  }
}

function formatSpread(value: number): string {
  return `$${Math.round(value).toLocaleString("en-US")}`;
}

interface StatCellProps {
  label: string;
  value: string;
  emphasis?: "primary" | "muted";
}

function StatCell({ label, value, emphasis = "primary" }: StatCellProps) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-zinc-800/80 bg-zinc-950/40 px-3 py-2 shadow-edge-top">
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <span
        className={cn(
          "font-mono text-sm tabular-nums",
          emphasis === "primary" ? "text-zinc-100" : "text-zinc-300",
        )}
      >
        {value}
      </span>
    </div>
  );
}

export default function OutcomeDistributionPanel({
  distributions,
  defaultMetric,
  meta,
}: OutcomeDistributionPanelProps) {
  const initialMetric =
    defaultMetric && distributions.some((d) => d.metric === defaultMetric)
      ? defaultMetric
      : distributions[0]?.metric ?? "final_balance";

  const [activeMetric, setActiveMetric] =
    useState<DistributionMetric>(initialMetric);

  const active =
    distributions.find((d) => d.metric === activeMetric) ?? distributions[0];

  if (!active) return null;

  const { stats, buckets, metric } = active;
  const sequenceCount = buckets.reduce((acc, b) => acc + b.count, 0);
  const fmt = (v: number) => formatStat(metric, v);
  // Sharpe-style ratio is only meaningful for the EV metric (positive
  // expectation vs spread). Hide it elsewhere to keep noise low.
  const showSharpe = metric === "ev_after_fees" && stats.std_dev !== 0;
  const sharpe = showSharpe ? stats.mean / stats.std_dev : null;

  return (
    <Panel
      title={PANEL_TITLE[metric]}
      meta={meta ?? `${sequenceCount.toLocaleString()} sequences · histogram`}
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-1.5">
          {distributions.map((d) => {
            const isActive = d.metric === activeMetric;
            return (
              <button
                key={d.metric}
                type="button"
                onClick={() => setActiveMetric(d.metric)}
                className={cn(
                  "rounded-md border px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest transition-all duration-150",
                  isActive
                    ? "border-zinc-600 bg-zinc-800 text-zinc-100 shadow-edge-top"
                    : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-900 hover:text-zinc-200",
                )}
              >
                {METRIC_TAB_LABEL[d.metric]}
              </button>
            );
          })}
        </div>

        <OutcomeDistributionChart distribution={active} />

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          <StatCell label="Mean" value={fmt(stats.mean)} />
          <StatCell label="Median" value={fmt(stats.median)} />
          <StatCell label="Std dev" value={formatSpread(stats.std_dev)} />
          <StatCell label="IQR (P25–P75)" value={formatSpread(stats.iqr)} />
          <StatCell label="Spread (P10–P90)" value={formatSpread(stats.spread)} />
          <StatCell
            label="Range (min–max)"
            value={formatSpread(stats.max - stats.min)}
          />
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          <StatCell label="Min" value={fmt(stats.min)} emphasis="muted" />
          <StatCell label="P10" value={fmt(stats.p10)} emphasis="muted" />
          <StatCell label="P25" value={fmt(stats.p25)} emphasis="muted" />
          <StatCell label="P75" value={fmt(stats.p75)} emphasis="muted" />
          <StatCell label="P90" value={fmt(stats.p90)} emphasis="muted" />
          <StatCell label="Max" value={fmt(stats.max)} emphasis="muted" />
        </div>

        {sharpe !== null ? (
          <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            <span className="text-zinc-400">Mean / σ</span> ·{" "}
            <span className="tabular-nums text-emerald-400">
              {sharpe.toFixed(2)}
            </span>
            <span className="ml-2 text-zinc-600">
              reward-to-volatility (sharpe-style)
            </span>
          </p>
        ) : null}
      </div>
    </Panel>
  );
}
