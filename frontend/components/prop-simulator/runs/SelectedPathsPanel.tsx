import Panel from "@/components/Panel";
import { cn } from "@/lib/utils";
import type { SelectedPath } from "@/lib/prop-simulator/types";
import {
 failureReasonLabel,
 formatCurrencyUnsigned,
 formatPercent,
} from "@/lib/prop-simulator/format";

interface SelectedPathsPanelProps {
 paths: SelectedPath[];
}

const BUCKET_LABEL: Record<SelectedPath["bucket"], string> = {
 best: "Best path",
 near_pass: "Near-pass path",
 median: "Median path",
 near_fail: "Near-fail path",
 worst: "Worst path",
};

const BUCKET_SUBTITLE: Record<SelectedPath["bucket"], string> = {
 best: "Fastest payout · lowest DD",
 near_pass: "Scraped through · high DD usage",
 median: "Representative middle sequence",
 near_fail: "One bad break from failure",
 worst: "Fastest washout",
};

const BUCKET_ORDER: SelectedPath["bucket"][] = [
 "best",
 "near_pass",
 "median",
 "near_fail",
 "worst",
];

export default function SelectedPathsPanel({ paths }: SelectedPathsPanelProps) {
 const sorted = BUCKET_ORDER.map((bucket) =>
 paths.find((p) => p.bucket === bucket),
 ).filter((p): p is SelectedPath => p !== undefined);

 return (
 <Panel title="Selected paths" meta="5 buckets · detail sample">
 <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-5">
 {sorted.map((path) => {
 const statusTone =
 path.final_status === "passed" || path.final_status === "payout_reached"
 ? "text-pos"
 : "text-neg";
 return (
 <div
 key={path.bucket}
 className="flex flex-col gap-2 border border-border bg-surface p-3"
 >
 <div>
 <p className="tabular-nums text-[10px] text-text-mute">
 {BUCKET_LABEL[path.bucket]}
 </p>
 <p className="tabular-nums text-[11px] text-text-mute">
 {BUCKET_SUBTITLE[path.bucket]}
 </p>
 </div>
 <div className="flex flex-col gap-0.5 tabular-nums text-[11px] text-text-dim">
 <div className="flex justify-between">
 <span className="text-text-mute">Status</span>
 <span className={cn(statusTone, "tabular-nums")}>
 {path.final_status}
 </span>
 </div>
 <div className="flex justify-between">
 <span className="text-text-mute">Seq #</span>
 <span className="tabular-nums">{path.sequence_number}</span>
 </div>
 <div className="flex justify-between">
 <span className="text-text-mute">Days / trades</span>
 <span className="tabular-nums">
 {path.days} · {path.trades}
 </span>
 </div>
 <div className="flex justify-between">
 <span className="text-text-mute">Ending balance</span>
 <span className="tabular-nums">
 {formatCurrencyUnsigned(path.ending_balance)}
 </span>
 </div>
 <div className="flex justify-between">
 <span className="text-text-mute">DD usage</span>
 <span className="tabular-nums">
 {formatPercent(path.max_drawdown_usage_percent)}
 </span>
 </div>
 <div className="flex justify-between">
 <span className="text-text-mute">Fail reason</span>
 <span className="tabular-nums">
 {failureReasonLabel(path.failure_reason)}
 </span>
 </div>
 </div>
 </div>
 );
 })}
 </div>
 </Panel>
 );
}
