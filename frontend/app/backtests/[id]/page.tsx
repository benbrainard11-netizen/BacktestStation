import Link from "next/link";
import { notFound } from "next/navigation";

import EquityChart from "@/components/backtests/EquityChart";
import MetricsGrid from "@/components/backtests/MetricsGrid";
import TradeTable from "@/components/backtests/TradeTable";
import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import { ApiError, apiGet } from "@/lib/api/client";
import type {
  BacktestRun,
  EquityPoint,
  RunMetrics,
  Trade,
} from "@/lib/api/types";

export const dynamic = "force-dynamic";

interface BacktestDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function BacktestDetailPage({
  params,
}: BacktestDetailPageProps) {
  const { id } = await params;

  const run = await apiGet<BacktestRun>(`/api/backtests/${id}`).catch(
    (error) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    },
  );

  const [metrics, trades, equity] = await Promise.all([
    apiGet<RunMetrics>(`/api/backtests/${id}/metrics`).catch((error) => {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }),
    apiGet<Trade[]>(`/api/backtests/${id}/trades`),
    apiGet<EquityPoint[]>(`/api/backtests/${id}/equity`),
  ]);

  return (
    <div className="pb-10">
      <div className="px-6 pt-4">
        <Link
          href="/backtests"
          className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
        >
          ← All runs
        </Link>
      </div>
      <PageHeader
        title={run.name ?? `Backtest ${run.id}`}
        description={`${run.symbol} · ${run.timeframe ?? "—"} · ${run.session_label ?? "—"} · ${formatDateRange(run.start_ts, run.end_ts)}`}
        meta={`status ${run.status}`}
      />

      <div className="flex flex-col gap-4 px-6">
        <MetricsGrid metrics={metrics} />

        <Panel title="Equity · Drawdown" meta={`${equity.length} points`}>
          <EquityChart points={equity} />
        </Panel>

        <Panel title="Trades" meta={`${trades.length} total`}>
          <TradeTable trades={trades} />
        </Panel>
      </div>
    </div>
  );
}

function formatDate(iso: string | null): string {
  if (iso === null) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toISOString().slice(0, 10);
}

function formatDateRange(start: string | null, end: string | null): string {
  const s = formatDate(start);
  const e = formatDate(end);
  if (s === "—" && e === "—") return "—";
  return `${s} → ${e}`;
}
