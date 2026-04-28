import Panel from "@/components/Panel";
import ConfidenceIntervalValue from "@/components/prop-simulator/shared/ConfidenceIntervalValue";
import type { SimulationAggregatedStats } from "@/lib/prop-simulator/types";

interface MonteCarloOutcomePanelProps {
 stats: SimulationAggregatedStats;
 sequenceCount: number;
}

function StackedBarRow({
 label,
 pct,
 tone,
}: {
 label: string;
 pct: number;
 tone: "emerald" | "rose" | "zinc";
}) {
 const width = Math.max(0, Math.min(100, pct * 100));
 const toneClass =
 tone === "emerald"
 ? "bg-pos/70"
 : tone === "rose"
 ? "bg-neg/70"
 : "bg-text-mute";
 return (
 <div className="flex items-center gap-3">
 <span className="w-24 shrink-0 tabular-nums text-[10px] text-text-mute">
 {label}
 </span>
 <div className="relative h-2 flex-1 overflow-hidden border border-border bg-surface">
 <div className={`h-full ${toneClass}`} style={{ width: `${width}%` }} />
 </div>
 </div>
 );
}

export default function MonteCarloOutcomePanel({
 stats,
 sequenceCount,
}: MonteCarloOutcomePanelProps) {
 return (
 <Panel
 title="Monte Carlo outcomes"
 meta={`${sequenceCount.toLocaleString()} sequences · 95% CI`}
 >
 <div className="flex flex-col gap-5">
 <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
 <div className="flex flex-col gap-1 border border-border bg-surface px-3 py-2">
 <span className="tabular-nums text-[10px] text-text-mute">
 Pass rate
 </span>
 <ConfidenceIntervalValue interval={stats.pass_rate} format="percent" />
 </div>
 <div className="flex flex-col gap-1 border border-border bg-surface px-3 py-2">
 <span className="tabular-nums text-[10px] text-text-mute">
 Fail rate
 </span>
 <ConfidenceIntervalValue
 interval={stats.fail_rate}
 format="percent"
 tone="negative"
 />
 </div>
 <div className="flex flex-col gap-1 border border-border bg-surface px-3 py-2">
 <span className="tabular-nums text-[10px] text-text-mute">
 Payout rate
 </span>
 <ConfidenceIntervalValue
 interval={stats.payout_rate}
 format="percent"
 tone="positive"
 />
 </div>
 </div>
 <div className="flex flex-col gap-2">
 <StackedBarRow label="Pass" pct={stats.pass_rate.value} tone="emerald" />
 <StackedBarRow label="Fail" pct={stats.fail_rate.value} tone="rose" />
 <StackedBarRow label="Payout" pct={stats.payout_rate.value} tone="zinc" />
 </div>
 <p className="tabular-nums text-[10px] text-text-mute">
 Pass = profit target hit. Payout = eligible for first payout after
 firm gates. Fail = any terminating rule violation.
 </p>
 </div>
 </Panel>
 );
}
