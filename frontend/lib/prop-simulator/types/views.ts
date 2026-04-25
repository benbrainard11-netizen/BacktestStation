// Composite view types — assembled for list, compare, and detail pages.

import type { FirmRuleProfile, PoolBacktestSummary } from "./firm";
import type {
  FailureReason,
  FanBands,
  RiskSweepRow,
  RuleViolationEventType,
  SamplingMode,
  SelectedPath,
  SimulationAggregatedStats,
  SimulationRunConfig,
} from "./simulation";
import type { SimulatorConfidenceScore } from "./confidence";

export interface SimulationRunListRow {
  simulation_id: string;
  name: string;
  strategy_name: string;
  backtests_used: number;
  firm_name: string;
  account_size: number;
  sampling_mode: SamplingMode;
  simulation_count: number;
  risk_label: string;
  pass_rate: number;
  fail_rate: number;
  payout_rate: number;
  ev_after_fees: number;
  confidence: number;
  created_at: string;
}

export interface CompareSetupRow {
  setup_id: string;
  setup_label: string;
  firm_name: string;
  account_size: number;
  risk_label: string;
  sampling_mode: SamplingMode;
  pass_rate: number;
  payout_rate: number;
  fail_rate: number;
  avg_days_to_pass: number;
  average_dd_usage_percent: number;
  ev_after_fees: number;
  confidence: number;
  main_failure_reason: FailureReason;
}

export interface DailyPnL {
  date: string; // ISO yyyy-mm-dd
  pnl: number;
  trades: number;
}

export interface SimulationRunDetail {
  config: SimulationRunConfig;
  firm: FirmRuleProfile;
  pool_backtests: PoolBacktestSummary[];
  aggregated: SimulationAggregatedStats;
  risk_sweep: RiskSweepRow[] | null;
  selected_paths: SelectedPath[];
  fan_bands: FanBands;
  rule_violation_counts: Record<RuleViolationEventType, number>;
  confidence: SimulatorConfidenceScore;
  /** Daily P&L for the underlying backtest that fed this run — used by
   *  the calendar heatmap on the dashboard. */
  daily_pnl: DailyPnL[];
}

export interface FirmRuleStatusSummary {
  total: number;
  verified: number;
  unverified: number;
  demo: number;
}

export interface DashboardSummary {
  total_simulations: number;
  recent_runs: SimulationRunListRow[];
  best_setup: CompareSetupRow | null;
  highest_ev_setup: CompareSetupRow | null;
  safest_pass_setup: CompareSetupRow | null;
  risk_sweep_preview: RiskSweepRow[];
  firm_rule_status: FirmRuleStatusSummary;
}
