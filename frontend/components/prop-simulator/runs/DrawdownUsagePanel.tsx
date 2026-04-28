import Panel from "@/components/Panel";
import ChartPlaceholder from "@/components/prop-simulator/shared/ChartPlaceholder";
import ConfidenceIntervalValue from "@/components/prop-simulator/shared/ConfidenceIntervalValue";
import type { SimulationAggregatedStats } from "@/lib/prop-simulator/types";
import {
 formatCurrencyUnsigned,
 formatPercent,
} from "@/lib/prop-simulator/format";

interface DrawdownUsagePanelProps {
 stats: SimulationAggregatedStats;
}

function Row({ label, value }: { label: string; value: string }) {
 return (
 <div className="flex items-center justify-between border-b border-border py-1.5 last:border-b-0">
 <span className="tabular-nums text-[10px] text-text-mute">
 {label}
 </span>
 <span className="tabular-nums text-xs tabular-nums text-text">
 {value}
 </span>
 </div>
 );
}

export default function DrawdownUsagePanel({ stats }: DrawdownUsagePanelProps) {
 return (
 <Panel title="Drawdown usage" meta="share of max-DD touched">
 <div className="flex flex-col gap-4">
 <div className="flex flex-col gap-1 border border-border bg-surface px-3 py-3">
 <span className="tabular-nums text-[10px] text-text-mute">
 Avg drawdown usage
 </span>
 <ConfidenceIntervalValue
 interval={stats.average_drawdown_usage}
 format="percent"
 />
 </div>

 <div>
 <Row
 label="Median DD usage"
 value={formatPercent(stats.median_drawdown_usage)}
 />
 <Row
 label="Avg max drawdown"
 value={formatCurrencyUnsigned(stats.average_max_drawdown)}
 />
 <Row
 label="Median max drawdown"
 value={formatCurrencyUnsigned(stats.median_max_drawdown)}
 />
 <Row
 label="Worst max drawdown"
 value={formatCurrencyUnsigned(stats.worst_max_drawdown)}
 />
 </div>

 <ChartPlaceholder
 title="Drawdown-usage distribution"
 detail="Density plot of per-sequence DD usage lands with chart phase."
 minHeight={140}
 />
 </div>
 </Panel>
 );
}
