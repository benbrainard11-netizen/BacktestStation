// Simulation configuration + per-sequence + aggregate + risk-sweep types.

export type SamplingMode =
  | "trade_bootstrap"
  | "day_bootstrap"
  | "regime_bootstrap";

export type PhaseMode = "eval_only" | "funded_only" | "eval_to_payout";

export type RiskMode =
  | "fixed_dollar"
  | "fixed_contracts"
  | "percent_balance"
  | "risk_sweep";

export interface SimulationRunConfig {
  simulation_id: string;
  name: string;
  created_at: string;

  selected_backtest_ids: number[];
  selected_strategy_ids: number[];

  firm_profile_id: string;
  account_size: number;
  starting_balance: number;
  phase_mode: PhaseMode;

  sampling_mode: SamplingMode;
  simulation_count: number;
  max_trades_per_sequence: number | null;
  max_days_per_sequence: number | null;
  use_replacement: boolean;
  random_seed: number;

  risk_mode: RiskMode;
  risk_per_trade: number | null;
  risk_sweep_values: number[] | null;

  commission_override: number | null;
  slippage_override: number | null;

  daily_trade_limit: number | null;
  daily_loss_stop: number | null;
  daily_profit_stop: number | null;
  walkaway_after_winner: boolean;
  reduce_risk_after_loss: boolean;
  max_losses_per_day: number | null;
  copy_trade_accounts: number;

  fees_enabled: boolean;
  payout_rules_enabled: boolean;
  notes: string;
}

export type SequenceFinalStatus =
  | "passed"
  | "failed"
  | "payout_reached"
  | "expired";

export type FailureReason =
  | "daily_loss_limit"
  | "trailing_drawdown"
  | "max_drawdown"
  | "consistency_rule"
  | "payout_blocked"
  | "min_days_not_met"
  | "account_expired"
  | "max_trades_reached"
  | "other"
  | null;

export interface SequenceSummary {
  sequence_id: string;
  simulation_id: string;
  sequence_number: number;
  final_status: SequenceFinalStatus;
  starting_balance: number;
  ending_balance: number;
  peak_balance: number;
  lowest_balance: number;
  max_drawdown: number;
  max_drawdown_percent: number;
  max_drawdown_usage_percent: number;
  profit_target_hit: boolean;
  days_to_pass: number | null;
  trades_to_pass: number | null;
  payout_eligible: boolean;
  payout_amount: number;
  fees_paid: number;
  net_ev_after_fees: number;
  failure_reason: FailureReason;
  failure_day: number | null;
  failure_trade: number | null;
  best_day_pnl: number;
  worst_day_pnl: number;
  longest_losing_streak: number;
  longest_winning_streak: number;
  average_daily_pnl: number;
  median_daily_pnl: number;
}

export type RuleViolationEventType =
  | "daily_loss_limit"
  | "trailing_drawdown"
  | "profit_target_hit"
  | "consistency_rule"
  | "payout_eligible"
  | "payout_blocked"
  | "max_contracts_exceeded"
  | "minimum_days_not_met";

export type RuleViolationSeverity = "info" | "warning" | "violation";

export interface RuleViolationEvent {
  event_id: string;
  simulation_id: string;
  sequence_id: string;
  event_type: RuleViolationEventType;
  event_day: number;
  event_trade_index: number | null;
  balance_before: number;
  balance_after: number;
  rule_threshold: number;
  distance_to_rule: number;
  message: string;
  severity: RuleViolationSeverity;
}

export interface ConfidenceInterval {
  value: number;
  low: number;
  high: number;
}

export interface DistributionStats {
  mean: number;
  median: number;
  std_dev: number;
  min: number;
  max: number;
  p10: number;
  p25: number;
  p75: number;
  p90: number;
  iqr: number;
  spread: number;
}

export interface DistributionBucket {
  range_low: number;
  range_high: number;
  count: number;
}

export type DistributionMetric =
  | "final_balance"
  | "ev_after_fees"
  | "max_drawdown";

export interface OutcomeDistribution {
  metric: DistributionMetric;
  stats: DistributionStats;
  buckets: DistributionBucket[];
}

export interface SimulationAggregatedStats {
  pass_rate: ConfidenceInterval;
  fail_rate: ConfidenceInterval;
  payout_rate: ConfidenceInterval;
  average_final_balance: number;
  median_final_balance: number;
  std_dev_final_balance: number;
  p10_final_balance: number;
  p25_final_balance: number;
  p75_final_balance: number;
  p90_final_balance: number;
  average_days_to_pass: ConfidenceInterval;
  median_days_to_pass: number;
  average_trades_to_pass: number;
  median_trades_to_pass: number;
  average_max_drawdown: number;
  median_max_drawdown: number;
  worst_max_drawdown: number;
  average_drawdown_usage: ConfidenceInterval;
  median_drawdown_usage: number;
  average_payout: number;
  median_payout: number;
  expected_value_before_fees: number;
  expected_value_after_fees: ConfidenceInterval;
  std_dev_ev_after_fees: number;
  average_fees_paid: number;
  most_common_failure_reason: FailureReason;
  daily_loss_failure_rate: number;
  trailing_drawdown_failure_rate: number;
  consistency_failure_rate: number;
  profit_target_hit_rate: number;
  payout_blocked_rate: number;
  /** Histogram + percentile stats for ending-balance shape. */
  final_balance_distribution: OutcomeDistribution;
  /** Histogram + percentile stats for EV after fees. */
  ev_after_fees_distribution: OutcomeDistribution;
  /** Histogram + percentile stats for max drawdown across sequences. */
  max_drawdown_distribution: OutcomeDistribution;
}

export interface RiskSweepRow {
  risk_per_trade: number;
  pass_rate: number;
  fail_rate: number;
  payout_rate: number;
  avg_days_to_pass: number;
  average_dd_usage_percent: number;
  ev_after_fees: number;
  main_failure_reason: FailureReason;
}

export type SelectedPathBucket =
  | "best"
  | "worst"
  | "median"
  | "near_fail"
  | "near_pass";

export interface SelectedPath {
  bucket: SelectedPathBucket;
  sequence_number: number;
  final_status: SequenceFinalStatus;
  days: number;
  trades: number;
  ending_balance: number;
  max_drawdown_usage_percent: number;
  failure_reason: FailureReason;
  equity_curve: number[];
}
