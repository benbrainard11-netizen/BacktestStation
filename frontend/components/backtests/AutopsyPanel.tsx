import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Report = components["schemas"]["AutopsyReportRead"];
type Slice = components["schemas"]["AutopsyConditionSlice"];

interface AutopsyPanelProps {
 report: Report | null;
 loadError: string | null;
}

const RECOMMENDATION_LABEL: Record<string, string> = {
 not_ready: "NOT READY",
 forward_test_only: "FORWARD TEST ONLY",
 small_size: "SMALL SIZE OK",
 validated: "VALIDATED",
};

const RECOMMENDATION_STYLE: Record<string, string> = {
 not_ready: "border-neg/30 bg-neg/10 text-neg",
 forward_test_only: "border-warn/30 bg-warn/10 text-warn",
 small_size: "border-sky-900 bg-sky-950/40 text-sky-200",
 validated: "border-pos/30 bg-pos/10 text-pos",
};

export default function AutopsyPanel({ report, loadError }: AutopsyPanelProps) {
 if (loadError !== null) {
 return (
 <div className="border border-neg/30 bg-neg/10 p-3 tabular-nums text-xs text-text">
 <p className="tabular-nums text-[10px] text-neg">
 Autopsy unavailable
 </p>
 <p className="mt-1">{loadError}</p>
 </div>
 );
 }
 if (report === null) {
 return (
 <p className="tabular-nums text-xs text-text-mute">Autopsy not generated.</p>
 );
 }

 const recStyle =
 RECOMMENDATION_STYLE[report.go_live_recommendation] ??
 RECOMMENDATION_STYLE.not_ready;
 const recLabel =
 RECOMMENDATION_LABEL[report.go_live_recommendation] ??
 report.go_live_recommendation;

 return (
 <div className="flex flex-col gap-4">
 <div className={cn("border p-3", recStyle)}>
 <div className="flex items-start justify-between gap-3">
 <div>
 <p className="tabular-nums text-[10px] ">
 {recLabel}
 </p>
 <p className="mt-1 tabular-nums text-xs text-text">
 {report.overall_verdict}
 </p>
 </div>
 <div className="shrink-0 text-right">
 <p className="tabular-nums text-[10px] text-text-dim">
 Edge confidence
 </p>
 <p className="tabular-nums text-3xl leading-none text-text">
 {report.edge_confidence}
 <span className="text-text-mute">/100</span>
 </p>
 </div>
 </div>
 </div>

 <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
 <BulletList
 title="Strengths"
 color="text-pos"
 items={report.strengths}
 fallback="None identified by the current rules."
 />
 <BulletList
 title="Weaknesses"
 color="text-neg"
 items={report.weaknesses}
 fallback="None identified."
 />
 <BulletList
 title="Overfitting warnings"
 color="text-warn"
 items={report.overfitting_warnings}
 fallback="No overfitting flags triggered."
 />
 <BulletList
 title="Risk notes"
 color="text-sky-300"
 items={report.risk_notes}
 fallback="Nothing flagged beyond the drawdown stats."
 />
 </div>

 <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
 <ConditionList
 title="Best conditions"
 color="text-pos"
 slices={report.best_conditions}
 />
 <ConditionList
 title="Worst conditions"
 color="text-neg"
 slices={report.worst_conditions}
 />
 </div>

 <div className="border border-border bg-surface p-3">
 <p className="tabular-nums text-[10px] text-text-mute">
 Suggested next test
 </p>
 <p className="mt-1 text-sm text-text">{report.suggested_next_test}</p>
 </div>
 </div>
 );
}

function BulletList({
 title,
 color,
 items,
 fallback,
}: {
 title: string;
 color: string;
 items: string[];
 fallback: string;
}) {
 return (
 <div className="border border-border bg-surface p-3">
 <p className={cn("tabular-nums text-[10px] ", color)}>
 {title}
 </p>
 {items.length === 0 ? (
 <p className="mt-2 tabular-nums text-xs text-text-mute">{fallback}</p>
 ) : (
 <ul className="mt-2 flex flex-col gap-1 tabular-nums text-xs text-text-dim">
 {items.map((item, i) => (
 <li key={i}>· {item}</li>
 ))}
 </ul>
 )}
 </div>
 );
}

function ConditionList({
 title,
 color,
 slices,
}: {
 title: string;
 color: string;
 slices: Slice[];
}) {
 return (
 <div className="border border-border bg-surface p-3">
 <p className={cn("tabular-nums text-[10px] ", color)}>
 {title}
 </p>
 {slices.length === 0 ? (
 <p className="mt-2 tabular-nums text-xs text-text-mute">
 Not enough trades per group (min 5) to slice.
 </p>
 ) : (
 <ul className="mt-2 flex flex-col gap-1 tabular-nums text-[11px] text-text-dim">
 {slices.map((slice, i) => (
 <li key={i} className="flex items-center justify-between gap-3">
 <span className="text-text-dim">{slice.label}</span>
 <span className="shrink-0">
 <span
 className={
 slice.net_r > 0
 ? "text-pos"
 : slice.net_r < 0
 ? "text-neg"
 : "text-text-dim"
 }
 >
 {slice.net_r > 0 ? "+" : ""}
 {slice.net_r.toFixed(1)}R
 </span>
 <span className="ml-2 text-text-mute">{slice.trades} trades</span>
 </span>
 </li>
 ))}
 </ul>
 )}
 </div>
 );
}
