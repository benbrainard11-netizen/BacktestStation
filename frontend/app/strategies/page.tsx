import NewStrategyButton from "@/components/strategies/NewStrategyButton";
import StrategyCardGrid from "@/components/strategies/StrategyCardGrid";
import PageHeader from "@/components/PageHeader";
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

/**
 * Strategy selection. One job: pick a strategy or make a new one.
 * Cards only — no sort/filter/board/table toggle. The whole quant
 * workflow lives inside `/strategies/[id]`.
 */
export default async function StrategiesPage() {
  const [strategies, stagesResponse, allRuns] = await Promise.all([
    apiGet<Strategy[]>("/api/strategies"),
    apiGet<Stages>("/api/strategies/stages").catch(
      () => ({ stages: FALLBACK_STAGES } as Stages),
    ),
    apiGet<BacktestRun[]>("/api/backtests").catch(() => [] as BacktestRun[]),
  ]);

  // Aggregate per-strategy run summaries (used to show "latest run" on each card).
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

  // Sort by recent activity so freshly-touched strategies float up.
  const sorted = [...strategies].sort((a, b) => {
    const ta = summaries.get(a.id)?.latest_run_created_at ?? a.created_at;
    const tb = summaries.get(b.id)?.latest_run_created_at ?? b.created_at;
    return new Date(tb).getTime() - new Date(ta).getTime();
  });

  return (
    <div className="auto-enter">
      <PageHeader
        title="Strategies"
        description="Pick one to enter its workspace, or start a new one."
      />
      <div className="auto-enter flex flex-col gap-5 px-8 pb-10">
        <div className="flex items-center justify-between gap-3">
          <NewStrategyButton stages={stagesResponse.stages ?? FALLBACK_STAGES} />
          <span className="text-xs text-text-mute">
            {strategies.length} total
          </span>
        </div>
        {strategies.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-surface px-6 py-10">
            <p className="m-0 text-xs text-text-mute">No strategies yet</p>
            <p className="m-0 mt-2 text-[13px] text-text-dim">
              Click <strong>+ new strategy</strong> above to start one from
              scratch.
            </p>
          </div>
        ) : (
          <StrategyCardGrid
            strategies={sorted}
            summaries={Object.fromEntries(summaries)}
          />
        )}
      </div>
    </div>
  );
}
