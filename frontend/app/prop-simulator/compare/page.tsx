import PageHeader from "@/components/PageHeader";
import Btn from "@/components/ui/Btn";
import Panel from "@/components/ui/Panel";
import CompareWorkspace from "@/components/prop-simulator/compare/CompareWorkspace";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

type ListRow = components["schemas"]["SimulationRunListRow"];

export const dynamic = "force-dynamic";

export default async function ComparePage() {
  const runs = await apiGet<ListRow[]>("/api/prop-firm/simulations").catch(
    () => [] as ListRow[],
  );

  return (
    <div className="pb-10">
      <div className="px-8 pt-4">
        <Btn href="/prop-simulator">← Simulator</Btn>
      </div>
      <PageHeader
        title="Compare"
        description="Pick 2–6 simulation runs to compare side-by-side. Column winners are highlighted."
        meta={`${runs.length} run${runs.length === 1 ? "" : "s"} available`}
      />
      <div className="flex flex-col gap-4 px-8">
        {runs.length < 2 ? (
          <Panel title="Need at least 2 runs to compare">
            <p className="m-0 text-[13px] text-text-dim">
              Run more simulations and they&apos;ll appear here for selection.
            </p>
            <div className="mt-3 flex items-center gap-2">
              <Btn href="/prop-simulator/new" variant="primary">
                New simulation
              </Btn>
              <Btn href="/prop-simulator/runs">All runs</Btn>
            </div>
          </Panel>
        ) : (
          <CompareWorkspace runs={runs} />
        )}
      </div>
    </div>
  );
}
