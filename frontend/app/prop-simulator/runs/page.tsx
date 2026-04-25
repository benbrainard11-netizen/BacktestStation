import Link from "next/link";

import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import SimulationRunsTable from "@/components/prop-simulator/runs/SimulationRunsTable";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";
import type { SimulationRunListRow } from "@/lib/prop-simulator/types";

type ApiRow = components["schemas"]["SimulationRunListRow"];

export const dynamic = "force-dynamic";

export default async function SimulationRunsPage() {
  const rows = await apiGet<ApiRow[]>("/api/prop-firm/simulations").catch(
    () => [] as ApiRow[],
  );
  // The generated API row shape mirrors the local SimulationRunListRow
  // shape field-for-field; cast through unknown to satisfy TS without
  // changing component interfaces.
  const runs = rows as unknown as SimulationRunListRow[];

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
        <Panel
          title="All runs"
          meta={runs.length === 0 ? "no runs yet" : "live data"}
        >
          {runs.length === 0 ? (
            <p className="px-3 py-6 font-mono text-xs text-zinc-500">
              No simulations yet. Create one from{" "}
              <Link
                href="/prop-simulator/new"
                className="text-zinc-300 underline hover:text-zinc-100"
              >
                /prop-simulator/new
              </Link>
              .
            </p>
          ) : (
            <SimulationRunsTable rows={runs} />
          )}
        </Panel>
      </div>
    </div>
  );
}
