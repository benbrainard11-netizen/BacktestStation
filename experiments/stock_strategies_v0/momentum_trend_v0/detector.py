"""Momentum / High-Tight-Flag breakout detector (SPEC momentum_trend_v0 §3-4).

Structure at a breakout day D (all features causal, computed from data <= D):
    [ thrust leg: +thrust_pct over thrust_window ] -> [ tight low-volume base of base_len ]
    -> D: close breaks above the base high, on expanding volume, closing near the HOD.

emits Signal(ticker, signal_date=D, tag='htf_breakout'); the shell enters next-open.
Two-pass: vectorized candidate mask, then a per-candidate log-price linearity (R^2) check.
Also provides naive_breakout() — the dumb floor the real detector must beat.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common as C  # noqa: E402
import loaders as L  # noqa: E402
from shell import Signal  # noqa: E402


@dataclass
class DetectorConfig:
    thrust_pct: float = 0.30        # prior run-up (30% tier; 1.0/3.0 are registered tiers)
    thrust_window: int = 60         # trading days for the thrust leg
    base_len: int = 10              # consolidation length (3-20+; registered default)
    base_width: float = 0.25        # base high-low spread <= this fraction of base mid
    vol_dry: float = 0.7            # base avg vol < thrust avg vol * this (drying up)
    bo_vol_mult: float = 1.5        # breakout vol >= base avg vol * this (and > prior day)
    extend_max: float = 0.10        # (close-ma10)/ma10 <= this at the breakout
    hod_frac: float = 0.25          # (high-close)/(high-low) <= this (closes near HOD)
    nr_days: int = 3                # narrow-range run-in length
    linearity_min: float = 0.80     # R^2 of log-close over the thrust leg
    min_price: float = 5.0          # liquidity / not-junk
    min_dollar_vol: float = 3e6     # 20d avg dollar volume floor


def _candidate_mask(d: pd.DataFrame, cfg: DetectorConfig) -> pd.Series:
    """Vectorized breakout conditions (everything except the linearity R^2)."""
    hi, lo, cl, vol = d["high"], d["low"], d["close"], d["volume"]
    rng = hi - lo
    base_hi = hi.rolling(cfg.base_len).max().shift(1)
    base_lo = lo.rolling(cfg.base_len).min().shift(1)
    base_mid = (base_hi + base_lo) / 2
    base_vol = vol.rolling(cfg.base_len).mean().shift(1)
    base_med_rng = rng.rolling(cfg.base_len).median().shift(1)
    thrust_vol = vol.rolling(cfg.thrust_window).mean().shift(1 + cfg.base_len)
    thrust_runup = cl.shift(cfg.base_len + 1) / cl.shift(cfg.base_len + cfg.thrust_window) - 1
    recent_rng = rng.rolling(cfg.nr_days).mean().shift(1)
    dollar_vol = (cl * vol).rolling(20).mean().shift(1)

    m = (
        (cl > base_hi)                                              # breakout above base
        & ((base_hi - base_lo) / base_mid <= cfg.base_width)       # tight base
        & (base_vol < thrust_vol * cfg.vol_dry)                    # volume dried up
        & (vol > vol.shift(1)) & (vol >= base_vol * cfg.bo_vol_mult)  # breakout volume
        & (thrust_runup >= cfg.thrust_pct)                         # prior thrust
        & (cl > d["ma10"]) & (d["ma10"] > d["ma20"])               # MA alignment
        & ((cl - d["ma10"]) / d["ma10"] <= cfg.extend_max)         # not extended
        & (rng > 0) & ((hi - cl) / rng <= cfg.hod_frac)            # closes near HOD
        & (recent_rng < base_med_rng)                              # narrow-range run-in
        & (cl >= cfg.min_price) & (dollar_vol >= cfg.min_dollar_vol)  # liquidity
    )
    return m.fillna(False)


def _linearity_ok(d: pd.DataFrame, i: int, cfg: DetectorConfig) -> bool:
    """R^2 of log close over the thrust leg ending at the base start (linear, not barcode)."""
    a = i - cfg.base_len - cfg.thrust_window
    b = i - cfg.base_len
    if a < 0:
        return False
    y = np.log(d["close"].iloc[a:b].to_numpy())
    x = np.arange(len(y))
    if len(y) < 5 or not np.all(np.isfinite(y)):
        return False
    r = np.corrcoef(x, y)[0, 1]
    return r * r >= cfg.linearity_min


def detect(df: pd.DataFrame, cfg: DetectorConfig = DetectorConfig()) -> list[pd.Timestamp]:
    """Breakout dates for one ticker's daily frame (already MA-augmented)."""
    if len(df) < cfg.thrust_window + cfg.base_len + 25:
        return []
    mask = _candidate_mask(df, cfg)
    return [df["dt"].iloc[i] for i in np.flatnonzero(mask.to_numpy())
            if _linearity_ok(df, i, cfg)]


def naive_breakout(df: pd.DataFrame, lookback: int = 20, cfg: DetectorConfig = DetectorConfig()) -> list[pd.Timestamp]:
    """Dumb floor: close breaks a `lookback`-day high, same liquidity screen, nothing else."""
    if len(df) < lookback + 25:
        return []
    cl, vol = df["close"], df["volume"]
    prior_hi = df["high"].rolling(lookback).max().shift(1)
    dollar_vol = (cl * vol).rolling(20).mean().shift(1)
    m = ((cl > prior_hi) & (cl >= cfg.min_price) & (dollar_vol >= cfg.min_dollar_vol)).fillna(False)
    return [df["dt"].iloc[i] for i in np.flatnonzero(m.to_numpy())]


def scan_universe(cfg: DetectorConfig = DetectorConfig(), tickers: list[str] | None = None,
                  naive: bool = False, end: str | None = None) -> list[Signal]:
    """Scan the daily universe (minus quarantine) -> Signals. `end` caps signal_date
    (keep the holdout sealed). Set naive=True for the baseline floor."""
    qfile = Path(__file__).resolve().parents[1] / "data" / "quarantine_tickers.txt"
    bad = set(qfile.read_text().split()) if qfile.exists() else set()
    tickers = tickers or [t for t in L.list_universe("daily") if t not in bad]
    cap = pd.Timestamp(end) if end else None
    tag = "naive_breakout" if naive else "htf_breakout"
    out: list[Signal] = []
    for t in tickers:
        try:
            d = L.with_mas(L.load_daily(t))
        except Exception:
            continue
        dates = naive_breakout(d, cfg=cfg) if naive else detect(d, cfg)
        out += [Signal(t, dt, tag=tag) for dt in dates if cap is None or dt <= cap]
    return out
