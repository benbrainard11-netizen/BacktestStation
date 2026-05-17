"""Build parent/child timeframe-stack context reports.

This answers the research question:

    "When a parent SMT fires, which lower-timeframe concepts were already
    present, and which child timeframes seem to improve the SMT forward label?"

The output is descriptive, not a trading rule. `phase=pre` rows are safe as
model inputs because child events must be knowable at or before the parent
cutoff. `phase=post` rows are analysis-only because they form after the parent
signal and should not be used as parent-signal model features.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from snapshot_feature_registry import (  # noqa: E402
    DISP_LAG_MIN,
    EQL_LAG_MIN,
    FVG_LAG_MIN,
    OB_LAG_MIN,
    PSP_LAG_MIN,
    SMT_LAG_MIN,
    SMT_MTF_LAG_MIN,
    SWEEP_LAG_MIN,
    SWING_LAG_MIN,
)

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
FEATURES_DIR = ROOT / "data" / "ml" / "features"
CONTEXT_DIR = ROOT / "data" / "ml" / "context"
DOC_PATH = ROOT / "docs" / "ML_TIMEFRAME_STACK_CONTEXT.md"
SUMMARY_CSV = CONTEXT_DIR / "timeframe_stack_context_summary.csv"
SUMMARY_PARQUET = CONTEXT_DIR / "timeframe_stack_context_summary.parquet"
MANIFEST_JSON = CONTEXT_DIR / "timeframe_stack_context_manifest.json"

NS_PER_MIN = 60 * 1_000_000_000
WINDOWS_MIN = {
    "1h": 60,
    "4h": 240,
    "1d": 24 * 60,
    "3d": 3 * 24 * 60,
    "7d": 7 * 24 * 60,
}

TF_MINUTES = {
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "90m": 90,
    "4h": 240,
    "6h": 360,
    "1d": 24 * 60,
    "daily": 24 * 60,
    "1w": 7 * 24 * 60,
    "weekly": 7 * 24 * 60,
}

PARENT_CONFIGS = {
    "smt": {
        "path": FEATURES_DIR / "smt.parquet",
        "lag_min": SMT_LAG_MIN,
        "labels": (
            "oc.next_period.thesis_confirmed_strict",
            "oc.next_period.close_moved_with_thesis",
            "oc.n_plus_2.thesis_confirmed_strict",
        ),
    },
    "smt_mtf": {
        "path": FEATURES_DIR / "smt_mtf.parquet",
        "lag_min": SMT_MTF_LAG_MIN,
        "labels": (
            "oc.next_15m.thesis_confirmed",
            "oc.next_30m.thesis_confirmed",
            "oc.next_60m.thesis_confirmed",
            "oc.next_240m.thesis_confirmed",
            "oc.next_1d.thesis_confirmed",
        ),
    },
}

CHILD_CONFIGS = {
    "ob": {"path": FEATURES_DIR / "ob.parquet", "lag_min": OB_LAG_MIN},
    "fvg": {"path": FEATURES_DIR / "fvg.parquet", "lag_min": FVG_LAG_MIN},
    "sweep": {"path": FEATURES_DIR / "sweep.parquet", "lag_min": SWEEP_LAG_MIN},
    "psp": {"path": FEATURES_DIR / "psp.parquet", "lag_min": PSP_LAG_MIN},
    "swing": {"path": FEATURES_DIR / "swing.parquet", "lag_min": SWING_LAG_MIN},
    "eql": {"path": FEATURES_DIR / "eql.parquet", "lag_min": EQL_LAG_MIN},
    "disp": {"path": FEATURES_DIR / "disp.parquet", "lag_min": DISP_LAG_MIN},
}


@dataclass(frozen=True, slots=True)
class ChildBucket:
    concept: str
    child_tf: str
    child_tf_min: int
    relation: str
    primary_symbol: str
    times_ns: np.ndarray


def _parse_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


def _safe_bool_rate(values: pd.Series) -> float:
    valid = values.dropna()
    if valid.empty:
        return float("nan")
    return float(valid.astype(bool).mean())


def _pct(value: float | None) -> str:
    if value is None or not math.isfinite(float(value)):
        return "-"
    return f"{float(value) * 100:.1f}%"


def _signed_pct(value: float | None) -> str:
    if value is None or not math.isfinite(float(value)):
        return "-"
    return f"{float(value) * 100:+.1f}%"


def _fmt_int(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    return f"{int(value):,}"


def _read_existing(path: Path, columns: list[str] | None = None) -> pd.DataFrame | None:
    if not path.exists():
        return None
    if columns is None:
        return pd.read_parquet(path)
    available = set(pd.read_parquet(path, engine="pyarrow").columns)
    keep = [col for col in columns if col in available]
    return pd.read_parquet(path, columns=keep)


def _tf_from_event_type(event_type: str) -> str | None:
    text = str(event_type).lower()
    for token in ("15m", "30m", "90m", "1h", "4h", "6h", "daily"):
        if token in text:
            return "1d" if token == "daily" else token
    return None


def _normalize_tf(value: Any, event_type: Any = None) -> str | None:
    if value is not None and not pd.isna(value):
        text = str(value).strip().lower()
        aliases = {"1d": "1d", "daily": "1d", "day": "1d", "4h": "4h", "1h": "1h"}
        if text in aliases:
            return aliases[text]
        if text in TF_MINUTES:
            return text
    if event_type is not None:
        return _tf_from_event_type(str(event_type))
    return None


def _minutes_for_tf(tf: str | None) -> int | None:
    if tf is None:
        return None
    return TF_MINUTES.get(tf)


def _parent_tf(row: pd.Series, parent: str) -> str | None:
    event_type = str(row.get("event_type", ""))
    if parent == "smt":
        if event_type == "weekly_smt":
            return "1w"
        if event_type == "previous_day_smt":
            return "1d"
    return _normalize_tf(row.get("ed.tracking_timeframe"), event_type)


def _direction_from_side(side: Any) -> str | None:
    if side is None or pd.isna(side):
        return None
    text = str(side).lower()
    if text in {"low", "bullish", "up", "long"}:
        return "up"
    if text in {"high", "bearish", "down", "short"}:
        return "down"
    return None


def _lagged_cutoff(df: pd.DataFrame, lag_map: dict[str, int]) -> pd.Series:
    lag = df["event_type"].map(lag_map).fillna(0).astype(int)
    return pd.to_datetime(df["bar_end_utc"], utc=True) + pd.to_timedelta(lag, unit="m")


def load_parents(selected: set[str] | None) -> tuple[pd.DataFrame, list[str]]:
    frames: list[pd.DataFrame] = []
    missing: list[str] = []
    for parent, config in PARENT_CONFIGS.items():
        if selected is not None and parent not in selected:
            continue
        path = config["path"]
        df = _read_existing(path)
        if df is None:
            missing.append(parent)
            continue
        needed_labels = [label for label in config["labels"] if label in df.columns]
        if not needed_labels:
            missing.append(f"{parent}:no_labels")
            continue
        keep = [
            "event_id",
            "bar_end_utc",
            "event_type",
            "side",
            "primary_symbol",
            "ed.tracking_timeframe",
            *needed_labels,
        ]
        df = df[[col for col in keep if col in df.columns]].copy()
        df["parent"] = parent
        df["parent_tf"] = df.apply(lambda row: _parent_tf(row, parent), axis=1)
        df["parent_tf_min"] = df["parent_tf"].map(_minutes_for_tf)
        df["parent_cutoff_ts"] = _lagged_cutoff(df, config["lag_min"])
        df["parent_thesis"] = df["side"].map(_direction_from_side)
        df["year"] = df["parent_cutoff_ts"].dt.year
        df["label_columns"] = ",".join(needed_labels)
        frames.append(df)
    if not frames:
        return pd.DataFrame(), missing
    out = pd.concat(frames, ignore_index=True)
    out = out[out["parent_tf_min"].notna() & out["parent_thesis"].notna()].copy()
    out["parent_tf_min"] = out["parent_tf_min"].astype(int)
    return out, missing


def load_children(selected: set[str] | None) -> tuple[list[ChildBucket], dict[str, int]]:
    buckets: list[ChildBucket] = []
    counts: dict[str, int] = {}
    for concept, config in CHILD_CONFIGS.items():
        if selected is not None and concept not in selected:
            continue
        df = _read_existing(config["path"])
        if df is None or df.empty:
            counts[concept] = 0
            continue
        keep = [
            "bar_end_utc",
            "event_type",
            "side",
            "primary_symbol",
            "ed.tracking_timeframe",
            "ctx.tracking_timeframe",
        ]
        df = df[[col for col in keep if col in df.columns]].copy()
        tf_source = df.get("ed.tracking_timeframe")
        if tf_source is None:
            tf_source = df.get("ctx.tracking_timeframe")
        if tf_source is None:
            tf_source = pd.Series([None] * len(df), index=df.index)
        df["child_tf"] = [
            _normalize_tf(tf, event_type)
            for tf, event_type in zip(tf_source, df["event_type"], strict=False)
        ]
        df["child_tf_min"] = df["child_tf"].map(_minutes_for_tf)
        df["child_cutoff_ts"] = _lagged_cutoff(df, config["lag_min"])
        df["child_direction"] = df["side"].map(_direction_from_side)
        df = df[
            df["child_tf_min"].notna()
            & df["child_direction"].notna()
            & df["primary_symbol"].notna()
        ].copy()
        df["child_tf_min"] = df["child_tf_min"].astype(int)
        counts[concept] = int(len(df))
        for (child_tf, child_tf_min, primary), sub in df.groupby(
            ["child_tf", "child_tf_min", "primary_symbol"],
            dropna=False,
        ):
            times = sub["child_cutoff_ts"].to_numpy(dtype="datetime64[ns]").astype("int64")
            times.sort()
            buckets.append(
                ChildBucket(
                    concept=concept,
                    child_tf=str(child_tf),
                    child_tf_min=int(child_tf_min),
                    relation="any:any",
                    primary_symbol=str(primary),
                    times_ns=times,
                )
            )
        # Actual alignment is applied per parent thesis below; keep both
        # directions as separate buckets for fast filtering.
        for relation in ("aligned", "opposed"):
            for (child_tf, child_tf_min, direction, primary), sub in df.groupby(
                ["child_tf", "child_tf_min", "child_direction", "primary_symbol"],
                dropna=False,
            ):
                times = sub["child_cutoff_ts"].to_numpy(dtype="datetime64[ns]").astype("int64")
                times.sort()
                buckets.append(
                    ChildBucket(
                        concept=concept,
                        child_tf=str(child_tf),
                        child_tf_min=int(child_tf_min),
                        relation=f"{relation}:{direction}",
                        primary_symbol=str(primary),
                        times_ns=times,
                    )
                )
    return buckets, counts


def _has_in_pre_window(cutoff_ns: np.ndarray, child_ns: np.ndarray, window_min: int) -> np.ndarray:
    left = np.searchsorted(child_ns, cutoff_ns - window_min * NS_PER_MIN, side="left")
    right = np.searchsorted(child_ns, cutoff_ns, side="right")
    return right > left


def _has_in_post_window(cutoff_ns: np.ndarray, child_ns: np.ndarray, window_min: int) -> np.ndarray:
    left = np.searchsorted(child_ns, cutoff_ns, side="right")
    right = np.searchsorted(child_ns, cutoff_ns + window_min * NS_PER_MIN, side="right")
    return right > left


def _base_rows_for_group(group: pd.DataFrame, labels: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for label in labels:
        if label not in group.columns:
            continue
        y = group[label]
        valid = y.notna()
        out[label] = {
            "base_n": int(valid.sum()),
            "base_rate": _safe_bool_rate(y),
        }
    return out


def build_summary(
    parents: pd.DataFrame,
    child_buckets: list[ChildBucket],
    *,
    min_n: int,
    phases: set[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if parents.empty or not child_buckets:
        return pd.DataFrame(rows)

    bucket_groups: dict[tuple[str, str, int, str], list[ChildBucket]] = defaultdict(list)
    for bucket in child_buckets:
        bucket_groups[
            (bucket.concept, bucket.child_tf, bucket.child_tf_min, bucket.relation)
        ].append(bucket)

    labels_by_parent = {
        parent: [label for label in PARENT_CONFIGS[parent]["labels"] if label in parents.columns]
        for parent in parents["parent"].unique()
    }

    group_cols = ["parent", "event_type", "parent_tf", "side"]
    for group_key, group in parents.groupby(group_cols, dropna=False):
        parent, event_type, parent_tf, side = group_key
        parent_tf_min = int(group["parent_tf_min"].iloc[0])
        thesis = str(group["parent_thesis"].iloc[0])
        labels = labels_by_parent.get(str(parent), [])
        base_by_label = _base_rows_for_group(group, labels)
        if not base_by_label:
            continue
        cutoff_ns_all = group["parent_cutoff_ts"].to_numpy(dtype="datetime64[ns]").astype("int64")
        primary_all = group["primary_symbol"].astype(str).to_numpy()

        for (concept, child_tf, child_tf_min, relation_key), buckets in bucket_groups.items():
            if child_tf_min >= parent_tf_min:
                continue
            raw_relation, direction = relation_key.split(":", 1)
            if raw_relation == "aligned" and direction != thesis:
                continue
            if raw_relation == "opposed" and direction == thesis:
                continue
            relation = raw_relation

            for window_label, window_min in WINDOWS_MIN.items():
                for phase in phases:
                    has = np.zeros(len(group), dtype=bool)
                    for bucket in buckets:
                        primary_mask = primary_all == bucket.primary_symbol
                        if not primary_mask.any():
                            continue
                        idx = np.where(primary_mask)[0]
                        if phase == "pre":
                            has[idx] |= _has_in_pre_window(
                                cutoff_ns_all[idx],
                                bucket.times_ns,
                                window_min,
                            )
                        elif phase == "post":
                            has[idx] |= _has_in_post_window(
                                cutoff_ns_all[idx],
                                bucket.times_ns,
                                window_min,
                            )
                        else:
                            continue
                    n_with_any_label = int(has.sum())
                    if n_with_any_label < min_n:
                        continue

                    for label, base in base_by_label.items():
                        y = group[label]
                        valid = y.notna().to_numpy()
                        filt = has & valid
                        n_with = int(filt.sum())
                        if n_with < min_n:
                            continue
                        rate = float(y.iloc[np.where(filt)[0]].astype(bool).mean())
                        base_n = int(base["base_n"])
                        base_rate = float(base["base_rate"])
                        rows.append(
                            {
                                "parent": parent,
                                "parent_event_type": event_type,
                                "parent_tf": parent_tf,
                                "parent_side": side,
                                "parent_thesis": thesis,
                                "child_concept": concept,
                                "child_tf": child_tf,
                                "child_relation": relation,
                                "phase": phase,
                                "window": window_label,
                                "label": label,
                                "base_n": base_n,
                                "base_rate": base_rate,
                                "n_with_child": n_with,
                                "rate_with_child": rate,
                                "lift": rate - base_rate,
                                "coverage": n_with / base_n if base_n else float("nan"),
                                "tf_ratio_parent_to_child": parent_tf_min / child_tf_min,
                            }
                        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = out.sort_values(
        ["phase", "lift", "n_with_child"],
        ascending=[True, False, False],
    ).reset_index(drop=True)
    return out


def _markdown_table(rows: list[list[Any]], headers: list[str]) -> str:
    if not rows:
        return "_No rows._"
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def write_doc(
    path: Path,
    summary: pd.DataFrame,
    *,
    missing_parents: list[str],
    child_counts: dict[str, int],
    args: argparse.Namespace,
) -> None:
    generated = datetime.now(UTC).isoformat(timespec="seconds")
    lines = [
        "# ML Timeframe Stack Context",
        "",
        f"_Generated {generated} by `backend/scripts/ml/build_timeframe_stack_context.py`._",
        "",
        "## What This Tests",
        "",
        "This tests parent SMT events against lower-timeframe child concepts.",
        "Example: weekly SMT with daily/4H/1H OB/FVG/sweep/PSP context, or 4H SMT with 1H/30m/15m child context once `smt_mtf.parquet` exists.",
        "",
        "- `phase=pre`: child concept was already knowable before or at the parent cutoff. This is safe as ML context.",
        "- `phase=post`: child concept formed after the parent cutoff. This is useful descriptive research, but not legal as an input to the parent signal.",
        "- `aligned`: child direction matches SMT thesis. High-side SMT implies down; low-side SMT implies up.",
        "- `opposed`: child direction goes against SMT thesis.",
        "- Only child timeframes shorter than the parent timeframe are counted.",
        "",
        "## Inputs",
        "",
        f"- Parents requested: `{args.parents or 'all'}`",
        f"- Children requested: `{args.children or 'all'}`",
        f"- Minimum bucket size: `{args.min_n}`",
        f"- Missing/skipped parent matrices: `{', '.join(missing_parents) if missing_parents else 'none'}`",
        "",
        "Child rows loaded:",
        "",
    ]
    child_rows = [[k, _fmt_int(v)] for k, v in sorted(child_counts.items())]
    lines.append(_markdown_table(child_rows, ["child", "rows"]))
    lines.extend(["", "## Best Pre-Context Buckets", ""])
    if summary.empty:
        lines.append("_No timeframe-stack rows met the filters._")
    else:
        pre = summary[summary["phase"].eq("pre")].copy()
        pre = pre.sort_values(["lift", "n_with_child"], ascending=[False, False]).head(30)
        rows = []
        for r in pre.itertuples(index=False):
            rows.append(
                [
                    r.parent_event_type,
                    r.parent_side,
                    r.child_concept,
                    r.child_tf,
                    r.child_relation,
                    r.window,
                    r.label.replace("oc.", ""),
                    _fmt_int(r.n_with_child),
                    _pct(r.base_rate),
                    _pct(r.rate_with_child),
                    _signed_pct(r.lift),
                    f"{float(r.coverage) * 100:.1f}%",
                ]
            )
        lines.append(
            _markdown_table(
                rows,
                [
                    "parent",
                    "side",
                    "child",
                    "child_tf",
                    "relation",
                    "window",
                    "label",
                    "n",
                    "base",
                    "with_child",
                    "lift",
                    "coverage",
                ],
            )
        )
        lines.extend(["", "## Best Post-Formation Buckets", ""])
        post = summary[summary["phase"].eq("post")].copy()
        post = post.sort_values(["lift", "n_with_child"], ascending=[False, False]).head(30)
        rows = []
        for r in post.itertuples(index=False):
            rows.append(
                [
                    r.parent_event_type,
                    r.parent_side,
                    r.child_concept,
                    r.child_tf,
                    r.child_relation,
                    r.window,
                    r.label.replace("oc.", ""),
                    _fmt_int(r.n_with_child),
                    _pct(r.base_rate),
                    _pct(r.rate_with_child),
                    _signed_pct(r.lift),
                ]
            )
        lines.append(
            _markdown_table(
                rows,
                [
                    "parent",
                    "side",
                    "child",
                    "child_tf",
                    "relation",
                    "window",
                    "label",
                    "n",
                    "base",
                    "with_child",
                    "lift",
                ],
            )
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Summary CSV: `{SUMMARY_CSV}`",
            f"- Summary parquet: `{SUMMARY_PARQUET}`",
            f"- Manifest: `{MANIFEST_JSON}`",
            "",
            "## Current Gap",
            "",
            "`smt_mtf.parquet` will stay missing until the new previous-candle SMT detector is scanned, outcomes are computed, and `build_feature_matrix.py --detectors smt_prev_candle_divergence` is run. After that, rerun this script to rank 4H/6H/1H/90m/30m/15m SMT stacks directly.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_outputs(
    summary: pd.DataFrame,
    *,
    missing_parents: list[str],
    child_counts: dict[str, int],
    args: argparse.Namespace,
) -> None:
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    if summary.empty:
        summary.to_csv(SUMMARY_CSV, index=False)
        summary.to_parquet(SUMMARY_PARQUET, index=False)
    else:
        summary.to_csv(SUMMARY_CSV, index=False)
        summary.to_parquet(SUMMARY_PARQUET, index=False)
    manifest = {
        "schema_version": 1,
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "parents": args.parents,
        "children": args.children,
        "phases": args.phases,
        "min_n": args.min_n,
        "missing_parents": missing_parents,
        "child_counts": child_counts,
        "rows": int(len(summary)),
        "outputs": {
            "summary_csv": str(SUMMARY_CSV),
            "summary_parquet": str(SUMMARY_PARQUET),
            "doc": str(DOC_PATH),
        },
    }
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_doc(DOC_PATH, summary, missing_parents=missing_parents, child_counts=child_counts, args=args)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parents", default=None, help="Comma-separated parent shorts. Default: all.")
    parser.add_argument("--children", default=None, help="Comma-separated child shorts. Default: all.")
    parser.add_argument("--phases", default="pre,post", help="Comma-separated phases: pre,post.")
    parser.add_argument("--min-n", type=int, default=25, help="Minimum events in a bucket.")
    args = parser.parse_args()

    parent_filter = set(_parse_csv(args.parents) or [])
    child_filter = set(_parse_csv(args.children) or [])
    phases = set(_parse_csv(args.phases) or ["pre", "post"])
    args.parents = ",".join(sorted(parent_filter)) if parent_filter else None
    args.children = ",".join(sorted(child_filter)) if child_filter else None
    args.phases = ",".join(sorted(phases))

    parents, missing_parents = load_parents(parent_filter or None)
    child_buckets, child_counts = load_children(child_filter or None)
    summary = build_summary(parents, child_buckets, min_n=args.min_n, phases=phases)
    write_outputs(summary, missing_parents=missing_parents, child_counts=child_counts, args=args)

    print(f"parents: {len(parents):,}")
    print(f"child buckets: {len(child_buckets):,}")
    print(f"summary rows: {len(summary):,}")
    print(f"wrote {SUMMARY_CSV}")
    print(f"wrote {SUMMARY_PARQUET}")
    print(f"wrote {DOC_PATH}")
    if missing_parents:
        print(f"missing/skipped parents: {', '.join(missing_parents)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
