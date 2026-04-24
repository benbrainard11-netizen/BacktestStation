import Link from "next/link";
import { Plus } from "lucide-react";

import PageHeader from "@/components/PageHeader";
import DemoFirmsWarning from "@/components/prop-simulator/dashboard/DemoFirmsWarning";
import FirmRuleStatusPanel from "@/components/prop-simulator/dashboard/FirmRuleStatusPanel";
import QuickStatsRow from "@/components/prop-simulator/dashboard/QuickStatsRow";
import RecentRunsPanel from "@/components/prop-simulator/dashboard/RecentRunsPanel";
import RiskSweepSummaryPanel from "@/components/prop-simulator/dashboard/RiskSweepSummaryPanel";
import SetupHighlightPanel from "@/components/prop-simulator/dashboard/SetupHighlightPanel";
import { MOCK_DASHBOARD_SUMMARY } from "@/lib/prop-simulator/mocks";

export default function PropSimulatorDashboardPage() {
  const summary = MOCK_DASHBOARD_SUMMARY;

  return (
    <div className="pb-10">
      <div className="flex items-center justify-between px-6 pt-6">
        <div className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          Prop Firm Simulator
        </div>
        <Link
          href="/prop-simulator/new"
          className="inline-flex items-center gap-2 border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-zinc-100 hover:bg-zinc-800"
        >
          <Plus className="h-3 w-3" strokeWidth={1.75} aria-hidden="true" />
          New simulation
        </Link>
      </div>
      <PageHeader
        title="Simulator"
        description="Monte Carlo prop-firm projections across imported backtests, firm rule profiles, and risk settings."
        meta={`${summary.total_simulations} total runs`}
      />

      <div className="flex flex-col gap-4 px-6">
        <DemoFirmsWarning status={summary.firm_rule_status} />

        <QuickStatsRow summary={summary} />

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          <SetupHighlightPanel
            title="Best recent setup"
            subtitle="composite"
            setup={summary.best_setup}
          />
          <SetupHighlightPanel
            title="Highest EV setup"
            subtitle="ev after fees"
            setup={summary.highest_ev_setup}
          />
          <SetupHighlightPanel
            title="Safest pass setup"
            subtitle="pass − dd usage"
            setup={summary.safest_pass_setup}
          />
        </div>

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <RecentRunsPanel runs={summary.recent_runs} />
          </div>
          <FirmRuleStatusPanel summary={summary.firm_rule_status} />
        </div>

        <RiskSweepSummaryPanel rows={summary.risk_sweep_preview} />
      </div>
    </div>
  );
}
