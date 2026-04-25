import Link from "next/link";

import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import SimulationCompareTable from "@/components/prop-simulator/compare/SimulationCompareTable";
import { MOCK_COMPARE_ROWS } from "@/lib/prop-simulator/mocks";

export default function ComparePage() {
  return (
    <div className="pb-10">
      <div className="px-6 pt-4">
        <Link
          href="/prop-simulator"
          className="inline-block border border-zinc-800 bg-zinc-950 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-400 hover:bg-zinc-900"
        >
          ← Simulator
        </Link>
      </div>
      <PageHeader
        title="Compare"
        description="Side-by-side comparison of simulation setups across firms, account sizes, risk levels, and sampling modes."
        meta={`${MOCK_COMPARE_ROWS.length} setups`}
      />
      <div className="flex flex-col gap-4 px-6">
        <Panel title="Setup comparison" meta="mock scaffold">
          <SimulationCompareTable rows={MOCK_COMPARE_ROWS} />
          <p className="mt-3 font-mono text-[10px] uppercase tracking-widest text-zinc-600">
            Best / lowest badges are computed client-side from these rows — they
            highlight the winner per column. Real comparisons will support
            multi-select from Simulation Runs.
          </p>
        </Panel>
      </div>
    </div>
  );
}
