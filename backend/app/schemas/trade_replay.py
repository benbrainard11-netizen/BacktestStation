"""Trade replay API schemas.

Drives the /trade-replay page: a TBBO-tick-resolution playback of one
historical live trade with optional client-side ghost-order overlays.

The "live" qualifier matters: the picker only surfaces
`BacktestRun(source="live")` rows. Engine + imported runs aren't
shown — they don't represent real fills, so replaying around them
isn't meaningful for this feature. (Backtest-run replay is what the
existing /replay page is for.)
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TradeReplayTradeRead(BaseModel):
    """One trade in the picker.

    `tbbo_available` is the gate — true if the TBBO partition for this
    trade's entry date exists on disk. Trades without TBBO render as
    disabled rows in the picker.
    """

    trade_id: int
    entry_ts: datetime
    exit_ts: datetime | None
    side: str
    entry_price: float
    exit_price: float | None
    stop_price: float | None
    target_price: float | None
    r_multiple: float | None
    pnl: float | None
    exit_reason: str | None
    tbbo_available: bool


class TradeReplayRunRead(BaseModel):
    """A live backtest run with its trades, for the /trade-replay picker."""

    run_id: int
    run_name: str | None
    symbol: str
    start_ts: datetime | None
    end_ts: datetime | None
    trades: list[TradeReplayTradeRead]


class TradeReplayAnchor(BaseModel):
    """The actual trade being replayed — drawn as fixed lines on the chart."""

    entry_ts: datetime
    exit_ts: datetime | None
    side: str
    entry_price: float
    exit_price: float | None
    stop_price: float | None
    target_price: float | None
    r_multiple: float | None


class TradeReplayTickRead(BaseModel):
    """One TBBO tick payload sent to the chart.

    `ts` is the event time (`ts_event`). Trade-print fields are nullable
    since only `action="T"` rows carry a trade size + side; quote-only
    rows still update bid/ask.
    """

    ts: datetime
    bid_px: float | None
    ask_px: float | None
    trade_px: float | None
    trade_size: int | None
    side: str | None  # "A" | "B" | "N"


class TradeReplayWindowRead(BaseModel):
    """Windowed TBBO payload for one anchored trade."""

    trade_id: int
    symbol: str
    window_start: datetime
    window_end: datetime
    anchor: TradeReplayAnchor
    ticks: list[TradeReplayTickRead]
