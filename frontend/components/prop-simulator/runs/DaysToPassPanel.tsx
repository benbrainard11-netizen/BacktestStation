import Panel from "@/components/Panel";
import ChartPlaceholder from "@/components/prop-simulator/shared/ChartPlaceholder";
import ConfidenceIntervalValue from "@/components/prop-simulator/shared/ConfidenceIntervalValue";
import type { SimulationAggregatedStats } from "@/lib/prop-simulator/types";
import { formatDays } from "@/lib/prop-simulator/format";

interface DaysToPassPanelProps {
  stats: SimulationAggregatedStats;
}

export default function DaysToPassPanel({ stats }: DaysToPassPanelProps) {
  return (
    <Panel title="Days to pass" meta="successful sequences only">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1 border border-zinc-800 bg-zinc-950 px-3 py-3">
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            Avg days to pass
          </span>
          <ConfidenceIntervalValue
            interval={stats.average_days_to_pass}
            format="days"
          />
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
            Median {formatDays(stats.median_days_to_pass)} · avg{" "}
            {stats.average_trades_to_pass.toFixed(1)} trades to pass
          </span>
        </div>

        <ChartPlaceholder
          title="Days-to-pass histogram"
          detail="Binned distribution + median marker land with chart phase."
          minHeight={140}
        />
      </div>
    </Panel>
  );
}
