import DailyPnLPanel from "@/components/prop-simulator/dashboard/DailyPnLPanel";
import DemoFirmsWarning from "@/components/prop-simulator/dashboard/DemoFirmsWarning";
import FirmRuleStatusPanel from "@/components/prop-simulator/dashboard/FirmRuleStatusPanel";
import QuickStatsRow from "@/components/prop-simulator/dashboard/QuickStatsRow";
import RecentRunsPanel from "@/components/prop-simulator/dashboard/RecentRunsPanel";
import RiskSweepSummaryPanel from "@/components/prop-simulator/dashboard/RiskSweepSummaryPanel";
import SamplePathsPanel from "@/components/prop-simulator/dashboard/SamplePathsPanel";
import SetupHighlightPanel from "@/components/prop-simulator/dashboard/SetupHighlightPanel";
import SimulationCorePanel from "@/components/prop-simulator/dashboard/SimulationCorePanel";
import OutcomeDistributionPanel from "@/components/prop-simulator/OutcomeDistributionPanel";
import { findMockRunDetail, MOCK_DASHBOARD_SUMMARY } from "@/lib/prop-simulator/mocks";

export default function PropSimulatorDashboardPage() {
 const summary = MOCK_DASHBOARD_SUMMARY;
 // Pull the canonical run detail so we can preview equity paths inline on
 // the dashboard. Fallback gracefully if the mock id ever moves.
 const featuredRun = findMockRunDetail("sim-001");

 return (
 <div className="flex flex-col gap-4 px-8 pb-10 pt-6 auto-enter">
 <SimulationCorePanel summary={summary} />

 <DemoFirmsWarning status={summary.firm_rule_status} />

 <QuickStatsRow summary={summary} />

 {featuredRun ? (
 <>
 <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
 <OutcomeDistributionPanel
 distributions={[
 featuredRun.aggregated.final_balance_distribution,
 featuredRun.aggregated.ev_after_fees_distribution,
 featuredRun.aggregated.max_drawdown_distribution,
 ]}
 meta="featured run · sim-001 · 10,000 sequences"
 />
 <SamplePathsPanel
 paths={featuredRun.selected_paths}
 fanBands={featuredRun.fan_bands}
 meta="featured run · sim-001 · envelope + paths"
 />
 </div>
 <DailyPnLPanel data={featuredRun.daily_pnl} />
 </>
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
