"""Pydantic schemas for the Monte Carlo prop firm simulator.

Mirrors `frontend/lib/prop-simulator/types/{simulation,firm,confidence,
views}.ts` so the openapi -> TS regeneration produces matching shapes.

Some fields are best-effort placeholders (e.g. confidence sub-scores
are heuristic, not deeply researched). Fields the UI shows but the
backend can't compute meaningfully yet are documented inline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SamplingMode = Literal["trade_bootstrap", "day_bootstrap", "regime_bootstrap"]
PhaseMode = Literal["eval_only", "funded_only", "eval_to_payout"]
RiskMode = Literal[
    "fixed_dollar", "fixed_contracts", "percent_balance", "risk_sweep"
]
SequenceFinalStatus = Literal[
    "passed", "failed", "payout_reached", "expired"
]
FailureReason = Literal[
    "daily_loss_limit",
    "trailing_drawdown",
    "max_drawdown",
    "consistency_rule",
    "payout_blocked",
    "min_days_not_met",
    "account_expired",
    "max_trades_reached",
    "other",
]
RuleViolationEventType = Literal[
    "daily_loss_limit",
    "trailing_drawdown",
    "profit_target_hit",
    "consistency_rule",
    "payout_eligible",
    "payout_blocked",
    "max_contracts_exceeded",
    "minimum_days_not_met",
]
ConfidenceLabel = Literal["low", "moderate", "high", "very_high"]
DistributionMetric = Literal["final_balance", "ev_after_fees", "max_drawdown"]


# --- Request --------------------------------------------------------------


class SimulationRunRequest(BaseModel):
    """POST /api/prop-firm/simulations body."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=120)
    selected_backtest_ids: list[int] = Field(..., min_length=1)
    firm_profile_id: str = Field(..., min_length=1)
    account_size: float = Field(..., gt=0)
    starting_balance: float = Field(..., gt=0)
    phase_mode: PhaseMode = "eval_only"

    sampling_mode: SamplingMode = "trade_bootstrap"
    simulation_count: int = Field(default=500, ge=10, le=10_000)
    max_trades_per_sequence: int | None = None
    max_days_per_sequence: int | None = None
    use_replacement: bool = True
    random_seed: int = 42

    risk_mode: RiskMode = "fixed_dollar"
    risk_per_trade: float | None = Field(default=200.0, gt=0)
    risk_sweep_values: list[float] | None = None

    commission_override: float | None = None
    slippage_override: float | None = None

    daily_trade_limit: int | None = None
    daily_loss_stop: float | None = None
    daily_profit_stop: float | None = None
    walkaway_after_winner: bool = False
    reduce_risk_after_loss: bool = False
    max_losses_per_day: int | None = None
    copy_trade_accounts: int = 1

    fees_enabled: bool = True
    payout_rules_enabled: bool = True
    notes: str = ""


# --- Sub-shapes for results ----------------------------------------------


class ConfidenceInterval(BaseModel):
    value: float
    low: float
    high: float


class DistributionStats(BaseModel):
    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    p10: float
    p25: float
    p75: float
    p90: float
    iqr: float
    spread: float


class DistributionBucket(BaseModel):
    range_low: float
    range_high: float
    count: int


class OutcomeDistribution(BaseModel):
    metric: DistributionMetric
    stats: DistributionStats
    buckets: list[DistributionBucket]


class SimulationAggregatedStats(BaseModel):
    pass_rate: ConfidenceInterval
    fail_rate: ConfidenceInterval
    payout_rate: ConfidenceInterval
    average_final_balance: float
    median_final_balance: float
    std_dev_final_balance: float
    p10_final_balance: float
    p25_final_balance: float
    p75_final_balance: float
    p90_final_balance: float
    average_days_to_pass: ConfidenceInterval
    median_days_to_pass: float
    average_trades_to_pass: float
    median_trades_to_pass: float
    average_max_drawdown: float
    median_max_drawdown: float
    worst_max_drawdown: float
    average_drawdown_usage: ConfidenceInterval
    median_drawdown_usage: float
    average_payout: float
    median_payout: float
    expected_value_before_fees: float
    expected_value_after_fees: ConfidenceInterval
    std_dev_ev_after_fees: float
    average_fees_paid: float
    most_common_failure_reason: FailureReason | None
    daily_loss_failure_rate: float
    trailing_drawdown_failure_rate: float
    consistency_failure_rate: float
    profit_target_hit_rate: float
    payout_blocked_rate: float
    final_balance_distribution: OutcomeDistribution
    ev_after_fees_distribution: OutcomeDistribution
    max_drawdown_distribution: OutcomeDistribution


class RiskSweepRow(BaseModel):
    risk_per_trade: float
    pass_rate: float
    fail_rate: float
    payout_rate: float
    avg_days_to_pass: float
    average_dd_usage_percent: float
    ev_after_fees: float
    main_failure_reason: FailureReason | None


SelectedPathBucket = Literal["best", "worst", "median", "near_fail", "near_pass"]


class SelectedPath(BaseModel):
    bucket: SelectedPathBucket
    sequence_number: int
    final_status: SequenceFinalStatus
    days: int
    trades: int
    ending_balance: float
    max_drawdown_usage_percent: float
    failure_reason: FailureReason | None
    equity_curve: list[float]


class FanBands(BaseModel):
    starting_balance: float
    median: list[float]
    p10: list[float]
    p25: list[float]
    p75: list[float]
    p90: list[float]


class SimulatorConfidenceSubscores(BaseModel):
    monte_carlo_stability: float
    trade_pool_quality: float
    day_pool_quality: float
    firm_rule_accuracy: float
    risk_model_accuracy: float
    sampling_method_quality: float
    backtest_input_quality: float


class SimulatorConfidenceScore(BaseModel):
    overall: float
    label: ConfidenceLabel
    subscores: SimulatorConfidenceSubscores
    weaknesses: list[str]
    sequence_count: int
    convergence_stability: float


class SimulationRunConfigOut(BaseModel):
    """Echo of the request shape for the run-detail page's config panel."""

    simulation_id: str
    name: str
    created_at: str

    selected_backtest_ids: list[int]
    selected_strategy_ids: list[int]

    firm_profile_id: str
    account_size: float
    starting_balance: float
    phase_mode: PhaseMode

    sampling_mode: SamplingMode
    simulation_count: int
    max_trades_per_sequence: int | None
    max_days_per_sequence: int | None
    use_replacement: bool
    random_seed: int

    risk_mode: RiskMode
    risk_per_trade: float | None
    risk_sweep_values: list[float] | None

    commission_override: float | None
    slippage_override: float | None

    daily_trade_limit: int | None
    daily_loss_stop: float | None
    daily_profit_stop: float | None
    walkaway_after_winner: bool
    reduce_risk_after_loss: bool
    max_losses_per_day: int | None
    copy_trade_accounts: int

    fees_enabled: bool
    payout_rules_enabled: bool
    notes: str


# --- Firm rule profile (echo of frontend FirmRuleProfile) -----------------


class FirmRuleProfile(BaseModel):
    profile_id: str
    firm_name: str
    account_name: str
    account_size: float
    phase_type: Literal["evaluation", "funded", "payout"] = "evaluation"

    profit_target: float | None
    max_drawdown: float
    daily_loss_limit: float | None

    trailing_drawdown_enabled: bool = False
    trailing_drawdown_type: Literal[
        "intraday", "end_of_day", "static", "none"
    ] = "none"
    trailing_drawdown_stop_level: float | None = None

    minimum_trading_days: int | None = None
    maximum_trading_days: int | None = None
    max_contracts: int | None = None

    scaling_plan_enabled: bool = False
    scaling_plan_rules: list[dict[str, Any]] = Field(default_factory=list)

    consistency_rule_enabled: bool = False
    consistency_rule_type: Literal[
        "best_day_pct_of_total", "min_trading_days", "max_daily_swing", "none"
    ] = "none"
    consistency_rule_value: float | None = None

    news_trading_allowed: bool = True
    overnight_holding_allowed: bool = False
    weekend_holding_allowed: bool = False
    copy_trading_allowed: bool = True

    payout_min_days: int | None = None
    payout_min_profit: float | None = None
    payout_cap: float | None = None
    payout_split: float = 0.9
    first_payout_rules: str | None = None
    recurring_payout_rules: str | None = None

    eval_fee: float = 0.0
    activation_fee: float = 0.0
    reset_fee: float = 0.0
    monthly_fee: float = 0.0
    refund_rules: str | None = None

    rule_source_url: str | None = None
    rule_last_verified_at: str | None = None
    verification_status: Literal["verified", "unverified", "demo"] = "demo"
    notes: str = ""
    version: int = 1
    active: bool = True


class PoolBacktestSummary(BaseModel):
    backtest_id: int
    strategy_id: int
    strategy_name: str
    strategy_version: str
    symbol: str
    market: str
    timeframe: str
    start_date: str
    end_date: str
    data_source: str
    commission_model: str
    slippage_model: str
    initial_balance: float
    confidence_score: float
    trade_count: int
    day_count: int


class DailyPnL(BaseModel):
    date: str
    pnl: float
    trades: int


class SimulationRunDetail(BaseModel):
    """Full run-detail payload consumed by /prop-simulator/runs/[id]."""

    config: SimulationRunConfigOut
    firm: FirmRuleProfile
    pool_backtests: list[PoolBacktestSummary]
    aggregated: SimulationAggregatedStats
    risk_sweep: list[RiskSweepRow] | None = None
    selected_paths: list[SelectedPath]
    fan_bands: FanBands
    rule_violation_counts: dict[str, int]
    confidence: SimulatorConfidenceScore
    daily_pnl: list[DailyPnL]


# --- List-row + dashboard shapes -----------------------------------------


class SimulationRunListRow(BaseModel):
    simulation_id: str
    name: str
    strategy_name: str
    backtests_used: int
    firm_name: str
    account_size: float
    sampling_mode: SamplingMode
    simulation_count: int
    risk_label: str
    pass_rate: float
    fail_rate: float
    payout_rate: float
    ev_after_fees: float
    confidence: float
    created_at: str
