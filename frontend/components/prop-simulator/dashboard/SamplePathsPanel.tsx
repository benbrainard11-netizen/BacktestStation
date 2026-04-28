"use client";

import { useState } from "react";

import Panel from "@/components/Panel";
import EquityOverlayChart from "@/components/prop-simulator/EquityOverlayChart";
import FanChart from "@/components/prop-simulator/FanChart";
import { cn } from "@/lib/utils";
import type { FanBands, SelectedPath } from "@/lib/prop-simulator/types";
import {
 failureReasonLabel,
 formatCurrencyUnsigned,
 formatPercent,
} from "@/lib/prop-simulator/format";

interface SamplePathsPanelProps {
 paths: SelectedPath[];
 fanBands: FanBands;
 meta?: string;
}

type ViewMode = "fan" | "paths";

const BUCKET_LABEL: Record<SelectedPath["bucket"], string> = {
 best: "Best",
 near_pass: "Near-pass",
 median: "Median",
 near_fail: "Near-fail",
 worst: "Worst",
};

const BUCKET_DOT: Record<SelectedPath["bucket"], string> = {
 best: "bg-pos",
 near_pass: "bg-pos/55",
 median: "bg-text-dim",
 near_fail: "bg-neg/60",
 worst: "bg-neg",
};

const BUCKET_ORDER: SelectedPath["bucket"][] = [
 "best",
 "near_pass",
 "median",
 "near_fail",
 "worst",
];

function statusTone(status: SelectedPath["final_status"]): string {
 if (status === "passed" || status === "payout_reached") {
 return "text-pos";
 }
 return "text-neg";
}

function BucketCard({ path }: { path: SelectedPath }) {
 return (
 <div className="flex flex-col gap-1.5 rounded-md border border-border bg-surface px-3 py-2 ">
 <div className="flex items-center gap-2">
 <span
 aria-hidden="true"
 className={cn("h-1.5 w-1.5 rounded-full", BUCKET_DOT[path.bucket])}
 />
 <span className="tabular-nums text-[10px] text-text-dim">
 {BUCKET_LABEL[path.bucket]}
 </span>
 </div>
 <div className="flex items-baseline justify-between gap-2">
 <span className="tabular-nums text-xs tabular-nums text-text">
 {formatCurrencyUnsigned(path.ending_balance)}
 </span>
 <span
 className={cn(
 "tabular-nums text-[10px] tabular-nums",
 statusTone(path.final_status),
 )}
 >
 {path.final_status === "passed" || path.final_status === "payout_reached"
 ? "PASS"
 : "FAIL"}
 </span>
 </div>
 <div className="flex items-center justify-between tabular-nums text-[10px] text-text-mute">
 <span>
 {path.days}d · {path.trades}t
 </span>
 <span className="tabular-nums text-text-dim">
 dd {formatPercent(path.max_drawdown_usage_percent)}
 </span>
 </div>
 {path.failure_reason !== null ? (
 <span className="truncate tabular-nums text-[10px] text-text-mute">
 {failureReasonLabel(path.failure_reason)}
 </span>
 ) : (
 <span className="tabular-nums text-[10px] text-text-mute">—</span>
 )}
 </div>
 );
}

const VIEW_TABS: { key: ViewMode; label: string }[] = [
 { key: "fan", label: "Fan" },
 { key: "paths", label: "Paths" },
];

export default function SamplePathsPanel({
 paths,
 fanBands,
 meta = "envelope · 10,000 sequences · 5 selected paths",
}: SamplePathsPanelProps) {
 const [view, setView] = useState<ViewMode>("fan");
 const sorted = BUCKET_ORDER.map((b) => paths.find((p) => p.bucket === b)).filter(
 (p): p is SelectedPath => p !== undefined,
 );

 return (
 <Panel title="Sample equity paths" meta={meta}>
 <div className="flex flex-col gap-4">
 <div className="flex flex-wrap gap-1.5">
 {VIEW_TABS.map((tab) => {
 const isActive = tab.key === view;
 return (
 <button
 key={tab.key}
 type="button"
 onClick={() => setView(tab.key)}
 className={cn(
 "rounded-md border px-2.5 py-1 tabular-nums text-[10px] transition-all duration-150",
 isActive
 ? "border-border bg-surface-alt text-text "
 : "border-border bg-surface text-text-dim hover:border-border-strong hover:bg-surface-alt hover:text-text",
 )}
 >
 {tab.label}
 </button>
 );
 })}
 </div>

 {view === "fan" ? (
 <FanChart bands={fanBands} height={220} />
 ) : (
 <EquityOverlayChart paths={paths} height={220} />
 )}

 <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
 {sorted.map((p) => (
 <BucketCard key={p.bucket} path={p} />
 ))}
 </div>
 </div>
 </Panel>
 );
}
