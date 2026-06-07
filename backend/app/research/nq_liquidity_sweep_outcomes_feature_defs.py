"""Feature definitions for the NQ liquidity sweep outcome study."""

from __future__ import annotations

import pandas as pd

FEATURE_WINDOWS = {
    "pre_60s": (-60, 0, "pre_sweep"),
    "pre_10s": (-10, 0, "pre_sweep"),
    "sweep_0_5s": (0, 5, "post_sweep_confirmation"),
    "post_5_30s": (5, 30, "post_sweep_confirmation"),
}

WINDOW_FEATURE_GROUPS = {
    "mean_top_book_imbalance": "imbalance",
    "directional_top_book_imbalance": "imbalance",
    "mean_bid_size": "size_changes",
    "mean_ask_size": "size_changes",
    "bid_size_change": "size_changes",
    "ask_size_change": "size_changes",
    "directional_size_change": "size_changes",
    "mean_spread": "spread",
    "max_spread": "spread",
    "spread_widening": "spread",
    "mbp_event_count": "event_intensity",
    "mbp_events_per_second": "event_intensity",
    "trade_count": "trade_activity",
    "trade_volume": "trade_activity",
    "trade_events_per_second": "trade_activity",
    "aggressive_trade_ratio": "trade_activity",
    "directional_aggressive_trade_ratio": "trade_activity",
}


def feature_metadata() -> pd.DataFrame:
    rows = [
        _meta("ticks_through_level", "trade_activity", "at_sweep", "at_sweep"),
        _meta("sweep_spread", "spread", "at_sweep", "at_sweep"),
        _meta("sweep_top_book_imbalance", "imbalance", "at_sweep", "at_sweep"),
        _meta(
            "directional_sweep_top_book_imbalance",
            "imbalance",
            "at_sweep",
            "at_sweep",
        ),
        _meta("sweep_bid_size", "size_changes", "at_sweep", "at_sweep"),
        _meta("sweep_ask_size", "size_changes", "at_sweep", "at_sweep"),
        _meta(
            "time_to_reclaim_level_0_30s",
            "trade_activity",
            "post_0_30s",
            "post_sweep_confirmation",
        ),
    ]
    for window, (_, _, timing) in FEATURE_WINDOWS.items():
        for name, group in WINDOW_FEATURE_GROUPS.items():
            rows.append(_meta(f"{window}_{name}", group, window, timing))
    return pd.DataFrame(rows)


def _meta(name: str, group: str, window: str, timing: str) -> dict[str, object]:
    return {
        "feature_name": name,
        "feature_group": group,
        "feature_window": window,
        "timing_class": timing,
        "knowable_before_entry": timing != "post_outcome",
    }
