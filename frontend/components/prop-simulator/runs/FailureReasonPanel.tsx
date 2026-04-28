import Panel from "@/components/Panel";
import { cn } from "@/lib/utils";
import type { SimulationAggregatedStats } from "@/lib/prop-simulator/types";
import {
 failureReasonLabel,
 formatPercent,
} from "@/lib/prop-simulator/format";

interface FailureReasonPanelProps {
 stats: SimulationAggregatedStats;
}

function Row({
 label,
 pct,
 tone,
}: {
 label: string;
 pct: number;
 tone: "rose" | "amber" | "zinc";
}) {
 const width = Math.max(0, Math.min(100, pct * 100));
 const toneClass =
 tone === "rose"
 ? "bg-neg/60"
 : tone === "amber"
 ? "bg-warn/60"
 : "bg-text-mute";
 return (
 <div className="flex items-center gap-3">
 <span className="w-40 shrink-0 tabular-nums text-[10px] text-text-mute">
 {label}
 </span>
 <div className="relative h-2 flex-1 overflow-hidden border border-border bg-surface">
 <div className={cn("h-full", toneClass)} style={{ width: `${width}%` }} />
 </div>
 <span className="w-14 shrink-0 text-right tabular-nums text-xs tabular-nums text-text">
 {formatPercent(pct)}
 </span>
 </div>
 );
}

export default function FailureReasonPanel({ stats }: FailureReasonPanelProps) {
 return (
 <Panel
 title="Failure reason breakdown"
 meta={`most common · ${failureReasonLabel(stats.most_common_failure_reason)}`}
 >
 <div className="flex flex-col gap-2">
 <Row
 label="Trailing drawdown"
 pct={stats.trailing_drawdown_failure_rate}
 tone="rose"
 />
 <Row
 label="Daily loss limit"
 pct={stats.daily_loss_failure_rate}
 tone="rose"
 />
 <Row
 label="Consistency rule"
 pct={stats.consistency_failure_rate}
 tone="amber"
 />
 <Row
 label="Payout blocked"
 pct={stats.payout_blocked_rate}
 tone="amber"
 />
 <Row
 label="Profit target hit"
 pct={stats.profit_target_hit_rate}
 tone="zinc"
 />
 </div>
 <p className="mt-3 tabular-nums text-[10px] text-text-mute">
 Rates are fraction of all {stats.most_common_failure_reason !== null
 ? "terminating"
 : ""}{" "}
 sequences. Rows can sum to more than 100% across overlapping categories
 (e.g., payout-blocked sequences also counted as passes).
 </p>
 </Panel>
 );
}
