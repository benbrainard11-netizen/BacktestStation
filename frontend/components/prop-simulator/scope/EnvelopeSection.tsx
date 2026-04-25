// Centerpiece — fan chart spanning wide, with a tight stat column to the
// right. The chart is the visual anchor of the spread.

import { cn } from "@/lib/utils";
import FanChart from "@/components/prop-simulator/FanChart";
import type {
  FanBands,
  SimulationAggregatedStats,
} from "@/lib/prop-simulator/types";

interface EnvelopeSectionProps {
  bands: FanBands;
  stats: SimulationAggregatedStats;
}

function StatRow({
  label,
  value,
  emphasis = "primary",
}: {
  label: string;
  value: string;
  emphasis?: "primary" | "muted";
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-zinc-800 py-2 last:border-b-0">
      <span className="text-[10px] uppercase tracking-[0.32em] text-zinc-500">
        {label}
      </span>
      <span
        className={cn(
          "font-light tabular-nums",
          emphasis === "primary" ? "text-zinc-100" : "text-zinc-300",
        )}
      >
        {value}
      </span>
    </div>
  );
}

function dollar(v: number): string {
  const sign = v < 0 ? "-" : "";
  return `${sign}$${Math.abs(Math.round(v)).toLocaleString("en-US")}`;
}

export default function EnvelopeSection({
  bands,
  stats,
}: EnvelopeSectionProps) {
  const fb = stats.final_balance_distribution;
  return (
    <section className="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:gap-12">
      <div className="lg:col-span-8">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-xs uppercase tracking-[0.5em] text-zinc-300">
            Probability envelope
          </h2>
          <span className="text-[10px] uppercase tracking-[0.32em] text-zinc-600">
            10,000 sequences
          </span>
        </div>
        <div className="border border-zinc-800 bg-zinc-950/40 p-4 shadow-edge-top">
          <FanChart bands={bands} height={300} />
        </div>
      </div>

      <div className="flex flex-col gap-4 lg:col-span-4">
        <div>
          <h3 className="mb-2 text-[10px] uppercase tracking-[0.5em] text-zinc-600">
            Final balance distribution
          </h3>
          <StatRow label="Mean" value={dollar(fb.stats.mean)} />
          <StatRow label="Median" value={dollar(fb.stats.median)} />
          <StatRow label="Std dev (σ)" value={dollar(fb.stats.std_dev)} />
          <StatRow label="IQR (P25–P75)" value={dollar(fb.stats.iqr)} />
          <StatRow label="Spread (P10–P90)" value={dollar(fb.stats.spread)} />
        </div>
        <div>
          <h3 className="mb-2 text-[10px] uppercase tracking-[0.5em] text-zinc-600">
            Drawdown
          </h3>
          <StatRow label="Mean DD" value={dollar(stats.average_max_drawdown)} />
          <StatRow label="Worst DD" value={dollar(stats.worst_max_drawdown)} />
          <StatRow
            label="Avg DD usage"
            value={`${(stats.average_drawdown_usage.value * 100).toFixed(1)}%`}
          />
        </div>
      </div>
    </section>
  );
}
