import PageHeader from "@/components/PageHeader";
import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import NewSimulationForm from "@/components/prop-simulator/new/NewSimulationForm";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type BacktestRun = components["schemas"]["BacktestRunRead"];
type Profile = components["schemas"]["FirmRuleProfileRead"];

export const dynamic = "force-dynamic";

export default async function NewSimulationPage() {
  const [runs, profiles] = await Promise.all([
    apiGet<BacktestRun[]>("/api/backtests").catch(() => [] as BacktestRun[]),
    apiGet<Profile[]>("/api/prop-firm/profiles").catch(() => [] as Profile[]),
  ]);

  return (
    <div className="pb-10">
      <div className="px-8 pt-4">
        <Btn href="/prop-simulator">← Simulator</Btn>
      </div>
      <PageHeader
        title="New simulation"
        description="Run a Monte Carlo simulation against one or more imported backtests under a chosen firm rule profile."
      />
      <div className="flex flex-col gap-4 px-8">
        {runs.length === 0 || profiles.length === 0 ? (
          <Prerequisites
            runsCount={runs.length}
            profilesCount={profiles.length}
          />
        ) : (
          <NewSimulationForm runs={runs} profiles={profiles} />
        )}
      </div>
    </div>
  );
}

function Prerequisites({
  runsCount,
  profilesCount,
}: {
  runsCount: number;
  profilesCount: number;
}) {
  return (
    <Panel title="Missing prerequisites">
      <p className="m-0 text-[13px] text-text-dim">
        A Monte Carlo simulation needs at least one imported backtest and one
        firm rule profile.
      </p>
      <ul className="m-0 mt-3 flex list-none flex-col gap-2 p-0 text-[13px]">
        <li className="flex items-center gap-2">
          <span
            className={
              runsCount > 0 ? "text-pos" : "text-neg"
            }
          >
            {runsCount > 0 ? "✓" : "✗"}
          </span>
          <span className="text-text-dim">
            {runsCount} imported backtest{runsCount === 1 ? "" : "s"}
          </span>
          {runsCount === 0 ? (
            <Btn href="/import">Import →</Btn>
          ) : null}
        </li>
        <li className="flex items-center gap-2">
          <span
            className={
              profilesCount > 0 ? "text-pos" : "text-neg"
            }
          >
            {profilesCount > 0 ? "✓" : "✗"}
          </span>
          <span className="text-text-dim">
            {profilesCount} firm profile{profilesCount === 1 ? "" : "s"}
          </span>
          {profilesCount === 0 ? (
            <Btn href="/prop-simulator/firms">Open firms →</Btn>
          ) : null}
        </li>
      </ul>
    </Panel>
  );
}
