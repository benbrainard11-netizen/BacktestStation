"""Pydantic schemas for the prop-firm simulator."""

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
