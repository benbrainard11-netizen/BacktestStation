"""Named constants for prop_intraday_resolver_v0.

Per CLAUDE.md rule 7, magic numbers live here, not inline in logic. Contract
economics (point value, tick size, commission, slippage) are NOT redefined here
on purpose -- they are owned by ``backend/app/core/config.py`` and
``backend/app/backtest/broker.py::BrokerConfig``. Import them from there at
implementation time so there is exactly one source of truth.
"""

from __future__ import annotations

# --- universe -----------------------------------------------------------------
SYMBOLS: tuple[str, ...] = ("ES", "NQ", "YM", "RTY")
# build order: prove ES + NQ first, then add YM, RTY (see PLAN.md Phase 2)
PHASE1_SYMBOLS: tuple[str, ...] = ("ES", "NQ")
CONTINUOUS: dict[str, str] = {s: f"{s}.c.0" for s in SYMBOLS}

# --- event-time feature windows (AT the touch) --------------------------------
# matches market_state/intraday/zone_events.py W_OFI = "2s"; the others are the
# tiered windows from the design. Every feature must end at or before t_decision.
FEATURE_WINDOWS: tuple[str, ...] = ("100ms", "250ms", "1s", "2s")
OFI_WINDOW: str = "2s"  # the canonical baseline window / decision boundary

# --- event families (Layer 1) -------------------------------------------------
# Phase 1 baseline is PDH/PDL only (to reproduce market_state Stage 1).
# Later families must each earn their seat vs the OFI-only judge (PLAN Phase 2).
PHASE1_LEVEL_FAMILIES: tuple[str, ...] = ("pdh", "pdl")
CANDIDATE_LEVEL_FAMILIES: tuple[str, ...] = (
    "onh",
    "onl",  # overnight high / low
    "orh",
    "orl",  # opening-range high / low
    "vwap",
    "vwap_band",  # session VWAP + bands
    "gap_mid",
    "gap_fill",  # gap levels
    "vpoc",  # volume POC (only after base passes)
)

# --- conditioner contract (Layer 3) -------------------------------------------
# risk_conditioner_v0 locked contract: a multiplier, nothing more.
SIZE_MULT_LADDER: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)

# --- prop firms (Layer 4) -----------------------------------------------------
# audited rule-sets live in experiments/sizing_v1/config/firms/*.yaml
FIRMS: tuple[str, ...] = ("topstep", "apex", "mffu", "lucid", "tradeify", "tpt")

# --- judge / kill thresholds --------------------------------------------------
# the non-negotiable baseline; the full system must beat this OOS.
JUDGE_BASELINE: str = "event_time_ofi_only"
# day-block bootstrap settings reused from hold_break_model.py
N_BOOTSTRAP: int = 2000
CALIBRATION_TOLERANCE: float = 0.05  # predicted-60% bucket must win ~60% OOS

# --- data discipline ----------------------------------------------------------
# Clean trading-day reads only. NEVER read raw UTC partitions.
# Use backend/app/data/reader.py::read_mbo_trading_day / read_mbp1_trading_day.
CLEAN_MBO_FIRST_DAY: str = "2026-01-02"  # clean MBO cache starts here (112 days)
MBP1_FIRST_DAY: str = "2025-05-01"  # 342 days of MBP-1 / TBBO available
