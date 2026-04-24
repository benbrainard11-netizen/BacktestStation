import Link from "next/link";

import NewStrategyButton from "@/components/strategies/NewStrategyButton";
import StrategiesView from "@/components/strategies/StrategiesView";
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

export default async function StrategiesPage() {
  const [strategies, stagesResponse, allRuns] = await Promise.all([
    apiGet<Strategy[]>("/api/strategies"),
    apiGet<Stages>("/api/strategies/stages").catch(
      () => ({ stages: FALLBACK_STAGES } as Stages),
    ),
    apiGet<BacktestRun[]>("/api/backtests").catch(() => [] as BacktestRun[]),
  ]);

  // Aggregate per-strategy run summaries client-side. A dedicated backend
  // endpoint can replace this once the run count grows past a few hundred.
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

  return (
    <div>
      <PageHeader
        title="Strategies"
        description="Pipeline board or table view. Move ideas toward live via the stage buttons on each card."
      />
      <div className="flex flex-col gap-4 px-6 pb-10">
        <div className="flex items-center justify-between gap-3">
          <NewStrategyButton stages={stagesResponse.stages ?? FALLBACK_STAGES} />
          <span className="font-mono text-[11px] text-zinc-500">
            {strategies.length} total ·{" "}
            {strategies.reduce((n, s) => n + s.versions.length, 0)} versions
          </span>
        </div>
        {strategies.length === 0 ? (
          <div className="border border-dashed border-zinc-800 bg-zinc-950 px-6 py-10">
            <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
              No strategies yet
            </p>
            <p className="mt-2 text-sm text-zinc-300">
              Start one from scratch with{" "}
              <strong>+ new strategy</strong>, or import an existing backtest
              to auto-register a strategy.
            </p>
            <Link
              href="/import"
              className="mt-3 inline-block border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-100 hover:bg-zinc-800"
            >
              Go to Import →
            </Link>
          </div>
        ) : (
          <StrategiesView
            strategies={strategies}
            stages={stagesResponse.stages ?? FALLBACK_STAGES}
            summaries={Object.fromEntries(summaries)}
          />
        )}
      </div>
    </div>
  );
}
