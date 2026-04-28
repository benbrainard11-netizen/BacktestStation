import { ArrowUpRight, Plus } from "lucide-react";

import Panel from "@/components/Panel";
import InteractiveCoreStats from "@/components/prop-simulator/dashboard/InteractiveCoreStats";
import SimulationCoreVisual from "@/components/prop-simulator/SimulationCoreVisual";
import Btn from "@/components/ui/Btn";
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
 >
 <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_240px]">
 <div className="flex min-w-0 flex-col gap-5">
 <p className="max-w-2xl text-sm text-text-dim">
 Probability distribution from{" "}
 <span className="tabular-nums text-text">10,000</span>{" "}
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
 <Btn href="/prop-simulator/new" variant="primary">
 <Plus className="h-3 w-3" strokeWidth={1.75} aria-hidden="true" />
 New simulation
 </Btn>
 <Btn href="/prop-simulator/runs">
 <ArrowUpRight className="h-3 w-3" strokeWidth={1.75} aria-hidden="true" />
 Open runs
 </Btn>
 <Btn href="/prop-simulator/compare">
 <ArrowUpRight className="h-3 w-3" strokeWidth={1.75} aria-hidden="true" />
 Compare setups
 </Btn>
 </div>
 </div>
 <div className="flex items-center justify-center">
 <SimulationCoreVisual />
 </div>
 </div>
 </Panel>
 );
}
