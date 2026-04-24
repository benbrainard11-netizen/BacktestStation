import Link from "next/link";

import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import SimulationRunsTable from "@/components/prop-simulator/runs/SimulationRunsTable";
import { MOCK_SIMULATION_RUNS_LIST } from "@/lib/prop-simulator/mocks";

export default function SimulationRunsPage() {
  const runs = MOCK_SIMULATION_RUNS_LIST;

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
        title="Simulation Runs"
        description="Every saved Monte Carlo run. Click a row for the full pass/fail/payout/EV breakdown, risk sweep, and selected paths."
        meta={`${runs.length} runs`}
      />
      <div className="flex flex-col gap-4 px-6">
        <Panel title="All runs" meta="mock scaffold">
          <SimulationRunsTable rows={runs} />
        </Panel>
      </div>
    </div>
  );
}
