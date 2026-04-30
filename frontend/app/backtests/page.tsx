import BacktestsScopeShell from "@/components/backtests/BacktestsScopeShell";
import PageHeader from "@/components/PageHeader";
import Btn from "@/components/ui/Btn";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type Strategy = components["schemas"]["StrategyRead"];

export const dynamic = "force-dynamic";

export default async function BacktestsPage() {
  const [runs, strategies] = await Promise.all([
    apiGet<BacktestRun[]>("/api/backtests").catch(() => [] as BacktestRun[]),
    apiGet<Strategy[]>("/api/strategies").catch(() => [] as Strategy[]),
  ]);

  return (
    <div className="auto-enter">
      <PageHeader
        title="Backtests"
        description="Imported runs from existing backtest result files"
      />

      <div className="auto-enter flex flex-col gap-3 px-8 pb-10">
        {runs.length >= 2 ? (
          <div>
            <Btn href="/backtests/compare">Compare runs →</Btn>
          </div>
        ) : null}
        {runs.length === 0 ? (
          <EmptyRuns />
        ) : (
          <BacktestsScopeShell runs={runs} strategies={strategies} />
        )}
      </div>
    </div>
  );
}

function EmptyRuns() {
  return (
    <div className="rounded-lg border border-dashed border-border bg-surface px-6 py-10">
      <p className="m-0 text-xs text-text-mute">No runs yet</p>
      <p className="m-0 mt-2 text-[13px] text-text-dim">
        Import a backtest bundle to populate this list.
      </p>
      <div className="mt-3">
        <Btn href="/import" variant="primary">
          Go to Import →
        </Btn>
      </div>
    </div>
  );
}
