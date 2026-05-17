"""Build a universal level-reaction table for NDOG/NWOG opening gaps.

Input is the flattened opening-gap feature matrix (`ogap.parquet`). The
detector creates the level at the gap open; existing opening-gap outcomes
already use real future 1m bars. This script maps those custom outcomes into a
common `level.*` + `lr.<horizon>.*` schema that can later be reused for FVG,
order blocks, sweeps, pivots, and volume-profile levels.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.research.outcomes.level_reactions import (
    LEVEL_HORIZONS,
    STANDARD_HORIZON_FIELDS,
    age_bucket_minutes,
    level_reaction_column,
    schema_payload,
)

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
FEATURES_DIR = ROOT / "data" / "ml" / "features"
LEVELS_DIR = ROOT / "data" / "ml" / "levels"

DEFAULT_FEATURES = FEATURES_DIR / "ogap.parquet"
DEFAULT_OUTPUT = LEVELS_DIR / "opening_gap_level_reactions.parquet"
DEFAULT_SCHEMA_OUTPUT = LEVELS_DIR / "opening_gap_level_reactions.schema.json"
DEFAULT_STATS = LEVELS_DIR / "opening_gap_level_reaction_stats.csv"
DEFAULT_AGE_DECAY = LEVELS_DIR / "opening_gap_level_age_decay.csv"
DEFAULT_DOC = ROOT / "docs" / "ML_OPENING_GAP_LEVEL_REACTIONS.md"

STAT_FIELDS = (
    "touched",
    "meaningful_touch",
    "partial_touch",
    "full_touch",
    "directional_rejection",
    "directional_break_acceptance",
    "partial_touch_rejected",
    "full_touch_rejected_inside",
    "clean_fill_through",
    "unfilled_expanded_away",
    "unfilled_clean_continuation",
)


def _bool_col(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(False, index=df.index)
    s = df[col]
    if s.dtype == bool:
        return s.fillna(False)
    if str(s.dtype).startswith("bool"):
        return s.fillna(False).astype(bool)
    return pd.to_numeric(s, errors="coerce").fillna(0).astype(bool)


def _num_col(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype="float64")
    return pd.to_numeric(df[col], errors="coerce")


def _obj_col(df: pd.DataFrame, col: str, default: Any = None) -> pd.Series:
    if col not in df.columns:
        return pd.Series(default, index=df.index, dtype="object")
    return df[col]


def _ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    den = denominator.replace(0, np.nan)
    return numerator / den


def _base_frame(df: pd.DataFrame) -> pd.DataFrame:
    created_ts = (
        _obj_col(df, "ed.gap_open_ts_utc")
        if "ed.gap_open_ts_utc" in df.columns
        else _obj_col(df, "bar_end_utc")
    )
    direction = (
        _obj_col(df, "ed.gap_direction")
        if "ed.gap_direction" in df.columns
        else _obj_col(df, "side")
    )
    return pd.DataFrame(
        {
            "level.event_id": _obj_col(df, "event_id"),
            "level.kind": "opening_gap",
            "level.subtype": _obj_col(df, "event_type"),
            "level.symbol": _obj_col(df, "primary_symbol"),
            "level.side": _obj_col(df, "side"),
            "level.created_ts_utc": created_ts,
            "level.price_low": _num_col(df, "ed.gap_low"),
            "level.price_high": _num_col(df, "ed.gap_high"),
            "level.price_mid": _num_col(df, "ed.gap_mid"),
            "level.size_pts": _num_col(df, "ed.gap_size_pts"),
            "level.direction": direction,
            "source.event_type": _obj_col(df, "event_type"),
            "source.bar_end_utc": _obj_col(df, "bar_end_utc"),
            "source.year": _obj_col(df, "year"),
            "source.month": _obj_col(df, "month"),
        },
        index=df.index,
    )


def _horizon_frame(base: pd.DataFrame, df: pd.DataFrame, horizon: str) -> pd.DataFrame:
    prefix = f"oc.{horizon}."
    gap_up = base["level.direction"].astype(str).eq("gap_up")
    gap_down = base["level.direction"].astype(str).eq("gap_down")
    size = base["level.size_pts"].astype(float)

    touched = _bool_col(df, prefix + "touched_gap")
    full_touch = _bool_col(df, prefix + "fully_filled")
    midpoint_touched = _bool_col(df, prefix + "touched_midpoint")
    meaningful_touch = midpoint_touched | full_touch
    partial_touch = meaningful_touch & ~full_touch
    closed_inside = _bool_col(df, prefix + "closed_inside")
    closed_through = _bool_col(df, prefix + "closed_through")
    accepted_above = _bool_col(df, prefix + "accepted_above_3bar")
    accepted_below = _bool_col(df, prefix + "accepted_below_3bar")
    support_rejection = _bool_col(df, prefix + "support_rejection_3bar")
    resistance_rejection = _bool_col(df, prefix + "resistance_rejection_3bar")
    support_break = _bool_col(df, prefix + "support_break_acceptance_3bar")
    resistance_break = _bool_col(df, prefix + "resistance_break_acceptance_3bar")
    closed_above = _bool_col(df, prefix + "closed_above_gap_high")
    closed_below = _bool_col(df, prefix + "closed_below_gap_low")
    low_rejected_inside = _bool_col(df, prefix + "took_gap_low_rejected_inside")
    high_rejected_inside = _bool_col(df, prefix + "took_gap_high_rejected_inside")
    unfilled = _bool_col(df, prefix + "unfilled_at_window_end")

    directional_rejection = (gap_up & support_rejection) | (gap_down & resistance_rejection)
    directional_break = (gap_up & support_break) | (gap_down & resistance_break)
    continuation_acceptance = (gap_up & accepted_above) | (gap_down & accepted_below)
    through_acceptance = (gap_up & accepted_below) | (gap_down & accepted_above)
    close_away = (gap_up & closed_above) | (gap_down & closed_below)
    rejected_inside = (gap_up & low_rejected_inside) | (gap_down & high_rejected_inside)

    mfe_up = _num_col(df, prefix + "mfe_up_pts")
    mfe_down = _num_col(df, prefix + "mfe_down_pts")
    forward_low = _num_col(df, prefix + "forward_low")
    forward_high = _num_col(df, prefix + "forward_high")
    gap_low = base["level.price_low"].astype(float)
    gap_high = base["level.price_high"].astype(float)
    reaction_away = pd.Series(np.where(gap_up, mfe_up, mfe_down), index=df.index, dtype="float64")
    reaction_through = pd.Series(
        np.where(gap_up, gap_low - forward_low, forward_high - gap_high),
        index=df.index,
        dtype="float64",
    ).clip(lower=0)
    unfilled_expanded_away = unfilled & (reaction_away >= size)

    values: dict[str, Any] = {
        "touched": touched,
        "meaningful_touch": meaningful_touch,
        "partial_touch": partial_touch,
        "midpoint_touched": midpoint_touched,
        "full_touch": full_touch,
        "closed_inside": closed_inside,
        "closed_through": closed_through,
        "directional_rejection": directional_rejection,
        "directional_break_acceptance": directional_break,
        "continuation_acceptance": continuation_acceptance,
        "through_acceptance": through_acceptance,
        "partial_touch_rejected": partial_touch & directional_rejection,
        "full_touch_rejected_inside": full_touch & rejected_inside & ~through_acceptance,
        "clean_fill_through": full_touch & through_acceptance,
        "unfilled_expanded_away": unfilled_expanded_away,
        "unfilled_clean_continuation": unfilled & continuation_acceptance & close_away,
        "time_to_touch_minutes": _num_col(df, prefix + "first_touch_minutes"),
        "time_to_meaningful_touch_minutes": _num_col(df, prefix + "first_midpoint_minutes"),
        "time_to_full_touch_minutes": _num_col(df, prefix + "first_full_fill_minutes"),
        "reaction_away_pts": reaction_away,
        "reaction_through_pts": reaction_through,
        "reaction_away_x_size": _ratio(reaction_away, size),
        "reaction_through_x_size": _ratio(reaction_through, size),
    }
    return pd.DataFrame(
        {
            level_reaction_column(horizon, field): values[field]
            for field in STANDARD_HORIZON_FIELDS
            if field in values
        },
        index=df.index,
    )


def build_level_reactions(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per NDOG/NWOG level using the shared level schema."""
    work = df[df["event_type"].isin(("ndog", "nwog"))].copy()
    base = _base_frame(work)
    parts = [base]
    for horizon in LEVEL_HORIZONS:
        parts.append(_horizon_frame(base, work, horizon))

    out = pd.concat(parts, axis=1)
    out["level.first_meaningful_touch_age_bucket"] = out[
        level_reaction_column("full_horizon", "time_to_meaningful_touch_minutes")
    ].map(age_bucket_minutes)
    out["level.first_full_touch_age_bucket"] = out[
        level_reaction_column("full_horizon", "time_to_full_touch_minutes")
    ].map(age_bucket_minutes)
    return out.reset_index(drop=True)


def _rate(series: pd.Series) -> float:
    if series.empty:
        return float("nan")
    return float(series.fillna(False).astype(bool).mean())


def build_stats(levels: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    groups: list[tuple[str, pd.DataFrame]] = [("all", levels)]
    groups.extend((str(k), g) for k, g in levels.groupby("level.subtype", dropna=False))
    groups.extend((str(k), g) for k, g in levels.groupby("level.side", dropna=False))
    groups.extend(
        (f"{subtype}/{side}", g)
        for (subtype, side), g in levels.groupby(["level.subtype", "level.side"], dropna=False)
    )
    for group, sub in groups:
        for horizon in LEVEL_HORIZONS:
            row: dict[str, Any] = {
                "group": group,
                "horizon": horizon,
                "rows": int(len(sub)),
                "avg_reaction_away_x_size": float(
                    pd.to_numeric(
                        sub[level_reaction_column(horizon, "reaction_away_x_size")],
                        errors="coerce",
                    ).mean()
                ),
            }
            for field in STAT_FIELDS:
                row[f"{field}_rate"] = _rate(sub[level_reaction_column(horizon, field)])
            rows.append(row)
    return pd.DataFrame(rows)


def build_age_decay(levels: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (subtype, side, bucket), sub in levels.groupby(
        ["level.subtype", "level.side", "level.first_meaningful_touch_age_bucket"],
        dropna=False,
    ):
        rows.append(
            {
                "level_subtype": str(subtype),
                "side": str(side),
                "first_meaningful_touch_age_bucket": str(bucket),
                "rows": int(len(sub)),
                "share_of_subtype_side": float(
                    len(sub)
                    / len(
                        levels[
                            levels["level.subtype"].eq(subtype)
                            & levels["level.side"].eq(side)
                        ]
                    )
                ),
                "full_horizon_directional_rejection_rate": _rate(
                    sub[level_reaction_column("full_horizon", "directional_rejection")]
                ),
                "full_horizon_directional_break_rate": _rate(
                    sub[level_reaction_column("full_horizon", "directional_break_acceptance")]
                ),
                "full_horizon_clean_fill_through_rate": _rate(
                    sub[level_reaction_column("full_horizon", "clean_fill_through")]
                ),
                "avg_reaction_away_x_size": float(
                    pd.to_numeric(
                        sub[level_reaction_column("full_horizon", "reaction_away_x_size")],
                        errors="coerce",
                    ).mean()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(["level_subtype", "side", "first_meaningful_touch_age_bucket"])


def _fmt_pct(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{100.0 * float(value):.1f}%"


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def _write_schema(path: Path, *, args: argparse.Namespace, levels: pd.DataFrame) -> None:
    payload = {
        **schema_payload(),
        "generated_utc": datetime.now(UTC).isoformat(),
        "builder": "backend/scripts/ml/build_opening_gap_level_reactions.py",
        "source_features": str(args.features),
        "output": str(args.output),
        "rows": int(len(levels)),
        "columns": list(levels.columns),
        "concept": {
            "level_kind": "opening_gap",
            "subtypes": ["ndog", "nwog"],
            "source_outcome_version": "opening_gap_reactions_v2",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_doc(path: Path, *, args: argparse.Namespace, levels: pd.DataFrame, stats: pd.DataFrame, age: pd.DataFrame) -> None:
    counts = levels.groupby(["level.subtype", "level.side"]).size().reset_index(name="rows")
    count_rows = [
        [f"`{r['level.subtype']}`", f"`{r['level.side']}`", f"{int(r['rows']):,}"]
        for _, r in counts.iterrows()
    ]
    stat_focus = stats[stats["group"].eq("all") & stats["horizon"].isin(("next_60m", "next_240m", "next_1d", "next_20d"))]
    stat_rows = []
    for _, r in stat_focus.iterrows():
        stat_rows.append(
            [
                f"`{r['horizon']}`",
                f"{int(r['rows']):,}",
                _fmt_pct(r["touched_rate"]),
                _fmt_pct(r["meaningful_touch_rate"]),
                _fmt_pct(r["partial_touch_rate"]),
                _fmt_pct(r["full_touch_rate"]),
                _fmt_pct(r["directional_rejection_rate"]),
                _fmt_pct(r["directional_break_acceptance_rate"]),
                f"{float(r['avg_reaction_away_x_size']):.2f}x",
            ]
        )
    age_focus = age[age["first_meaningful_touch_age_bucket"].ne("unreached_20d")]
    age_rows = []
    for _, r in age_focus.head(30).iterrows():
        age_rows.append(
            [
                f"`{r['level_subtype']}`",
                f"`{r['side']}`",
                f"`{r['first_meaningful_touch_age_bucket']}`",
                f"{int(r['rows']):,}",
                _fmt_pct(r["share_of_subtype_side"]),
                _fmt_pct(r["full_horizon_directional_rejection_rate"]),
                _fmt_pct(r["full_horizon_directional_break_rate"]),
                f"{float(r['avg_reaction_away_x_size']):.2f}x",
            ]
        )
    text = [
        "# Opening Gap Level Reactions",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "This is the first universal level-reaction artifact. It maps NDOG/NWOG",
        "opening-gap outcomes into shared `level.*` and `lr.*` columns so gaps can",
        "later be compared directly against FVGs, order blocks, sweeps, pivots,",
        "and volume-profile levels.",
        "",
        f"- Source: `{args.features}`",
        f"- Output: `{args.output}`",
        f"- Rows: `{len(levels):,}`",
        f"- Columns: `{len(levels.columns):,}`",
        "",
        "## Counts",
        "",
        _md_table(["Subtype", "Side", "Rows"], count_rows),
        "",
        "## Overall Reaction Rates",
        "",
        _md_table(
            [
                "Horizon",
                "Rows",
                "Raw Touch",
                "Meaningful Touch",
                "Partial Touch",
                "Full Fill",
                "Directional Reject",
                "Directional Break",
                "Avg Away / Size",
            ],
            stat_rows,
        ),
        "",
        "## Meaningful-Touch Age Decay",
        "",
        _md_table(
            [
                "Subtype",
                "Side",
                "Age",
                "Rows",
                "Share",
                "Reject",
                "Break",
                "Avg Away / Size",
            ],
            age_rows,
        ),
        "",
        "## Columns",
        "",
        "- `level.*` columns describe the level at creation time.",
        "- `lr.<horizon>.touched` is raw zone overlap. For opening gaps this is usually trivial at birth.",
        "- `lr.<horizon>.meaningful_touch` means midpoint/full-fill progress and is the field to use for age decay.",
        "- `lr.<horizon>.*` columns describe future reaction labels.",
        "- These are labels/outcomes, not model inputs.",
        "",
        "## Why This Matters",
        "",
        "This starts the shared level-reaction vocabulary. The next concepts can",
        "reuse the same fields, which lets the RTX training box compare level",
        "families apples-to-apples instead of learning separate custom labels for",
        "every concept.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(text) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_parquet(args.features)
    levels = build_level_reactions(df)
    stats = build_stats(levels)
    age = build_age_decay(levels)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    levels.to_parquet(args.output, index=False)
    stats.to_csv(args.stats_output, index=False)
    age.to_csv(args.age_decay_output, index=False)
    _write_schema(args.schema_output, args=args, levels=levels)
    _write_doc(args.doc, args=args, levels=levels, stats=stats, age=age)
    return levels, stats, age


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--schema-output", type=Path, default=DEFAULT_SCHEMA_OUTPUT)
    parser.add_argument("--stats-output", type=Path, default=DEFAULT_STATS)
    parser.add_argument("--age-decay-output", type=Path, default=DEFAULT_AGE_DECAY)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    args = parser.parse_args()

    levels, stats, age = build(args)
    print(f"wrote {args.output}: {len(levels):,} rows x {len(levels.columns):,} cols")
    print(f"wrote {args.schema_output}")
    print(f"wrote {args.stats_output}: {len(stats):,} rows")
    print(f"wrote {args.age_decay_output}: {len(age):,} rows")
    print(f"wrote {args.doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
