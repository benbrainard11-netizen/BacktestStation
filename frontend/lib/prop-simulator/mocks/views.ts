// MOCK aggregated views — dashboard + compare page data.

import type { CompareSetupRow, DashboardSummary } from "../types/views";
import { MOCK_FIRMS } from "./firms";
import { MOCK_SIMULATION_RUNS_LIST } from "./runs";

export const MOCK_COMPARE_ROWS: CompareSetupRow[] = [
  {
    setup_id: "cmp-001",
    setup_label: "Topstep 50K · $100 day boot",
    firm_name: "Topstep",
    account_size: 50_000,
    risk_label: "$100",
    sampling_mode: "day_bootstrap",
    pass_rate: 0.612,
    payout_rate: 0.448,
    fail_rate: 0.388,
    avg_days_to_pass: 18.4,
    average_dd_usage_percent: 0.39,
    ev_after_fees: 412,
    confidence: 68,
    main_failure_reason: "trailing_drawdown",
  },
  {
    setup_id: "cmp-002",
    setup_label: "Apex 50K · $150 trade boot",
    firm_name: "Apex",
    account_size: 50_000,
    risk_label: "$150",
    sampling_mode: "trade_bootstrap",
    pass_rate: 0.489,
    payout_rate: 0.311,
    fail_rate: 0.511,
    avg_days_to_pass: 12.6,
    average_dd_usage_percent: 0.58,
    ev_after_fees: -88,
    confidence: 61,
    main_failure_reason: "trailing_drawdown",
  },
  {
    setup_id: "cmp-003",
    setup_label: "Alpha Futures 50K · $100",
    firm_name: "Alpha Futures",
    account_size: 50_000,
    risk_label: "$100",
    sampling_mode: "day_bootstrap",
    pass_rate: 0.574,
    payout_rate: 0.401,
    fail_rate: 0.426,
    avg_days_to_pass: 20.1,
    average_dd_usage_percent: 0.37,
    ev_after_fees: 291,
    confidence: 72,
    main_failure_reason: "account_expired",
  },
  {
    setup_id: "cmp-004",
    setup_label: "MyFundedFutures 50K · $100",
    firm_name: "MyFundedFutures",
    account_size: 50_000,
    risk_label: "$100",
    sampling_mode: "trade_bootstrap",
    pass_rate: 0.659,
    payout_rate: 0.503,
    fail_rate: 0.341,
    avg_days_to_pass: 14.2,
    average_dd_usage_percent: 0.44,
    ev_after_fees: 512,
    confidence: 58,
    main_failure_reason: "payout_blocked",
  },
  {
    setup_id: "cmp-005",
    setup_label: "Tradeify 50K · $150",
    firm_name: "Tradeify",
    account_size: 50_000,
    risk_label: "$150",
    sampling_mode: "day_bootstrap",
    pass_rate: 0.551,
    payout_rate: 0.371,
    fail_rate: 0.449,
    avg_days_to_pass: 11.8,
    average_dd_usage_percent: 0.54,
    ev_after_fees: 184,
    confidence: 64,
    main_failure_reason: "trailing_drawdown",
  },
  {
    setup_id: "cmp-006",
    setup_label: "Apex 50K · $300 aggressive",
    firm_name: "Apex",
    account_size: 50_000,
    risk_label: "$300",
    sampling_mode: "trade_bootstrap",
    pass_rate: 0.321,
    payout_rate: 0.184,
    fail_rate: 0.679,
    avg_days_to_pass: 4.9,
    average_dd_usage_percent: 0.83,
    ev_after_fees: -244,
    confidence: 59,
    main_failure_reason: "trailing_drawdown",
  },
];

function highestBy<T>(rows: T[], key: (r: T) => number): T | null {
  if (rows.length === 0) return null;
  return rows.reduce((best, row) => (key(row) > key(best) ? row : best));
}

const BEST_SETUP = highestBy(
  MOCK_COMPARE_ROWS,
  (r) => r.pass_rate * 0.4 + r.payout_rate * 0.3 + (r.ev_after_fees / 1000) * 0.3,
);

const HIGHEST_EV_SETUP = highestBy(MOCK_COMPARE_ROWS, (r) => r.ev_after_fees);
const SAFEST_PASS_SETUP = highestBy(MOCK_COMPARE_ROWS, (r) => r.pass_rate - r.average_dd_usage_percent);

export const MOCK_DASHBOARD_SUMMARY: DashboardSummary = {
  total_simulations: MOCK_SIMULATION_RUNS_LIST.length,
  recent_runs: MOCK_SIMULATION_RUNS_LIST.slice(0, 5),
  best_setup: BEST_SETUP,
  highest_ev_setup: HIGHEST_EV_SETUP,
  safest_pass_setup: SAFEST_PASS_SETUP,
  risk_sweep_preview: [
    { risk_per_trade: 50, pass_rate: 0.732, fail_rate: 0.268, payout_rate: 0.411, avg_days_to_pass: 24.8, average_dd_usage_percent: 0.28, ev_after_fees: 189, main_failure_reason: "account_expired" },
    { risk_per_trade: 100, pass_rate: 0.712, fail_rate: 0.288, payout_rate: 0.448, avg_days_to_pass: 18.4, average_dd_usage_percent: 0.39, ev_after_fees: 412, main_failure_reason: "account_expired" },
    { risk_per_trade: 150, pass_rate: 0.687, fail_rate: 0.313, payout_rate: 0.493, avg_days_to_pass: 13.1, average_dd_usage_percent: 0.52, ev_after_fees: 721, main_failure_reason: "trailing_drawdown" },
    { risk_per_trade: 200, pass_rate: 0.624, fail_rate: 0.376, payout_rate: 0.461, avg_days_to_pass: 10.4, average_dd_usage_percent: 0.62, ev_after_fees: 683, main_failure_reason: "trailing_drawdown" },
    { risk_per_trade: 250, pass_rate: 0.554, fail_rate: 0.446, payout_rate: 0.410, avg_days_to_pass: 7.8, average_dd_usage_percent: 0.71, ev_after_fees: 603, main_failure_reason: "trailing_drawdown" },
    { risk_per_trade: 300, pass_rate: 0.421, fail_rate: 0.579, payout_rate: 0.297, avg_days_to_pass: 5.8, average_dd_usage_percent: 0.83, ev_after_fees: 211, main_failure_reason: "trailing_drawdown" },
    { risk_per_trade: 500, pass_rate: 0.249, fail_rate: 0.751, payout_rate: 0.162, avg_days_to_pass: 3.2, average_dd_usage_percent: 0.94, ev_after_fees: -188, main_failure_reason: "trailing_drawdown" },
  ],
  firm_rule_status: {
    total: MOCK_FIRMS.length,
    verified: 0,
    unverified: 0,
    demo: MOCK_FIRMS.length,
  },
};
