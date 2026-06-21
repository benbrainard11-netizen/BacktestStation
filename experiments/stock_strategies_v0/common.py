"""Shared constants + causal guards for the equities line (both strategies import this).

Data layers (see DATA_PULL_SPEC.md for provenance):
  - DAILY  = yfinance, split+div adjusted, 2010->2026  (detection / regime / models)
  - ETF    = yfinance, same                            (regime + sector models)
  - M1     = ThetaData, RTH only, 2023-06->2026        (intraday entry mechanic)
  - EARN   = yfinance earnings calendar

Run everything with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path
from zoneinfo import ZoneInfo

# --- roots -------------------------------------------------------------------
REPO = Path(r"C:\Users\benbr\BacktestStation")
DATA_ROOT = Path(r"D:\data")
STOCKS = DATA_ROOT / "processed" / "stocks"
STOCKS_DAILY = STOCKS / "daily"   # 527 ~S&P500, yfinance adjusted, 2010->2026
STOCKS_ETF = STOCKS / "etf"       # SPY/QQQ/IWM/DIA + 11 XL* + SMH
STOCKS_M1 = STOCKS / "m1"         # ThetaData 1m RTH, 133 NDX names
STOCKS_EOD = STOCKS / "eod"       # ThetaData daily, 133 NDX names (superseded by DAILY)
EARNINGS_CAL = STOCKS / "earnings_calendar.parquet"

_LAYER_DIR = {"daily": STOCKS_DAILY, "etf": STOCKS_ETF, "eod": STOCKS_EOD}

# --- time / session ----------------------------------------------------------
ET = ZoneInfo("America/New_York")
RTH_OPEN_MS = 9 * 3600_000 + 30 * 60_000   # 09:30 ET
RTH_CLOSE_MS = 16 * 3600_000               # 16:00 ET
FIRST_30_END_MS = RTH_OPEN_MS + 30 * 60_000  # 10:00 ET (open + first 30 min)

# --- windows (equities line; both SPECs §2) ----------------------------------
DAILY_HISTORY_START = "2010-01-01"  # daily layer reaches back here (model training only)
INTRADAY_START = "2023-06-01"       # m1 floor => tradeable/realized-R window starts here
DEV_END = "2025-09-30"              # walk-forward dev ends
HOLDOUT_START = "2025-10-01"        # sealed; 2 lifetime reads per strategy
DATA_END = "2026-06-18"             # current daily end

# --- equities economics (defaults; the execution shell owns the real model) --
COMMISSION_PER_SHARE = 0.005        # $/share each side
SLIP_PER_SHARE = 0.01              # $/share, stressed in later phases
STOP_BUFFER_USD = 0.02            # stop clears the LOD by this (honest-fill rule)


def assert_no_lookahead(feature_ts_max, decision_ts, what: str = "") -> None:
    """feature-window <= decision time, asserted at build time.

    Both args must be comparable timestamps (same tz-awareness). RAISES on violation —
    never downgrade to a warning; the futures lines lost multiple champions to this bug.
    """
    if feature_ts_max > decision_ts:
        raise AssertionError(
            f"LOOKAHEAD{f' [{what}]' if what else ''}: feature ts {feature_ts_max} "
            f"> decision ts {decision_ts}"
        )


def layer_dir(layer: str) -> Path:
    if layer not in _LAYER_DIR:
        raise ValueError(f"unknown layer {layer!r}; expected one of {list(_LAYER_DIR)}")
    return _LAYER_DIR[layer]
