import NewStrategyButton from "@/components/strategies/NewStrategyButton";
import StrategiesView from "@/components/strategies/StrategiesView";
import PageHeader from "@/components/PageHeader";
import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import StatTile from "@/components/ui/StatTile";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type Stages = components["schemas"]["StrategyStagesRead"];

export interface StrategySummary {
  run_count: number;
  latest_run_created_at: string | null;
  latest_run_id: number | null;
  latest_run_name: string | null;
}

export const dynamic = "force-dynamic";

const FALLBACK_STAGES: string[] = [
  "idea",
  "research",
  "building",
  "backtest_validated",
  "forward_test",
  "live",
  "retired",
  "archived",
];

const ACTIVE_STAGES = new Set([
  "research",
  "building",
  "backtest_validated",
  "forward_test",
  "live",
]);

export default async function StrategiesPage() {
  const [strategies, stagesResponse, allRuns] = await Promise.all([
    apiGet<Strategy[]>("/api/strategies").catch(() => [] as Strategy[]),
    apiGet<Stages>("/api/strategies/stages").catch(
      () => ({ stages: FALLBACK_STAGES }) as Stages,
    ),
    apiGet<BacktestRun[]>("/api/backtests").catch(() => [] as BacktestRun[]),
  ]);

  const summaries = new Map<number, StrategySummary>();
  for (const strategy of strategies) {
    const versionIds = new Set(strategy.versions.map((v) => v.id));
    const runs = allRuns
      .filter((r) => versionIds.has(r.strategy_version_id))
      .sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
    summaries.set(strategy.id, {
      run_count: runs.length,
      latest_run_created_at: runs[0]?.created_at ?? null,
      latest_run_id: runs[0]?.id ?? null,
      latest_run_name: runs[0]?.name ?? null,
    });
  }

  const totalVersions = strategies.reduce((n, s) => n + s.versions.length, 0);
  const totalRuns = allRuns.length;
  const activeCount = strategies.filter((s) =>
    ACTIVE_STAGES.has(s.status),
  ).length;
  const liveCount = strategies.filter(
    (s) => s.status === "live" || s.status === "forward_test",
  ).length;
  const stageBreakdown = countByStage(strategies);

  return (
    <div className="auto-enter">
      <PageHeader
        title="Strategies"
        description="Every thesis you're working on. Pick one to focus the dashboard, or open a strategy to drill into its versions, runs, and prop firm sim."
      />
      <div className="auto-enter flex flex-col gap-4 px-8 pb-10">
        <div className="grid grid-cols-4 gap-4">
          <StatTile
            label="Strategies"
            value={String(strategies.length)}
            sub={`${activeCount} active · ${strategies.length - activeCount} idle`}
            tone="neutral"
          />
          <StatTile
            label="Versions"
            value={String(totalVersions)}
            sub={
              strategies.length > 0
                ? `~${(totalVersions / strategies.length).toFixed(1)} per strategy`
                : "—"
            }
            tone="neutral"
          />
          <StatTile
            label="Runs imported"
            value={String(totalRuns)}
            sub={totalRuns > 0 ? "across all versions" : "none"}
            tone="neutral"
            href="/backtests"
          />
          <StatTile
            label="Live or forward"
            value={String(liveCount)}
            sub={
              liveCount > 0
                ? "deployed to bot or forward test"
                : "nothing deployed"
            }
            tone={liveCount > 0 ? "pos" : "neutral"}
          />
        </div>

        {strategies.length === 0 ? (
          <Panel title="No strategies yet">
            <div className="flex flex-col gap-3 py-2">
              <p className="m-0 text-[13px] text-text-dim">
                A strategy is a thesis you iterate on with versions, runs, and
                notes. Start one from scratch, or import an existing backtest
                to auto-register one.
              </p>
              <div className="flex items-center gap-2">
                <NewStrategyButton
                  stages={stagesResponse.stages ?? FALLBACK_STAGES}
                />
                <Btn href="/import">Or import a backtest →</Btn>
              </div>
            </div>
          </Panel>
        ) : (
          <>
            <div className="flex items-end justify-between gap-3">
              <StageBreakdown counts={stageBreakdown} total={strategies.length} />
              <NewStrategyButton
                stages={stagesResponse.stages ?? FALLBACK_STAGES}
              />
            </div>
            <StrategiesView
              strategies={strategies}
              stages={stagesResponse.stages ?? FALLBACK_STAGES}
              summaries={Object.fromEntries(summaries)}
            />
          </>
        )}
      </div>
    </div>
  );
}

function countByStage(strategies: Strategy[]): Map<string, number> {
  const out = new Map<string, number>();
  for (const s of strategies) {
    out.set(s.status, (out.get(s.status) ?? 0) + 1);
  }
  return out;
}

function StageBreakdown({
  counts,
  total,
}: {
  counts: Map<string, number>;
  total: number;
}) {
  if (total === 0) return null;
  const ordered = Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-text-mute">stage breakdown</span>
      {ordered.map(([stage, n]) => (
        <span
          key={stage}
          className="rounded border border-border bg-surface-alt px-2 py-[2px] text-xs text-text-dim"
        >
          {stage} <span className="text-text">{n}</span>
        </span>
      ))}
    </div>
  );
}
