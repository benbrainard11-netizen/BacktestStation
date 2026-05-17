"""Build a universal level-reaction table for equal-high/low levels.

Equal levels are point/cluster levels that are usually used as liquidity
draws. The existing outcome computer measures whether a future 1h bar takes
the level and what happens after the take; this script maps those outcomes into
the shared `level.*` and `lr.*` vocabulary.
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
    STANDARD_HORIZON_FIELDS,
    age_bucket_minutes,
    level_reaction_column,
    schema_payload,
)

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
FEATURES_DIR = ROOT / "data" / "ml" / "features"
LEVELS_DIR = ROOT / "data" / "ml" / "levels"

DEFAULT_FEATURES = FEATURES_DIR / "eql.parquet"
DEFAULT_OUTPUT = LEVELS_DIR / "equal_level_reactions.parquet"
DEFAULT_SCHEMA_OUTPUT = LEVELS_DIR / "equal_level_reactions.schema.json"
DEFAULT_STATS = LEVELS_DIR / "equal_level_reaction_stats.csv"
DEFAULT_AGE_DECAY = LEVELS_DIR / "equal_level_age_decay.csv"
DEFAULT_DOC = ROOT / "docs" / "ML_EQUAL_LEVEL_REACTIONS.md"

EQL_CONFIRMATION_LAG_MIN = {
    "eq_pivot_3_1h_5pts": 4 * 60,
    "eq_pivot_3_1h_15pts": 4 * 60,
    "eq_pivot_5_1h_5pts": 6 * 60,
    "eq_pivot_5_1h_15pts": 6 * 60,
    "eq_pivot_3_4h_15pts": 4 * 240,
    "eq_pivot_5_4h_15pts": 6 * 240,
    "eq_pivot_5_daily_30pts": 6 * 24 * 60,
}
NATIVE_MINUTES = 60.0
NATIVE_HORIZONS = {
    "next_5_bars": 5,
    "next_25_bars": 25,
    "next_100_bars": 100,
    "next_250_bars": 250,
}
EQL_HORIZONS = (*NATIVE_HORIZONS.keys(), "full_horizon")
EQL_UNREACHED_BUCKET = "unreached_native_horizon"

STAT_FIELDS = (
    "touched",
    "meaningful_touch",
    "partial_touch",
    "midpoint_touched",
    "full_touch",
    "closed_through",
    "directional_rejection",
    "directional_break_acceptance",
    "partial_touch_rejected",
    "clean_fill_through",
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


def _num_col(df: pd.DataFrame, col: str, default: float = np.nan) -> pd.Series:
    if col not in df.columns:
        return pd.Series(default, index=df.index, dtype="float64")
    return pd.to_numeric(df[col], errors="coerce")


def _obj_col(df: pd.DataFrame, col: str, default: Any = None) -> pd.Series:
    if col not in df.columns:
        return pd.Series(default, index=df.index, dtype="object")
    return df[col]


def _ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    den = denominator.replace(0, np.nan)
    return numerator / den


def _within_bars(series: pd.Series, horizon_bars: int) -> pd.Series:
    value = pd.to_numeric(series, errors="coerce")
    return value.notna() & value.le(horizon_bars)


def _time_to_minutes(series: pd.Series, horizon_bars: int | None = None) -> pd.Series:
    bars = pd.to_numeric(series, errors="coerce")
    if horizon_bars is not None:
        bars = bars.where(bars <= horizon_bars)
    return bars * NATIVE_MINUTES


def _base_frame(df: pd.DataFrame) -> pd.DataFrame:
    confirmation_lag = df["event_type"].map(EQL_CONFIRMATION_LAG_MIN).astype("float64")
    event_ts = pd.to_datetime(df["bar_end_utc"], utc=True, errors="coerce")
    knowable_ts = event_ts + pd.to_timedelta(confirmation_lag, unit="m")
    level_price = _num_col(df, "ed.level_price").fillna(_num_col(df, "oc.level_price"))
    cluster_min = _num_col(df, "ed.cluster_min_price")
    cluster_max = _num_col(df, "ed.cluster_max_price")
    tolerance = _num_col(df, "ed.tolerance_pts")
    fallback_low = level_price - tolerance.fillna(0.0) / 2.0
    fallback_high = level_price + tolerance.fillna(0.0) / 2.0
    price_low = cluster_min.fillna(fallback_low)
    price_high = cluster_max.fillna(fallback_high)
    cluster_mid = _num_col(df, "ed.cluster_mid").fillna((price_low + price_high) / 2.0)
    cluster_spread = _num_col(df, "ed.cluster_spread_pts").fillna((price_high - price_low).abs())
    size = pd.concat([tolerance, cluster_spread, pd.Series(1.0, index=df.index)], axis=1).max(axis=1)
    side = _obj_col(df, "side").astype(str)
    direction = side.map({"high": "bearish", "low": "bullish"}).fillna(_obj_col(df, "oc.thesis_direction"))

    return pd.DataFrame(
        {
            "level.event_id": _obj_col(df, "event_id"),
            "level.kind": "equal_levels",
            "level.subtype": _obj_col(df, "event_type"),
            "level.symbol": _obj_col(df, "primary_symbol"),
            "level.side": _obj_col(df, "side"),
            "level.created_ts_utc": knowable_ts.map(lambda ts: ts.isoformat() if pd.notna(ts) else None),
            "level.price_low": price_low,
            "level.price_high": price_high,
            "level.price_mid": cluster_mid,
            "level.size_pts": size,
            "level.direction": direction,
            "level.thesis_direction": _obj_col(df, "oc.thesis_direction"),
            "level.take_price": level_price,
            "level.tolerance_pts": tolerance,
            "level.cluster_spread_pts": cluster_spread,
            "level.cluster_members": _num_col(df, "ed.n_members").fillna(_num_col(df, "ed.members__len")),
            "level.parent_pivot_mode": _obj_col(df, "ed.parent_pivot_mode"),
            "level.native_timeframe": "1h",
            "level.native_minutes": NATIVE_MINUTES,
            "level.confirmation_lag_minutes": confirmation_lag,
            "source.event_type": _obj_col(df, "event_type"),
            "source.bar_end_utc": _obj_col(df, "bar_end_utc"),
            "source.year": _obj_col(df, "year"),
            "source.month": _obj_col(df, "month"),
        },
        index=df.index,
    )


def _horizon_frame(base: pd.DataFrame, df: pd.DataFrame, horizon: str) -> pd.DataFrame:
    if horizon == "full_horizon":
        horizon_bars: int | None = None
        post_n = 250
    else:
        horizon_bars = NATIVE_HORIZONS[horizon]
        post_n = horizon_bars

    size = base["level.size_pts"].astype(float)
    bars_to_wick = _num_col(df, "oc.take.bars_to_wick")
    bars_to_close = _num_col(df, "oc.take.bars_to_close")
    deepest_past = _num_col(df, "oc.take.deepest_pts_past")

    if horizon_bars is None:
        touched = bars_to_wick.notna()
        closed_through = bars_to_close.notna()
    else:
        touched = _within_bars(bars_to_wick, horizon_bars)
        closed_through = _within_bars(bars_to_close, horizon_bars)

    post_prefix = f"oc.post_take_reaction.forward_{post_n}_after_take."
    post_mfe = _num_col(df, post_prefix + "mfe_pts_in_thesis")
    post_mae = _num_col(df, post_prefix + "mae_pts_against_thesis")
    first_take_reversal = _bool_col(df, "oc.take.first_take_was_reversal")
    post_reacted = post_mfe >= size
    through_extension = (post_mae >= size) | (deepest_past >= size)
    directional_rejection = touched & ~closed_through & first_take_reversal & post_reacted
    directional_break = closed_through & through_extension
    partial_touch = touched & ~closed_through
    full_touch_rejected_inside = closed_through & first_take_reversal & post_reacted & ~through_extension

    values: dict[str, Any] = {
        "touched": touched,
        "meaningful_touch": touched,
        "partial_touch": partial_touch,
        "midpoint_touched": touched,
        "full_touch": closed_through,
        "closed_inside": partial_touch | full_touch_rejected_inside,
        "closed_through": closed_through,
        "directional_rejection": directional_rejection,
        "directional_break_acceptance": directional_break,
        "continuation_acceptance": post_reacted,
        "through_acceptance": directional_break,
        "partial_touch_rejected": partial_touch & directional_rejection,
        "full_touch_rejected_inside": full_touch_rejected_inside,
        "clean_fill_through": closed_through & through_extension,
        "unfilled_expanded_away": pd.Series(False, index=df.index),
        "unfilled_clean_continuation": pd.Series(False, index=df.index),
        "time_to_touch_minutes": _time_to_minutes(bars_to_wick, horizon_bars),
        "time_to_meaningful_touch_minutes": _time_to_minutes(bars_to_wick, horizon_bars),
        "time_to_full_touch_minutes": _time_to_minutes(bars_to_close, horizon_bars),
        "reaction_away_pts": post_mfe,
        "reaction_through_pts": pd.concat([post_mae, deepest_past], axis=1).max(axis=1),
        "reaction_away_x_size": _ratio(post_mfe, size),
        "reaction_through_x_size": _ratio(pd.concat([post_mae, deepest_past], axis=1).max(axis=1), size),
    }
    standard = {
        level_reaction_column(horizon, field): values[field]
        for field in STANDARD_HORIZON_FIELDS
        if field in values
    }
    extra = {
        f"lr.{horizon}.wick_taken": touched,
        f"lr.{horizon}.close_past": closed_through,
        f"lr.{horizon}.first_take_was_reversal": first_take_reversal.where(touched, False),
        f"lr.{horizon}.deepest_pts_past": deepest_past.where(touched),
        f"lr.{horizon}.post_take_mfe_pts": post_mfe.where(touched),
        f"lr.{horizon}.post_take_mae_pts": post_mae.where(touched),
    }
    return pd.DataFrame({**standard, **extra}, index=df.index)


def build_level_reactions(df: pd.DataFrame) -> pd.DataFrame:
    work = df[df["event_type"].isin(EQL_CONFIRMATION_LAG_MIN)].copy()
    base = _base_frame(work)
    parts = [base]
    for horizon in EQL_HORIZONS:
        parts.append(_horizon_frame(base, work, horizon))
    out = pd.concat(parts, axis=1)
    out["level.first_meaningful_touch_age_bucket"] = out[
        level_reaction_column("full_horizon", "time_to_meaningful_touch_minutes")
    ].map(age_bucket_minutes).replace({"unreached_20d": EQL_UNREACHED_BUCKET})
    out["level.first_full_touch_age_bucket"] = out[
        level_reaction_column("full_horizon", "time_to_full_touch_minutes")
    ].map(age_bucket_minutes).replace({"unreached_20d": EQL_UNREACHED_BUCKET})
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
        for horizon in EQL_HORIZONS:
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
        denom = len(
            levels[
                levels["level.subtype"].eq(subtype)
                & levels["level.side"].eq(side)
            ]
        )
        rows.append(
            {
                "level_subtype": str(subtype),
                "side": str(side),
                "first_meaningful_touch_age_bucket": str(bucket),
                "rows": int(len(sub)),
                "share_of_subtype_side": float(len(sub) / denom) if denom else np.nan,
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
        "builder": "backend/scripts/ml/build_equal_level_reactions.py",
        "source_features": str(args.features),
        "output": str(args.output),
        "rows": int(len(levels)),
        "columns": list(levels.columns),
        "concept": {
            "level_kind": "equal_levels",
            "subtypes": sorted(EQL_CONFIRMATION_LAG_MIN),
            "source_outcome_version": "equal_levels_reactions_v1",
            "native_horizons": NATIVE_HORIZONS,
            "confirmation_lag_minutes": EQL_CONFIRMATION_LAG_MIN,
            "reaction_timeframe": "1h",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_doc(
    path: Path,
    *,
    args: argparse.Namespace,
    levels: pd.DataFrame,
    stats: pd.DataFrame,
    age: pd.DataFrame,
) -> None:
    counts = levels.groupby(["level.subtype", "level.side"]).size().reset_index(name="rows")
    count_rows = [
        [f"`{r['level.subtype']}`", f"`{r['level.side']}`", f"{int(r['rows']):,}"]
        for _, r in counts.iterrows()
    ]
    stat_focus = stats[
        stats["group"].eq("all")
        & stats["horizon"].isin(("next_5_bars", "next_25_bars", "next_100_bars", "next_250_bars", "full_horizon"))
    ]
    stat_rows = []
    for _, r in stat_focus.iterrows():
        stat_rows.append(
            [
                f"`{r['horizon']}`",
                f"{int(r['rows']):,}",
                _fmt_pct(r["meaningful_touch_rate"]),
                _fmt_pct(r["full_touch_rate"]),
                _fmt_pct(r["directional_rejection_rate"]),
                _fmt_pct(r["directional_break_acceptance_rate"]),
                f"{float(r['avg_reaction_away_x_size']):.2f}x",
            ]
        )
    age_rows = []
    for _, r in age.head(60).iterrows():
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
        "# Equal Levels Level Reactions",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "This maps equal-high/equal-low liquidity levels into the same `level.*`",
        "and `lr.*` vocabulary used by the other level families.",
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
                "Wick Took Level",
                "Close Past Level",
                "Rejected",
                "Break",
                "Avg Thesis / Size",
            ],
            stat_rows,
        ),
        "",
        "## First-Touch Age Decay",
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
                "Avg Thesis / Size",
            ],
            age_rows,
        ),
        "",
        "## Notes",
        "",
        "- `level.created_ts_utc` adds the parent swing confirmation lag to the second pivot timestamp.",
        "- Equal-level reaction horizons are 1h native bars: 5, 25, 100, and 250 bars.",
        "- `level.price_low/high` preserves the cluster band when available; `level.take_price` is the exact liquidity price.",
        "- `meaningful_touch` means a future wick took the equal high/low.",
        "- `full_touch` and `closed_through` mean a future close accepted past the level.",
        "- `directional_rejection` means first take reversed, did not close past, and moved at least one level-size in thesis direction after take.",
        "- `directional_break_acceptance` means price closed past and extended through by at least one level-size.",
        f"- `{EQL_UNREACHED_BUCKET}` means no take inside the 250-hour source horizon.",
        "- `lr.*` columns are labels/outcomes, not model inputs.",
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
