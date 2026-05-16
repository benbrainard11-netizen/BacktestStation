"""Add stricter clock-time reaction labels to order-block snapshots.

The base order-block outcomes are native-candle based and include many easy
near-touch labels. This builder computes true 1-minute-bar windows after the
at-fire label start and appends behavior-named strict targets for next_60m and
next_240m. Outputs are labels only and must not be used as model features.
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
DEFAULT_MATRIX = ANCHORS_DIR / "ob_snapshots_xctx.parquet"
DEFAULT_SCHEMA = ANCHORS_DIR / "ob_snapshots_xctx.schema.json"
DEFAULT_OUTPUT = ANCHORS_DIR / "ob_snapshots_xctx_strict.parquet"
DEFAULT_SCHEMA_OUTPUT = ANCHORS_DIR / "ob_snapshots_xctx_strict.schema.json"
DEFAULT_STATS = ANCHORS_DIR / "ob_strict_label_stats.csv"
DEFAULT_DOC = ROOT / "docs" / "ML_OB_STRICT_LABELS.md"

WINDOWS = (60, 240)
WINDOW_NAMES = {60: "next_60m", 240: "next_240m"}
STRICT_SPECS: dict[str, str] = {
    "ob_respected_partial_test": (
        "Price tested the entry half of the OB body, did not close through the far body edge, "
        "and rejected in the OB thesis direction."
    ),
    "ob_respected_deep_test": (
        "Price tested at least 70% into the OB body, held the far body edge on closes, "
        "and rejected in the OB thesis direction."
    ),
    "ob_broken_through_continuation": (
        "Price closed through the far body edge and continued in the break direction."
    ),
    "ob_failed_immediately": (
        "The OB broke through early after it became knowable, before a slower retest sequence formed."
    ),
    "ob_swept_and_recovered": (
        "Price swept beyond the far OB boundary, then closed back on the OB thesis side and rejected away."
    ),
}
REQUIRED_COLUMNS = (
    "anchor.primary_symbol",
    "anchor.side",
    "anchor.event_type",
    "asof.label_start_ts",
    "ob.ed.ob_body_top",
    "ob.ed.ob_body_bottom",
    "ob.ed.ob_body_width_pts",
    "ob.ed.ob_range_top",
    "ob.ed.ob_range_bottom",
    "ob.ed.ob_range_width_pts",
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


def _first_true(mask: np.ndarray) -> int | None:
    if not bool(mask.any()):
        return None
    return int(np.argmax(mask))


def _window_flags(
    *,
    side: str,
    body_top: float,
    body_bottom: float,
    body_width: float,
    range_top: float,
    range_bottom: float,
    range_width: float,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    immediate_minutes: int,
    deep_frac: float,
    reaction_frac: float,
    continuation_frac: float,
    sweep_buffer_frac: float,
    min_reaction_pts: float,
    min_continuation_pts: float,
    min_sweep_buffer_pts: float,
) -> dict[str, bool]:
    if len(closes) == 0 or side not in {"bullish", "bearish"}:
        return {name: False for name in STRICT_SPECS}

    prices = np.asarray(
        [body_top, body_bottom, body_width, range_top, range_bottom, range_width],
        dtype="float64",
    )
    if not bool(np.isfinite(prices).all()) or body_top <= body_bottom:
        return {name: False for name in STRICT_SPECS}

    body_width = max(float(body_width), float(body_top - body_bottom), 1.0)
    range_width = max(float(range_width), float(range_top - range_bottom), body_width, 1.0)
    reaction_move = max(float(min_reaction_pts), body_width * float(reaction_frac))
    continuation_move = max(float(min_continuation_pts), body_width * float(continuation_frac))
    sweep_buffer = max(float(min_sweep_buffer_pts), range_width * float(sweep_buffer_frac))
    deep_frac = min(max(float(deep_frac), 0.50), 0.95)
    first_n = min(max(1, int(immediate_minutes)), len(closes))
    final_close = float(closes[-1])

    if side == "bullish":
        entry_edge = body_top
        mid_body = body_top - 0.50 * body_width
        deep_body = body_top - deep_frac * body_width
        far_edge = body_bottom
        swept_boundary = min(float(range_bottom), far_edge)

        touched_entry = lows <= entry_edge
        touched_partial = (lows <= entry_edge) & (lows > mid_body)
        touched_deep = lows <= deep_body
        close_broken = closes < far_edge
        wick_swept = lows < swept_boundary - sweep_buffer
        close_recovered = closes > mid_body
        thesis_excursion = np.maximum.accumulate(highs - entry_edge)
        break_extension = far_edge - np.minimum.accumulate(lows)

        first_partial = _first_true(touched_partial)
        first_deep = _first_true(touched_deep)
        first_break = _first_true(close_broken)
        first_sweep = _first_true(wick_swept | close_broken)

        no_close_break = not bool(close_broken.any())
        final_on_thesis_side = final_close > mid_body
        partial_rejected = (
            first_partial is not None
            and float(np.max(highs[first_partial:])) - entry_edge >= reaction_move
        )
        deep_rejected = (
            first_deep is not None
            and float(np.max(highs[first_deep:])) - entry_edge >= reaction_move
        )
        break_continued = (
            first_break is not None
            and far_edge - float(np.min(lows[first_break:])) >= continuation_move
        )
        swept_recovered = (
            first_sweep is not None
            and bool(close_recovered[first_sweep:].any())
            and float(np.max(highs[first_sweep:])) - entry_edge >= reaction_move
        )
    else:
        entry_edge = body_bottom
        mid_body = body_bottom + 0.50 * body_width
        deep_body = body_bottom + deep_frac * body_width
        far_edge = body_top
        swept_boundary = max(float(range_top), far_edge)

        touched_entry = highs >= entry_edge
        touched_partial = (highs >= entry_edge) & (highs < mid_body)
        touched_deep = highs >= deep_body
        close_broken = closes > far_edge
        wick_swept = highs > swept_boundary + sweep_buffer
        close_recovered = closes < mid_body
        thesis_excursion = np.maximum.accumulate(entry_edge - lows)
        break_extension = np.maximum.accumulate(highs - far_edge)

        first_partial = _first_true(touched_partial)
        first_deep = _first_true(touched_deep)
        first_break = _first_true(close_broken)
        first_sweep = _first_true(wick_swept | close_broken)

        no_close_break = not bool(close_broken.any())
        final_on_thesis_side = final_close < mid_body
        partial_rejected = (
            first_partial is not None
            and entry_edge - float(np.min(lows[first_partial:])) >= reaction_move
        )
        deep_rejected = (
            first_deep is not None
            and entry_edge - float(np.min(lows[first_deep:])) >= reaction_move
        )
        break_continued = (
            first_break is not None
            and float(np.max(highs[first_break:])) - far_edge >= continuation_move
        )
        swept_recovered = (
            first_sweep is not None
            and bool(close_recovered[first_sweep:].any())
            and entry_edge - float(np.min(lows[first_sweep:])) >= reaction_move
        )

    tested_entry = bool(touched_entry.any())
    broken_early = bool((close_broken[:first_n]).any())
    swept_early = bool((wick_swept[:first_n]).any())
    broke_or_swept_early = broken_early or swept_early
    moved_in_thesis = bool(float(np.max(thesis_excursion)) >= reaction_move)
    moved_in_break = bool(float(np.max(break_extension)) >= continuation_move)

    return {
        "ob_respected_partial_test": (
            tested_entry
            and bool(touched_partial.any())
            and no_close_break
            and bool(partial_rejected)
            and final_on_thesis_side
        ),
        "ob_respected_deep_test": (
            tested_entry
            and bool(touched_deep.any())
            and no_close_break
            and bool(deep_rejected)
            and final_on_thesis_side
        ),
        "ob_broken_through_continuation": (
            bool(close_broken.any())
            and bool(break_continued)
            and moved_in_break
        ),
        "ob_failed_immediately": broke_or_swept_early,
        "ob_swept_and_recovered": (
            bool((wick_swept | close_broken).any())
            and bool(swept_recovered)
            and moved_in_thesis
            and final_on_thesis_side
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
        body_tops = pd.to_numeric(sub["ob.ed.ob_body_top"], errors="coerce").to_numpy("float64")
        body_bottoms = pd.to_numeric(sub["ob.ed.ob_body_bottom"], errors="coerce").to_numpy("float64")
        body_widths = pd.to_numeric(sub["ob.ed.ob_body_width_pts"], errors="coerce").to_numpy("float64")
        range_tops = pd.to_numeric(sub["ob.ed.ob_range_top"], errors="coerce").to_numpy("float64")
        range_bottoms = pd.to_numeric(sub["ob.ed.ob_range_bottom"], errors="coerce").to_numpy("float64")
        range_widths = pd.to_numeric(sub["ob.ed.ob_range_width_pts"], errors="coerce").to_numpy("float64")

        for local_i, row_idx in enumerate(sub.index):
            start_i = int(np.searchsorted(ts, start_ns[local_i], side="left"))
            for window in WINDOWS:
                end_i = int(np.searchsorted(ts, start_ns[local_i] + window * NS_PER_MIN, side="left"))
                if end_i <= start_i:
                    coverage[WINDOW_NAMES[window]]["missing_bar_windows"] += 1
                    continue
                flags = _window_flags(
                    side=sides[local_i],
                    body_top=float(body_tops[local_i]),
                    body_bottom=float(body_bottoms[local_i]),
                    body_width=float(body_widths[local_i]),
                    range_top=float(range_tops[local_i]),
                    range_bottom=float(range_bottoms[local_i]),
                    range_width=float(range_widths[local_i]),
                    highs=highs[start_i:end_i],
                    lows=lows[start_i:end_i],
                    closes=closes[start_i:end_i],
                    immediate_minutes=args.immediate_minutes,
                    deep_frac=args.deep_frac,
                    reaction_frac=args.reaction_frac,
                    continuation_frac=args.continuation_frac,
                    sweep_buffer_frac=args.sweep_buffer_frac,
                    min_reaction_pts=args.min_reaction_pts,
                    min_continuation_pts=args.min_continuation_pts,
                    min_sweep_buffer_pts=args.min_sweep_buffer_pts,
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
        for group in ("all", "bullish", "bearish"):
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
            "builder": "backend/scripts/ml/build_ob_strict_labels.py",
            "source_schema": str(source_schema),
            "source_matrix": str(args.matrix),
            "rows": int(len(merged)),
            "label_columns": label_columns,
            "order_block_strict_labels": {
                "windows": [WINDOW_NAMES[w] for w in WINDOWS],
                "strict_label_columns": strict_cols,
                "definitions": STRICT_SPECS,
                "immediate_minutes": args.immediate_minutes,
                "deep_frac": args.deep_frac,
                "reaction_frac": args.reaction_frac,
                "continuation_frac": args.continuation_frac,
                "sweep_buffer_frac": args.sweep_buffer_frac,
                "min_reaction_pts": args.min_reaction_pts,
                "min_continuation_pts": args.min_continuation_pts,
                "min_sweep_buffer_pts": args.min_sweep_buffer_pts,
                "min_rate": args.min_rate,
                "max_rate": args.max_rate,
                "coverage": coverage,
                "warnings": warnings,
                "note": (
                    "These labels are computed from true 1m bars after asof.label_start_ts. "
                    "They are targets, not model inputs. Bullish/demand OBs reject up; "
                    "bearish/supply OBs reject down."
                ),
            },
            "notes": [
                *schema.get("notes", []),
                "label.strict.* columns are stricter clock-time order-block reaction targets.",
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
        "# Order Block Strict Labels",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "These labels add strict clock-time order-block reaction targets.",
        "They are appended to `label_columns` only. They are not features.",
        "",
        "Direction rule: bullish/demand OBs reject up; bearish/supply OBs reject down.",
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
    parser.add_argument("--deep-frac", type=float, default=0.70)
    parser.add_argument("--reaction-frac", type=float, default=0.18)
    parser.add_argument("--continuation-frac", type=float, default=0.55)
    parser.add_argument("--sweep-buffer-frac", type=float, default=0.05)
    parser.add_argument("--min-reaction-pts", type=float, default=1.0)
    parser.add_argument("--min-continuation-pts", type=float, default=1.0)
    parser.add_argument("--min-sweep-buffer-pts", type=float, default=0.25)
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
