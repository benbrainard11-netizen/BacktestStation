"""Add stricter composite reaction labels to opening-gap snapshot matrices."""

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
DEFAULT_MATRIX = ANCHORS_DIR / "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.parquet"
DEFAULT_SCHEMA = ANCHORS_DIR / "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.schema.json"
DEFAULT_OUTPUT = ANCHORS_DIR / "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict.parquet"
DEFAULT_SCHEMA_OUTPUT = ANCHORS_DIR / "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict.schema.json"
DEFAULT_STATS = ANCHORS_DIR / "opening_gap_strict_label_stats.csv"
DEFAULT_DOC = ROOT / "docs" / "ML_OPENING_GAP_STRICT_LABELS.md"

WINDOWS = ("next_60m", "next_240m", "next_1d")
STRICT_SPECS = {
    "gap_held_rejection": (
        "Gap was touched and then acted as directional support/resistance for the 3-bar hold rule.",
    ),
    "gap_failed_acceptance": (
        "Gap was touched and then accepted through against the opening-gap direction.",
    ),
    "partial_touch_rejected": (
        "Gap was touched but not fully filled, then rejected in the directional support/resistance sense.",
    ),
    "midpoint_hold_rejection": (
        "Gap midpoint was touched without full fill, then held/rejected in the directional sense.",
    ),
    "filled_then_rejected_inside": (
        "Gap fully filled, then rejected back inside instead of accepting through.",
    ),
    "filled_then_continued_through": (
        "Gap fully filled and then accepted through the far side.",
    ),
    "failed_fill_expanded_away": (
        "Gap was touched but left unfilled, then expanded away from the gap.",
    ),
    "no_touch_expanded_away": (
        "Gap was never touched and price expanded away from it.",
    ),
    "clean_gap_continuation": (
        "No touch plus 3-bar acceptance in the opening-gap continuation direction.",
    ),
}


def _bool(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(False, index=df.index)
    s = df[col]
    if s.dtype == bool:
        return s.fillna(False)
    return pd.to_numeric(s, errors="coerce").fillna(0).astype(bool)


def _dir_masks(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    if "anchor.side" in df.columns:
        side = df["anchor.side"].astype(str)
    elif "ogap.ed.gap_direction" in df.columns:
        side = df["ogap.ed.gap_direction"].astype(str)
    else:
        raise KeyError("missing anchor.side / ogap.ed.gap_direction")
    return side.eq("gap_up"), side.eq("gap_down")


def _label_col(window: str, name: str) -> str:
    return f"label.strict.{window}.{name}"


def _build_for_window(df: pd.DataFrame, window: str) -> dict[str, pd.Series]:
    gap_up, gap_down = _dir_masks(df)
    prefix = f"label.{window}."
    touched = _bool(df, prefix + "touched_gap")
    midpoint = _bool(df, prefix + "touched_midpoint")
    filled = _bool(df, prefix + "fully_filled")
    unfilled = _bool(df, prefix + "unfilled_at_window_end")
    expanded_1x = _bool(df, prefix + "range_expanded_1x_gap")

    support_rejection = _bool(df, prefix + "support_rejection_3bar")
    resistance_rejection = _bool(df, prefix + "resistance_rejection_3bar")
    support_break = _bool(df, prefix + "support_break_acceptance_3bar")
    resistance_break = _bool(df, prefix + "resistance_break_acceptance_3bar")

    accepted_above = _bool(df, prefix + "accepted_above_3bar")
    accepted_below = _bool(df, prefix + "accepted_below_3bar")
    closed_above = _bool(df, prefix + "closed_above_gap_high")
    closed_below = _bool(df, prefix + "closed_below_gap_low")
    rejected_low_inside = _bool(df, prefix + "took_gap_low_rejected_inside")
    rejected_high_inside = _bool(df, prefix + "took_gap_high_rejected_inside")

    directional_rejection = (gap_up & support_rejection) | (gap_down & resistance_rejection)
    directional_failure = (gap_up & support_break) | (gap_down & resistance_break)
    continuation_acceptance = (gap_up & accepted_above) | (gap_down & accepted_below)
    through_acceptance = (gap_up & accepted_below) | (gap_down & accepted_above)
    closed_away = (gap_up & closed_above) | (gap_down & closed_below)
    rejected_inside = (gap_up & rejected_low_inside) | (gap_down & rejected_high_inside)

    return {
        _label_col(window, "gap_held_rejection"): touched & directional_rejection,
        _label_col(window, "gap_failed_acceptance"): touched & directional_failure,
        _label_col(window, "partial_touch_rejected"): touched & ~filled & directional_rejection,
        _label_col(window, "midpoint_hold_rejection"): midpoint & ~filled & directional_rejection,
        _label_col(window, "filled_then_rejected_inside"): filled & rejected_inside & ~through_acceptance,
        _label_col(window, "filled_then_continued_through"): filled & through_acceptance,
        _label_col(window, "failed_fill_expanded_away"): touched & unfilled & expanded_1x & closed_away,
        _label_col(window, "no_touch_expanded_away"): ~touched & expanded_1x & closed_away,
        _label_col(window, "clean_gap_continuation"): ~touched & expanded_1x & continuation_acceptance,
    }


def build_labels(df: pd.DataFrame) -> pd.DataFrame:
    data: dict[str, pd.Series] = {}
    for window in WINDOWS:
        data.update(_build_for_window(df, window))
    return pd.DataFrame({col: s.astype("int8") for col, s in data.items()}, index=df.index)


def _stats(df: pd.DataFrame, label_cols: list[str]) -> pd.DataFrame:
    rows = []
    side = df.get("anchor.side", pd.Series("all", index=df.index)).astype(str)
    for label in label_cols:
        y = pd.to_numeric(df[label], errors="coerce")
        for group in ("all", "gap_up", "gap_down"):
            mask = pd.Series(True, index=df.index) if group == "all" else side.eq(group)
            sub = y[mask].dropna()
            rows.append(
                {
                    "label": label,
                    "side": group,
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
            "builder": "backend/scripts/ml/build_opening_gap_strict_labels.py",
            "source_schema": str(source_schema),
            "source_matrix": str(args.matrix),
            "rows": int(len(merged)),
            "label_columns": label_columns,
            "opening_gap_strict_labels": {
                "windows": list(WINDOWS),
                "strict_label_columns": strict_cols,
                "definitions": {name: desc for name, (desc,) in STRICT_SPECS.items()},
                "note": (
                    "These are composite forward labels derived only from existing "
                    "opening-gap outcome labels. They are targets, not model inputs."
                ),
            },
            "notes": [
                *schema.get("notes", []),
                "label.strict.* columns are stricter composite opening-gap reaction targets.",
            ],
        }
    )
    args.schema_output.parent.mkdir(parents=True, exist_ok=True)
    args.schema_output.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def _write_doc(path: Path, stats: pd.DataFrame, strict_cols: list[str]) -> None:
    rows = []
    top = stats[stats["side"].eq("all")].sort_values("rate", ascending=False)
    for _, r in top.iterrows():
        rows.append([
            f"`{r['label']}`",
            int(r["rows"]),
            int(r["positives"]),
            f"{100.0 * float(r['rate']):.1f}%",
        ])
    definition_rows = [
        [f"`label.strict.<window>.{name}`", desc]
        for name, (desc,) in STRICT_SPECS.items()
    ]
    text = [
        "# Opening Gap Strict Labels",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "These labels combine the raw opening-gap outcomes into stricter reaction targets.",
        "They are appended to `label_columns` only. They are not features.",
        "",
        "## Definitions",
        "",
        _md_table(["Pattern", "Meaning"], definition_rows),
        "",
        "## Generated Columns",
        "",
        f"- Strict label columns: `{len(strict_cols):,}`",
        f"- Windows: `{', '.join(WINDOWS)}`",
        "",
        "## Overall Rates",
        "",
        _md_table(["Label", "Rows", "Positives", "Rate"], rows),
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
