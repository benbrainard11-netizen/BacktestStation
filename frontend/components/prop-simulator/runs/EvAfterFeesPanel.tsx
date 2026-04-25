import Panel from "@/components/Panel";
import ChartPlaceholder from "@/components/prop-simulator/shared/ChartPlaceholder";
import ConfidenceIntervalValue from "@/components/prop-simulator/shared/ConfidenceIntervalValue";
import { cn } from "@/lib/utils";
import type { SimulationAggregatedStats } from "@/lib/prop-simulator/types";
import {
  formatCurrencySigned,
  formatCurrencyUnsigned,
} from "@/lib/prop-simulator/format";

interface EvAfterFeesPanelProps {
  stats: SimulationAggregatedStats;
}

function Row({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "positive" | "negative" | "neutral";
}) {
  const toneClass =
    tone === "positive"
      ? "text-emerald-400"
      : tone === "negative"
        ? "text-rose-400"
        : "text-zinc-100";
  return (
    <div className="flex items-center justify-between border-b border-zinc-900 py-1.5 last:border-b-0">
      <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <span className={cn("font-mono text-xs tabular-nums", toneClass)}>
        {value}
      </span>
    </div>
  );
}

export default function EvAfterFeesPanel({ stats }: EvAfterFeesPanelProps) {
  const ev = stats.expected_value_after_fees;
  const tone = ev.value > 0 ? "positive" : ev.value < 0 ? "negative" : "neutral";

  return (
    <Panel title="Expected value after fees" meta="95% CI">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1 border border-zinc-800 bg-zinc-950 px-3 py-3">
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            EV after fees
          </span>
          <ConfidenceIntervalValue
            interval={ev}
            format="currency"
            tone="auto"
          />
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
            Before fees: {formatCurrencySigned(stats.expected_value_before_fees)}
            {" · "}fees paid avg {formatCurrencyUnsigned(stats.average_fees_paid)}
          </span>
        </div>

        <div>
          <Row
            label="Avg final balance"
            value={formatCurrencyUnsigned(stats.average_final_balance)}
          />
          <Row
            label="Median final balance"
            value={formatCurrencyUnsigned(stats.median_final_balance)}
          />
          <Row
            label="P10 final balance"
            value={formatCurrencyUnsigned(stats.p10_final_balance)}
          />
          <Row
            label="P90 final balance"
            value={formatCurrencyUnsigned(stats.p90_final_balance)}
          />
          <Row
            label="Avg payout"
            value={formatCurrencyUnsigned(stats.average_payout)}
            tone="positive"
          />
          <Row
            label="Median payout"
            value={formatCurrencyUnsigned(stats.median_payout)}
            tone={tone === "negative" ? "neutral" : tone}
          />
        </div>

        <ChartPlaceholder
          title="Ending-balance distribution"
          detail="Histogram + P10/P25/P50/P75/P90 markers land with chart phase."
          minHeight={140}
        />
      </div>
    </Panel>
  );
}
