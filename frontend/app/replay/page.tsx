import Link from "next/link";

import { PageHeader } from "@/components/atoms";
import ReplayLoader from "@/components/replay/ReplayLoader";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type Strategy = components["schemas"]["StrategyRead"];

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

  // If we arrived via deep-link from a strategy, find which strategy this
  // run belongs to and offer a "back to strategy" link.
  let backToStrategy: { id: number; name: string } | null = null;
  if (runId !== null) {
    const run = recentRuns.find((r) => r.id === runId);
    if (run) {
      const strategies = await apiGet<Strategy[]>("/api/strategies").catch(
        () => [] as Strategy[],
      );
      for (const s of strategies) {
        if (s.versions.some((v) => v.id === run.strategy_version_id)) {
          backToStrategy = { id: s.id, name: s.name };
          break;
        }
      }
    }
  }

  return (
    <div>
      {backToStrategy && (
        <div className="border-b border-line bg-bg-1 px-6 py-2">
          <div className="mx-auto max-w-[1280px]">
            <Link
              href={`/strategies/${backToStrategy.id}/replay`}
              className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-accent hover:text-accent-strong"
            >
              ← Back to {backToStrategy.name} replay
            </Link>
          </div>
        </div>
      )}
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
