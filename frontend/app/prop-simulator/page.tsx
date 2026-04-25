import DemoFirmsWarning from "@/components/prop-simulator/dashboard/DemoFirmsWarning";
import FirmRuleStatusPanel from "@/components/prop-simulator/dashboard/FirmRuleStatusPanel";
import QuickStatsRow from "@/components/prop-simulator/dashboard/QuickStatsRow";
import RecentRunsPanel from "@/components/prop-simulator/dashboard/RecentRunsPanel";
import RiskSweepSummaryPanel from "@/components/prop-simulator/dashboard/RiskSweepSummaryPanel";
import SamplePathsPanel from "@/components/prop-simulator/dashboard/SamplePathsPanel";
import SetupHighlightPanel from "@/components/prop-simulator/dashboard/SetupHighlightPanel";
import SimulationCorePanel from "@/components/prop-simulator/dashboard/SimulationCorePanel";
import { findMockRunDetail, MOCK_DASHBOARD_SUMMARY } from "@/lib/prop-simulator/mocks";

export default function PropSimulatorDashboardPage() {
  const summary = MOCK_DASHBOARD_SUMMARY;
  // Pull the canonical run detail so we can preview equity paths inline on
  // the dashboard. Fallback gracefully if the mock id ever moves.
  const featuredRun = findMockRunDetail("sim-001");

  return (
    <div className="flex flex-col gap-4 px-6 pb-10 pt-6">
      <SimulationCorePanel summary={summary} />

      <DemoFirmsWarning status={summary.firm_rule_status} />

      <QuickStatsRow summary={summary} />

      {featuredRun ? (
        <SamplePathsPanel
          paths={featuredRun.selected_paths}
          meta="featured run · sim-001 · 5 buckets"
        />
      ) : null}

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
  );
}
