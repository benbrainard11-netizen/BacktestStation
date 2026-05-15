"""Add stricter composite reaction labels to FVG snapshot matrices.

The source FVG outcome computer already records mitigation, zone reaction, and
post-tap excursions. This builder turns those raw outcome fields into cleaner
model targets so the training PC can learn concepts like tap rejection, full
fill failure, and no-touch continuation without using label columns as inputs.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
ANCHORS_DIR = ROOT / "data" / "ml" / "anchors"
DEFAULT_MATRIX = ANCHORS_DIR / "fvg_snapshots_xctx_fvggeom_obgeom.parquet"
DEFAULT_SCHEMA = ANCHORS_DIR / "fvg_snapshots_xctx_fvggeom_obgeom.schema.json"
DEFAULT_OUTPUT = ANCHORS_DIR / "fvg_snapshots_xctx_fvggeom_obgeom_strict.parquet"
DEFAULT_SCHEMA_OUTPUT = ANCHORS_DIR / "fvg_snapshots_xctx_fvggeom_obgeom_strict.schema.json"
DEFAULT_STATS = ANCHORS_DIR / "fvg_strict_label_stats.csv"
DEFAULT_DOC = ROOT / "docs" / "ML_FVG_STRICT_LABELS.md"

WINDOWS: tuple[int, ...] = (3, 10, 50)

STATIC_SPECS: dict[str, str] = {
    "tap_wick_rejected": (
        "First FVG tap entered by wick only and closed back outside the gap."
    ),
    "partial_touch_rejected": (
        "First tap was a wick reject, did not reach the midpoint, and produced a clean 10-candle thesis move after tap."
    ),
    "mid_fill_rejected": (
        "FVG reached midpoint but not full fill, avoided close-through, and produced a 10-candle thesis move after tap."
    ),
    "full_fill_rejected_inside": (
        "FVG fully filled but rejected back inside the zone instead of closing through the far side."
    ),
    "full_fill_continued_through": (
        "FVG fully filled and later closed through the far side of the zone."
    ),
    "no_touch_continuation": (
        "FVG never tapped and made a clean 2x-width thesis move within 50 native candles."
    ),
}

WINDOW_SPECS: dict[str, str] = {
    "thesis_1x_clean": (
        "From FVG confirmation, price moved at least 1x FVG width in thesis direction with limited adverse excursion."
    ),
    "thesis_2x": (
        "From FVG confirmation, price moved at least 2x FVG width in thesis direction."
    ),
    "failed_1x_against": (
        "From FVG confirmation, adverse excursion reached at least 1x FVG width before a 1x thesis move."
    ),
    "after_tap_1x_clean": (
        "After first tap, price moved at least 1x FVG width in thesis direction with limited adverse excursion."
    ),
    "after_tap_2x": (
        "After first tap, price moved at least 2x FVG width in thesis direction."
    ),
    "after_tap_failed_1x_against": (
        "After first tap, adverse excursion reached at least 1x FVG width before a 1x thesis move."
    ),
}


def _bool(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(False, index=df.index)
    s = df[col]
    if s.dtype == bool:
        return s.fillna(False)
    return pd.to_numeric(s, errors="coerce").fillna(0).astype(bool)


def _num(df: pd.DataFrame, col: str, default: float = np.nan) -> pd.Series:
    if col not in df.columns:
        return pd.Series(default, index=df.index, dtype="float64")
    return pd.to_numeric(df[col], errors="coerce")


def _str(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series("", index=df.index, dtype="object")
    return df[col].fillna("").astype(str)


def _side_masks(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    side = df.get("anchor.side", pd.Series("", index=df.index)).fillna("").astype(str)
    return side.eq("bullish"), side.eq("bearish")


def _static_label_col(name: str) -> str:
    return f"label.strict.{name}"


def _window_label_col(window: int, name: str) -> str:
    return f"label.strict.forward_{window}c.{name}"


def _build_static_labels(df: pd.DataFrame) -> dict[str, pd.Series]:
    bullish, bearish = _side_masks(df)
    valid_width = _num(df, "fvg.ed.fvg_width_pts") > 0
    width = _num(df, "fvg.ed.fvg_width_pts").where(valid_width)

    tapped = _bool(df, "label.mitigation.tapped")
    mid_filled = _bool(df, "label.mitigation.mid_filled")
    fully_filled = _bool(df, "label.mitigation.fully_filled")
    closed_through = _bool(df, "label.mitigation.closed_through")
    tap_class = _str(df, "label.mitigation.tap_bar_classification")

    post10_mfe = _num(df, "label.post_tap_reaction.forward_10_after_tap.mfe_pts_in_thesis")
    post10_mae = _num(df, "label.post_tap_reaction.forward_10_after_tap.mae_pts_against_thesis")
    fwd50_mfe = _num(df, "label.forward_50_candles.mfe_pts_in_thesis")
    fwd50_mae = _num(df, "label.forward_50_candles.mae_pts_against_thesis")

    wick_reject = tapped & tap_class.eq("wick_reject")
    clean_post10_1x = (post10_mfe >= width) & (post10_mae <= 0.5 * width)
    clean_no_touch_2x = (~tapped) & (fwd50_mfe >= 2.0 * width) & (fwd50_mae <= width)
    rejected_inside = (
        (bullish & _bool(df, "label.zone_reaction.took_fvg_low_rejected_inside"))
        | (bearish & _bool(df, "label.zone_reaction.took_fvg_high_rejected_inside"))
    )

    return {
        _static_label_col("tap_wick_rejected"): valid_width & wick_reject,
        _static_label_col("partial_touch_rejected"): (
            valid_width & wick_reject & ~mid_filled & clean_post10_1x
        ),
        _static_label_col("mid_fill_rejected"): (
            valid_width & mid_filled & ~fully_filled & ~closed_through & clean_post10_1x
        ),
        _static_label_col("full_fill_rejected_inside"): (
            valid_width & fully_filled & rejected_inside & ~closed_through
        ),
        _static_label_col("full_fill_continued_through"): (
            valid_width & fully_filled & closed_through
        ),
        _static_label_col("no_touch_continuation"): valid_width & clean_no_touch_2x,
    }


def _build_window_labels(df: pd.DataFrame, window: int) -> dict[str, pd.Series]:
    valid_width = _num(df, "fvg.ed.fvg_width_pts") > 0
    width = _num(df, "fvg.ed.fvg_width_pts").where(valid_width)
    tapped = _bool(df, "label.mitigation.tapped")

    fwd_mfe = _num(df, f"label.forward_{window}_candles.mfe_pts_in_thesis")
    fwd_mae = _num(df, f"label.forward_{window}_candles.mae_pts_against_thesis")
    tap_mfe = _num(df, f"label.post_tap_reaction.forward_{window}_after_tap.mfe_pts_in_thesis")
    tap_mae = _num(df, f"label.post_tap_reaction.forward_{window}_after_tap.mae_pts_against_thesis")

    return {
        _window_label_col(window, "thesis_1x_clean"): (
            valid_width & (fwd_mfe >= width) & (fwd_mae <= 0.5 * width)
        ),
        _window_label_col(window, "thesis_2x"): (
            valid_width & (fwd_mfe >= 2.0 * width)
        ),
        _window_label_col(window, "failed_1x_against"): (
            valid_width & (fwd_mae >= width) & (fwd_mfe < width)
        ),
        _window_label_col(window, "after_tap_1x_clean"): (
            valid_width & tapped & (tap_mfe >= width) & (tap_mae <= 0.5 * width)
        ),
        _window_label_col(window, "after_tap_2x"): (
            valid_width & tapped & (tap_mfe >= 2.0 * width)
        ),
        _window_label_col(window, "after_tap_failed_1x_against"): (
            valid_width & tapped & (tap_mae >= width) & (tap_mfe < width)
        ),
    }


def build_labels(df: pd.DataFrame) -> pd.DataFrame:
    data: dict[str, pd.Series] = {}
    data.update(_build_static_labels(df))
    for window in WINDOWS:
        data.update(_build_window_labels(df, window))
    return pd.DataFrame({col: s.astype("int8") for col, s in data.items()}, index=df.index)


def _stats(df: pd.DataFrame, label_cols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    side = df.get("anchor.side", pd.Series("all", index=df.index)).astype(str)
    event_type = df.get("anchor.event_type", pd.Series("all", index=df.index)).astype(str)
    for label in label_cols:
        y = pd.to_numeric(df[label], errors="coerce")
        for group in ("all", "bullish", "bearish"):
            side_mask = pd.Series(True, index=df.index) if group == "all" else side.eq(group)
            for tf in ("all", "15m_fvg", "1h_fvg", "4h_fvg", "daily_fvg"):
                tf_mask = pd.Series(True, index=df.index) if tf == "all" else event_type.eq(tf)
                mask = side_mask & tf_mask
                sub = y[mask].dropna()
                rows.append(
                    {
                        "label": label,
                        "side": group,
                        "event_type": tf,
                        "rows": int(len(sub)),
                        "positives": int(sub.sum()) if len(sub) else 0,
                        "rate": float(sub.mean()) if len(sub) else np.nan,
                    }
                )
    return pd.DataFrame(rows)


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def _write_schema(
    *,
    schema: dict[str, Any],
    source_schema: Path,
    args: argparse.Namespace,
    merged: pd.DataFrame,
    strict_cols: list[str],
) -> None:
    old_labels = list(schema.get("label_columns", []))
    label_columns = [*old_labels, *[c for c in strict_cols if c not in old_labels]]
    schema.update(
        {
            "generated_utc": datetime.now(UTC).isoformat(),
            "builder": "backend/scripts/ml/build_fvg_strict_labels.py",
            "source_schema": str(source_schema),
            "source_matrix": str(args.matrix),
            "rows": int(len(merged)),
            "label_columns": label_columns,
            "fvg_strict_labels": {
                "windows_native_candles": list(WINDOWS),
                "strict_label_columns": strict_cols,
                "static_definitions": STATIC_SPECS,
                "window_definitions": WINDOW_SPECS,
                "note": (
                    "These are composite forward labels derived from FVG mitigation, "
                    "zone-reaction, and post-tap outcome labels. They are targets, "
                    "not model inputs."
                ),
            },
            "notes": [
                *schema.get("notes", []),
                "label.strict.* columns are stricter composite FVG reaction targets.",
            ],
        }
    )
    args.schema_output.parent.mkdir(parents=True, exist_ok=True)
    args.schema_output.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def _write_doc(path: Path, stats: pd.DataFrame, strict_cols: list[str]) -> None:
    overall = stats[
        stats["side"].eq("all") & stats["event_type"].eq("all")
    ].sort_values("rate", ascending=False)
    rate_rows = [
        [
            f"`{r['label']}`",
            int(r["rows"]),
            int(r["positives"]),
            f"{100.0 * float(r['rate']):.1f}%",
        ]
        for _, r in overall.iterrows()
    ]
    definition_rows = [
        [f"`label.strict.{name}`", desc]
        for name, desc in STATIC_SPECS.items()
    ] + [
        [f"`label.strict.forward_<n>c.{name}`", desc]
        for name, desc in WINDOW_SPECS.items()
    ]
    text = [
        "# FVG Strict Labels",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "These labels combine raw FVG mitigation, zone reaction, and post-tap outcomes into stricter reaction targets.",
        "They are appended to `label_columns` only. They are not features.",
        "",
        "## Definitions",
        "",
        _md_table(["Pattern", "Meaning"], definition_rows),
        "",
        "## Generated Columns",
        "",
        f"- Strict label columns: `{len(strict_cols):,}`",
        f"- Native forward windows: `{', '.join(str(w) for w in WINDOWS)}` candles",
        "",
        "## Overall Rates",
        "",
        _md_table(["Label", "Rows", "Positives", "Rate"], rate_rows),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(text) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> tuple[Path, Path, Path, pd.DataFrame]:
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    df = pd.read_parquet(args.matrix)
    labels = build_labels(df)
    strict_cols = list(labels.columns)
    merged = pd.concat([df, labels], axis=1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(args.output, index=False)
    _write_schema(
        schema=schema,
        source_schema=args.schema,
        args=args,
        merged=merged,
        strict_cols=strict_cols,
    )
    stats = _stats(merged, strict_cols)
    args.stats_output.parent.mkdir(parents=True, exist_ok=True)
    stats.to_csv(args.stats_output, index=False)
    _write_doc(args.doc, stats, strict_cols)
    return args.output, args.schema_output, args.stats_output, merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--schema-output", type=Path, default=DEFAULT_SCHEMA_OUTPUT)
    parser.add_argument("--stats-output", type=Path, default=DEFAULT_STATS)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    args = parser.parse_args()
    output, schema_output, stats_output, merged = build(args)
    strict_count = sum(c.startswith("label.strict.") for c in merged.columns)
    print(f"wrote {output}: {len(merged):,} rows x {len(merged.columns):,} cols")
    print(f"wrote {schema_output}")
    print(f"wrote {stats_output}: {strict_count:,} strict labels")
    print(f"wrote {args.doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
