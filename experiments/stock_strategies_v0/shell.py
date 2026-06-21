"""Shared execution shell for the equities line — the engine BOTH strategies run on.

A detector emits Signals ("enter T on date D"); the shell turns each into an honest Trade:
entry -> LOD stop -> partial into strength -> breakeven -> MA trail/exit, with honest fills
(stop wins ties, gap-throughs honored) and costs. Detectors/models live elsewhere; the
shell is pure + deterministic (same inputs -> identical Trades).

v0 = DAILY-resolution fills on the adjusted yfinance layer (works for the whole ~5,310
universe). The m1 intraday-entry refinement (NDX subset) is a later fidelity layer
(DATA_NOTES reconciliation rule). Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import pandas as pd

import common as C
import loaders as L


@dataclass(frozen=True)
class Signal:
    ticker: str
    signal_date: pd.Timestamp        # the day the setup completes
    side: str = "long"               # long-only for now
    tag: str = ""                    # detector label, e.g. 'htf_breakout' / 'earnings_gap'


@dataclass
class ShellConfig:
    entry_mode: str = "next_open"    # 'next_open' (breakout) | 'signal_open' (earnings gap)
    stop_buffer: float = C.STOP_BUFFER_USD
    partial_frac: float = 0.5        # 25-50% per the docs
    partial_day_min: int = 3
    partial_day_max: int = 5
    trail_ma: str = "ma10"           # exit runner on a daily close below this
    trail_after_partial_only: bool = False  # else trail arms once past partial_day_min
    do_partial: bool = True          # False => never sell the partial (let the whole run)
    move_to_be: bool = True          # move stop to breakeven after the partial window
    target_r: float = 0.0            # >0 => take-profit exit at entry + target_r * risk
    stop_mode: str = "low"           # 'low' (signal-day LOD) | 'pct' (fixed % of entry)
    stop_pct: float = 0.08           # used when stop_mode='pct' (stable risk for gap entries)
    max_hold: int = 0                # 0 = no time stop
    risk_floor_frac: float = 0.005   # min risk = this * entry (kills near-zero-risk fake R)
    cost_per_share: float = C.COMMISSION_PER_SHARE + C.SLIP_PER_SHARE  # charged each side


@dataclass
class Trade:
    ticker: str
    tag: str
    entry_date: pd.Timestamp
    entry_px: float
    stop_px: float
    risk_ps: float
    exit_date: pd.Timestamp
    exit_px: float
    partial_date: object
    partial_px: object
    realized_r: float
    bars_held: int
    exit_reason: str
    fill_confidence: str
    mae_r: float
    mfe_r: float


def size_position(equity: float, entry_px: float, stop_px: float,
                  risk_frac: float = 0.01, max_exposure: float = 0.30) -> int:
    """Shares for a fixed-fractional risk, capped by max exposure (gap-down protection)."""
    per_share_risk = entry_px - stop_px
    if per_share_risk <= 0:
        return 0
    by_risk = (risk_frac * equity) / per_share_risk
    by_exposure = (max_exposure * equity) / entry_px
    return int(min(by_risk, by_exposure))


def simulate_trade(signal: Signal, daily: pd.DataFrame | None = None,
                   cfg: ShellConfig = ShellConfig()) -> Trade | None:
    """Simulate one trade on daily bars. `daily` must carry dt + OHLCV + the trail MA
    (pass L.with_mas(L.load_daily(t))); if None it is loaded. Returns None if the signal
    date / entry session isn't available or the setup is degenerate (risk <= 0)."""
    d = daily if daily is not None else L.with_mas(L.load_daily(signal.ticker))
    loc = d.index[d["dt"] == pd.Timestamp(signal.signal_date)]
    if len(loc) == 0:
        return None
    si = int(loc[0])
    ei = si + (1 if cfg.entry_mode == "next_open" else 0)
    if ei >= len(d):
        return None
    er = d.iloc[ei]
    entry_px = float(er["open"]) + cfg.cost_per_share          # buy: pay the cost
    if cfg.stop_mode == "pct":                                 # stable risk (gap entries)
        stop_px = entry_px * (1.0 - cfg.stop_pct)
    else:                                                      # 'low': LOD of the signal day, floored
        stop_ref = float(d.iloc[si]["low"]) - cfg.stop_buffer
        stop_px = min(stop_ref, entry_px * (1.0 - cfg.risk_floor_frac))
    risk = entry_px - stop_px
    if risk <= 0:
        return None

    cur_stop, frac, r_acc = stop_px, 1.0, 0.0
    partial_date = partial_px = None
    staged = False
    mae = mfe = 0.0

    def finish(j_row, exit_px, reason, conf="daily") -> Trade:
        nonlocal r_acc
        r_acc += frac * (exit_px - entry_px) / risk
        return Trade(signal.ticker, signal.tag, er["dt"], round(entry_px, 4),
                     round(stop_px, 4), round(risk, 4), j_row["dt"], round(exit_px, 4),
                     partial_date, None if partial_px is None else round(partial_px, 4),
                     round(r_acc, 4), int(j_row.name) - ei, reason, conf,
                     round(mae, 4), round(mfe, 4))

    for j in range(ei + 1, len(d)):
        row = d.iloc[j]
        mfe = max(mfe, frac * (float(row["high"]) - entry_px) / risk)
        mae = min(mae, frac * (float(row["low"]) - entry_px) / risk)
        # 1) STOP first (stop wins ties); gap-through => fill at the open
        if float(row["low"]) <= cur_stop:
            fill = float(row["open"]) if float(row["open"]) < cur_stop else cur_stop
            reason = "breakeven" if cur_stop >= entry_px else "stop"
            return finish(row, fill - cfg.cost_per_share, reason)
        # 2) TARGET take-profit (checked after the stop, so the stop still wins a tie)
        if cfg.target_r > 0:
            tgt = entry_px + cfg.target_r * risk
            if float(row["high"]) >= tgt:
                fill = float(row["open"]) if float(row["open"]) > tgt else tgt  # gap above => better
                return finish(row, fill - cfg.cost_per_share, "target")
        # 3) one-time PARTIAL into strength and/or move stop to breakeven
        if (not staged and cfg.partial_day_min <= (j - ei) <= cfg.partial_day_max
                and float(row["close"]) > entry_px):
            if cfg.do_partial and cfg.partial_frac > 0:
                partial_px = float(row["close"]) - cfg.cost_per_share
                r_acc += cfg.partial_frac * (partial_px - entry_px) / risk
                frac -= cfg.partial_frac
                partial_date = row["dt"]
            if cfg.move_to_be:
                cur_stop = entry_px
            staged = True
        # 3) TRAIL exit on a daily close below the MA
        trail_on = (partial_date is not None) if cfg.trail_after_partial_only else (j - ei >= cfg.partial_day_min)
        if trail_on and pd.notna(row[cfg.trail_ma]) and float(row["close"]) < float(row[cfg.trail_ma]):
            return finish(row, float(row["close"]) - cfg.cost_per_share, "trail")
        # 4) optional time stop
        if cfg.max_hold and (j - ei) >= cfg.max_hold:
            return finish(row, float(row["close"]) - cfg.cost_per_share, "time")

    last = d.iloc[-1]
    return finish(last, float(last["close"]) - cfg.cost_per_share, "eod_data")


def run_signals(signals: list[Signal], cfg: ShellConfig = ShellConfig()) -> pd.DataFrame:
    """Simulate many signals (loads each ticker's adjusted daily once). Returns a tidy
    trades frame; signals whose data is unavailable are dropped."""
    trades, cache = [], {}
    for s in signals:
        if s.ticker not in cache:
            cache[s.ticker] = L.with_mas(L.load_daily(s.ticker))
        t = simulate_trade(s, cache[s.ticker], cfg)
        if t is not None:
            trades.append(asdict(t))
    return pd.DataFrame(trades)
