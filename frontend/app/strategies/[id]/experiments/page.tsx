import { notFound } from "next/navigation";

import ExperimentsPanel from "@/components/strategies/ExperimentsPanel";
import { ApiError, apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type Strategy = components["schemas"]["StrategyRead"];
type BacktestRun = components["schemas"]["BacktestRunRead"];
type ExperimentDecisions = components["schemas"]["ExperimentDecisionsRead"];

interface PageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = "force-dynamic";

/**
 * Per-strategy experiments. Existing ExperimentsPanel handles the
 * A/B + decisions ledger; this page just gives it room to breathe.
 * Future: side-by-side overlaid equity curves for picked baseline
 * vs variant (use OverlaidEquityChart from /backtests/compare).
 */
export default async function ExperimentsPage({ params }: PageProps) {
  const { id } = await params;
  const [strategy, runs, decisionsResponse] = await Promise.all([
    apiGet<Strategy>(`/api/strategies/${id}`).catch((error) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    }),
    apiGet<BacktestRun[]>(`/api/strategies/${id}/runs`).catch(
      () => [] as BacktestRun[],
    ),
    apiGet<ExperimentDecisions>("/api/experiments/decisions").catch(
      () => ({ decisions: [] }) as ExperimentDecisions,
    ),
  ]);

  return (
    <section className="flex flex-col gap-3">
      <header className="border-b border-border pb-2">
        <h2 className="m-0 text-[15px] font-medium tracking-[-0.01em] text-text">
          Experiments
        </h2>
        <p className="m-0 mt-0.5 text-xs text-text-mute">
          A/B versions, decisions, and rollouts. Pick a baseline + a
          variant from this strategy&apos;s runs.
        </p>
      </header>
      <ExperimentsPanel
        strategyId={strategy.id}
        versions={strategy.versions}
        runs={runs}
        decisions={decisionsResponse.decisions ?? []}
      />
    </section>
  );
}
