// MOCK canonical simulation run detail — used by /runs/[id].

import type {
  DistributionBucket,
  FanBands,
  RiskSweepRow,
  SelectedPath,
  SimulationAggregatedStats,
  SimulationRunConfig,
} from "../types/simulation";
import type { SimulatorConfidenceScore } from "../types/confidence";
import type { SimulationRunDetail } from "../types/views";
import { MOCK_FIRMS, findMockFirm } from "./firms";
import { MOCK_POOL_BACKTESTS, MOCK_SIMULATION_RUNS_LIST } from "./runs";

const MOCK_RUN_CONFIG: SimulationRunConfig = {
  simulation_id: "sim-001",
  name: "Topstep 50K · $100 risk · day bootstrap",
  created_at: "2026-04-23T19:24:00Z",
  selected_backtest_ids: [1, 2],
  selected_strategy_ids: [1],
  firm_profile_id: MOCK_FIRMS[0].profile_id,
  account_size: 50_000,
  starting_balance: 50_000,
  phase_mode: "eval_to_payout",
  sampling_mode: "day_bootstrap",
  simulation_count: 10_000,
  max_trades_per_sequence: null,
  max_days_per_sequence: 30,
  use_replacement: true,
  random_seed: 42,
  risk_mode: "fixed_dollar",
  risk_per_trade: 100,
  risk_sweep_values: null,
  commission_override: null,
  slippage_override: null,
  daily_trade_limit: null,
  daily_loss_stop: 800,
  daily_profit_stop: null,
  walkaway_after_winner: false,
  reduce_risk_after_loss: false,
  max_losses_per_day: 3,
  copy_trade_accounts: 1,
  fees_enabled: true,
  payout_rules_enabled: true,
  notes: "Baseline demo simulation — numbers are fake.",
};

function gaussianHistogram(
  mean: number,
  stdDev: number,
  totalCount: number,
  bins: number,
  lower: number,
  upper: number,
): DistributionBucket[] {
  const binWidth = (upper - lower) / bins;
  const densities = Array.from({ length: bins }, (_, i) => {
    const center = lower + (i + 0.5) * binWidth;
    const z = (center - mean) / stdDev;
    return Math.exp(-0.5 * z * z);
  });
  const sumD = densities.reduce((a, b) => a + b, 0);
  return densities.map((d, i) => {
    const start = lower + i * binWidth;
    return {
      range_low: start,
      range_high: start + binWidth,
      count: Math.round((d / sumD) * totalCount),
    };
  });
}

const FINAL_BALANCE_MEAN = 51_920;
const FINAL_BALANCE_STDDEV = 2_050;
const FINAL_BALANCE_MIN = 47_810;
const FINAL_BALANCE_MAX = 55_120;
const FINAL_BALANCE_P10 = 47_980;
const FINAL_BALANCE_P25 = 49_740;
const FINAL_BALANCE_P75 = 53_420;
const FINAL_BALANCE_P90 = 54_560;

const MOCK_RUN_AGGREGATED: SimulationAggregatedStats = {
  pass_rate: { value: 0.612, low: 0.604, high: 0.623 },
  fail_rate: { value: 0.388, low: 0.377, high: 0.396 },
  payout_rate: { value: 0.448, low: 0.439, high: 0.458 },
  average_final_balance: FINAL_BALANCE_MEAN,
  median_final_balance: 52_100,
  std_dev_final_balance: FINAL_BALANCE_STDDEV,
  p10_final_balance: FINAL_BALANCE_P10,
  p25_final_balance: FINAL_BALANCE_P25,
  p75_final_balance: FINAL_BALANCE_P75,
  p90_final_balance: FINAL_BALANCE_P90,
  average_days_to_pass: { value: 18.4, low: 17.9, high: 19.0 },
  median_days_to_pass: 17,
  average_trades_to_pass: 41.2,
  median_trades_to_pass: 38,
  average_max_drawdown: 780,
  median_max_drawdown: 720,
  worst_max_drawdown: 2_040,
  average_drawdown_usage: { value: 0.39, low: 0.37, high: 0.41 },
  median_drawdown_usage: 0.36,
  average_payout: 720,
  median_payout: 500,
  expected_value_before_fees: 612,
  expected_value_after_fees: { value: 412, low: 284, high: 538 },
  std_dev_ev_after_fees: 127,
  average_fees_paid: 201,
  most_common_failure_reason: "trailing_drawdown",
  daily_loss_failure_rate: 0.112,
  trailing_drawdown_failure_rate: 0.201,
  consistency_failure_rate: 0.048,
  profit_target_hit_rate: 0.612,
  payout_blocked_rate: 0.164,
  final_balance_distribution: {
    metric: "final_balance",
    stats: {
      mean: FINAL_BALANCE_MEAN,
      median: 52_100,
      std_dev: FINAL_BALANCE_STDDEV,
      min: FINAL_BALANCE_MIN,
      max: FINAL_BALANCE_MAX,
      p10: FINAL_BALANCE_P10,
      p25: FINAL_BALANCE_P25,
      p75: FINAL_BALANCE_P75,
      p90: FINAL_BALANCE_P90,
      iqr: FINAL_BALANCE_P75 - FINAL_BALANCE_P25,
      spread: FINAL_BALANCE_P90 - FINAL_BALANCE_P10,
    },
    buckets: gaussianHistogram(
      FINAL_BALANCE_MEAN,
      FINAL_BALANCE_STDDEV,
      10_000,
      30,
      45_000,
      58_000,
    ),
  },
  ev_after_fees_distribution: {
    metric: "ev_after_fees",
    stats: {
      mean: 412,
      median: 388,
      std_dev: 127,
      min: -640,
      max: 1_412,
      p10: 224,
      p25: 312,
      p75: 528,
      p90: 612,
      iqr: 528 - 312,
      spread: 612 - 224,
    },
    buckets: gaussianHistogram(412, 127, 10_000, 30, -700, 1_500),
  },
  max_drawdown_distribution: {
    metric: "max_drawdown",
    stats: {
      mean: 780,
      median: 720,
      std_dev: 360,
      min: 0,
      max: 2_040,
      p10: 280,
      p25: 460,
      p75: 1_020,
      p90: 1_280,
      iqr: 1_020 - 460,
      spread: 1_280 - 280,
    },
    buckets: gaussianHistogram(780, 360, 10_000, 30, 0, 2_100),
  },
};

const MOCK_RISK_SWEEP: RiskSweepRow[] = [
  { risk_per_trade: 50, pass_rate: 0.732, fail_rate: 0.268, payout_rate: 0.411, avg_days_to_pass: 24.8, average_dd_usage_percent: 0.28, ev_after_fees: 189, main_failure_reason: "account_expired" },
  { risk_per_trade: 100, pass_rate: 0.712, fail_rate: 0.288, payout_rate: 0.448, avg_days_to_pass: 18.4, average_dd_usage_percent: 0.39, ev_after_fees: 412, main_failure_reason: "account_expired" },
  { risk_per_trade: 150, pass_rate: 0.687, fail_rate: 0.313, payout_rate: 0.493, avg_days_to_pass: 13.1, average_dd_usage_percent: 0.52, ev_after_fees: 721, main_failure_reason: "trailing_drawdown" },
  { risk_per_trade: 200, pass_rate: 0.624, fail_rate: 0.376, payout_rate: 0.461, avg_days_to_pass: 10.4, average_dd_usage_percent: 0.62, ev_after_fees: 683, main_failure_reason: "trailing_drawdown" },
  { risk_per_trade: 250, pass_rate: 0.554, fail_rate: 0.446, payout_rate: 0.410, avg_days_to_pass: 7.8, average_dd_usage_percent: 0.71, ev_after_fees: 603, main_failure_reason: "trailing_drawdown" },
  { risk_per_trade: 300, pass_rate: 0.421, fail_rate: 0.579, payout_rate: 0.297, avg_days_to_pass: 5.8, average_dd_usage_percent: 0.83, ev_after_fees: 211, main_failure_reason: "trailing_drawdown" },
  { risk_per_trade: 500, pass_rate: 0.249, fail_rate: 0.751, payout_rate: 0.162, avg_days_to_pass: 3.2, average_dd_usage_percent: 0.94, ev_after_fees: -188, main_failure_reason: "trailing_drawdown" },
];

function curve(start: number, deltas: number[]): number[] {
  const out: number[] = [start];
  let balance = start;
  for (const d of deltas) {
    balance += d;
    out.push(balance);
  }
  return out;
}

const MOCK_SELECTED_PATHS: SelectedPath[] = [
  {
    bucket: "best",
    sequence_number: 742,
    final_status: "payout_reached",
    days: 9,
    trades: 24,
    ending_balance: 55_120,
    max_drawdown_usage_percent: 0.18,
    failure_reason: null,
    equity_curve: curve(50_000, [120, 280, -90, 320, 140, -80, 420, 180, 190, -60, 250, 320, 210, 180, -70, 340, 290, 160, 310, 240, -110, 350, 220, 120]),
  },
  {
    bucket: "near_pass",
    sequence_number: 3988,
    final_status: "passed",
    days: 19,
    trades: 44,
    ending_balance: 53_050,
    max_drawdown_usage_percent: 0.61,
    failure_reason: null,
    equity_curve: curve(50_000, [-140, -180, 120, -90, 240, -60, -120, 180, 160, -210, 280, 90, -80, 210, -140, 260, 180, -90, 320, 140, -60, 210, 180, -80, 180, 220, -70, 160]),
  },
  {
    bucket: "median",
    sequence_number: 5012,
    final_status: "passed",
    days: 17,
    trades: 38,
    ending_balance: 52_100,
    max_drawdown_usage_percent: 0.36,
    failure_reason: null,
    equity_curve: curve(50_000, [80, -40, 140, -60, 120, 180, -80, 160, 220, -100, 90, 140, -70, 180, 160, -40, 130, 210, -60, 180, 120, -50, 170, 140, -90, 160, 110, 180]),
  },
  {
    bucket: "near_fail",
    sequence_number: 2017,
    final_status: "failed",
    days: 7,
    trades: 18,
    ending_balance: 48_090,
    max_drawdown_usage_percent: 0.97,
    failure_reason: "trailing_drawdown",
    equity_curve: curve(50_000, [-180, 120, -240, -180, 140, -90, -220, 180, -140, -180, 110, -220, 140, -180, -260]),
  },
  {
    bucket: "worst",
    sequence_number: 9421,
    final_status: "failed",
    days: 3,
    trades: 8,
    ending_balance: 47_810,
    max_drawdown_usage_percent: 1,
    failure_reason: "daily_loss_limit",
    equity_curve: curve(50_000, [-220, -180, -240, -320, -280, -150, -240, -180]),
  },
];

const MOCK_RUN_CONFIDENCE: SimulatorConfidenceScore = {
  overall: 68,
  label: "moderate",
  subscores: {
    monte_carlo_stability: 94,
    trade_pool_quality: 71,
    day_pool_quality: 64,
    firm_rule_accuracy: 58,
    risk_model_accuracy: 80,
    sampling_method_quality: 72,
    backtest_input_quality: 74,
  },
  weaknesses: [
    "Firm rules not verified recently — sourced from demo profile.",
    "Day pool under 300 unique trading days limits session coverage.",
    "No regime-aware sampling yet (trend vs range days blended).",
  ],
  sequence_count: 10_000,
  convergence_stability: 94,
};

// Synthesize per-day percentile bands. Spread grows with sqrt(day) to
// mimic Brownian-ish dispersion; drift moves the median toward the
// observed run mean.
function generateFanBands(
  days: number,
  startingBalance: number,
  endingMean: number,
  endingSpread: number,
): FanBands {
  const median: number[] = [];
  const p10: number[] = [];
  const p25: number[] = [];
  const p75: number[] = [];
  const p90: number[] = [];
  const totalDrift = endingMean - startingBalance;
  for (let d = 0; d <= days; d++) {
    const t = d / days;
    const m = startingBalance + totalDrift * t;
    const sd = Math.sqrt(t) * (endingSpread / 1.28); // P90 = mean + 1.28σ
    median.push(m);
    p10.push(m - 1.28 * sd);
    p25.push(m - 0.67 * sd);
    p75.push(m + 0.67 * sd);
    p90.push(m + 1.28 * sd);
  }
  return { starting_balance: startingBalance, median, p10, p25, p75, p90 };
}

const MOCK_FAN_BANDS: FanBands = generateFanBands(
  28, // days span on x-axis
  50_000,
  FINAL_BALANCE_MEAN,
  FINAL_BALANCE_P90 - FINAL_BALANCE_MEAN,
);

const CANONICAL_RUN_DETAIL: SimulationRunDetail = {
  config: MOCK_RUN_CONFIG,
  firm: MOCK_FIRMS[0],
  pool_backtests: MOCK_POOL_BACKTESTS,
  aggregated: MOCK_RUN_AGGREGATED,
  risk_sweep: MOCK_RISK_SWEEP,
  selected_paths: MOCK_SELECTED_PATHS,
  fan_bands: MOCK_FAN_BANDS,
  rule_violation_counts: {
    daily_loss_limit: 1_121,
    trailing_drawdown: 2_014,
    profit_target_hit: 6_118,
    consistency_rule: 478,
    payout_eligible: 4_482,
    payout_blocked: 1_640,
    max_contracts_exceeded: 0,
    minimum_days_not_met: 318,
  },
  confidence: MOCK_RUN_CONFIDENCE,
};

export function findMockRunDetail(simulationId: string): SimulationRunDetail | undefined {
  const row = MOCK_SIMULATION_RUNS_LIST.find((r) => r.simulation_id === simulationId);
  if (!row) return undefined;

  const firm = findMockFirm(CANONICAL_RUN_DETAIL.firm.profile_id) ?? CANONICAL_RUN_DETAIL.firm;

  return {
    ...CANONICAL_RUN_DETAIL,
    firm,
    config: {
      ...CANONICAL_RUN_DETAIL.config,
      simulation_id: row.simulation_id,
      name: row.name,
      sampling_mode: row.sampling_mode,
      simulation_count: row.simulation_count,
      created_at: row.created_at,
    },
  };
}
