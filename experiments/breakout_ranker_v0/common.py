"""breakout_ranker_v0 — the construction from the pasted advice, built honestly.

Question (verbatim from the advice): "Among liquid stocks in top-quartile sectors,
which names are compressing near 52-week highs and most likely to reach +2R before -1R
after breaking their pivot?"

This module = shared config + clean data access. We load the SURVIVORSHIP-CLEAN Polygon
universe (delisted-included common stocks, daily 2016-2026) directly from the parquets —
NOT the yfinance `daily/` layer (survivorship-biased) that loaders.py uses. All features
are causal (data <= the setup day); the +2R/-1R triple-barrier label uses future bars only.

Run with backend\\.venv\\Scripts\\python.exe -u.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

# --- universe / liquidity (advice: price>$10, ADV>$30M, real names) -----------
MIN_PRICE = 10.0
MIN_DVOL = 30e6          # 20-day average dollar volume
START_DATE = 20160101    # full clean history

# --- the "compression near 52-week high" base (advice's clean setup) ----------
BASE = 20               # consolidation / pivot lookback (advice: 10-40d)
HIGH52_PROX = 0.92      # close within 8% of the 252d high
MAX_BASE_WIDTH = 0.15   # tight base: (pivot-low)/close <= 15% (pullback < 15%)
MAX_VOL_CONTRACT = 1.00 # atr14 < atr50 (volatility contracted)
NOT_EXTENDED = 1.005    # close still <= pivot*1.005 (in the base, not already gone)

# --- pivot / trigger / triple-barrier (advice's trade construction) -----------
TRIG_ATR = 0.10         # trigger = pivot + 0.10*ATR
TRIG_WIN = 10           # arm the stop-buy for 10 sessions
STOP_ATR = 1.0          # stop = pivot - 1*ATR (advice: "below pivot by 1 ATR"); the
#                         tradeable R. The base-low stop makes +2R a ~+30% move (degenerate).
TARGET_R = 2.0          # +2R target
STOP_R = 1.0            # -1R = the ATR stop
BARRIER_DAYS = 20       # resolve within 20 sessions
STOP_BUF = 0.001        # stop sits a hair below the level (honest-fill buffer)
FRIC = 0.0015           # round-trip friction in price (15 bps); gross test uses 0.0
RCAP = 10.0             # clip realized R to +/-10 (timeouts only; barriers are +2/-1)


def load_universe(start: int = START_DATE) -> pd.DataFrame:
    """All survivorship-clean common-stock daily bars from `start`, sorted (ticker, date)."""
    df = pd.concat(
        [pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))],
        ignore_index=True,
    )
    meta = pd.read_parquet(POLY / "meta.parquet")
    cs = set(meta.loc[meta["type"] == "CS", "ticker"])
    active = dict(zip(meta["ticker"], meta["active"]))
    # keep SPY (an ETF, absent from the CS meta) so the regime / relative-strength refs work
    df = df[(df["ticker"].isin(cs) | (df["ticker"] == "SPY")) & (df["date"] >= start)].copy()
    df["active"] = df["ticker"].map(active).fillna(False)
    return df.sort_values(["ticker", "date"]).reset_index(drop=True)


def _sic_to_sector(sic) -> str:
    """Coarse, consistent sector buckets from the 2-digit SIC major group. The taxonomy
    only needs to be stable enough to rank sectors; it is not GICS."""
    try:
        mg = int(str(sic)[:4]) // 100
    except (ValueError, TypeError):
        return "Unknown"
    if mg in (35, 36, 38, 73, 78, 89):
        return "Technology"
    if mg == 28 or mg in (80, 87):
        return "HealthCare"
    if mg in (13, 29, 46):
        return "Energy"
    if mg in (10, 12, 14, 33, 34):
        return "Materials"
    if 60 <= mg <= 67:
        return "Financials"
    if mg == 48:
        return "Communications"
    if mg == 49:
        return "Utilities"
    if mg in (40, 41, 42, 43, 44, 45, 47):
        return "Transportation"
    if mg in (20, 21) or 52 <= mg <= 54 or mg in (58, 59):
        return "ConsumerStaples"
    if mg in (23, 25, 27, 30, 31, 32, 37, 39, 55, 56, 57, 70, 72, 79):
        return "ConsumerDiscretionary"
    if mg in (15, 16, 17, 24, 26):
        return "Industrials"
    if mg in (50, 51):
        return "Wholesale"
    return "Other"


def ticker_sector_map() -> dict[str, str]:
    """ticker -> coarse sector, from Polygon SIC, falling back to the xregime sector label."""
    out: dict[str, str] = {}
    sic = pd.read_parquet(POLY / "ticker_sic.parquet")
    for t, s in zip(sic["ticker"], sic["sic"]):
        out[t] = _sic_to_sector(s)
    xr = pd.read_parquet(POLY / "_xregime_with_sector.parquet")[["tkr", "sector"]].dropna()
    for t, s in zip(xr["tkr"], xr["sector"]):
        out.setdefault(t, s)
    return out


def sector_strength_table(df: pd.DataFrame, tsec: dict[str, str]) -> dict[tuple[int, str], float]:
    """(date, sector) -> cross-sectional percentile of the sector's median trailing-63d
    return that day. Causal (ret63 uses closes <= date). Top-quartile sector => pct >= 0.75."""
    w = df[["ticker", "date", "close"]].copy()
    w["ret63"] = w["close"] / w.groupby("ticker")["close"].shift(63) - 1
    w["sector"] = w["ticker"].map(tsec).fillna("Unknown")
    w = w.dropna(subset=["ret63"])
    sec = w.groupby(["date", "sector"])["ret63"].median().reset_index()
    sec["pct"] = sec.groupby("date")["ret63"].rank(pct=True)
    return {(int(d), s): float(p) for d, s, p in zip(sec["date"], sec["sector"], sec["pct"])}


def atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int) -> np.ndarray:
    pc = np.roll(c, 1)
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).rolling(n).mean().to_numpy()
