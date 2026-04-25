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
  best: "bg-emerald-400",
  near_pass: "bg-emerald-500/55",
  median: "bg-zinc-300",
  near_fail: "bg-rose-500/60",
  worst: "bg-rose-400",
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
    return "text-emerald-400";
  }
  return "text-rose-400";
}

function BucketCard({ path }: { path: SelectedPath }) {
  return (
    <div className="flex flex-col gap-1.5 rounded-md border border-zinc-800/80 bg-zinc-950/40 px-3 py-2 shadow-edge-top">
      <div className="flex items-center gap-2">
        <span
          aria-hidden="true"
          className={cn("h-1.5 w-1.5 rounded-full", BUCKET_DOT[path.bucket])}
        />
        <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
          {BUCKET_LABEL[path.bucket]}
        </span>
      </div>
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-mono text-xs tabular-nums text-zinc-100">
          {formatCurrencyUnsigned(path.ending_balance)}
        </span>
        <span
          className={cn(
            "font-mono text-[10px] tabular-nums",
            statusTone(path.final_status),
          )}
        >
          {path.final_status === "passed" || path.final_status === "payout_reached"
            ? "PASS"
            : "FAIL"}
        </span>
      </div>
      <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-widest text-zinc-500">
        <span>
          {path.days}d · {path.trades}t
        </span>
        <span className="tabular-nums text-zinc-400">
          dd {formatPercent(path.max_drawdown_usage_percent)}
        </span>
      </div>
      {path.failure_reason !== null ? (
        <span className="truncate font-mono text-[10px] text-zinc-600">
          {failureReasonLabel(path.failure_reason)}
        </span>
      ) : (
        <span className="font-mono text-[10px] text-zinc-700">—</span>
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
                  "rounded-md border px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest transition-all duration-150",
                  isActive
                    ? "border-zinc-600 bg-zinc-800 text-zinc-100 shadow-edge-top"
                    : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-900 hover:text-zinc-200",
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
