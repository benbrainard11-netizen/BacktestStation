import Link from "next/link";
import { ArrowUpRight, Plus } from "lucide-react";

import Panel from "@/components/Panel";
import InteractiveCoreStats from "@/components/prop-simulator/dashboard/InteractiveCoreStats";
import SimulationCoreVisual from "@/components/prop-simulator/SimulationCoreVisual";
import type { DashboardSummary } from "@/lib/prop-simulator/types";

interface SimulationCorePanelProps {
  summary: DashboardSummary;
}

export default function SimulationCorePanel({ summary }: SimulationCorePanelProps) {
  // Default the slider to the $100/trade row when present so the hero loads
  // with the configuration that matches the featured "best" setup.
  const defaultIndex = Math.max(
    0,
    summary.risk_sweep_preview.findIndex((r) => r.risk_per_trade === 100),
  );

  return (
    <Panel
      title="Monte Carlo Simulation Core"
      meta="research instrument · mock"
      tone="hero"
    >
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_240px]">
        <div className="flex min-w-0 flex-col gap-5">
          <p className="max-w-2xl text-sm text-zinc-400">
            Probability distribution from{" "}
            <span className="font-mono text-zinc-200">10,000</span>{" "}
            randomized account sequences sampled through firm rules,
            daily limits, trailing drawdown, and payout gates. Drag the
            risk slider to preview how the core stats shift across the
            sweep range.
          </p>

          <InteractiveCoreStats
            sweep={summary.risk_sweep_preview}
            defaultIndex={defaultIndex}
          />

          <div className="flex flex-wrap items-center gap-2">
            <Link
              href="/prop-simulator/new"
              className="inline-flex items-center gap-2 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-100 shadow-dim transition-all duration-150 hover:-translate-y-px hover:border-zinc-600 hover:bg-zinc-800 hover:shadow-dim-hover"
            >
              <Plus className="h-3 w-3" strokeWidth={1.75} aria-hidden="true" />
              New simulation
            </Link>
            <Link
              href="/prop-simulator/runs"
              className="inline-flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-950 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-400 transition-all duration-150 hover:-translate-y-px hover:border-zinc-700 hover:text-zinc-100"
            >
              <ArrowUpRight
                className="h-3 w-3"
                strokeWidth={1.75}
                aria-hidden="true"
              />
              Open runs
            </Link>
            <Link
              href="/prop-simulator/compare"
              className="inline-flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-950 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-400 transition-all duration-150 hover:-translate-y-px hover:border-zinc-700 hover:text-zinc-100"
            >
              <ArrowUpRight
                className="h-3 w-3"
                strokeWidth={1.75}
                aria-hidden="true"
              />
              Compare setups
            </Link>
          </div>
        </div>
        <div className="flex items-center justify-center">
          <SimulationCoreVisual />
        </div>
      </div>
    </Panel>
  );
}
