// MOCK firm rule profiles — fallback ONLY when /api/prop-firm/presets is
// unreachable. The backend's PRESETS dict in
// backend/app/services/prop_firm.py is the source of truth.
//
// Values here mirror the backend presets as of late 2025 so the
// fallback view doesn't look obviously stale. All entries are flagged
// `verification_status: "unverified"` — every prop firm changes rules
// constantly, so users should verify against the source_url before
// trusting these numbers.

import type { FirmRuleProfile } from "../types/firm";

type SeedInput = {
  key: string;
  firm_name: string;
  account_name: string;
  account_size: number;
  profit_target: number;
  max_drawdown: number;
  daily_loss_limit: number | null;
  trailing_type: FirmRuleProfile["trailing_drawdown_type"];
  minimum_trading_days: number | null;
  consistency_pct: number | null;
  max_contracts: number | null;
  payout_min_days: number | null;
  payout_min_profit: number | null;
  payout_split: number; // 0.9 = 90%
  eval_fee: number;
  activation_fee: number;
  reset_fee: number;
  monthly_fee: number;
  source_url: string;
  notes: string;
};

const VERIFY_PREFIX =
  "Approximation as of late 2025 — verify current rules at the source URL before trusting. ";

function profile(input: SeedInput): FirmRuleProfile {
  return {
    profile_id: input.key,
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

    consistency_rule_enabled: input.consistency_pct !== null,
    consistency_rule_type:
      input.consistency_pct !== null ? "best_day_pct_of_total" : "none",
    consistency_rule_value: input.consistency_pct,

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
    monthly_fee: input.monthly_fee,
    refund_rules: null,

    rule_source_url: input.source_url,
    rule_last_verified_at: "2025-12-01",
    verification_status: "unverified",
    notes: VERIFY_PREFIX + input.notes,
    version: 1,
    active: true,
  };
}

const SEEDS: SeedInput[] = [
  {
    key: "topstep_50k",
    firm_name: "Topstep",
    account_name: "Topstep 50K Combine",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_000,
    daily_loss_limit: 1_000,
    trailing_type: "end_of_day",
    minimum_trading_days: 5,
    consistency_pct: 0.5,
    max_contracts: null,
    payout_min_days: 5,
    payout_min_profit: null,
    payout_split: 0.9,
    eval_fee: 165,
    activation_fee: 0,
    reset_fee: 0,
    monthly_fee: 165,
    source_url: "https://www.topstep.com/",
    notes:
      "Trading Combine: $3K target, $2K trailing EOD drawdown, $1K daily loss limit, 50% consistency. Subscription model, no separate activation/reset.",
  },
  {
    key: "apex_50k",
    firm_name: "Apex",
    account_name: "Apex 50K Eval",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_500,
    daily_loss_limit: null,
    trailing_type: "intraday",
    minimum_trading_days: 8,
    consistency_pct: null,
    max_contracts: null,
    payout_min_days: 8,
    payout_min_profit: null,
    payout_split: 0.9,
    eval_fee: 167,
    activation_fee: 130,
    reset_fee: 80,
    monthly_fee: 97,
    source_url: "https://apextraderfunding.com/",
    notes:
      "Apex Trader Funding $50K Eval: $3K target, $2.5K intraday trailing, no daily loss limit, no consistency rule (removed late 2024). 100% of first $25K then 90/10.",
  },
  {
    key: "alpha_futures_50k",
    firm_name: "Alpha Futures",
    account_name: "Alpha Futures 50K",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_500,
    daily_loss_limit: 1_250,
    trailing_type: "end_of_day",
    minimum_trading_days: 5,
    consistency_pct: 0.4,
    max_contracts: null,
    payout_min_days: 5,
    payout_min_profit: 1_000,
    payout_split: 0.9,
    eval_fee: 140,
    activation_fee: 99,
    reset_fee: 49,
    monthly_fee: 0,
    source_url: "https://www.alphafutures.com/",
    notes:
      "Alpha Futures $50K eval: $3K target, $2.5K EOD trailing, $1.25K daily loss, 30-40% consistency varies by program.",
  },
  {
    key: "take_profit_trader_50k",
    firm_name: "Take Profit Trader",
    account_name: "Take Profit Trader 50K PRO",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_000,
    daily_loss_limit: 1_200,
    trailing_type: "static",
    minimum_trading_days: 5,
    consistency_pct: 0.5,
    max_contracts: null,
    payout_min_days: 7,
    payout_min_profit: 500,
    payout_split: 0.8,
    eval_fee: 150,
    activation_fee: 130,
    reset_fee: 99,
    monthly_fee: 0,
    source_url: "https://www.takeprofittrader.com/",
    notes:
      "TPT $50K PRO: $3K target, $2K STATIC drawdown (no trail), $1.2K daily loss, 50% consistency. 80% then 90% after first $10K paid.",
  },
  {
    key: "my_funded_futures_50k",
    firm_name: "MyFundedFutures",
    account_name: "MyFundedFutures Starter 50K",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_000,
    daily_loss_limit: null,
    trailing_type: "intraday",
    minimum_trading_days: 1,
    consistency_pct: null,
    max_contracts: null,
    payout_min_days: 5,
    payout_min_profit: 500,
    payout_split: 0.9,
    eval_fee: 80,
    activation_fee: 0,
    reset_fee: 65,
    monthly_fee: 80,
    source_url: "https://myfundedfutures.com/",
    notes:
      "MFFU Starter $50K: $3K target, $2K trailing, no daily loss limit, no consistency. Cheap monthly subscription. 100% of first $10K then 90/10.",
  },
  {
    key: "tradeify_50k",
    firm_name: "Tradeify",
    account_name: "Tradeify 50K Growth",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_000,
    daily_loss_limit: 1_250,
    trailing_type: "end_of_day",
    minimum_trading_days: 5,
    consistency_pct: 0.4,
    max_contracts: null,
    payout_min_days: 7,
    payout_min_profit: 750,
    payout_split: 0.9,
    eval_fee: 125,
    activation_fee: 100,
    reset_fee: 80,
    monthly_fee: 0,
    source_url: "https://tradeify.co/",
    notes:
      "Tradeify $50K Growth: $3K target, $2K EOD trailing, $1.25K daily loss, ~40% consistency.",
  },
  {
    key: "earn2trade_50k",
    firm_name: "Earn2Trade",
    account_name: "Earn2Trade TCP 50K",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_500,
    daily_loss_limit: 1_100,
    trailing_type: "end_of_day",
    minimum_trading_days: 10,
    consistency_pct: 0.4,
    max_contracts: null,
    payout_min_days: 15,
    payout_min_profit: 1_000,
    payout_split: 0.8,
    eval_fee: 130,
    activation_fee: 150,
    reset_fee: 0,
    monthly_fee: 130,
    source_url: "https://earn2trade.com/",
    notes:
      "Earn2Trade Trader Career Path $50K equivalent: $3K target, $2.5K EOD trailing, $1.1K daily loss. Multi-stage program. 80/20 split.",
  },
  {
    key: "bulenox_50k",
    firm_name: "Bulenox",
    account_name: "Bulenox 50K",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_500,
    daily_loss_limit: null,
    trailing_type: "intraday",
    minimum_trading_days: 5,
    consistency_pct: null,
    max_contracts: null,
    payout_min_days: 5,
    payout_min_profit: null,
    payout_split: 0.9,
    eval_fee: 115,
    activation_fee: 0,
    reset_fee: 55,
    monthly_fee: 0,
    source_url: "https://bulenox.com/",
    notes:
      "Bulenox $50K Eval: $3K target, $2.5K intraday trailing, no daily loss limit, no consistency rule.",
  },
  {
    key: "fast_track_trading_50k",
    firm_name: "Fast Track Trading",
    account_name: "Fast Track Trading 50K",
    account_size: 50_000,
    profit_target: 2_500,
    max_drawdown: 2_000,
    daily_loss_limit: 1_000,
    trailing_type: "static",
    minimum_trading_days: 3,
    consistency_pct: 0.5,
    max_contracts: null,
    payout_min_days: 5,
    payout_min_profit: 500,
    payout_split: 0.85,
    eval_fee: 99,
    activation_fee: 75,
    reset_fee: 60,
    monthly_fee: 0,
    source_url: "https://fasttracktrading.com/",
    notes:
      "FTT $50K Accelerator: $2.5K target (notably lower), $2K static drawdown, $1K daily loss, 50% consistency. Among the cheapest evals. 85/15 split.",
  },
  {
    key: "ticktick_trader_50k",
    firm_name: "TickTickTrader",
    account_name: "TickTickTrader 50K Classic",
    account_size: 50_000,
    profit_target: 3_000,
    max_drawdown: 2_500,
    daily_loss_limit: 1_250,
    trailing_type: "end_of_day",
    minimum_trading_days: 5,
    consistency_pct: 0.4,
    max_contracts: null,
    payout_min_days: 10,
    payout_min_profit: 750,
    payout_split: 0.8,
    eval_fee: 110,
    activation_fee: 90,
    reset_fee: 70,
    monthly_fee: 0,
    source_url: "https://tickticktrader.com/",
    notes:
      "TTT $50K Classic: $3K target, $2.5K EOD trailing, $1.25K daily loss, ~40% consistency. 80/20 split.",
  },
];

export const MOCK_FIRMS: FirmRuleProfile[] = SEEDS.map(profile);

export function findMockFirm(profileId: string): FirmRuleProfile | undefined {
  return MOCK_FIRMS.find((f) => f.profile_id === profileId);
}
