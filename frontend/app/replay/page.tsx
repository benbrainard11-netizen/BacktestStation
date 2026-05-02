import { PageHeader } from "@/components/atoms";
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
  const symbol = sp.symbol ?? "MNQM6";
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
        title="1m Replay"
        sub="Step through a trading day's 1-minute candles. Overlay a backtest run's entries and scan FVG zones detected on the day's 5m resampled bars."
      />
      <div className="px-6 pb-12">
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
