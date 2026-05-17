"""Build a universal level-reaction table for order-block zones.

Order-block outcomes are native-candle based. This script maps the existing
OB retest/invalidation outcomes into the shared `level.*` and `lr.*`
vocabulary used by opening gaps and FVGs.
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

DEFAULT_FEATURES = FEATURES_DIR / "ob.parquet"
DEFAULT_OUTPUT = LEVELS_DIR / "ob_level_reactions.parquet"
DEFAULT_SCHEMA_OUTPUT = LEVELS_DIR / "ob_level_reactions.schema.json"
DEFAULT_STATS = LEVELS_DIR / "ob_level_reaction_stats.csv"
DEFAULT_AGE_DECAY = LEVELS_DIR / "ob_level_age_decay.csv"
DEFAULT_DOC = ROOT / "docs" / "ML_OB_LEVEL_REACTIONS.md"

OB_LAG_MIN = {
    "swept_pdl_1h": 60,
    "swept_pdl_4h": 240,
    "swept_pdh_1h": 60,
    "swept_pdh_4h": 240,
    "swept_pwl_4h": 240,
    "swept_pwl_daily": 24 * 60,
    "swept_pwh_4h": 240,
    "swept_pwh_daily": 24 * 60,
    "swept_asia_low_1h": 60,
    "swept_asia_high_1h": 60,
    "swept_london_low_1h": 60,
    "swept_london_high_1h": 60,
    "swept_ny_low_1h": 60,
    "swept_ny_high_1h": 60,
}
NATIVE_HORIZONS = {
    "next_3_bars": 3,
    "next_10_bars": 10,
    "next_50_bars": 50,
}
OB_HORIZONS = (*NATIVE_HORIZONS.keys(), "full_horizon")
OB_UNREACHED_BUCKET = "unreached_native_horizon"

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
    "full_touch_rejected_inside",
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


def _time_to_minutes(series: pd.Series, lag_min: pd.Series, horizon_bars: int | None = None) -> pd.Series:
    bars = pd.to_numeric(series, errors="coerce")
    if horizon_bars is not None:
        bars = bars.where(bars <= horizon_bars)
    return bars * lag_min


def _level_bars(df: pd.DataFrame, level: str, kind: str) -> pd.Series:
    return _num_col(df, f"oc.level_tags.{level}.bars_to_{kind}")


def _base_frame(df: pd.DataFrame) -> pd.DataFrame:
    lag_min = df["event_type"].map(OB_LAG_MIN).astype("float64")
    confirmation_ts = pd.to_datetime(df["bar_end_utc"], utc=True)
    knowable_ts = confirmation_ts + pd.to_timedelta(lag_min, unit="m")
    body_bottom = _num_col(df, "ed.ob_body_bottom").fillna(_num_col(df, "oc.ob_levels.body_bottom"))
    body_top = _num_col(df, "ed.ob_body_top").fillna(_num_col(df, "oc.ob_levels.body_top"))
    body_mid = _num_col(df, "ed.ob_body_mid").fillna((body_top + body_bottom) / 2.0)
    body_width = _num_col(df, "ed.ob_body_width_pts").fillna(_num_col(df, "oc.ob_levels.body_width"))
    range_bottom = _num_col(df, "ed.ob_range_bottom").fillna(_num_col(df, "oc.ob_levels.range_bottom"))
    range_top = _num_col(df, "ed.ob_range_top").fillna(_num_col(df, "oc.ob_levels.range_top"))
    range_width = _num_col(df, "ed.ob_range_width_pts").fillna(_num_col(df, "oc.ob_levels.range_width"))
    direction = (
        _obj_col(df, "ed.direction")
        if "ed.direction" in df.columns
        else _obj_col(df, "side")
    )
    native_tf = (
        _obj_col(df, "ed.tracking_timeframe")
        if "ed.tracking_timeframe" in df.columns
        else df["event_type"].map(lambda x: "daily" if str(x).endswith("_daily") else str(x).rsplit("_", 1)[-1])
    )
    return pd.DataFrame(
        {
            "level.event_id": _obj_col(df, "event_id"),
            "level.kind": "order_block",
            "level.subtype": _obj_col(df, "event_type"),
            "level.symbol": _obj_col(df, "primary_symbol"),
            "level.side": _obj_col(df, "side"),
            "level.created_ts_utc": knowable_ts.map(lambda ts: ts.isoformat()),
            "level.price_low": body_bottom,
            "level.price_high": body_top,
            "level.price_mid": body_mid,
            "level.size_pts": body_width,
            "level.direction": direction,
            "level.range_low": range_bottom,
            "level.range_high": range_top,
            "level.range_mid": (range_top + range_bottom) / 2.0,
            "level.range_size_pts": range_width,
            "level.native_timeframe": native_tf,
            "level.native_minutes": lag_min,
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
        fwd_prefix = "oc.forward_50_candles."
        post_n = 50
    else:
        horizon_bars = NATIVE_HORIZONS[horizon]
        fwd_prefix = f"oc.forward_{horizon_bars}_candles."
        post_n = horizon_bars

    lag_min = base["level.native_minutes"].astype(float)
    size = base["level.size_pts"].astype(float)

    open_wick = _level_bars(df, "open", "wick_tap")
    q25_wick = _level_bars(df, "q25", "wick_tap")
    q50_wick = _level_bars(df, "q50", "wick_tap")
    q75_wick = _level_bars(df, "q75", "wick_tap")
    close_wick = _level_bars(df, "close", "wick_tap")
    range_far_wick = _level_bars(df, "range_far", "wick_tap")
    open_close = _level_bars(df, "open", "close_past")
    invalidation = _num_col(df, "oc.invalidation.bars_to_invalidation")

    if horizon_bars is None:
        touched = open_wick.notna()
        q25_touched = q25_wick.notna()
        midpoint_touched = q50_wick.notna()
        q75_touched = q75_wick.notna()
        full_touch = close_wick.notna()
        range_far_touched = range_far_wick.notna()
        closed_inside = open_close.notna()
        closed_through = invalidation.notna()
    else:
        touched = _within_bars(open_wick, horizon_bars)
        q25_touched = _within_bars(q25_wick, horizon_bars)
        midpoint_touched = _within_bars(q50_wick, horizon_bars)
        q75_touched = _within_bars(q75_wick, horizon_bars)
        full_touch = _within_bars(close_wick, horizon_bars)
        range_far_touched = _within_bars(range_far_wick, horizon_bars)
        closed_inside = _within_bars(open_close, horizon_bars)
        closed_through = _within_bars(invalidation, horizon_bars)

    meaningful_touch = q25_touched
    partial_touch = meaningful_touch & ~full_touch
    fwd_mfe = _num_col(df, fwd_prefix + "mfe_pts_in_thesis")
    fwd_mae = _num_col(df, fwd_prefix + "mae_pts_against_thesis")
    post_open_prefix = f"oc.post_tap_reactions.open_tap.forward_{post_n}_after_tap."
    post_full_prefix = f"oc.post_tap_reactions.close_tap.forward_{post_n}_after_tap."
    post_open_mfe = _num_col(df, post_open_prefix + "mfe_pts_in_thesis")
    post_open_mae = _num_col(df, post_open_prefix + "mae_pts_against_thesis")
    post_full_mfe = _num_col(df, post_full_prefix + "mfe_pts_in_thesis")
    post_full_mae = _num_col(df, post_full_prefix + "mae_pts_against_thesis")

    continuation_acceptance = fwd_mfe >= size
    directional_break = closed_through
    directional_rejection = touched & ~closed_through & continuation_acceptance
    partial_touch_rejected = partial_touch & directional_rejection
    full_touch_rejected_inside = full_touch & ~closed_through & directional_rejection
    clean_fill_through = full_touch & closed_through
    unfilled_expanded_away = ~touched & (fwd_mfe >= size)
    unfilled_clean_continuation = ~touched & (fwd_mfe >= 2.0 * size) & (fwd_mae <= size)

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
        "through_acceptance": directional_break,
        "partial_touch_rejected": partial_touch_rejected,
        "full_touch_rejected_inside": full_touch_rejected_inside,
        "clean_fill_through": clean_fill_through,
        "unfilled_expanded_away": unfilled_expanded_away,
        "unfilled_clean_continuation": unfilled_clean_continuation,
        "time_to_touch_minutes": _time_to_minutes(open_wick, lag_min, horizon_bars),
        "time_to_meaningful_touch_minutes": _time_to_minutes(q25_wick, lag_min, horizon_bars),
        "time_to_full_touch_minutes": _time_to_minutes(close_wick, lag_min, horizon_bars),
        "reaction_away_pts": fwd_mfe,
        "reaction_through_pts": fwd_mae,
        "reaction_away_x_size": _ratio(fwd_mfe, size),
        "reaction_through_x_size": _ratio(fwd_mae, size),
    }
    standard = {
        level_reaction_column(horizon, field): values[field]
        for field in STANDARD_HORIZON_FIELDS
        if field in values
    }
    extra = {
        f"lr.{horizon}.q25_touched": q25_touched,
        f"lr.{horizon}.q75_touched": q75_touched,
        f"lr.{horizon}.range_far_touched": range_far_touched,
        f"lr.{horizon}.post_open_tap_mfe_pts": post_open_mfe,
        f"lr.{horizon}.post_open_tap_mae_pts": post_open_mae,
        f"lr.{horizon}.post_full_tap_mfe_pts": post_full_mfe,
        f"lr.{horizon}.post_full_tap_mae_pts": post_full_mae,
    }
    return pd.DataFrame({**standard, **extra}, index=df.index)


def build_level_reactions(df: pd.DataFrame) -> pd.DataFrame:
    work = df[df["event_type"].isin(OB_LAG_MIN)].copy()
    base = _base_frame(work)
    parts = [base]
    for horizon in OB_HORIZONS:
        parts.append(_horizon_frame(base, work, horizon))
    out = pd.concat(parts, axis=1)
    out["level.first_meaningful_touch_age_bucket"] = out[
        level_reaction_column("full_horizon", "time_to_meaningful_touch_minutes")
    ].map(age_bucket_minutes).replace({"unreached_20d": OB_UNREACHED_BUCKET})
    out["level.first_full_touch_age_bucket"] = out[
        level_reaction_column("full_horizon", "time_to_full_touch_minutes")
    ].map(age_bucket_minutes).replace({"unreached_20d": OB_UNREACHED_BUCKET})
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
        for horizon in OB_HORIZONS:
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
        "builder": "backend/scripts/ml/build_ob_level_reactions.py",
        "source_features": str(args.features),
        "output": str(args.output),
        "rows": int(len(levels)),
        "columns": list(levels.columns),
        "concept": {
            "level_kind": "order_block",
            "subtypes": sorted(OB_LAG_MIN),
            "source_outcome_version": "order_block_reactions_v1",
            "native_horizons": NATIVE_HORIZONS,
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
        & stats["horizon"].isin(("next_3_bars", "next_10_bars", "next_50_bars", "full_horizon"))
    ]
    stat_rows = []
    for _, r in stat_focus.iterrows():
        stat_rows.append(
            [
                f"`{r['horizon']}`",
                f"{int(r['rows']):,}",
                _fmt_pct(r["meaningful_touch_rate"]),
                _fmt_pct(r["midpoint_touched_rate"]),
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
        "# Order Block Level Reactions",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "This maps order-block body zones into the same `level.*` and `lr.*`",
        "vocabulary used by opening gaps and FVGs. OB horizons are native-candle",
        "windows because the source outcome computer is native-timeframe based.",
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
                "Meaningful Test",
                "Mid Test",
                "Full Body Test",
                "Reject",
                "Break",
                "Avg Thesis / Size",
            ],
            stat_rows,
        ),
        "",
        "## First-Meaningful-Test Age Decay",
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
        "- `level.price_low/high` are the OB body bounds.",
        "- `level.range_low/high` preserve the full wick range of the OB candle.",
        "- `meaningful_touch` means price reached at least q25 into the body.",
        "- `full_touch` means price reached the far body edge.",
        "- `closed_through` means OB invalidation by close through the far body edge.",
        "- `directional_rejection` is broad: touched entry, avoided invalidation, and moved at least one body size in thesis direction inside the native horizon.",
        f"- `{OB_UNREACHED_BUCKET}` means no meaningful test inside the 50-native-candle source horizon.",
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
