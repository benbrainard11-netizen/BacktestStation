import Link from "next/link";

import LiveStrategyCard from "@/components/dashboard/LiveStrategyCard";
import RecentActivityFeed from "@/components/dashboard/RecentActivityFeed";
import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import StatTile from "@/components/ui/StatTile";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type LiveMonitorStatus = components["schemas"]["LiveMonitorStatus"];
type RunMetrics = components["schemas"]["RunMetricsRead"];
type Strategy = components["schemas"]["StrategyRead"];

export const dynamic = "force-dynamic";

/**
 * Portfolio-overview dashboard. Replaces the old Command Center.
 *
 * Top: KPI tiles (live count, today P&L, weekly trades, total runs).
 * Middle: live-strategy cards row (one per `Strategy.status === "live"`).
 *         Empty-state when no live strategies (the realistic state today).
 * Bottom: recent activity feed (latest backtest runs).
 *
 * v1 deliberately keeps the data fetches small — three batched calls.
 * No drift panel, no live tick tape, no per-strategy sparklines yet.
 */
export default async function Dashboard() {
  const [strategies, runs, monitor] = await Promise.all([
    apiGet<Strategy[]>("/api/strategies").catch(() => [] as Strategy[]),
    apiGet<BacktestRun[]>("/api/backtests").catch(() => [] as BacktestRun[]),
    apiGet<LiveMonitorStatus>("/api/monitor/live").catch(
      () => null as LiveMonitorStatus | null,
    ),
  ]);

  const liveStrategies = strategies.filter(
    (s) => s.status === "live" || s.status === "forward_test",
  );

  // Per-strategy latest run (across all versions) + its metrics, only
  // for the live cards. We sort runs once and pick by version-id.
  const runsByVersion = new Map<number, BacktestRun[]>();
  for (const r of runs) {
    const list = runsByVersion.get(r.strategy_version_id) ?? [];
    list.push(r);
    runsByVersion.set(r.strategy_version_id, list);
  }

  const liveStrategyMetrics = await Promise.all(
    liveStrategies.map(async (s) => {
      const versionIds = new Set(s.versions.map((v) => v.id));
      const myRuns = runs
        .filter((r) => versionIds.has(r.strategy_version_id))
        .sort(
          (a, b) =>
            new Date(b.created_at).getTime() -
            new Date(a.created_at).getTime(),
        );
      const latest = myRuns[0] ?? null;
      const metrics = latest
        ? await apiGet<RunMetrics>(`/api/backtests/${latest.id}/metrics`).catch(
            (e) => {
              if (e instanceof ApiError && e.status === 404) return null;
              return null;
            },
          )
        : null;
      return {
        strategy: s,
        latestRunId: latest?.id ?? null,
        metrics,
      };
    }),
  );

  // Trades-this-week = sum across all runs created in the last 7 days.
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const weeklyRunCount = runs.filter(
    (r) => new Date(r.created_at).getTime() >= weekAgo,
  ).length;

  const todayPnl = monitor?.today_pnl ?? null;
  const todayR = monitor?.today_r ?? null;
  const tradesToday = monitor?.trades_today ?? null;

  return (
    <div className="px-8 pb-10 pt-7">
      <Header
        strategyCount={strategies.length}
        liveCount={liveStrategies.length}
      />

      <div className="mb-5 grid grid-cols-4 gap-4">
        <StatTile
          label="Live strategies"
          value={liveStrategies.length.toString()}
          sub={
            liveStrategies.length === 0
              ? "none yet"
              : `of ${strategies.length} total`
          }
          tone={liveStrategies.length > 0 ? "pos" : "neutral"}
        />
        <StatTile
          label="Today P&L"
          value={
            todayPnl === null
              ? "—"
              : `${todayPnl >= 0 ? "+" : "-"}$${Math.abs(todayPnl).toFixed(0)}`
          }
          sub={
            todayR !== null && tradesToday !== null
              ? `${tradesToday} trades · ${todayR >= 0 ? "+" : ""}${todayR.toFixed(2)}R`
              : "no live data today"
          }
          tone={todayPnl === null ? "neutral" : todayPnl >= 0 ? "pos" : "neg"}
        />
        <StatTile
          label="Runs this week"
          value={weeklyRunCount.toString()}
          sub={`${runs.length} all-time`}
          tone="neutral"
        />
        <StatTile
          label="Drift"
          value="—"
          sub="not wired yet"
          tone="neutral"
        />
      </div>

      <div className="mb-5">
        <Panel
          title="Live strategies"
          meta={
            liveStrategies.length === 0
              ? "none"
              : `${liveStrategies.length} active`
          }
        >
          {liveStrategies.length === 0 ? (
            <div className="flex flex-col items-start gap-3 py-2">
              {strategies.length === 0 ? (
                <>
                  <p className="m-0 text-[13px] text-text-dim">
                    No strategies yet. Build your first by stacking
                    pre-made features in the visual builder — no code
                    required.
                  </p>
                  <Btn href="/strategies" variant="primary">
                    + Create your first strategy →
                  </Btn>
                </>
              ) : (
                <>
                  <p className="m-0 text-[13px] text-text-dim">
                    {strategies.length} strateg
                    {strategies.length === 1 ? "y" : "ies"} in development
                    — none shipped to live yet. Ship one when backtest +
                    validate are clean.
                  </p>
                  <Btn href="/strategies" variant="primary">
                    Open Strategies →
                  </Btn>
                </>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {liveStrategyMetrics.map((entry) => (
                <LiveStrategyCard
                  key={entry.strategy.id}
                  strategy={entry.strategy}
                  latestMetrics={entry.metrics}
                  latestRunId={entry.latestRunId}
                />
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel
        title="Recent activity"
        meta={runs.length === 0 ? "none" : `${runs.length} runs total`}
      >
        <RecentActivityFeed runs={runs.slice(0, 8)} />
      </Panel>
    </div>
  );
}

function Header({
  strategyCount,
  liveCount,
}: {
  strategyCount: number;
  liveCount: number;
}) {
  const greeting = greetingFor(new Date());
  return (
    <header className="mb-7 flex items-end justify-between gap-6 border-b border-border pb-5">
      <div>
        <p className="m-0 text-xs text-text-mute">
          Today · {new Date().toLocaleDateString()}
        </p>
        <h1 className="mt-1.5 text-[28px] font-medium leading-tight tracking-[-0.02em] text-text">
          {greeting}, Ben
        </h1>
        <p className="mt-1 text-sm text-text-dim">
          {strategyCount} strategies · {liveCount} live
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Btn href="/strategies" variant="primary">
          New strategy
        </Btn>
        <Link
          href="/strategies"
          className="text-xs text-text-dim hover:text-accent"
        >
          View all →
        </Link>
      </div>
    </header>
  );
}

function greetingFor(now: Date): string {
  const h = now.getHours();
  if (h < 5) return "Working late";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}
