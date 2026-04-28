import RunsExplorer from "@/components/backtests/RunsExplorer";
import PageHeader from "@/components/PageHeader";
import Btn from "@/components/ui/Btn";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];

export const dynamic = "force-dynamic";

export default async function BacktestsPage() {
  const runs = await apiGet<BacktestRun[]>("/api/backtests");

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
        {runs.length === 0 ? <EmptyRuns /> : <RunsExplorer runs={runs} />}
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
