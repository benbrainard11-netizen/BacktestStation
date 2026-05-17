"""Build a universal level-reaction table for swing-pivot levels.

Swing pivots are point levels that only become knowable after the right-side
confirmation candles close. This script maps the existing swing outcome fields
into the shared `level.*` and `lr.*` vocabulary used by the other level
families.
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

DEFAULT_FEATURES = FEATURES_DIR / "swing.parquet"
DEFAULT_OUTPUT = LEVELS_DIR / "swing_level_reactions.parquet"
DEFAULT_SCHEMA_OUTPUT = LEVELS_DIR / "swing_level_reactions.schema.json"
DEFAULT_STATS = LEVELS_DIR / "swing_level_reaction_stats.csv"
DEFAULT_AGE_DECAY = LEVELS_DIR / "swing_level_age_decay.csv"
DEFAULT_DOC = ROOT / "docs" / "ML_SWING_LEVEL_REACTIONS.md"

SWING_NATIVE_MIN = {
    "pivot_3_1h": 60,
    "pivot_5_1h": 60,
    "pivot_3_4h": 240,
    "pivot_5_4h": 240,
    "pivot_5_daily": 24 * 60,
}
SWING_CONFIRMATION_LAG_MIN = {
    "pivot_3_1h": 4 * 60,
    "pivot_5_1h": 6 * 60,
    "pivot_3_4h": 4 * 240,
    "pivot_5_4h": 6 * 240,
    "pivot_5_daily": 6 * 24 * 60,
}
NATIVE_HORIZONS = {
    "next_3_bars": 3,
    "next_10_bars": 10,
    "next_50_bars": 50,
}
SWING_HORIZONS = (*NATIVE_HORIZONS.keys(), "full_horizon")
SWING_UNREACHED_BUCKET = "unreached_native_horizon"

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


def _time_to_minutes(
    series: pd.Series,
    native_minutes: pd.Series,
    horizon_bars: int | None = None,
) -> pd.Series:
    bars = pd.to_numeric(series, errors="coerce")
    if horizon_bars is not None:
        bars = bars.where(bars <= horizon_bars)
    return bars * native_minutes


def _created_ts(df: pd.DataFrame, confirmation_lag_min: pd.Series) -> pd.Series:
    fallback = pd.to_datetime(df["bar_end_utc"], utc=True, errors="coerce") + pd.to_timedelta(
        confirmation_lag_min,
        unit="m",
    )
    if "ed.knowable_ts_utc" not in df.columns:
        return fallback
    knowable = pd.to_datetime(df["ed.knowable_ts_utc"], utc=True, errors="coerce")
    return knowable.fillna(fallback)


def _point_size(df: pd.DataFrame, pivot_price: pd.Series, reference_close: pd.Series) -> pd.Series:
    pivot_bar_range = (_num_col(df, "ed.pivot_bar.high") - _num_col(df, "ed.pivot_bar.low")).abs()
    size = (reference_close - pivot_price).abs()
    size = size.where(size.gt(0), pivot_bar_range)
    return size.where(size.gt(0), 1.0).fillna(1.0)


def _base_frame(df: pd.DataFrame) -> pd.DataFrame:
    native_minutes = df["event_type"].map(SWING_NATIVE_MIN).astype("float64")
    confirmation_lag = df["event_type"].map(SWING_CONFIRMATION_LAG_MIN).astype("float64")
    knowable_ts = _created_ts(df, confirmation_lag)
    pivot_price = _num_col(df, "ed.pivot_price").fillna(_num_col(df, "oc.pivot_price"))
    reference_close = _num_col(df, "oc.reference_close").fillna(_num_col(df, "ed.pivot_bar.close"))
    size = _point_size(df, pivot_price, reference_close)
    side = _obj_col(df, "side").astype(str)
    direction = side.map({"high": "bearish", "low": "bullish"}).fillna(_obj_col(df, "oc.thesis_direction"))
    thesis_direction = _obj_col(df, "oc.thesis_direction")

    return pd.DataFrame(
        {
            "level.event_id": _obj_col(df, "event_id"),
            "level.kind": "swing_pivot",
            "level.subtype": _obj_col(df, "event_type"),
            "level.symbol": _obj_col(df, "primary_symbol"),
            "level.side": _obj_col(df, "side"),
            "level.created_ts_utc": knowable_ts.map(lambda ts: ts.isoformat() if pd.notna(ts) else None),
            "level.price_low": pivot_price,
            "level.price_high": pivot_price,
            "level.price_mid": pivot_price,
            "level.size_pts": size,
            "level.direction": direction,
            "level.thesis_direction": thesis_direction,
            "level.reference_close": reference_close,
            "level.native_timeframe": _obj_col(df, "ed.tracking_timeframe"),
            "level.native_minutes": native_minutes,
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
        fwd_prefix = "oc.forward_50_candles."
    else:
        horizon_bars = NATIVE_HORIZONS[horizon]
        fwd_prefix = f"oc.forward_{horizon_bars}_candles."

    native_minutes = base["level.native_minutes"].astype(float)
    size = base["level.size_pts"].astype(float)
    bars_to_wick = _num_col(df, "oc.breakout.bars_to_wick")
    bars_to_close = _num_col(df, "oc.breakout.bars_to_close")

    if horizon_bars is None:
        touched = bars_to_wick.notna()
        closed_through = bars_to_close.notna()
    else:
        touched = _within_bars(bars_to_wick, horizon_bars)
        closed_through = _within_bars(bars_to_close, horizon_bars)

    fwd_mfe = _num_col(df, fwd_prefix + "mfe_pts_in_thesis")
    fwd_mae = _num_col(df, fwd_prefix + "mae_pts_against_thesis")
    continuation_acceptance = fwd_mfe >= size
    directional_rejection = touched & ~closed_through & continuation_acceptance
    directional_break = closed_through
    partial_touch = touched & ~closed_through
    unfilled_expanded_away = ~touched & (fwd_mfe >= size)
    unfilled_clean_continuation = ~touched & (fwd_mfe >= 2.0 * size) & (fwd_mae <= size)

    values: dict[str, Any] = {
        "touched": touched,
        "meaningful_touch": touched,
        "partial_touch": partial_touch,
        "midpoint_touched": touched,
        "full_touch": closed_through,
        "closed_inside": partial_touch,
        "closed_through": closed_through,
        "directional_rejection": directional_rejection,
        "directional_break_acceptance": directional_break,
        "continuation_acceptance": continuation_acceptance,
        "through_acceptance": directional_break,
        "partial_touch_rejected": partial_touch & directional_rejection,
        "full_touch_rejected_inside": pd.Series(False, index=df.index),
        "clean_fill_through": directional_break,
        "unfilled_expanded_away": unfilled_expanded_away,
        "unfilled_clean_continuation": unfilled_clean_continuation,
        "time_to_touch_minutes": _time_to_minutes(bars_to_wick, native_minutes, horizon_bars),
        "time_to_meaningful_touch_minutes": _time_to_minutes(bars_to_wick, native_minutes, horizon_bars),
        "time_to_full_touch_minutes": _time_to_minutes(bars_to_close, native_minutes, horizon_bars),
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
    deepest_breakout = _num_col(df, "oc.breakout.deepest_breakout_pts")
    extreme_bars = _num_col(df, "oc.extreme.bars_to_extreme")
    extreme_bars_in_horizon = extreme_bars if horizon_bars is None else extreme_bars.where(extreme_bars <= horizon_bars)
    extra = {
        f"lr.{horizon}.wick_taken": touched,
        f"lr.{horizon}.close_taken": closed_through,
        f"lr.{horizon}.deepest_breakout_pts": deepest_breakout,
        f"lr.{horizon}.bars_to_extreme": extreme_bars_in_horizon,
        f"lr.{horizon}.time_to_extreme_minutes": _time_to_minutes(
            extreme_bars,
            native_minutes,
            horizon_bars,
        ),
    }
    return pd.DataFrame({**standard, **extra}, index=df.index)


def build_level_reactions(df: pd.DataFrame) -> pd.DataFrame:
    work = df[df["event_type"].isin(SWING_NATIVE_MIN)].copy()
    base = _base_frame(work)
    parts = [base]
    for horizon in SWING_HORIZONS:
        parts.append(_horizon_frame(base, work, horizon))
    out = pd.concat(parts, axis=1)
    out["level.first_meaningful_touch_age_bucket"] = out[
        level_reaction_column("full_horizon", "time_to_meaningful_touch_minutes")
    ].map(age_bucket_minutes).replace({"unreached_20d": SWING_UNREACHED_BUCKET})
    out["level.first_full_touch_age_bucket"] = out[
        level_reaction_column("full_horizon", "time_to_full_touch_minutes")
    ].map(age_bucket_minutes).replace({"unreached_20d": SWING_UNREACHED_BUCKET})
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
        for horizon in SWING_HORIZONS:
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
        "builder": "backend/scripts/ml/build_swing_level_reactions.py",
        "source_features": str(args.features),
        "output": str(args.output),
        "rows": int(len(levels)),
        "columns": list(levels.columns),
        "concept": {
            "level_kind": "swing_pivot",
            "subtypes": sorted(SWING_NATIVE_MIN),
            "source_outcome_version": "swing_pivot_reactions_v1",
            "native_horizons": NATIVE_HORIZONS,
            "confirmation_lag_minutes": SWING_CONFIRMATION_LAG_MIN,
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
        "# Swing Pivot Level Reactions",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "This maps swing-pivot point levels into the same `level.*` and `lr.*`",
        "vocabulary used by opening gaps, FVGs, order blocks, and sweeps.",
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
                "Wick Took Pivot",
                "Close Broke Pivot",
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
        "- `level.created_ts_utc` is the first knowable timestamp after right-side pivot confirmation.",
        "- `level.price_low/high/mid` are all the pivot price because swing pivots are point levels.",
        "- `level.size_pts` is a scale value from pivot price to pivot close, with a 1-point fallback.",
        "- `meaningful_touch` means a future wick traded beyond the pivot.",
        "- `full_touch` and `closed_through` mean a future close accepted beyond the pivot.",
        "- `directional_rejection` means the pivot was wicked, not closed through, and price moved at least one scale unit in the thesis direction.",
        f"- `{SWING_UNREACHED_BUCKET}` means no pivot take inside the 50-native-candle source horizon.",
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
