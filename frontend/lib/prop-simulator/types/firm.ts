// Firm rule profile + pool backtest metadata — the inputs to a simulation.

export type FirmPhaseType = "evaluation" | "funded" | "payout";

export type TrailingDrawdownType =
  | "intraday"
  | "end_of_day"
  | "static"
  | "none";

export type ConsistencyRuleType =
  | "best_day_pct_of_total"
  | "min_trading_days"
  | "max_daily_swing"
  | "none";

export type RuleVerificationStatus = "verified" | "unverified" | "demo";

export interface ScalingPlanRule {
  stage: string;
  min_balance: number;
  max_contracts: number;
}

export interface FirmRuleProfile {
  profile_id: string;
  firm_name: string;
  account_name: string;
  account_size: number;
  phase_type: FirmPhaseType;

  profit_target: number | null;
  max_drawdown: number;
  daily_loss_limit: number | null;

  trailing_drawdown_enabled: boolean;
  trailing_drawdown_type: TrailingDrawdownType;
  trailing_drawdown_stop_level: number | null;

  minimum_trading_days: number | null;
  maximum_trading_days: number | null;
  max_contracts: number | null;

  scaling_plan_enabled: boolean;
  scaling_plan_rules: ScalingPlanRule[];

  consistency_rule_enabled: boolean;
  consistency_rule_type: ConsistencyRuleType;
  consistency_rule_value: number | null;

  news_trading_allowed: boolean;
  overnight_holding_allowed: boolean;
  weekend_holding_allowed: boolean;
  copy_trading_allowed: boolean;

  payout_min_days: number | null;
  payout_min_profit: number | null;
  payout_cap: number | null;
  payout_split: number;
  first_payout_rules: string | null;
  recurring_payout_rules: string | null;

  eval_fee: number;
  activation_fee: number;
  reset_fee: number;
  monthly_fee: number;
  refund_rules: string | null;

  rule_source_url: string | null;
  rule_last_verified_at: string | null;
  verification_status: RuleVerificationStatus;
  notes: string;
  version: number;
  active: boolean;
}

export interface PoolBacktestSummary {
  backtest_id: number;
  strategy_id: number;
  strategy_name: string;
  strategy_version: string;
  symbol: string;
  market: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  data_source: string;
  commission_model: string;
  slippage_model: string;
  initial_balance: number;
  confidence_score: number;
  trade_count: number;
  day_count: number;
}
