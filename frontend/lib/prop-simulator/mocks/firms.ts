// MOCK firm rule profiles for the Prop Firm Simulator UI scaffold.
//
// ALL entries here are DEMO. Every profile has:
//   - verification_status: "demo"
//   - rule_last_verified_at: null
//   - rule_source_url:        null
//
// Do NOT treat these numbers as the real rules for the firms listed. Prop
// firms change rules constantly; real rule ingestion is a later phase.

import type { FirmRuleProfile } from "../types/firm";

type DemoFirmInput = {
  firm_name: string;
  account_name: string;
  account_size: number;
  profit_target: number;
  max_drawdown: number;
  daily_loss_limit: number | null;
  trailing_type: FirmRuleProfile["trailing_drawdown_type"];
  minimum_trading_days: number | null;
  consistency_rule_value: number | null;
  max_contracts: number | null;
  payout_min_days: number | null;
  payout_min_profit: number | null;
  payout_split: number;
  eval_fee: number;
  activation_fee: number;
  reset_fee: number;
  notes?: string;
};

function demoProfile(input: DemoFirmInput, index: number): FirmRuleProfile {
  return {
    profile_id: `demo-${index + 1}`,
    firm_name: input.firm_name,
    account_name: input.account_name,
    account_size: input.account_size,
    phase_type: "evaluation",

    profit_target: input.profit_target,
    max_drawdown: input.max_drawdown,
    daily_loss_limit: input.daily_loss_limit,

    trailing_drawdown_enabled: input.trailing_type !== "none",
    trailing_drawdown_type: input.trailing_type,
    trailing_drawdown_stop_level: null,

    minimum_trading_days: input.minimum_trading_days,
    maximum_trading_days: null,
    max_contracts: input.max_contracts,

    scaling_plan_enabled: false,
    scaling_plan_rules: [],

    consistency_rule_enabled: input.consistency_rule_value !== null,
    consistency_rule_type: input.consistency_rule_value !== null
      ? "best_day_pct_of_total"
      : "none",
    consistency_rule_value: input.consistency_rule_value,

    news_trading_allowed: true,
    overnight_holding_allowed: false,
    weekend_holding_allowed: false,
    copy_trading_allowed: true,

    payout_min_days: input.payout_min_days,
    payout_min_profit: input.payout_min_profit,
    payout_cap: null,
    payout_split: input.payout_split,
    first_payout_rules: null,
    recurring_payout_rules: null,

    eval_fee: input.eval_fee,
    activation_fee: input.activation_fee,
    reset_fee: input.reset_fee,
    monthly_fee: 0,
    refund_rules: null,

    rule_source_url: null,
    rule_last_verified_at: null,
    verification_status: "demo",
    notes: input.notes ?? "Demo profile — edit before trusting.",
    version: 1,
    active: true,
  };
}

const DEMO_INPUTS: DemoFirmInput[] = [
  {
    firm_name: "Topstep",
    account_name: "50K Trading Combine",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_000,
    daily_loss_limit: 1_000,
    trailing_type: "end_of_day",
    minimum_trading_days: 2,
    consistency_rule_value: 0.5,
    max_contracts: 5,
    payout_min_days: 5,
    payout_min_profit: 500,
    payout_split: 90,
    eval_fee: 165,
    activation_fee: 149,
    reset_fee: 99,
  },
  {
    firm_name: "Apex",
    account_name: "50K Eval",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_500,
    daily_loss_limit: null,
    trailing_type: "intraday",
    minimum_trading_days: null,
    consistency_rule_value: null,
    max_contracts: 10,
    payout_min_days: 10,
    payout_min_profit: null,
    payout_split: 90,
    eval_fee: 147,
    activation_fee: 85,
    reset_fee: 80,
  },
  {
    firm_name: "Alpha Futures",
    account_name: "50K Alpha Eval",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_500,
    daily_loss_limit: 1_250,
    trailing_type: "end_of_day",
    minimum_trading_days: 5,
    consistency_rule_value: 0.35,
    max_contracts: 5,
    payout_min_days: 10,
    payout_min_profit: 1_000,
    payout_split: 90,
    eval_fee: 129,
    activation_fee: 99,
    reset_fee: 49,
  },
  {
    firm_name: "Take Profit Trader",
    account_name: "50K PRO",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_000,
    daily_loss_limit: 1_200,
    trailing_type: "static",
    minimum_trading_days: 5,
    consistency_rule_value: 0.5,
    max_contracts: 5,
    payout_min_days: 10,
    payout_min_profit: 500,
    payout_split: 80,
    eval_fee: 150,
    activation_fee: 130,
    reset_fee: 99,
  },
  {
    firm_name: "MyFundedFutures",
    account_name: "Starter 50K",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_000,
    daily_loss_limit: null,
    trailing_type: "intraday",
    minimum_trading_days: 3,
    consistency_rule_value: null,
    max_contracts: 5,
    payout_min_days: 3,
    payout_min_profit: 500,
    payout_split: 90,
    eval_fee: 80,
    activation_fee: 0,
    reset_fee: 65,
  },
  {
    firm_name: "Tradeify",
    account_name: "50K Growth",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_000,
    daily_loss_limit: 1_250,
    trailing_type: "end_of_day",
    minimum_trading_days: 5,
    consistency_rule_value: 0.4,
    max_contracts: 5,
    payout_min_days: 7,
    payout_min_profit: 750,
    payout_split: 90,
    eval_fee: 125,
    activation_fee: 100,
    reset_fee: 80,
  },
  {
    firm_name: "Earn2Trade",
    account_name: "Trader Career Path 50K",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_500,
    daily_loss_limit: 1_100,
    trailing_type: "end_of_day",
    minimum_trading_days: 10,
    consistency_rule_value: 0.4,
    max_contracts: 8,
    payout_min_days: 15,
    payout_min_profit: 1_000,
    payout_split: 80,
    eval_fee: 130,
    activation_fee: 150,
    reset_fee: 0,
  },
  {
    firm_name: "BulenoX",
    account_name: "50K Evaluation",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_500,
    daily_loss_limit: null,
    trailing_type: "intraday",
    minimum_trading_days: 5,
    consistency_rule_value: null,
    max_contracts: 10,
    payout_min_days: 5,
    payout_min_profit: null,
    payout_split: 90,
    eval_fee: 115,
    activation_fee: 0,
    reset_fee: 55,
  },
  {
    firm_name: "Fast Track Trading",
    account_name: "50K Accelerator",
    account_size: 50_000,
    profit_target: 2_500,
    max_drawdown: 2_000,
    daily_loss_limit: 1_000,
    trailing_type: "static",
    minimum_trading_days: 3,
    consistency_rule_value: 0.5,
    max_contracts: 5,
    payout_min_days: 5,
    payout_min_profit: 500,
    payout_split: 85,
    eval_fee: 99,
    activation_fee: 75,
    reset_fee: 60,
  },
  {
    firm_name: "TickTickTrader",
    account_name: "50K Classic",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_500,
    daily_loss_limit: 1_250,
    trailing_type: "end_of_day",
    minimum_trading_days: 5,
    consistency_rule_value: 0.4,
    max_contracts: 5,
    payout_min_days: 10,
    payout_min_profit: 750,
    payout_split: 80,
    eval_fee: 110,
    activation_fee: 90,
    reset_fee: 70,
  },
];

export const MOCK_FIRMS: FirmRuleProfile[] = DEMO_INPUTS.map((input, index) =>
  demoProfile(input, index),
);

export function findMockFirm(profileId: string): FirmRuleProfile | undefined {
  return MOCK_FIRMS.find((f) => f.profile_id === profileId);
}
