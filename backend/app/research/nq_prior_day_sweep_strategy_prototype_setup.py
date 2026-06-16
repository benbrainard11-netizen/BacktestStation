"""Frozen setup rules for the NQ prior-day sweep prototype study."""

from __future__ import annotations

import pandas as pd

from app.research.nq_prior_day_sweep_strategy_prototype_types import (
    ENTRY_METHODS,
    STOP_METHODS,
    TARGET_METHODS,
    EntryMethod,
    PriorDaySweepPrototypeConfig,
    Side,
    StopMethod,
    TargetMethod,
)


def strategy_side(sweep_side: str) -> Side:
    if sweep_side == "high":
        return "long"
    if sweep_side == "low":
        return "short"
    raise ValueError(f"unknown sweep_side: {sweep_side!r}")


def add_frozen_context_flags(
    events: pd.DataFrame,
    config: PriorDaySweepPrototypeConfig,
) -> pd.DataFrame:
    out = events.copy()
    out["overnight_location_aligned"] = (
        out["overnight_range_location_vs_sweep"] == "near_sweep_side"
    )
    out["rth_gap_aligned"] = out["rth_gap_vs_sweep"] == "with_sweep"
    out["opening_drive_aligned"] = out["time_of_day_bucket"] == "opening_drive"
    out["context_score"] = (
        out["overnight_location_aligned"].astype(int)
        + out["rth_gap_aligned"].astype(int)
        + out["opening_drive_aligned"].astype(int)
    )
    out["qualifies"] = out["context_score"] >= config.min_context_score
    out["trade_side"] = out["sweep_side"].map({"high": "long", "low": "short"})
    out["month"] = pd.to_datetime(out["session_date"]).dt.to_period("M").astype(str)
    return out


def qualifying_events(
    events: pd.DataFrame,
    config: PriorDaySweepPrototypeConfig,
) -> pd.DataFrame:
    with_flags = add_frozen_context_flags(events, config)
    out = with_flags.loc[with_flags["qualifies"]].copy()
    out["sweep_ts"] = pd.to_datetime(out["sweep_ts"], utc=True)
    for col in ("level_price", "sweep_price"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.sort_values(["sweep_ts", "event_id"]).reset_index(drop=True)


def variant_rows(selected_variant_ids: tuple[str, ...] = ()) -> list[dict[str, str]]:
    rows = []
    selected = set(selected_variant_ids)
    for entry in ENTRY_METHODS:
        for stop in STOP_METHODS:
            for target in TARGET_METHODS:
                candidate_id = variant_id(entry, stop, target)
                if selected and candidate_id not in selected:
                    continue
                rows.append(
                    {
                        "variant_id": candidate_id,
                        "entry_method": entry,
                        "stop_method": stop,
                        "target_method": target,
                    }
                )
    return rows


def variant_id(
    entry_method: EntryMethod,
    stop_method: StopMethod,
    target_method: TargetMethod,
) -> str:
    return f"{entry_method}__{stop_method}__{target_method}"
