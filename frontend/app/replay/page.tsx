import PageHeader from "@/components/PageHeader";
import ReplayLoader from "@/components/replay/ReplayLoader";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];

export const dynamic = "force-dynamic";

interface SearchParams {
 symbol?: string;
 date?: string;
 backtest_run_id?: string;
}

export default async function ReplayPage({
 searchParams,
}: {
 searchParams: Promise<SearchParams>;
}) {
 const sp = await searchParams;
 const symbol = sp.symbol ?? "NQ.c.0";
 const date = sp.date ?? defaultDate();
 const runId = sp.backtest_run_id
 ? Number.parseInt(sp.backtest_run_id, 10)
 : null;

 const recentRuns = await apiGet<BacktestRun[]>(
 "/api/backtests",
 ).catch(() => [] as BacktestRun[]);

 return (
 <div>
 <PageHeader
 title="Replay"
 description="Load a trading day's 1m candles and step through them. Overlay a backtest run's entries to see exactly when each trade fired on the chart."
 />
 <div className="px-8 pb-12">
 <ReplayLoader
 initialSymbol={symbol}
 initialDate={date}
 initialRunId={runId}
 recentRuns={recentRuns.slice(0, 50)}
 />
 </div>
 </div>
 );
}

function defaultDate(): string {
 // A meaningful default for first-time visitors: 2026-04-22 has both
 // live trades and a port-matched FILLED run if Ben has one set up.
 // Falls back gracefully when bars aren't backfilled (chart shows
 // empty-state).
 return "2026-04-22";
}
