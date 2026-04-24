import Link from "next/link";

import PageHeader from "@/components/PageHeader";
import NewSimulationWorkflow from "@/components/prop-simulator/new/NewSimulationWorkflow";

export default function NewSimulationPage() {
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
        title="New simulation"
        description="Assemble a Monte Carlo prop-firm simulation from imported backtests, firm rules, sampling mode, risk model, and personal rules."
        meta="design scaffold"
      />
      <div className="px-6">
        <NewSimulationWorkflow />
      </div>
    </div>
  );
}
