"""API shapes for the bar-by-bar replay endpoint."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class ReplayBar(BaseModel):
    """One OHLCV bar in the replay timeline. ts is ISO-8601 UTC."""

    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class ReplayEntry(BaseModel):
    """One entry/exit pair from a backtest run, anchored to the
    corresponding bars on the timeline.

    `entry_ts` and `exit_ts` are timestamps the chart can use to draw
    markers at the right candle. `pnl` is in dollars, `r_multiple` if
    available; both are nullable because some imports leave them blank.
    """

    trade_id: int
    entry_ts: datetime
    exit_ts: datetime | None
    side: str  # "long" | "short"
    entry_price: float
    exit_price: float | None
    stop_price: float | None
    target_price: float | None
    pnl: float | None
    r_multiple: float | None
    exit_reason: str | None


class ReplayPayload(BaseModel):
    """Full payload for one (symbol, date) replay request."""

    symbol: str
    date: date
    bars: list[ReplayBar] = Field(default_factory=list)
    entries: list[ReplayEntry] = Field(default_factory=list)
    backtest_run_id: int | None = None
