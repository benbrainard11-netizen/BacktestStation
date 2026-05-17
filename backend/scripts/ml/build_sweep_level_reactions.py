"""Build a universal level-reaction table for liquidity-sweep levels.

A sweep level is already touched at event creation, so the useful forward
questions are whether price recovered/rejected back through the swept level or
continued beyond the manipulation extreme. Horizons are native-candle based.
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

DEFAULT_FEATURES = FEATURES_DIR / "sweep.parquet"
DEFAULT_OUTPUT = LEVELS_DIR / "sweep_level_reactions.parquet"
DEFAULT_SCHEMA_OUTPUT = LEVELS_DIR / "sweep_level_reactions.schema.json"
DEFAULT_STATS = LEVELS_DIR / "sweep_level_reaction_stats.csv"
DEFAULT_AGE_DECAY = LEVELS_DIR / "sweep_level_age_decay.csv"
DEFAULT_DOC = ROOT / "docs" / "ML_SWEEP_LEVEL_REACTIONS.md"

SWEEP_LAG_MIN = {
    "pdl_1h": 60,
    "pdl_4h": 240,
    "pdh_1h": 60,
    "pdh_4h": 240,
    "pwl_4h": 240,
    "pwl_daily": 24 * 60,
    "pwh_4h": 240,
    "pwh_daily": 24 * 60,
    "asia_low_1h": 60,
    "asia_high_1h": 60,
    "london_low_1h": 60,
    "london_high_1h": 60,
    "ny_low_1h": 60,
    "ny_high_1h": 60,
}
NATIVE_HORIZONS = {
    "next_3_bars": 3,
    "next_10_bars": 10,
    "next_50_bars": 50,
}
SWEEP_HORIZONS = (*NATIVE_HORIZONS.keys(), "full_horizon")
SWEEP_UNREACHED_BUCKET = "unreached_native_horizon"

STAT_FIELDS = (
    "touched",
    "meaningful_touch",
    "full_touch",
    "closed_inside",
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


def _base_frame(df: pd.DataFrame) -> pd.DataFrame:
    lag_min = df["event_type"].map(SWEEP_LAG_MIN).astype("float64")
    manipulation_ts = pd.to_datetime(df["bar_end_utc"], utc=True)
    knowable_ts = manipulation_ts + pd.to_timedelta(lag_min, unit="m")
    ref_price = _num_col(df, "ed.swept_reference.level_price").fillna(_num_col(df, "oc.ref_price"))
    depth = _num_col(df, "ed.sweep_depth_pts")
    thesis = _obj_col(df, "ed.thesis").fillna(_obj_col(df, "oc.thesis_direction"))
    native_tf = (
        _obj_col(df, "ed.tracking_timeframe")
        if "ed.tracking_timeframe" in df.columns
        else df["event_type"].map(lambda x: "daily" if str(x).endswith("_daily") else str(x).rsplit("_", 1)[-1])
    )
    return pd.DataFrame(
        {
            "level.event_id": _obj_col(df, "event_id"),
            "level.kind": "liquidity_sweep",
            "level.subtype": _obj_col(df, "event_type"),
            "level.symbol": _obj_col(df, "primary_symbol"),
            "level.side": _obj_col(df, "side"),
            "level.created_ts_utc": knowable_ts.map(lambda ts: ts.isoformat()),
            "level.price_low": ref_price,
            "level.price_high": ref_price,
            "level.price_mid": ref_price,
            "level.size_pts": depth,
            "level.direction": thesis,
            "level.ref_type": _obj_col(df, "ed.ref_type"),
            "level.ref_side": _obj_col(df, "ed.ref_side", _obj_col(df, "side")),
            "level.manipulation_low": _num_col(df, "ed.manipulation_candle.low"),
            "level.manipulation_high": _num_col(df, "ed.manipulation_candle.high"),
            "level.manipulation_close": _num_col(df, "ed.manipulation_candle.close").fillna(
                _num_col(df, "oc.manipulation_close")
            ),
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
    else:
        horizon_bars = NATIVE_HORIZONS[horizon]
        fwd_prefix = f"oc.forward_{horizon_bars}_candles."

    lag_min = base["level.native_minutes"].astype(float)
    size = base["level.size_pts"].astype(float)
    recovery_bars = _num_col(df, "oc.swept_level_recovery.bars_to_recovery")
    continuation_bars = _num_col(df, "oc.forward_continuation.bars_to_first_extension")
    ob_bars = _num_col(df, "oc.ob_confirmation.bars_to_first_ob")

    if horizon_bars is None:
        recovered = recovery_bars.notna()
        continued = continuation_bars.notna()
        ob_confirmed = ob_bars.notna()
    else:
        recovered = _within_bars(recovery_bars, horizon_bars)
        continued = _within_bars(continuation_bars, horizon_bars)
        ob_confirmed = _within_bars(ob_bars, horizon_bars)

    touched = pd.Series(True, index=df.index)
    fwd_mfe = _num_col(df, fwd_prefix + "mfe_pts_in_thesis")
    fwd_mae = _num_col(df, fwd_prefix + "mae_pts_against_thesis")
    thesis_move_1x = fwd_mfe >= size
    thesis_move_half = fwd_mfe >= 0.5 * size
    adverse_move_1x = fwd_mae >= size
    directional_rejection = recovered & thesis_move_1x
    directional_break = continued & adverse_move_1x
    weak_recovery = recovered & thesis_move_half & ~directional_rejection
    unfilled_continuation = ~recovered & directional_break

    values: dict[str, Any] = {
        "touched": touched,
        "meaningful_touch": recovered,
        "partial_touch": weak_recovery,
        "midpoint_touched": recovered,
        "full_touch": recovered,
        "closed_inside": recovered,
        "closed_through": directional_break,
        "directional_rejection": directional_rejection,
        "directional_break_acceptance": directional_break,
        "continuation_acceptance": directional_rejection,
        "through_acceptance": directional_break,
        "partial_touch_rejected": weak_recovery,
        "full_touch_rejected_inside": directional_rejection,
        "clean_fill_through": recovered & directional_break,
        "unfilled_expanded_away": unfilled_continuation,
        "unfilled_clean_continuation": unfilled_continuation,
        "time_to_touch_minutes": pd.Series(0.0, index=df.index),
        "time_to_meaningful_touch_minutes": _time_to_minutes(recovery_bars, lag_min, horizon_bars),
        "time_to_full_touch_minutes": _time_to_minutes(recovery_bars, lag_min, horizon_bars),
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
        f"lr.{horizon}.sweep_recovered": recovered,
        f"lr.{horizon}.continued_beyond_manipulation": continued,
        f"lr.{horizon}.ob_confirmed": ob_confirmed,
        f"lr.{horizon}.sweep_failed_recovered": recovered,
        f"lr.{horizon}.sweep_held_rejection": directional_rejection & ~continued,
        f"lr.{horizon}.sweep_recovered_then_continued": recovered & continued,
        f"lr.{horizon}.sweep_extended_continuation": unfilled_continuation,
        f"lr.{horizon}.time_to_continuation_minutes": _time_to_minutes(continuation_bars, lag_min, horizon_bars),
        f"lr.{horizon}.time_to_ob_confirm_minutes": _time_to_minutes(ob_bars, lag_min, horizon_bars),
    }
    return pd.DataFrame({**standard, **extra}, index=df.index)


def build_level_reactions(df: pd.DataFrame) -> pd.DataFrame:
    work = df[df["event_type"].isin(SWEEP_LAG_MIN)].copy()
    base = _base_frame(work)
    parts = [base]
    for horizon in SWEEP_HORIZONS:
        parts.append(_horizon_frame(base, work, horizon))
    out = pd.concat(parts, axis=1)
    out["level.first_meaningful_touch_age_bucket"] = out[
        level_reaction_column("full_horizon", "time_to_meaningful_touch_minutes")
    ].map(age_bucket_minutes).replace({"unreached_20d": SWEEP_UNREACHED_BUCKET})
    out["level.first_full_touch_age_bucket"] = out[
        level_reaction_column("full_horizon", "time_to_full_touch_minutes")
    ].map(age_bucket_minutes).replace({"unreached_20d": SWEEP_UNREACHED_BUCKET})
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
        for horizon in SWEEP_HORIZONS:
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
                "ob_confirmed_rate": _rate(sub[f"lr.{horizon}.ob_confirmed"]),
                "continued_beyond_manipulation_rate": _rate(
                    sub[f"lr.{horizon}.continued_beyond_manipulation"]
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
                "full_horizon_ob_confirmed_rate": _rate(sub["lr.full_horizon.ob_confirmed"]),
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
        "builder": "backend/scripts/ml/build_sweep_level_reactions.py",
        "source_features": str(args.features),
        "output": str(args.output),
        "rows": int(len(levels)),
        "columns": list(levels.columns),
        "concept": {
            "level_kind": "liquidity_sweep",
            "subtypes": sorted(SWEEP_LAG_MIN),
            "source_outcome_version": "liquidity_sweep_reactions_v2",
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
                _fmt_pct(r["directional_rejection_rate"]),
                _fmt_pct(r["directional_break_acceptance_rate"]),
                _fmt_pct(r["continued_beyond_manipulation_rate"]),
                _fmt_pct(r["ob_confirmed_rate"]),
                f"{float(r['avg_reaction_away_x_size']):.2f}x",
            ]
        )
    age_rows = []
    for _, r in age.head(70).iterrows():
        age_rows.append(
            [
                f"`{r['level_subtype']}`",
                f"`{r['side']}`",
                f"`{r['first_meaningful_touch_age_bucket']}`",
                f"{int(r['rows']):,}",
                _fmt_pct(r["share_of_subtype_side"]),
                _fmt_pct(r["full_horizon_directional_rejection_rate"]),
                _fmt_pct(r["full_horizon_directional_break_rate"]),
                _fmt_pct(r["full_horizon_ob_confirmed_rate"]),
                f"{float(r['avg_reaction_away_x_size']):.2f}x",
            ]
        )
    text = [
        "# Liquidity Sweep Level Reactions",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "This maps swept reference levels into the same `level.*` and `lr.*`",
        "vocabulary used by opening gaps, FVGs, and order blocks.",
        "Sweep horizons are native-candle windows because the source outcome computer is native-timeframe based.",
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
                "Recovered",
                "Reject",
                "Break",
                "Continued",
                "OB Confirmed",
                "Avg Thesis / Depth",
            ],
            stat_rows,
        ),
        "",
        "## Recovery Age Decay",
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
                "OB Confirmed",
                "Avg Thesis / Depth",
            ],
            age_rows,
        ),
        "",
        "## Notes",
        "",
        "- `level.price_low/high` are both the swept reference price; sweeps are point-level events.",
        "- `level.size_pts` is sweep depth from reference level to manipulation extreme.",
        "- `touched` is always true because a sweep event is created only after the level is swept.",
        "- `meaningful_touch` means price closed back through the swept level in the rejection thesis direction.",
        "- `directional_rejection` means recovery plus at least 1x sweep-depth thesis movement.",
        "- `directional_break_acceptance` means continuation beyond the manipulation extreme plus at least 1x adverse movement.",
        "- Extra columns include `lr.<horizon>.ob_confirmed`, `sweep_held_rejection`, and `sweep_extended_continuation`.",
        f"- `{SWEEP_UNREACHED_BUCKET}` means no recovery inside the 50-native-candle source horizon.",
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
