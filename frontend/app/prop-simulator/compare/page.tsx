import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import SimulationCompareTable from "@/components/prop-simulator/compare/SimulationCompareTable";
import Btn from "@/components/ui/Btn";
import { MOCK_COMPARE_ROWS } from "@/lib/prop-simulator/mocks";

export default function ComparePage() {
  return (
    <div className="pb-10">
      <div className="px-8 pt-4">
        <Btn href="/prop-simulator">← Simulator</Btn>
      </div>
      <PageHeader
        title="Compare"
        description="Side-by-side comparison of simulation setups across firms, account sizes, risk levels, and sampling modes."
        meta={`${MOCK_COMPARE_ROWS.length} setups`}
      />
      <div className="flex flex-col gap-4 px-8">
        <Panel title="Setup comparison" meta="mock scaffold">
          <SimulationCompareTable rows={MOCK_COMPARE_ROWS} />
          <p className="m-0 mt-3 text-xs text-text-mute">
            Best / lowest badges are computed client-side from these rows — they
            highlight the winner per column. Real comparisons will support
            multi-select from Simulation Runs.
          </p>
        </Panel>
      </div>
    </div>
  );
}
