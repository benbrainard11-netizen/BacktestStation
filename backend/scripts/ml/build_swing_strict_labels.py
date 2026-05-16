"""Add stricter clock-time reaction labels to swing-pivot snapshots.

The base swing outcomes are native-candle based. This builder computes true
1-minute-bar windows after the at-fire label start and appends behavior-named
strict targets for next_60m and next_240m. Outputs are labels only and must not
be used as model features.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(r"C:\Users\benbr\BacktestStation")
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.data.reader import read_bars  # noqa: E402

UTC = timezone.utc
ANCHORS_DIR = ROOT / "data" / "ml" / "anchors"
DEFAULT_MATRIX = ANCHORS_DIR / "swing_snapshots.parquet"
DEFAULT_SCHEMA = ANCHORS_DIR / "swing_snapshots.schema.json"
DEFAULT_OUTPUT = ANCHORS_DIR / "swing_snapshots_strict.parquet"
DEFAULT_SCHEMA_OUTPUT = ANCHORS_DIR / "swing_snapshots_strict.schema.json"
DEFAULT_STATS = ANCHORS_DIR / "swing_strict_label_stats.csv"
DEFAULT_DOC = ROOT / "docs" / "ML_SWING_STRICT_LABELS.md"

WINDOWS = (60, 240)
WINDOW_NAMES = {60: "next_60m", 240: "next_240m"}
STRICT_SPECS: dict[str, str] = {
    "pivot_held_rejection": (
        "Price tested the pivot, did not close through it, and moved away in the rejection thesis."
    ),
    "pivot_broken_through_continuation": (
        "Price closed through the pivot and continued in the break direction."
    ),
    "pivot_partial_test_rejected": (
        "Price entered the pivot zone without a full touch, then rejected away from the level."
    ),
    "pivot_failed_immediately": (
        "The pivot traded through early after it became knowable, before a slower retest sequence formed."
    ),
    "pivot_double_test_held": (
        "Price tested the pivot in at least two separate clusters, held, and rejected after the second test."
    ),
}
REQUIRED_COLUMNS = (
    "anchor.primary_symbol",
    "anchor.side",
    "anchor.event_type",
    "asof.label_start_ts",
    "swing.ed.pivot_price",
    "swing.ed.pivot_bar.high",
    "swing.ed.pivot_bar.low",
    "swing.ed.pivot_bar.close",
)
NS_PER_MIN = 60 * 1_000_000_000


def _label_col(window_min: int, name: str) -> str:
    return f"label.strict.{WINDOW_NAMES[window_min]}.{name}"


def _to_ns(s: pd.Series) -> np.ndarray:
    return pd.to_datetime(s, utc=True).to_numpy("datetime64[ns]").astype("int64")


def _load_symbol_bars(
    symbol: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    bars = read_bars(
        symbol=symbol,
        timeframe="1m",
        start=start.floor("D").to_pydatetime(),
        end=end.ceil("D").to_pydatetime(),
    )
    if bars is None or bars.empty:
        empty_i = np.array([], dtype="int64")
        empty_f = np.array([], dtype="float64")
        return empty_i, empty_f, empty_f, empty_f
    if "ts_event" in bars.columns:
        ts = pd.to_datetime(bars["ts_event"], utc=True)
    else:
        ts = pd.to_datetime(bars.index, utc=True)
    return (
        ts.to_numpy("datetime64[ns]").astype("int64"),
        bars["high"].astype("float64").to_numpy(),
        bars["low"].astype("float64").to_numpy(),
        bars["close"].astype("float64").to_numpy(),
    )


def _cluster_starts(mask: np.ndarray) -> list[int]:
    starts: list[int] = []
    prev = False
    for idx, value in enumerate(mask.astype(bool)):
        if value and not prev:
            starts.append(idx)
        prev = bool(value)
    return starts


def _window_flags(
    *,
    side: str,
    pivot_price: float,
    pivot_high: float,
    pivot_low: float,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    immediate_minutes: int,
    zone_frac: float,
    reaction_frac: float,
    continuation_frac: float,
    min_zone_pts: float,
    min_reaction_pts: float,
    min_continuation_pts: float,
) -> dict[str, bool]:
    if len(closes) == 0 or side not in {"high", "low"} or not np.isfinite(pivot_price):
        return {name: False for name in STRICT_SPECS}

    pivot_range = abs(float(pivot_high) - float(pivot_low))
    if not np.isfinite(pivot_range) or pivot_range <= 0:
        pivot_range = 1.0
    zone_width = max(float(min_zone_pts), pivot_range * float(zone_frac))
    reaction_move = max(float(min_reaction_pts), pivot_range * float(reaction_frac))
    continuation_move = max(float(min_continuation_pts), pivot_range * float(continuation_frac))
    first_n = min(max(1, int(immediate_minutes)), len(closes))
    final_close = float(closes[-1])

    if side == "high":
        touched = highs >= pivot_price
        partial = (highs >= pivot_price - zone_width) & (highs < pivot_price)
        test_zone = touched | partial
        close_broken = closes > pivot_price
        first_close_broken = closes[:first_n] > pivot_price
        first_wick_broken = highs[:first_n] > pivot_price
        rejection_excursion = pivot_price - float(np.min(lows))
        continuation_excursion = float(np.max(highs)) - pivot_price
        final_on_rejection_side = final_close < pivot_price

        test_starts = _cluster_starts(test_zone)
        first_test = test_starts[0] if test_starts else None
        second_test = test_starts[1] if len(test_starts) >= 2 else None
        rejected_after_touch = (
            first_test is not None
            and pivot_price - float(np.min(lows[first_test:])) >= reaction_move
        )
        rejected_after_second = (
            second_test is not None
            and pivot_price - float(np.min(lows[second_test:])) >= reaction_move
        )
        partial_starts = _cluster_starts(partial)
        rejected_after_partial = (
            partial_starts
            and pivot_price - float(np.min(lows[partial_starts[0]:])) >= reaction_move
        )
    else:
        touched = lows <= pivot_price
        partial = (lows <= pivot_price + zone_width) & (lows > pivot_price)
        test_zone = touched | partial
        close_broken = closes < pivot_price
        first_close_broken = closes[:first_n] < pivot_price
        first_wick_broken = lows[:first_n] < pivot_price
        rejection_excursion = float(np.max(highs)) - pivot_price
        continuation_excursion = pivot_price - float(np.min(lows))
        final_on_rejection_side = final_close > pivot_price

        test_starts = _cluster_starts(test_zone)
        first_test = test_starts[0] if test_starts else None
        second_test = test_starts[1] if len(test_starts) >= 2 else None
        rejected_after_touch = (
            first_test is not None
            and float(np.max(highs[first_test:])) - pivot_price >= reaction_move
        )
        rejected_after_second = (
            second_test is not None
            and float(np.max(highs[second_test:])) - pivot_price >= reaction_move
        )
        partial_starts = _cluster_starts(partial)
        rejected_after_partial = (
            partial_starts
            and float(np.max(highs[partial_starts[0]:])) - pivot_price >= reaction_move
        )

    touched_any = bool(touched.any())
    test_zone_any = bool(test_zone.any())
    close_broken_any = bool(close_broken.any())
    broken_early = bool(first_close_broken.any() or first_wick_broken.any())
    no_close_through = not close_broken_any
    partial_only = bool(partial.any()) and not touched_any

    return {
        "pivot_held_rejection": (
            test_zone_any
            and no_close_through
            and rejected_after_touch
            and final_on_rejection_side
        ),
        "pivot_broken_through_continuation": (
            close_broken_any
            and continuation_excursion >= continuation_move
        ),
        "pivot_partial_test_rejected": (
            partial_only
            and bool(rejected_after_partial)
            and final_on_rejection_side
        ),
        "pivot_failed_immediately": (
            broken_early
        ),
        "pivot_double_test_held": (
            len(test_starts) >= 2
            and no_close_through
            and rejected_after_second
            and final_on_rejection_side
            and rejection_excursion >= reaction_move
        ),
    }


def build_labels(df: pd.DataFrame, args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, Any]]:
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise KeyError(f"missing required columns: {', '.join(missing)}")

    label_data: dict[str, np.ndarray] = {
        _label_col(window, name): np.zeros(len(df), dtype=np.int8)
        for window in WINDOWS
        for name in STRICT_SPECS
    }
    coverage = {
        WINDOW_NAMES[window]: {"rows": int(len(df)), "missing_bar_windows": 0}
        for window in WINDOWS
    }

    work = df[list(REQUIRED_COLUMNS)].copy()
    work["asof.label_start_ts"] = pd.to_datetime(work["asof.label_start_ts"], utc=True)
    max_window = max(WINDOWS)

    for symbol, sub in work.groupby("anchor.primary_symbol", sort=False):
        start = sub["asof.label_start_ts"].min()
        end = sub["asof.label_start_ts"].max() + pd.Timedelta(minutes=max_window + 5)
        ts, highs, lows, closes = _load_symbol_bars(str(symbol), start, end)
        if len(ts) == 0:
            for window in WINDOWS:
                coverage[WINDOW_NAMES[window]]["missing_bar_windows"] += int(len(sub))
            continue

        start_ns = _to_ns(sub["asof.label_start_ts"])
        sides = sub["anchor.side"].fillna("").astype(str).to_numpy()
        pivots = pd.to_numeric(sub["swing.ed.pivot_price"], errors="coerce").to_numpy("float64")
        pivot_highs = pd.to_numeric(sub["swing.ed.pivot_bar.high"], errors="coerce").to_numpy("float64")
        pivot_lows = pd.to_numeric(sub["swing.ed.pivot_bar.low"], errors="coerce").to_numpy("float64")

        for local_i, row_idx in enumerate(sub.index):
            start_i = int(np.searchsorted(ts, start_ns[local_i], side="left"))
            for window in WINDOWS:
                end_i = int(np.searchsorted(ts, start_ns[local_i] + window * NS_PER_MIN, side="left"))
                if end_i <= start_i:
                    coverage[WINDOW_NAMES[window]]["missing_bar_windows"] += 1
                    continue
                flags = _window_flags(
                    side=sides[local_i],
                    pivot_price=float(pivots[local_i]),
                    pivot_high=float(pivot_highs[local_i]),
                    pivot_low=float(pivot_lows[local_i]),
                    highs=highs[start_i:end_i],
                    lows=lows[start_i:end_i],
                    closes=closes[start_i:end_i],
                    immediate_minutes=args.immediate_minutes,
                    zone_frac=args.zone_frac,
                    reaction_frac=args.reaction_frac,
                    continuation_frac=args.continuation_frac,
                    min_zone_pts=args.min_zone_pts,
                    min_reaction_pts=args.min_reaction_pts,
                    min_continuation_pts=args.min_continuation_pts,
                )
                for name, value in flags.items():
                    label_data[_label_col(window, name)][row_idx] = int(value)

    return pd.DataFrame(label_data, index=df.index), coverage


def _stats(df: pd.DataFrame, label_cols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    side = df.get("anchor.side", pd.Series("all", index=df.index)).astype(str)
    event_type = df.get("anchor.event_type", pd.Series("all", index=df.index)).astype(str)
    for label in label_cols:
        y = pd.to_numeric(df[label], errors="coerce")
        for group in ("all", "high", "low"):
            side_mask = pd.Series(True, index=df.index) if group == "all" else side.eq(group)
            for mode in ["all", *sorted(str(x) for x in event_type.dropna().unique())]:
                mode_mask = pd.Series(True, index=df.index) if mode == "all" else event_type.eq(mode)
                sub = y[side_mask & mode_mask].dropna()
                rows.append(
                    {
                        "label": label,
                        "side": group,
                        "event_type": mode,
                        "rows": int(len(sub)),
                        "positives": int(sub.sum()) if len(sub) else 0,
                        "rate": float(sub.mean()) if len(sub) else np.nan,
                    }
                )
    return pd.DataFrame(rows)


def _validate_rates(stats: pd.DataFrame, *, min_rate: float, max_rate: float, allow_out_of_band: bool) -> list[str]:
    overall = stats[stats["side"].eq("all") & stats["event_type"].eq("all")]
    warnings: list[str] = []
    for _, row in overall.iterrows():
        rate = float(row["rate"])
        if rate <= 0.0 or rate >= 1.0:
            warnings.append(f"{row['label']} has broken all-side rate {rate:.4f}")
        elif rate < min_rate or rate > max_rate:
            warnings.append(
                f"{row['label']} has all-side rate {rate:.4f}, outside {min_rate:.2f}-{max_rate:.2f}"
            )
    if warnings and not allow_out_of_band:
        raise ValueError("strict label rate validation failed:\n- " + "\n- ".join(warnings))
    return warnings


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
    coverage: dict[str, Any],
    warnings: list[str],
) -> None:
    old_labels = list(schema.get("label_columns", []))
    label_columns = [*old_labels, *[c for c in strict_cols if c not in old_labels]]
    schema.update(
        {
            "generated_utc": datetime.now(UTC).isoformat(),
            "builder": "backend/scripts/ml/build_swing_strict_labels.py",
            "source_schema": str(source_schema),
            "source_matrix": str(args.matrix),
            "rows": int(len(merged)),
            "label_columns": label_columns,
            "swing_strict_labels": {
                "windows": [WINDOW_NAMES[w] for w in WINDOWS],
                "strict_label_columns": strict_cols,
                "definitions": STRICT_SPECS,
                "immediate_minutes": args.immediate_minutes,
                "zone_frac": args.zone_frac,
                "reaction_frac": args.reaction_frac,
                "continuation_frac": args.continuation_frac,
                "min_zone_pts": args.min_zone_pts,
                "min_reaction_pts": args.min_reaction_pts,
                "min_continuation_pts": args.min_continuation_pts,
                "min_rate": args.min_rate,
                "max_rate": args.max_rate,
                "coverage": coverage,
                "warnings": warnings,
                "note": (
                    "These labels are computed from true 1m bars after asof.label_start_ts. "
                    "They are targets, not model inputs. Swing highs are resistance/reject down; "
                    "swing lows are support/reject up."
                ),
            },
            "notes": [
                *schema.get("notes", []),
                "label.strict.* columns are stricter clock-time swing-pivot reaction targets.",
            ],
        }
    )
    args.schema_output.parent.mkdir(parents=True, exist_ok=True)
    args.schema_output.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def _write_doc(path: Path, stats: pd.DataFrame, strict_cols: list[str], coverage: dict[str, Any], warnings: list[str]) -> None:
    overall = stats[
        stats["side"].eq("all") & stats["event_type"].eq("all")
    ].sort_values("label")
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
        [f"`label.strict.<window>.{name}`", desc]
        for name, desc in STRICT_SPECS.items()
    ]
    coverage_rows = [
        [window, values["rows"], values["missing_bar_windows"]]
        for window, values in coverage.items()
    ]
    text = [
        "# Swing Pivot Strict Labels",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "These labels add strict clock-time swing-pivot reaction targets.",
        "They are appended to `label_columns` only. They are not features.",
        "",
        "Direction rule: swing highs act as resistance and reject down; swing lows act as support and reject up.",
        "",
        "## Definitions",
        "",
        _md_table(["Pattern", "Meaning"], definition_rows),
        "",
        "## Generated Columns",
        "",
        f"- Strict label columns: `{len(strict_cols):,}`",
        f"- Windows: `{', '.join(WINDOW_NAMES[w] for w in WINDOWS)}`",
        "",
        "## Coverage",
        "",
        _md_table(["Window", "Rows", "Missing bar windows"], coverage_rows),
        "",
        "## Overall Rates",
        "",
        _md_table(["Label", "Rows", "Positives", "Rate"], rate_rows),
    ]
    if warnings:
        text.extend(["", "## Warnings", "", *[f"- {w}" for w in warnings]])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(text) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> tuple[Path, Path, Path, pd.DataFrame]:
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    df = pd.read_parquet(args.matrix)
    labels, coverage = build_labels(df, args)
    strict_cols = list(labels.columns)
    merged = pd.concat([df, labels], axis=1)
    stats = _stats(merged, strict_cols)
    warnings = _validate_rates(
        stats,
        min_rate=args.min_rate,
        max_rate=args.max_rate,
        allow_out_of_band=args.allow_out_of_band,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(args.output, index=False)
    _write_schema(
        schema=schema,
        source_schema=args.schema,
        args=args,
        merged=merged,
        strict_cols=strict_cols,
        coverage=coverage,
        warnings=warnings,
    )
    args.stats_output.parent.mkdir(parents=True, exist_ok=True)
    stats.to_csv(args.stats_output, index=False)
    _write_doc(args.doc, stats, strict_cols, coverage, warnings)
    return args.output, args.schema_output, args.stats_output, merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--schema-output", type=Path, default=DEFAULT_SCHEMA_OUTPUT)
    parser.add_argument("--stats-output", type=Path, default=DEFAULT_STATS)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--immediate-minutes", type=int, default=45)
    parser.add_argument("--zone-frac", type=float, default=0.50)
    parser.add_argument("--reaction-frac", type=float, default=0.25)
    parser.add_argument("--continuation-frac", type=float, default=0.20)
    parser.add_argument("--min-zone-pts", type=float, default=1.0)
    parser.add_argument("--min-reaction-pts", type=float, default=1.0)
    parser.add_argument("--min-continuation-pts", type=float, default=1.0)
    parser.add_argument("--min-rate", type=float, default=0.05)
    parser.add_argument("--max-rate", type=float, default=0.40)
    parser.add_argument("--allow-out-of-band", action="store_true")
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
