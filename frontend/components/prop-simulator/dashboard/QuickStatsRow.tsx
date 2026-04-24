import MetricCard from "@/components/MetricCard";
import type { DashboardSummary } from "@/lib/prop-simulator/types";
import {
  formatCurrencySigned,
  formatDays,
  formatPercent,
} from "@/lib/prop-simulator/format";

interface QuickStatsRowProps {
  summary: DashboardSummary;
}

export default function QuickStatsRow({ summary }: QuickStatsRowProps) {
  // Top-line numbers come from the currently featured "best" setup so the
  // dashboard previews pass/fail/payout/EV for one coherent example rather
  // than an aggregate across all runs.
  const best = summary.best_setup;
  const recent = summary.recent_runs[0] ?? null;

  const pass = best?.pass_rate ?? 0;
  const fail = best?.fail_rate ?? 0;
  const payout = best?.payout_rate ?? 0;
  const ev = best?.ev_after_fees ?? 0;
  const avgDays = best?.avg_days_to_pass ?? 0;
  const confidence = recent?.confidence ?? 0;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 2xl:grid-cols-6">
      <MetricCard
        label="Pass probability"
        value={formatPercent(pass)}
        valueTone="neutral"
        delta={best ? `${best.setup_label}` : undefined}
      />
      <MetricCard
        label="Fail probability"
        value={formatPercent(fail)}
        valueTone="neutral"
      />
      <MetricCard
        label="Payout probability"
        value={formatPercent(payout)}
        valueTone="neutral"
      />
      <MetricCard
        label="EV after fees"
        value={formatCurrencySigned(ev)}
        valueTone={ev > 0 ? "positive" : ev < 0 ? "negative" : "neutral"}
      />
      <MetricCard
        label="Avg days to pass"
        value={formatDays(avgDays)}
        valueTone="neutral"
      />
      <MetricCard
        label="Simulation confidence"
        value={`${confidence} / 100`}
        valueTone="neutral"
        delta={recent ? `${recent.simulation_count.toLocaleString()} seq` : undefined}
      />
    </div>
  );
}
