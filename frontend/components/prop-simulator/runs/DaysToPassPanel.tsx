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
 <div className="flex flex-col gap-1 border border-border bg-surface px-3 py-3">
 <span className="tabular-nums text-[10px] text-text-mute">
 Avg days to pass
 </span>
 <ConfidenceIntervalValue
 interval={stats.average_days_to_pass}
 format="days"
 />
 <span className="tabular-nums text-[10px] text-text-mute">
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
