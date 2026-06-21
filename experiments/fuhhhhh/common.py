"""Shared constants for the fuhhhhh experiment. See SPEC.md; rules referenced by number.

Run everything with backend\\.venv\\Scripts\\python.exe (lightgbm lives there).
"""

from __future__ import annotations

import sys
from pathlib import Path

# --- repo / data roots -------------------------------------------------------
REPO = Path(r"C:\Users\benbr\BacktestStation")
BACKEND = REPO / "backend"
DATA_ROOT = Path(r"D:\data")

# Futures (ES.c.0 primary; NQ.c.0 used as the SMT confirmation index)
BARS_1M_ROOT = DATA_ROOT / "processed" / "bars" / "timeframe=1m"
BARS_1M = BARS_1M_ROOT / "symbol=ES.c.0"
BARS_1M_NQ = BARS_1M_ROOT / "symbol=NQ.c.0"
MBP1_ES = DATA_ROOT / "raw" / "databento" / "mbp-1" / "symbol=ES.c.0"
MBP1_NQ = DATA_ROOT / "raw" / "databento" / "mbp-1" / "symbol=NQ.c.0"
MBO_CLEAN_ES = DATA_ROOT / "clean" / "databento" / "mbo_trading_day" / "symbol=ES.c.0"
MBO_CLEAN_NQ = DATA_ROOT / "clean" / "databento" / "mbo_trading_day" / "symbol=NQ.c.0"

# Options (SPX/SPXW via ThetaData cache + derived panels in options_signals_v0)
THETA_RAW = DATA_ROOT / "raw" / "thetadata"
OSV_OUT = REPO / "experiments" / "options_signals_v0" / "out"
INTRADAY_GEX = OSV_OUT / "intraday_gex_spx.parquet"  # per-minute net_gex/walls/pin/spot
DTE0_FLOW = OSV_OUT / "dte0_intraday_spx.parquet"  # 0DTE flow (net gamma/vanna/charm)
IV_INTRADAY = OSV_OUT / "iv_intraday_spx.parquet"
SPOT_INTRADAY = OSV_OUT / "spot_intraday_spx.parquet"
GEX_LEVELS_DAILY = OSV_OUT / "gex_levels_spx.parquet"  # EOD walls (audited, 2025-05+)
WALLS_DEEP = REPO / "experiments" / "prop_model_v0" / "data" / "walls_deep.parquet"

# --- windows (SPEC §2) -------------------------------------------------------
DEV_START = "2025-05-01"
DEV_END = "2026-03-31"  # inclusive
HOLDOUT_START = "2026-04-01"  # sealed; 2 lifetime reads; ledger in HOLDOUT_LEDGER.md

# --- session / decision grid (SPEC §2) ----------------------------------------
ET = "America/New_York"
GRID_START_ET = "09:35"
GRID_END_ET = "15:45"
GRID_STEP_MIN = 5
TIME_BARRIER_MIN = 45  # primary; 30/60 registered secondaries

# --- ES economics (rule 6: per-symbol, honest) --------------------------------
TICK = 0.25
POINT_VALUE_ES = 50.0
POINT_VALUE_MES = 5.0
COMMISSION_RT = 3.80  # round-trip, per contract
SLIP_TICKS_PER_SIDE = 1.0
WALL_ZONE_TICKS = 8  # rule 3: walls are zones, ±8 ticks (±2 pts) until re-registered
STOP_CLEARANCE_TICKS = 3  # rule 6: stops clear extremes by 2-4 ticks

# --- NQ economics (NASDAQ port; rule 6 — per-symbol, honest) -------------------
POINT_VALUE_NQ = 20.0
POINT_VALUE_MNQ = 2.0
COST_PTS_NQ = COMMISSION_RT / POINT_VALUE_NQ + 2 * SLIP_TICKS_PER_SIDE * TICK  # 0.69 pts/trade
TRIG_TGT_MIN_PTS_NQ = 8.0  # NQ scale: wall must be >= 8 pts away (no degenerate target)

# --- NDX options (self-computed walls: IV->BS gamma; see build_walls_ndx.py) ----
# DAILY EOD walls (one row/day at EOD spot). Prior-day row is causal for today's
# session (OI fixed at prior EOD). NOT intraday-repriced like the SPX panel — a
# documented simplification of the NASDAQ port vs the ES intraday-GEX model.
WALLS_NDX = REPO / "experiments" / "fuhhhhh" / "out" / "walls_ndx.parquet"

# --- objective engine (registered, not fished) ---------------------------------
OBJ_MIN_PTS = 1.0  # nearest objective must be >= 4 ticks away (no degenerate races)
OBJ_CAP_ATR_FRAC = 0.5  # ... and <= 0.5 x daily ATR(14) away, else "no clean setup"
OPENING_RANGE_MIN = 15  # ORH/ORL form at 09:45 ET; invalid (rule: valid_from) before
ATR_LEN = 14
COST_PTS = COMMISSION_RT / POINT_VALUE_ES + 2 * SLIP_TICKS_PER_SIDE * TICK  # 0.576 pts/trade

# --- Iteration 3: trigger -> seek-the-wall model (registered) --------------------
# A trigger fires => price is expected to travel to an options wall; stop = adverse
# ATR move; horizon = open until session end (intraday only).
TRIG_STOP_ATR = 0.5          # invalidation = 0.5 x daily ATR against entry
TRIG_TGT_MIN_PTS = 2.0       # wall must be >= 2 pts away (no degenerate target)
TRIG_TGT_MAX_ATR = 2.0       # ... and <= 2.0 x ATR away (open-ish horizon)
TRIG_LAST_ENTRY_MS = 15 * 3600_000  # no new triggers after 15:00 ET (room to resolve)
SWING_K = 3                  # fractal pivot half-width (confirmed K bars later)
SWEEP_LOOKBACK_MIN = 35      # reference-extreme window for a liquidity sweep
SWEEP_RECENT_MIN = 6         # the poke+reclaim must occur within this recent window
SWEEP_BUF_TK = 2             # sweep must exceed the reference extreme by >= 2 ticks
FLOW_Z = 1.0                 # |signed-volume z| past this = a flow-shift trigger


def backend_on_path() -> None:
    """Make `from app.data.reader import read_bars` importable."""
    p = str(BACKEND)
    if p not in sys.path:
        sys.path.insert(0, p)


def assert_no_lookahead(feature_ts_max, decision_ts, what: str = "") -> None:
    """Rule 1: feature-window <= decision time, asserted at build time.

    Both args must be comparable timestamps (same tz-awareness). Raises on violation —
    never downgrade this to a warning; two champions died from exactly this bug.
    """
    if feature_ts_max > decision_ts:
        raise AssertionError(
            f"LOOKAHEAD{f' [{what}]' if what else ''}: feature ts {feature_ts_max} "
            f"> decision ts {decision_ts}"
        )
