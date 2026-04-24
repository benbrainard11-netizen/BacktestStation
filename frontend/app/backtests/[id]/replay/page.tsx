import Link from "next/link";
import { notFound } from "next/navigation";

import TradeDetailsCard from "@/components/backtests/TradeDetailsCard";
import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { BacktestRun, Trade } from "@/lib/api/types";
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
      <div className="flex gap-2 px-6 pt-4">
        <Link
          href={`/backtests/${id}`}
          className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
        >
          ← Run {run.id}
        </Link>
        <Link
          href="/backtests"
          className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
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

      <div className="flex flex-col gap-4 px-6">
        {selected ? (
          <>
            <PrevNextNav trades={trades} current={selected} runId={run.id} />
            <Panel title="Trade details">
              <TradeDetailsCard trade={selected} />
            </Panel>
            <p className="border border-dashed border-zinc-800 bg-zinc-950 px-4 py-3 font-mono text-[11px] text-zinc-500">
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
    <div className="flex items-center justify-between font-mono text-[11px]">
      {prev ? (
        <Link
          href={`/backtests/${runId}/replay?trade=${prev.id}`}
          className="border border-zinc-800 bg-zinc-950 px-2.5 py-1 uppercase tracking-widest text-zinc-300 hover:bg-zinc-900"
        >
          ← Prev (#{prev.id})
        </Link>
      ) : (
        <span className="px-2.5 py-1 uppercase tracking-widest text-zinc-700">
          ← Prev
        </span>
      )}
      <span className="text-zinc-500">
        {idx + 1} of {sorted.length}
      </span>
      {next ? (
        <Link
          href={`/backtests/${runId}/replay?trade=${next.id}`}
          className="border border-zinc-800 bg-zinc-950 px-2.5 py-1 uppercase tracking-widest text-zinc-300 hover:bg-zinc-900"
        >
          Next (#{next.id}) →
        </Link>
      ) : (
        <span className="px-2.5 py-1 uppercase tracking-widest text-zinc-700">
          Next →
        </span>
      )}
    </div>
  );
}

function TradePicker({ trades, runId }: { trades: Trade[]; runId: number }) {
  if (trades.length === 0) {
    return (
      <div className="border border-dashed border-zinc-800 bg-zinc-950 p-6 text-center">
        <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          No trades
        </p>
        <p className="mt-2 text-xs text-zinc-500">
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
              "border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-[11px]",
              "hover:bg-zinc-900",
              t.r_multiple !== null && t.r_multiple > 0 && "text-emerald-400",
              t.r_multiple !== null && t.r_multiple < 0 && "text-rose-400",
              (t.r_multiple === null || t.r_multiple === 0) && "text-zinc-300",
            )}
            title={`${t.symbol} ${t.side} · ${t.entry_ts}`}
          >
            #{t.id} {t.side === "long" ? "L" : "S"}
          </Link>
        ))}
      </div>
      <p className="mt-3 text-xs text-zinc-500">
        Or open the{" "}
        <Link
          href={`/backtests/${runId}`}
          className="underline hover:text-zinc-300"
        >
          trade table
        </Link>{" "}
        and click Replay on any row.
      </p>
    </Panel>
  );
}
