"""Build generic at-fire snapshot matrices for non-SMT concept anchors.

This is the generic, conservative snapshot factory. It turns existing
per-detector feature matrices into audited as-of rows:

  - one row per research event
  - feature cutoff = detector knowable timestamp
  - event-time features are renamed under the detector prefix
  - future outcomes are renamed under label.*

It intentionally does not add period-close aligned pc.* features yet. Those are
concept-specific and should be added after the at-fire factory is stable.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from baseline_per_detector import _feature_columns  # noqa: E402
from snapshot_feature_registry import (  # noqa: E402
    DISP_LAG_MIN,
    EQL_LAG_MIN,
    FVG_LAG_MIN,
    OB_LAG_MIN,
    PSP_LAG_MIN,
    SWEEP_LAG_MIN,
    registry_as_dict,
)

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
FEATURES_DIR = ROOT / "data" / "ml" / "features"
OUT_DIR = ROOT / "data" / "ml" / "anchors"


@dataclass(frozen=True, slots=True)
class AnchorConfig:
    short_name: str
    feature_name: str
    feature_path: Path
    output_stem: str
    lag_minutes_by_event_type: dict[str, int] | None = None
    knowable_col: str | None = None
    knowable_offset_min: int = 0
    label_horizon_minutes: int | None = None


ANCHORS: dict[str, AnchorConfig] = {
    "fvg": AnchorConfig(
        short_name="fvg",
        feature_name="fvg_formation",
        feature_path=FEATURES_DIR / "fvg.parquet",
        output_stem="fvg_snapshots",
        lag_minutes_by_event_type=FVG_LAG_MIN,
    ),
    "sweep": AnchorConfig(
        short_name="sweep",
        feature_name="liquidity_sweep",
        feature_path=FEATURES_DIR / "sweep.parquet",
        output_stem="sweep_snapshots",
        lag_minutes_by_event_type=SWEEP_LAG_MIN,
    ),
    "disp": AnchorConfig(
        short_name="disp",
        feature_name="displacement_candle",
        feature_path=FEATURES_DIR / "disp.parquet",
        output_stem="disp_snapshots",
        lag_minutes_by_event_type=DISP_LAG_MIN,
    ),
    "ob": AnchorConfig(
        short_name="ob",
        feature_name="order_block",
        feature_path=FEATURES_DIR / "ob.parquet",
        output_stem="ob_snapshots",
        lag_minutes_by_event_type=OB_LAG_MIN,
    ),
    "psp": AnchorConfig(
        short_name="psp",
        feature_name="psp_candle_divergence",
        feature_path=FEATURES_DIR / "psp.parquet",
        output_stem="psp_snapshots",
        lag_minutes_by_event_type=PSP_LAG_MIN,
    ),
    "swing": AnchorConfig(
        short_name="swing",
        feature_name="swing_pivot",
        feature_path=FEATURES_DIR / "swing.parquet",
        output_stem="swing_snapshots",
        knowable_col="ed.knowable_ts_utc",
        label_horizon_minutes=60 * 24 * 30,
    ),
    "eql": AnchorConfig(
        short_name="eql",
        feature_name="equal_levels",
        feature_path=FEATURES_DIR / "eql.parquet",
        output_stem="eql_snapshots",
        lag_minutes_by_event_type=EQL_LAG_MIN,
    ),
    "ft": AnchorConfig(
        short_name="ft",
        feature_name="first_third_range",
        feature_path=FEATURES_DIR / "ft.parquet",
        output_stem="ft_snapshots",
        knowable_col="ed.first_third_end_utc",
        knowable_offset_min=1,
        label_horizon_minutes=60 * 24 * 14,
    ),
    "orb": AnchorConfig(
        short_name="orb",
        feature_name="opening_range_breakout",
        feature_path=FEATURES_DIR / "orb.parquet",
        output_stem="orb_snapshots",
        knowable_col="ed.range_end_utc",
        label_horizon_minutes=60 * 24 * 3,
    ),
    "tp": AnchorConfig(
        short_name="tp",
        feature_name="time_profile",
        feature_path=FEATURES_DIR / "tp.parquet",
        output_stem="tp_snapshots",
        knowable_col="ed.parent_period_end_utc",
        label_horizon_minutes=60 * 24 * 30,
    ),
    "vp": AnchorConfig(
        short_name="vp",
        feature_name="volume_profile",
        feature_path=FEATURES_DIR / "vp.parquet",
        output_stem="vp_snapshots",
        knowable_col="ed.parent_period_end_utc",
        label_horizon_minutes=60 * 24 * 30,
    ),
    "fvp": AnchorConfig(
        short_name="fvp",
        feature_name="forming_volume_profile",
        feature_path=FEATURES_DIR / "fvp.parquet",
        output_stem="forming_vp_snapshots",
        knowable_col="ed.asof_ts_utc",
        label_horizon_minutes=60 * 24,
    ),
    "ogap": AnchorConfig(
        short_name="ogap",
        feature_name="opening_gap_levels",
        feature_path=FEATURES_DIR / "ogap.parquet",
        output_stem="opening_gap_snapshots",
        knowable_col="ed.gap_open_ts_utc",
        label_horizon_minutes=20 * 24 * 60,
    ),
    "itr": AnchorConfig(
        short_name="itr",
        feature_name="interval_true_range",
        feature_path=FEATURES_DIR / "itr.parquet",
        output_stem="itr_snapshots",
        knowable_col="ed.interval_end_utc",
        label_horizon_minutes=60 * 24 * 45,
    ),
}

OUTCOME_NON_TARGET_COLUMNS = {
    "oc.schema_version",
    "oc.outcome_version",
    "oc.thesis_direction",
    "oc.reference_close",
    "oc.manipulation_close",
    "oc.ref_price",
    "oc.ref_side",
    "oc.fvg_high",
    "oc.fvg_low",
    "oc.fvg_mid",
    "oc.fvg_width_pts",
    "oc.next_period.ts_utc_start",
    "oc.next_period.ts_utc_end",
    "oc.n_plus_2.ts_utc_start",
    "oc.n_plus_2.ts_utc_end",
}
OUTCOME_NON_TARGET_PREFIXES = (
    "oc.displacement_levels.",
)


def _parse_csv_arg(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _label_name(col: str) -> str:
    return "label." + col.removeprefix("oc.")


def _is_target_label_col(col: str) -> bool:
    leaf = col.rsplit(".", 1)[-1]
    return (
        col.startswith("oc.")
        and col not in OUTCOME_NON_TARGET_COLUMNS
        and not col.startswith(OUTCOME_NON_TARGET_PREFIXES)
        and not leaf.startswith("ts_")
        and not leaf.endswith("_utc")
    )


def _filter_df(df: pd.DataFrame, *, event_type: str, side: str) -> pd.DataFrame:
    out = df.copy()
    if event_type != "all":
        out = out[out["event_type"] == event_type].copy()
    if side != "all":
        out = out[out["side"] == side].copy()
    return out


def _snapshot_ts(df: pd.DataFrame, config: AnchorConfig) -> pd.Series:
    if config.knowable_col:
        if config.knowable_col not in df.columns:
            raise KeyError(f"{config.short_name}: missing knowable_col={config.knowable_col!r}")
        snapshot_ts = pd.to_datetime(df[config.knowable_col], utc=True)
        if snapshot_ts.isna().any():
            missing_count = int(snapshot_ts.isna().sum())
            raise ValueError(
                f"{config.short_name}: {config.knowable_col} has {missing_count:,} null values"
            )
        if config.knowable_offset_min:
            snapshot_ts = snapshot_ts + pd.to_timedelta(config.knowable_offset_min, unit="m")
        return snapshot_ts

    if config.lag_minutes_by_event_type is None:
        raise ValueError(f"{config.short_name}: no knowable_col or lag rule configured")

    lag_minutes = df["event_type"].map(config.lag_minutes_by_event_type)
    if lag_minutes.isna().any():
        missing = sorted(str(x) for x in df.loc[lag_minutes.isna(), "event_type"].unique())
        raise ValueError(
            f"{config.short_name} has event_type values missing lag rules: {missing}"
        )

    bar_end = pd.to_datetime(df["bar_end_utc"], utc=True)
    return bar_end + pd.to_timedelta(lag_minutes.astype(int), unit="m")


def _label_horizon_minutes(config: AnchorConfig) -> int:
    if config.label_horizon_minutes is not None:
        return config.label_horizon_minutes
    if config.lag_minutes_by_event_type:
        return max(config.lag_minutes_by_event_type.values()) * 50
    return 60 * 24 * 14


def _build_rows(df: pd.DataFrame, config: AnchorConfig) -> pd.DataFrame:
    numeric_cols, categorical_cols = _feature_columns(df, config.short_name)
    raw_feature_cols = numeric_cols + categorical_cols
    feature_rename = {
        col: col if col.startswith("xd.") else f"{config.short_name}.{col}"
        for col in raw_feature_cols
    }
    features = df[raw_feature_cols].rename(columns=feature_rename)

    label_cols = [col for col in df.columns if _is_target_label_col(col)]
    labels = df[label_cols].rename(columns={col: _label_name(col) for col in label_cols})
    for col in labels.columns:
        if labels[col].dtype == "object":
            num = pd.to_numeric(labels[col], errors="coerce")
            if labels[col].notna().sum() and num.notna().sum() > 0.95 * labels[col].notna().sum():
                labels[col] = num

    bar_end = pd.to_datetime(df["bar_end_utc"], utc=True)
    snapshot_ts = _snapshot_ts(df, config)
    label_horizon_minutes = _label_horizon_minutes(config)

    base = pd.DataFrame(index=df.index)
    base["anchor.event_id"] = df["event_id"].astype(int)
    base["asof.snapshot"] = "at_fire"
    base["anchor.feature_name"] = config.feature_name
    base["anchor.short_name"] = config.short_name
    base["anchor.event_type"] = df["event_type"]
    base["anchor.side"] = df["side"]
    base["anchor.primary_symbol"] = df["primary_symbol"]
    base["anchor.bar_end_utc"] = bar_end
    base["asof.snapshot_ts"] = snapshot_ts
    base["asof.feature_cutoff_ts"] = snapshot_ts
    # Generic future-response labels begin after the detector is knowable.
    base["asof.label_start_ts"] = snapshot_ts + pd.to_timedelta(1, unit="s")
    base["asof.label_end_ts"] = snapshot_ts + pd.to_timedelta(label_horizon_minutes, unit="m")

    ts = pd.to_datetime(base["asof.snapshot_ts"], utc=True)
    base["ts.year"] = ts.dt.year
    base["ts.month"] = ts.dt.month
    base["ts.day_of_week"] = ts.dt.dayofweek
    base["ts.hour_of_day_utc"] = ts.dt.hour

    matrix = pd.concat([base, features, labels], axis=1)
    matrix = matrix.sort_values(["asof.snapshot_ts", "anchor.event_id"]).reset_index(drop=True)
    return matrix


def _write_schema(
    path: Path,
    *,
    matrix: pd.DataFrame,
    config: AnchorConfig,
    args: argparse.Namespace,
) -> None:
    feature_prefixes = (f"{config.short_name}.", "xd.", "ts.")
    feature_cols = [c for c in matrix.columns if c.startswith(feature_prefixes)]
    label_cols = [c for c in matrix.columns if c.startswith("label.")]
    meta = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "builder": "backend/scripts/ml/build_generic_anchor_snapshots.py",
        "anchor": {
            "feature_name": config.feature_name,
            "short_name": config.short_name,
            "event_type": args.event_type,
            "side": args.side,
            "knowable_col": config.knowable_col,
            "knowable_offset_min": config.knowable_offset_min,
            "lag_event_types": sorted((config.lag_minutes_by_event_type or {}).keys()),
        },
        "snapshot_names": sorted(matrix["asof.snapshot"].unique().tolist()),
        "rows": int(len(matrix)),
        "feature_columns": feature_cols,
        "label_columns": label_cols,
        "registry": registry_as_dict(),
        "notes": [
            "Generic at-fire snapshots only.",
            "Feature cutoff is detector knowable timestamp from explicit event knowable columns or configured event-type lags.",
            "Labels are copied from oc.* and are not model features.",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def build_one(config: AnchorConfig, args: argparse.Namespace) -> tuple[Path, Path, pd.DataFrame]:
    df = pd.read_parquet(config.feature_path)
    df["bar_end_utc"] = pd.to_datetime(df["bar_end_utc"], utc=True)
    df = _filter_df(df, event_type=args.event_type, side=args.side)
    if df.empty:
        raise ValueError(
            f"{config.short_name}: no rows after event_type={args.event_type}, side={args.side}"
        )
    matrix = _build_rows(df, config)
    suffix = ""
    if args.event_type != "all":
        suffix += f"_{args.event_type}"
    if args.side != "all":
        suffix += f"_{args.side}"
    out_path = args.output_dir / f"{config.output_stem}{suffix}.parquet"
    schema_path = args.output_dir / f"{config.output_stem}{suffix}.schema.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    matrix.to_parquet(out_path, index=False)
    _write_schema(schema_path, matrix=matrix, config=config, args=args)
    return out_path, schema_path, matrix


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchors", type=_parse_csv_arg, default=sorted(ANCHORS))
    parser.add_argument("--event-type", default="all")
    parser.add_argument("--side", default="all")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    for name in args.anchors:
        if name not in ANCHORS:
            raise KeyError(f"unknown anchor {name!r}; choices={sorted(ANCHORS)}")

    for name in args.anchors:
        config = ANCHORS[name]
        out_path, schema_path, matrix = build_one(config, args)
        print(
            f"wrote {out_path}: {len(matrix):,} rows x {len(matrix.columns)} cols"
        )
        print(f"wrote {schema_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
