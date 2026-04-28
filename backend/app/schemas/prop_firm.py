"""Pydantic schemas for the prop-firm simulator."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PropFirmPresetRead(BaseModel):
    key: str
    name: str
    notes: str
    starting_balance: float
    profit_target: float
    max_drawdown: float
    trailing_drawdown: bool
    daily_loss_limit: float | None
    consistency_pct: float | None
    max_trades_per_day: int | None
    risk_per_trade_dollars: float
    # Display metadata — passthrough into the rendered FirmRuleProfile.
    # Defaults preserve backwards-compat for any preset that doesn't set them.
    trailing_drawdown_type: str = "none"
    minimum_trading_days: int | None = None
    payout_split: float = 0.9
    payout_min_days: int | None = None
    payout_min_profit: float | None = None
    eval_fee: float = 0.0
    activation_fee: float = 0.0
    reset_fee: float = 0.0
    monthly_fee: float = 0.0
    source_url: str | None = None
    last_known_at: str | None = None


class PropFirmConfigIn(BaseModel):
    """POST body. Either pass `preset_key` (with optional overrides) or fully
    specify every field."""

    model_config = ConfigDict(extra="forbid")

    starting_balance: float = Field(..., gt=0)
    profit_target: float = Field(..., gt=0)
    max_drawdown: float = Field(..., gt=0)
    trailing_drawdown: bool = True
    daily_loss_limit: float | None = Field(default=None, gt=0)
    consistency_pct: float | None = Field(default=None, gt=0, le=1)
    max_trades_per_day: int | None = Field(default=None, gt=0)
    risk_per_trade_dollars: float = Field(..., gt=0)


class FirmRuleProfileRead(BaseModel):
    """Full editable firm rule profile — what /profiles endpoints return."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: str
    firm_name: str
    account_name: str
    account_size: float
    phase_type: str
    profit_target: float
    max_drawdown: float
    daily_loss_limit: float | None
    trailing_drawdown_enabled: bool
    trailing_drawdown_type: str
    consistency_pct: float | None
    consistency_rule_type: str
    max_trades_per_day: int | None
    minimum_trading_days: int | None
    risk_per_trade_dollars: float
    payout_split: float
    payout_min_days: int | None
    payout_min_profit: float | None
    eval_fee: float
    activation_fee: float
    reset_fee: float
    monthly_fee: float
    source_url: str | None
    last_known_at: str | None
    notes: str | None
    verification_status: str
    verified_at: datetime | None
    verified_by: str | None
    is_seed: bool
    is_archived: bool
    created_at: datetime | None
    updated_at: datetime | None


class FirmRuleProfileCreate(BaseModel):
    """POST body for a brand-new (custom) firm profile. The simulator's
    8 sim-relevant fields are required; everything else has a sensible
    default."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(..., min_length=1, max_length=60)
    firm_name: str = Field(..., min_length=1, max_length=120)
    account_name: str = Field(..., min_length=1, max_length=120)
    account_size: float = Field(..., gt=0)
    profit_target: float = Field(..., gt=0)
    max_drawdown: float = Field(..., gt=0)
    daily_loss_limit: float | None = Field(default=None, gt=0)
    trailing_drawdown_enabled: bool = True
    trailing_drawdown_type: str = "intraday"
    consistency_pct: float | None = Field(default=None, gt=0, le=1)
    consistency_rule_type: str = "none"
    max_trades_per_day: int | None = Field(default=None, gt=0)
    minimum_trading_days: int | None = Field(default=None, ge=0)
    risk_per_trade_dollars: float = Field(default=200.0, gt=0)
    payout_split: float = Field(default=0.9, gt=0, le=1)
    payout_min_days: int | None = Field(default=None, ge=0)
    payout_min_profit: float | None = Field(default=None, ge=0)
    eval_fee: float = Field(default=0.0, ge=0)
    activation_fee: float = Field(default=0.0, ge=0)
    reset_fee: float = Field(default=0.0, ge=0)
    monthly_fee: float = Field(default=0.0, ge=0)
    source_url: str | None = None
    last_known_at: str | None = None
    notes: str | None = None
    phase_type: str = "evaluation"


class FirmRuleProfilePatch(BaseModel):
    """PATCH body — every field optional. Pydantic v2 distinguishes
    "field omitted" from "field set to null" via `model_dump(
    exclude_unset=True)`, which the endpoint relies on for partial
    updates. Setting `verification_status="verified"` stamps
    `verified_at = now()`; editing any rule field while currently
    verified flips the status back to unverified."""

    model_config = ConfigDict(extra="forbid")

    firm_name: str | None = None
    account_name: str | None = None
    account_size: float | None = Field(default=None, gt=0)
    phase_type: str | None = None
    profit_target: float | None = Field(default=None, gt=0)
    max_drawdown: float | None = Field(default=None, gt=0)
    daily_loss_limit: float | None = None  # null is meaningful — disables the rule
    trailing_drawdown_enabled: bool | None = None
    trailing_drawdown_type: str | None = None
    consistency_pct: float | None = None
    consistency_rule_type: str | None = None
    max_trades_per_day: int | None = None
    minimum_trading_days: int | None = None
    risk_per_trade_dollars: float | None = Field(default=None, gt=0)
    payout_split: float | None = Field(default=None, gt=0, le=1)
    payout_min_days: int | None = None
    payout_min_profit: float | None = None
    eval_fee: float | None = Field(default=None, ge=0)
    activation_fee: float | None = Field(default=None, ge=0)
    reset_fee: float | None = Field(default=None, ge=0)
    monthly_fee: float | None = Field(default=None, ge=0)
    source_url: str | None = None
    last_known_at: str | None = None
    notes: str | None = None
    verification_status: str | None = None
    verified_by: str | None = None


class PropFirmDayRow(BaseModel):
    date: str
    pnl: float
    trades: int
    balance_at_eod: float


class PropFirmResultRead(BaseModel):
    passed: bool
    fail_reason: str | None
    days_simulated: int
    days_to_pass: int | None
    max_drawdown_reached: float
    peak_balance: float
    final_balance: float
    total_profit: float
    best_day: PropFirmDayRow | None
    worst_day: PropFirmDayRow | None
    consistency_ok: bool | None
    best_day_share_of_profit: float | None
    total_trades: int
    skipped_trades_no_r: int
    days: list[PropFirmDayRow]
