import Panel from "@/components/Panel";
import OutcomeDistributionChart from "@/components/prop-simulator/OutcomeDistributionChart";
import { cn } from "@/lib/utils";
import type {
  DistributionMetric,
  OutcomeDistribution,
} from "@/lib/prop-simulator/types";

interface OutcomeDistributionPanelProps {
  distribution: OutcomeDistribution;
  /** Optional Panel meta override; defaults to "n sequences · histogram". */
  meta?: string;
}

const METRIC_LABEL: Record<DistributionMetric, string> = {
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

function formatSpread(metric: DistributionMetric, value: number): string {
  // Spread / IQR / std-dev are always positive ranges, no sign prefix.
  switch (metric) {
    case "final_balance":
    case "max_drawdown":
      return `$${Math.round(value).toLocaleString("en-US")}`;
    case "ev_after_fees":
      return `$${Math.round(value).toLocaleString("en-US")}`;
  }
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
  distribution,
  meta,
}: OutcomeDistributionPanelProps) {
  const { stats, buckets, metric } = distribution;
  const sequenceCount = buckets.reduce((acc, b) => acc + b.count, 0);
  const fmt = (v: number) => formatStat(metric, v);
  const sp = (v: number) => formatSpread(metric, v);

  return (
    <Panel
      title={METRIC_LABEL[metric]}
      meta={meta ?? `${sequenceCount.toLocaleString()} sequences · histogram`}
    >
      <div className="flex flex-col gap-4">
        <OutcomeDistributionChart distribution={distribution} />

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          <StatCell label="Mean" value={fmt(stats.mean)} />
          <StatCell label="Median" value={fmt(stats.median)} />
          <StatCell label="Std dev" value={sp(stats.std_dev)} />
          <StatCell label="IQR (P25–P75)" value={sp(stats.iqr)} />
          <StatCell label="Spread (P10–P90)" value={sp(stats.spread)} />
          <StatCell label="Range (min–max)" value={sp(stats.max - stats.min)} />
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          <StatCell label="Min" value={fmt(stats.min)} emphasis="muted" />
          <StatCell label="P10" value={fmt(stats.p10)} emphasis="muted" />
          <StatCell label="P25" value={fmt(stats.p25)} emphasis="muted" />
          <StatCell label="P75" value={fmt(stats.p75)} emphasis="muted" />
          <StatCell label="P90" value={fmt(stats.p90)} emphasis="muted" />
          <StatCell label="Max" value={fmt(stats.max)} emphasis="muted" />
        </div>
      </div>
    </Panel>
  );
}
