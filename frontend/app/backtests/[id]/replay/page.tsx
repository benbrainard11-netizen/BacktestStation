import Link from "next/link";
import { notFound } from "next/navigation";

import TradeDetailsCard from "@/components/backtests/TradeDetailsCard";
import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type Trade = components["schemas"]["TradeRead"];
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

interface PageProps {
 params: Promise<{ id: string }>;
 searchParams: Promise<{ trade?: string }>;
}

export default async function ReplayPage({ params, searchParams }: PageProps) {
 const { id } = await params;
 const { trade: tradeId } = await searchParams;

 const run = await apiGet<BacktestRun>(`/api/backtests/${id}`).catch((e) => {
 if (e instanceof ApiError && e.status === 404) notFound();
 throw e;
 });

 const trades = await apiGet<Trade[]>(`/api/backtests/${id}/trades`);
 const selected = pickTrade(trades, tradeId);

 return (
 <div className="pb-10">
 <div className="flex gap-2 px-8 pt-4">
 <Link
 href={`/backtests/${id}`}
 className="inline-block border border-border bg-surface px-2.5 py-1 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt"
 >
 ← Run {run.id}
 </Link>
 <Link
 href="/backtests"
 className="inline-block border border-border bg-surface px-2.5 py-1 tabular-nums text-[10px] text-text-dim hover:bg-surface-alt"
 >
 All runs
 </Link>
 </div>
 <PageHeader
 title={selected ? `Replay · Trade ${selected.id}` : "Replay"}
 description={
 selected
 ? `${run.name ?? `BT-${run.id}`} · ${selected.symbol} · ${selected.side} · ${selected.exit_reason ?? "—"}`
 : `${run.name ?? `BT-${run.id}`} — pick a trade to replay`
 }
 meta={`${trades.length} trades in run`}
 />

 <div className="flex flex-col gap-4 px-8">
 {selected ? (
 <>
 <PrevNextNav trades={trades} current={selected} runId={run.id} />
 <Panel title="Trade details">
 <TradeDetailsCard trade={selected} />
 </Panel>
 <p className="rounded-lg border border-dashed border-border bg-surface px-4 py-3 text-xs text-text-mute">
 Candle chart will land once the Databento tick pipeline is wired.
 Details card + Prev/Next nav are the Phase 1 surface.
 </p>
 </>
 ) : (
 <TradePicker trades={trades} runId={run.id} />
 )}
 </div>
 </div>
 );
}

function pickTrade(trades: Trade[], tradeId: string | undefined): Trade | null {
 if (!tradeId) return null;
 const id = Number(tradeId);
 if (!Number.isFinite(id)) return null;
 return trades.find((t) => t.id === id) ?? null;
}

function PrevNextNav({
 trades,
 current,
 runId,
}: {
 trades: Trade[];
 current: Trade;
 runId: number;
}) {
 const sorted = [...trades].sort(
 (a, b) =>
 new Date(a.entry_ts).getTime() - new Date(b.entry_ts).getTime() ||
 a.id - b.id,
 );
 const idx = sorted.findIndex((t) => t.id === current.id);
 const prev = idx > 0 ? sorted[idx - 1] : null;
 const next = idx >= 0 && idx < sorted.length - 1 ? sorted[idx + 1] : null;

 return (
 <div className="flex items-center justify-between tabular-nums text-[11px]">
 {prev ? (
 <Link
 href={`/backtests/${runId}/replay?trade=${prev.id}`}
 className="border border-border bg-surface px-2.5 py-1 text-text-dim hover:bg-surface-alt"
 >
 ← Prev (#{prev.id})
 </Link>
 ) : (
 <span className="px-2.5 py-1 text-text-mute">
 ← Prev
 </span>
 )}
 <span className="text-text-mute">
 {idx + 1} of {sorted.length}
 </span>
 {next ? (
 <Link
 href={`/backtests/${runId}/replay?trade=${next.id}`}
 className="border border-border bg-surface px-2.5 py-1 text-text-dim hover:bg-surface-alt"
 >
 Next (#{next.id}) →
 </Link>
 ) : (
 <span className="px-2.5 py-1 text-text-mute">
 Next →
 </span>
 )}
 </div>
 );
}

function TradePicker({ trades, runId }: { trades: Trade[]; runId: number }) {
 if (trades.length === 0) {
 return (
 <div className="border border-dashed border-border bg-surface p-6 text-center">
 <p className="tabular-nums text-[10px] text-text-mute">
 No trades
 </p>
 <p className="mt-2 text-xs text-text-mute">
 Nothing to replay in this run.
 </p>
 </div>
 );
 }
 const sorted = [...trades].sort(
 (a, b) =>
 new Date(a.entry_ts).getTime() - new Date(b.entry_ts).getTime() ||
 a.id - b.id,
 );
 const preview = sorted.slice(0, 50);
 return (
 <Panel
 title="Pick a trade"
 meta={`first ${preview.length} of ${trades.length}`}
 >
 <div className="flex flex-wrap gap-2">
 {preview.map((t) => (
 <Link
 key={t.id}
 href={`/backtests/${runId}/replay?trade=${t.id}`}
 className={cn(
 "border border-border bg-surface px-2 py-1 tabular-nums text-[11px]",
 "hover:bg-surface-alt",
 t.r_multiple !== null && t.r_multiple > 0 && "text-pos",
 t.r_multiple !== null && t.r_multiple < 0 && "text-neg",
 (t.r_multiple === null || t.r_multiple === 0) && "text-text-dim",
 )}
 title={`${t.symbol} ${t.side} · ${t.entry_ts}`}
 >
 #{t.id} {t.side === "long" ? "L" : "S"}
 </Link>
 ))}
 </div>
 <p className="mt-3 text-xs text-text-mute">
 Or open the{" "}
 <Link
 href={`/backtests/${runId}`}
 className="underline hover:text-text-dim"
 >
 trade table
 </Link>{" "}
 and click Replay on any row.
 </p>
 </Panel>
 );
}
