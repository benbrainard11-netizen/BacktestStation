"""Stats helpers for frozen prior-day-low forward validation."""

from __future__ import annotations

import numpy as np
import pandas as pd

BASELINE_DIRECTIONS = {
    "post_5_30s_trade_events_per_second": "higher_in_winners",
    "time_of_day_bucket=opening_drive": "higher_in_winners",
    "opening_drive_aligned=True": "higher_in_winners",
    "overnight_range_location_vs_sweep=near_sweep_side": "higher_in_winners",
    "overnight_range_location=lower_third": "higher_in_winners",
}


def cumulative_performance(execution: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if execution.empty:
        return pd.DataFrame(columns=_cumulative_columns())
    max_event = int(execution["forward_event_number"].max())
    for checkpoint in range(25, min(100, max_event) + 1, 25):
        frame = execution.loc[execution["forward_event_number"] <= checkpoint]
        rows.append(_performance_row("all_variants", checkpoint, frame))
        for variant_id, group in frame.groupby("variant_id", sort=True):
            rows.append(_performance_row(str(variant_id), checkpoint, group))
    return pd.DataFrame(rows, columns=_cumulative_columns())


def effect_consistency(events: pd.DataFrame, execution: pd.DataFrame) -> pd.DataFrame:
    rows = [
        _numeric_effect(
            execution,
            "post_5_30s_trade_events_per_second",
            BASELINE_DIRECTIONS["post_5_30s_trade_events_per_second"],
        )
    ]
    rows.extend(_categorical_effects(execution))
    rows.extend(_event_outcome_effects(events))
    out = pd.DataFrame([row for row in rows if row is not None])
    if out.empty:
        return pd.DataFrame(columns=_effect_columns())
    return out.sort_values(["evaluable", "same_direction"], ascending=[False, False])


def _performance_row(label: str, checkpoint: int, frame: pd.DataFrame) -> dict[str, object]:
    filled = frame.loc[frame["status"] == "filled"]
    win_loss = filled.loc[filled["trade_result"].isin(["win", "loss"])]
    wins = int((win_loss["trade_result"] == "win").sum())
    losses = int((win_loss["trade_result"] == "loss").sum())
    pnl = pd.to_numeric(frame["pnl_num"], errors="coerce").fillna(0.0)
    return {
        "checkpoint_events": checkpoint,
        "variant_id": label,
        "unique_events": int(frame["event_id"].nunique()),
        "attempt_rows": int(len(frame)),
        "filled_trades": int(len(filled)),
        "skips": int((frame["status"] == "skipped").sum()),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / (wins + losses) if wins + losses else np.nan,
        "net_pnl": float(pnl.sum()),
        "avg_pnl_per_event": float(pnl.sum() / frame["event_id"].nunique())
        if frame["event_id"].nunique()
        else np.nan,
        "avg_pnl_per_attempt": float(pnl.mean()) if len(pnl) else np.nan,
    }


def _numeric_effect(
    execution: pd.DataFrame,
    feature: str,
    baseline_direction: str,
) -> dict[str, object] | None:
    frame = execution.loc[execution["trade_result"].isin(["win", "loss"])].copy()
    if frame.empty or feature not in frame.columns:
        return _pending_effect("execution", feature, baseline_direction, "missing_feature")
    values = pd.to_numeric(frame[feature], errors="coerce")
    frame = frame.loc[values.notna()].copy()
    frame[feature] = values.loc[values.notna()]
    wins = frame.loc[frame["trade_result"] == "win", feature].to_numpy(float)
    losses = frame.loc[frame["trade_result"] == "loss", feature].to_numpy(float)
    if len(wins) == 0 or len(losses) == 0:
        return _pending_effect("execution", feature, baseline_direction, "needs_wins_and_losses")
    diff = float(np.median(wins) - np.median(losses))
    observed = _direction(diff)
    return {
        "scope": "execution",
        "effect_name": feature,
        "baseline_direction": baseline_direction,
        "observed_direction": observed,
        "same_direction": observed == baseline_direction,
        "evaluable": True,
        "sample_size": int(len(wins) + len(losses)),
        "wins": int(len(wins)),
        "losses": int(len(losses)),
        "primary_effect": diff,
        "win_median": float(np.median(wins)),
        "loss_median": float(np.median(losses)),
        "note": None,
    }


def _categorical_effects(execution: pd.DataFrame) -> list[dict[str, object]]:
    return [
        _categorical_effect(
            execution,
            "time_of_day_bucket",
            "opening_drive",
            BASELINE_DIRECTIONS["time_of_day_bucket=opening_drive"],
        ),
        _categorical_effect(
            execution,
            "opening_drive_aligned",
            True,
            BASELINE_DIRECTIONS["opening_drive_aligned=True"],
        ),
        _categorical_effect(
            execution,
            "overnight_range_location_vs_sweep",
            "near_sweep_side",
            BASELINE_DIRECTIONS["overnight_range_location_vs_sweep=near_sweep_side"],
        ),
        _categorical_effect(
            execution,
            "overnight_range_location",
            "lower_third",
            BASELINE_DIRECTIONS["overnight_range_location=lower_third"],
        ),
    ]


def _categorical_effect(
    execution: pd.DataFrame,
    factor: str,
    category: object,
    baseline_direction: str,
) -> dict[str, object]:
    name = f"{factor}={category}"
    frame = execution.loc[execution["trade_result"].isin(["win", "loss"])].copy()
    if frame.empty or factor not in frame.columns:
        return _pending_effect("execution", name, baseline_direction, "missing_feature")
    values = frame[factor].astype(str)
    category_value = str(category)
    wins = frame["trade_result"] == "win"
    losses = frame["trade_result"] == "loss"
    win_total = int(wins.sum())
    loss_total = int(losses.sum())
    if win_total == 0 or loss_total == 0:
        return _pending_effect("execution", name, baseline_direction, "needs_wins_and_losses")
    win_share = float((values.loc[wins] == category_value).mean())
    loss_share = float((values.loc[losses] == category_value).mean())
    diff = win_share - loss_share
    observed = _direction(diff)
    return {
        "scope": "execution",
        "effect_name": name,
        "baseline_direction": baseline_direction,
        "observed_direction": observed,
        "same_direction": observed == baseline_direction,
        "evaluable": True,
        "sample_size": int(len(frame)),
        "wins": win_total,
        "losses": loss_total,
        "primary_effect": diff,
        "win_median": np.nan,
        "loss_median": np.nan,
        "note": None,
    }


def _event_outcome_effects(events: pd.DataFrame) -> list[dict[str, object]]:
    if events.empty or "fixed_outcome_label" not in events.columns:
        return []
    labeled = events.loc[
        events["fixed_outcome_label"].isin(["continuation_breakout", "failed_breakout_reversal"])
    ]
    if labeled.empty:
        return []
    cont = int((labeled["fixed_outcome_label"] == "continuation_breakout").sum())
    rev = int((labeled["fixed_outcome_label"] == "failed_breakout_reversal").sum())
    return [
        {
            "scope": "event_outcome",
            "effect_name": "fixed_continuation_rate",
            "baseline_direction": "continuation_majority",
            "observed_direction": "continuation_majority" if cont >= rev else "reversal_majority",
            "same_direction": cont >= rev,
            "evaluable": True,
            "sample_size": int(len(labeled)),
            "wins": cont,
            "losses": rev,
            "primary_effect": cont / len(labeled),
            "win_median": np.nan,
            "loss_median": np.nan,
            "note": "wins column is continuations; losses column is reversals",
        }
    ]


def _pending_effect(
    scope: str,
    name: str,
    baseline_direction: str,
    note: str,
) -> dict[str, object]:
    return {
        "scope": scope,
        "effect_name": name,
        "baseline_direction": baseline_direction,
        "observed_direction": "not_evaluable",
        "same_direction": False,
        "evaluable": False,
        "sample_size": 0,
        "wins": 0,
        "losses": 0,
        "primary_effect": np.nan,
        "win_median": np.nan,
        "loss_median": np.nan,
        "note": note,
    }


def _direction(value: float) -> str:
    if value > 0:
        return "higher_in_winners"
    if value < 0:
        return "higher_in_losers"
    return "flat"


def _cumulative_columns() -> list[str]:
    return [
        "checkpoint_events",
        "variant_id",
        "unique_events",
        "attempt_rows",
        "filled_trades",
        "skips",
        "wins",
        "losses",
        "win_rate",
        "net_pnl",
        "avg_pnl_per_event",
        "avg_pnl_per_attempt",
    ]


def _effect_columns() -> list[str]:
    return [
        "scope",
        "effect_name",
        "baseline_direction",
        "observed_direction",
        "same_direction",
        "evaluable",
        "sample_size",
        "wins",
        "losses",
        "primary_effect",
        "win_median",
        "loss_median",
        "note",
    ]
