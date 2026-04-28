"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { BackendErrorBody } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import { cn } from "@/lib/utils";

type Strategy = components["schemas"]["StrategyRead"];

interface StrategySummary {
 run_count: number;
 latest_run_created_at: string | null;
 latest_run_id: number | null;
 latest_run_name: string | null;
}

interface StrategyPipelineBoardProps {
 strategies: Strategy[];
 stages: string[];
 summaries: Record<number, StrategySummary | undefined>;
}

const STAGE_LABEL: Record<string, string> = {
 idea: "Idea",
 research: "Research",
 building: "Building",
 backtest_validated: "Backtest validated",
 forward_test: "Forward test",
 live: "Live",
 retired: "Retired",
 archived: "Archived",
 // Legacy (pre-pipeline) vocab — still surface so no data disappears.
 testing: "Testing (legacy)",
};

const STAGE_ACCENT: Record<string, string> = {
 idea: "text-text-dim",
 research: "text-sky-300",
 building: "text-warn",
 backtest_validated: "text-pos",
 forward_test: "text-pos",
 live: "text-pos",
 retired: "text-text-mute",
 archived: "text-text-mute",
 testing: "text-warn",
};

export default function StrategyPipelineBoard({
 strategies,
 stages,
 summaries,
}: StrategyPipelineBoardProps) {
 const router = useRouter();
 const [pending, setPending] = useState<number | null>(null);
 const [error, setError] = useState<string | null>(null);

 // Group strategies by stage, preserve backend stage order. Legacy/unknown
 // stages get their own column at the end.
 const known = new Set(stages);
 const buckets: Record<string, Strategy[]> = {};
 for (const stage of stages) buckets[stage] = [];
 const extras: string[] = [];
 for (const s of strategies) {
 if (!known.has(s.status)) {
 if (!(s.status in buckets)) {
 buckets[s.status] = [];
 extras.push(s.status);
 }
 }
 buckets[s.status].push(s);
 }

 const orderedStages = [...stages, ...extras];

 async function moveStrategy(id: number, nextStatus: string) {
 setPending(id);
 setError(null);
 try {
 const response = await fetch(`/api/strategies/${id}`, {
 method: "PATCH",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify({ status: nextStatus }),
 });
 if (!response.ok) {
 setError(await describe(response));
 setPending(null);
 return;
 }
 setPending(null);
 router.refresh();
 } catch (e) {
 setError(e instanceof Error ? e.message : "Network error");
 setPending(null);
 }
 }

 return (
 <div className="flex flex-col gap-3">
 {error !== null ? (
 <div className="border border-neg/30 bg-neg/10 p-2 tabular-nums text-[11px] text-neg">
 {error}
 </div>
 ) : null}
 <div className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2">
 {orderedStages.map((stage) => {
 const list = buckets[stage] ?? [];
 const label = STAGE_LABEL[stage] ?? stage;
 const accent = STAGE_ACCENT[stage] ?? "text-text-dim";
 return (
 <div
 key={stage}
 className="flex w-72 shrink-0 snap-start flex-col gap-2 border border-border bg-surface p-2"
 >
 <div className="flex items-baseline justify-between">
 <span
 className={cn(
 "tabular-nums text-[10px] ",
 accent,
 )}
 >
 {label}
 </span>
 <span className="tabular-nums text-[10px] text-text-mute">
 {list.length}
 </span>
 </div>
 {list.length === 0 ? (
 <p className="border border-dashed border-border p-2 tabular-nums text-[11px] text-text-mute">
 empty
 </p>
 ) : (
 <ul className="flex flex-col gap-2">
 {list.map((s) => (
 <StrategyCard
 key={s.id}
 strategy={s}
 summary={summaries[s.id]}
 stages={stages}
 onMove={moveStrategy}
 pending={pending === s.id}
 />
 ))}
 </ul>
 )}
 </div>
 );
 })}
 </div>
 </div>
 );
}

function StrategyCard({
 strategy,
 summary,
 stages,
 onMove,
 pending,
}: {
 strategy: Strategy;
 summary: StrategySummary | undefined;
 stages: string[];
 onMove: (id: number, status: string) => void;
 pending: boolean;
}) {
 const runCount = summary?.run_count ?? 0;
 const lastRunAt = summary?.latest_run_created_at ?? null;
 return (
 <li
 className={cn(
 "border border-border bg-surface p-2 text-xs",
 pending && "opacity-50",
 )}
 >
 <div className="flex items-start justify-between gap-2">
 <Link
 href={`/strategies/${strategy.id}`}
 className="tabular-nums text-text hover:text-pos"
 >
 {strategy.name}
 </Link>
 <span className="tabular-nums text-[10px] text-text-mute">
 #{strategy.id}
 </span>
 </div>
 <p className="mt-1 tabular-nums text-[10px] text-text-mute">
 {strategy.slug} · {strategy.versions.length}v · {runCount} run
 {runCount === 1 ? "" : "s"}
 </p>
 {strategy.tags && strategy.tags.length > 0 ? (
 <div className="mt-1 flex flex-wrap gap-1">
 {strategy.tags.map((tag) => (
 <span
 key={tag}
 className="border border-border bg-surface px-1 py-0.5 tabular-nums text-[9px] text-text-mute"
 >
 {tag}
 </span>
 ))}
 </div>
 ) : null}
 {summary?.latest_run_id !== undefined && summary.latest_run_id !== null ? (
 <p className="mt-1 tabular-nums text-[10px] text-text-mute">
 latest ·{" "}
 <Link
 href={`/backtests/${summary.latest_run_id}`}
 className="text-text-dim hover:text-text"
 >
 {summary.latest_run_name ?? `BT-${summary.latest_run_id}`}
 </Link>
 {lastRunAt ? ` · ${formatShort(lastRunAt)}` : ""}
 </p>
 ) : null}
 <div className="mt-2 flex flex-wrap items-center gap-1">
 <span className="tabular-nums text-[10px] text-text-mute">
 move →
 </span>
 {stages
 .filter((s) => s !== strategy.status)
 .map((s) => (
 <button
 key={s}
 type="button"
 disabled={pending}
 onClick={() => onMove(strategy.id, s)}
 className="border border-border bg-surface px-1.5 py-0.5 tabular-nums text-[9px] text-text-dim hover:border-border-strong hover:bg-surface-alt hover:text-text disabled:opacity-50"
 >
 {STAGE_LABEL[s] ?? s}
 </button>
 ))}
 </div>
 </li>
 );
}

function formatShort(iso: string): string {
 const d = new Date(iso);
 if (Number.isNaN(d.getTime())) return iso;
 return d.toISOString().slice(0, 10);
}

async function describe(response: Response): Promise<string> {
 try {
 const parsed = (await response.json()) as BackendErrorBody;
 if (typeof parsed.detail === "string" && parsed.detail.length > 0) {
 return parsed.detail;
 }
 } catch {
 /* fall through */
 }
 return `${response.status} ${response.statusText || "Request failed"}`;
}
