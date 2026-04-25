"""Fractal AMD signal-detection primitives (stubs).

This module will hold the pure functions that detect setups, validate
SMT divergence, build HTF candle bounds, and resolve FVGs. None of
them depend on the engine -- they take bars + config and return signal
data, which `strategy.py` translates into OrderIntents.

Stub-only for the scaffold. Each function below is the eventual port
target from `FractalAMD-/production/live_bot.py`. Filling them in is
the bulk of the multi-session port; signatures are pinned now so the
strategy loop in `strategy.py` can be written against them.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

from app.backtest.strategy import Bar


Direction = Literal["BULLISH", "BEARISH"]


@dataclass(frozen=True)
class HTFCandle:
    """One higher-timeframe candle (session, 1H, 15m, 5m).

    Built by aggregating the underlying 1m bars. The trusted live bot
    uses `_candle_bounds(day, tf)` to compute these on the fly; the
    port should mirror that.
    """

    timeframe: str
    start: dt.datetime
    end: dt.datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class Setup:
    """A detected trading setup waiting for entry.

    Mirrors `live_bot.Setup` so the eventual port can copy state
    machine behavior (WATCHING -> TOUCHED -> FILLED) verbatim.
    """

    direction: Direction
    htf_tf: str
    htf_candle_start: dt.datetime
    htf_candle_end: dt.datetime
    ltf_tf: str
    ltf_candle_end: dt.datetime
    fvg_high: float
    fvg_low: float
    fvg_mid: float
    status: Literal["WATCHING", "TOUCHED", "FILLED"] = "WATCHING"
    touch_bar_time: dt.datetime | None = None


def build_htf_candles(
    bars: list[Bar], timeframe: str, day: dt.date
) -> list[HTFCandle]:
    """Aggregate 1m bars into HTF candles for a given day + timeframe.

    Eventual port target: `_candle_bounds(day, tf)` + the resampling
    pattern around `nq_candles.loc[(...)]` in live_bot.scan_for_setups.

    Stub: returns empty list. The scaffold's smoke test passes because
    no candles -> no setups -> no orders.
    """
    return []


def detect_smt_rejection(
    *,
    primary: list[Bar],
    aux: dict[str, list[Bar]],
    htf_candle: HTFCandle,
    prior_htf_candle: HTFCandle,
) -> Direction | None:
    """Check for SMT divergence between primary (NQ) and aux (ES, YM).

    Returns the direction the divergence implies, or None if no
    divergence at this HTF candle.

    Eventual port target: `detect_rejection` in live_bot.py +
    `SignalEngine.scan_for_setups` SMT logic. The validated rule:
    sweep outside daily VA at 58.6% WR is the strongest VP signal;
    PDH SMT is the strongest single reference at 60% WR.

    Stub: returns None.
    """
    return None


def detect_fvg(
    bars: list[Bar], lookback: int = 3
) -> tuple[float, float, float] | None:
    """Detect a Fair Value Gap in the most recent N bars.

    Returns (high, low, mid) of the gap, or None if no FVG present.
    The trusted live bot detects FVGs on resampled LTF bars (5m/15m),
    not raw 1m -- the caller is responsible for the resampling.

    Eventual port target: live_bot's FVG-detection helper (the
    `check_touch` function uses these). FVG limit entries are built
    but not yet in the cascade per project memory.

    Stub: returns None.
    """
    return None


def check_touch(
    setup: Setup, bar: Bar
) -> bool:
    """Has this 1m bar's [low, high] range crossed into the FVG?

    Sets `setup.touch_bar_time` on first contact (live bot pattern).

    Eventual port target: `check_touch` in live_bot.py.

    Stub: returns False.
    """
    return False


def is_in_entry_window(
    now_et: dt.datetime, *, open_hour: int, open_min: int, close_hour: int
) -> bool:
    """Is the timestamp inside the strategy's entry window?

    Trusted backtest gate: `et.hour < open_hour or et.hour >= close_hour`,
    combined with `rth_s = (open_hour, open_min)`. Pure function -- the
    only signal helper that's safe to wire into the scaffold today.
    """
    if now_et.hour < open_hour:
        return False
    if now_et.hour == open_hour and now_et.minute < open_min:
        return False
    if now_et.hour >= close_hour:
        return False
    return True
