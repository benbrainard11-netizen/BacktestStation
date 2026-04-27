"""Risk Profile API schemas + evaluation result types.

Risk profiles are user-defined caps applied retroactively to a backtest
run. Profiles themselves are pure metadata; evaluation lives in
`app.services.risk_evaluator`.

Caps are R-multiples (so they're contract-size-independent). None on
any cap means "no limit on this dimension." `allowed_hours` is a list
of UTC integer hours (0-23); None means any hour allowed.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Vocabulary mirrors `Strategy.status`'s archive-not-delete pattern.
RISK_PROFILE_STATUSES: tuple[str, ...] = ("active", "archived")


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RiskProfileRead(OrmModel):
    """Profile as returned to the client.

    `allowed_hours` is parsed back from `RiskProfile.allowed_hours_json`
    in the API endpoint before serialization. `strategy_params` is the
    dict of default strategy params this profile prefills on the
    Run-a-Backtest form (None = no opinion).
    """

    id: int
    name: str
    status: str
    max_daily_loss_r: float | None
    max_drawdown_r: float | None
    max_consecutive_losses: int | None
    max_position_size: int | None
    allowed_hours: list[int] | None
    notes: str | None
    strategy_params: dict | None = None
    created_at: object  # datetime, intentionally loose for FastAPI serialization
    updated_at: object


class RiskProfileCreate(BaseModel):
    """POST /risk-profiles body."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=120)
    status: str = "active"
    max_daily_loss_r: float | None = None
    max_drawdown_r: float | None = None
    max_consecutive_losses: int | None = None
    max_position_size: int | None = None
    allowed_hours: list[int] | None = None
    notes: str | None = None
    strategy_params: dict | None = None

    @field_validator("status", mode="after")
    @classmethod
    def _valid_status(cls, value: str) -> str:
        if value not in RISK_PROFILE_STATUSES:
            raise ValueError(
                f"status must be one of {RISK_PROFILE_STATUSES}, got {value!r}"
            )
        return value

    @field_validator("allowed_hours", mode="after")
    @classmethod
    def _valid_hours(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        for h in value:
            if not (0 <= h <= 23):
                raise ValueError(f"allowed_hours entries must be 0-23, got {h}")
        return sorted(set(value))


class RiskProfileUpdate(BaseModel):
    """PATCH body — fields are optional; endpoint applies only those set."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    status: str | None = None
    max_daily_loss_r: float | None = None
    max_drawdown_r: float | None = None
    max_consecutive_losses: int | None = None
    max_position_size: int | None = None
    allowed_hours: list[int] | None = None
    notes: str | None = None
    strategy_params: dict | None = None

    @field_validator("status", mode="after")
    @classmethod
    def _valid_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in RISK_PROFILE_STATUSES:
            raise ValueError(
                f"status must be one of {RISK_PROFILE_STATUSES}, got {value!r}"
            )
        return value

    @field_validator("allowed_hours", mode="after")
    @classmethod
    def _valid_hours(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        for h in value:
            if not (0 <= h <= 23):
                raise ValueError(f"allowed_hours entries must be 0-23, got {h}")
        return sorted(set(value))


class RiskViolation(BaseModel):
    """One cap-crossing recorded during evaluation."""

    kind: str  # daily_loss | drawdown | consecutive_losses | position_size | hour_window
    at_trade_id: int
    at_trade_index: int  # zero-based, in entry-time order
    message: str


class RiskEvaluationRead(BaseModel):
    """Result of applying a profile to a backtest run."""

    profile_id: int
    run_id: int
    total_trades_evaluated: int
    violations: list[RiskViolation]


class RiskProfileStatusesRead(BaseModel):
    """Vocabulary endpoint payload — mirrors STRATEGY_STAGES exposure."""

    statuses: list[str]


def parse_allowed_hours(allowed_hours_json: str | None) -> list[int] | None:
    """Inverse of `serialize_allowed_hours`. Defensive — returns None on
    parse failure rather than raising, so a malformed DB row doesn't
    take the whole list endpoint down."""
    if allowed_hours_json is None:
        return None
    try:
        parsed = json.loads(allowed_hours_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    out = [h for h in parsed if isinstance(h, int) and 0 <= h <= 23]
    return out or None


def serialize_allowed_hours(allowed_hours: list[int] | None) -> str | None:
    if allowed_hours is None:
        return None
    return json.dumps(sorted(set(allowed_hours)))
