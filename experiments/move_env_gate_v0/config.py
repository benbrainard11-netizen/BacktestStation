"""Shared constants for move_env_gate_v0."""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"

DEFAULT_SOURCE = (
    ROOT
    / "experiments"
    / "prop_intraday_resolver_v0"
    / "out"
    / "dataset_ES_trading_day.parquet"
)
DEFAULT_EVENT_TABLE = OUT / "event_table.parquet"
DEFAULT_REPORT = OUT / "gate_report.md"
DEFAULT_STRATEGY_TABLE = OUT / "strategy_event_table.parquet"
DEFAULT_STRATEGY_REPORT = OUT / "strategy_gate_report.md"

FRACTAL_TRADES = ROOT / "samples" / "fractal_trusted_multiyear" / "trades.csv"
MIRA_RECENT_REPLAY = (
    ROOT
    / "experiments"
    / "sizing_v1"
    / "out"
    / "mira_short_revalidation"
    / "recent_live_replay_setups.csv"
)
MIRA_JAN_TRAIL = (
    ROOT
    / "experiments"
    / "sizing_v1"
    / "out"
    / "mira_short_revalidation"
    / "jan2026_trail_2R.parquet"
)

DEFAULT_SYMBOL = "ES.c.0"
DEFAULT_OOS_START = "2026-03-01"
DEFAULT_TAKE_FRACTION = 0.80
DEFAULT_STRATEGY_TAKE_FRACTION = 0.80

TARGET_R = 1.0
BAD_R = 1.0
TRADE_MOVE_R = 0.50

BASE_FEATURES = [
    "level_is_pdh",
    "level_is_pdl",
    "dir",
]

OFI_FEATURES = [
    "ofi_signed",
]

MBP1_FEATURES = [
    "ofi_signed",
    "qimb_signed",
    "svol_signed",
]

CROSS_ASSET_FEATURES = [
    "nq_ofi",
    "rty_ofi",
    "ym_ofi",
    "complex_mean_ofi",
    "complex_ofi_dispersion",
    "es_complex_agree",
]

FEATURE_BLOCKS = {
    "geometry": BASE_FEATURES,
    "ofi_only": OFI_FEATURES,
    "mbp1": MBP1_FEATURES,
    "cross_asset": CROSS_ASSET_FEATURES,
    "mbp1_cross": MBP1_FEATURES + CROSS_ASSET_FEATURES,
    "all_v0": BASE_FEATURES + MBP1_FEATURES + CROSS_ASSET_FEATURES,
}

STRATEGY_FEATURE_BLOCKS = {
    "metadata": [
        "direction_int",
        "hour",
        "weekday",
        "month_num",
        "risk_points",
        "risk_log",
    ],
    "setup_context": [
        "symbol",
        "setup_type",
        "source_kind",
    ],
    "existing_gate": [
        "gate_score",
        "existing_gate_passed",
    ],
    "all_strategy_v0": [
        "direction_int",
        "hour",
        "weekday",
        "month_num",
        "risk_points",
        "risk_log",
        "symbol",
        "setup_type",
        "source_kind",
        "gate_score",
        "existing_gate_passed",
    ],
}
