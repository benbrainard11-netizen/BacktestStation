"""Add stricter clock-time reaction labels to liquidity-sweep snapshots.

The base sweep outcomes are native-candle based. This builder computes true
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
DEFAULT_MATRIX = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet"
DEFAULT_SCHEMA = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json"
DEFAULT_OUTPUT = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict.parquet"
DEFAULT_SCHEMA_OUTPUT = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict.schema.json"
DEFAULT_STATS = ANCHORS_DIR / "sweep_strict_label_stats.csv"
DEFAULT_DOC = ROOT / "docs" / "ML_SWEEP_STRICT_LABELS.md"

WINDOWS = (60, 240)
WINDOW_NAMES = {60: "next_60m", 240: "next_240m"}
STRICT_SPECS: dict[str, str] = {
    "sweep_failed_recovered": (
        "Price closed back through the swept reference and ended the window on the rejection-thesis side."
    ),
    "sweep_succeeded_held_rejection": (
        "Price recovered the swept reference, held the manipulation extreme, and moved at least 1x sweep depth in the rejection thesis."
    ),
    "sweep_partial_retest_rejected": (
        "After recovery, price retested the swept level without taking the manipulation extreme, then rejected in the thesis direction."
    ),
    "sweep_failed_immediately": (
        "Within the first minutes after the sweep, price extended past the manipulation extreme without immediate recovery."
    ),
    "sweep_extended_continuation": (
        "Price did not recover the swept level and extended at least 0.5x sweep depth in the continuation direction."
    ),
}
REQUIRED_COLUMNS = (
    "anchor.primary_symbol",
    "anchor.side",
    "anchor.event_type",
    "asof.label_start_ts",
    "sweep.ed.swept_reference.level_price",
    "sweep.ed.manipulation_candle.high",
    "sweep.ed.manipulation_candle.low",
    "sweep.ed.manipulation_candle.close",
    "sweep.ed.sweep_depth_pts",
)
NS_PER_MIN = 60 * 1_000_000_000


def _label_col(window_min: int, name: str) -> str:
    return f"label.strict.{WINDOW_NAMES[window_min]}.{name}"


def _to_ns(s: pd.Series) -> np.ndarray:
    return pd.to_datetime(s, utc=True).to_numpy("datetime64[ns]").astype("int64")


def _load_symbol_bars(symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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


def _window_flags(
    *,
    side: str,
    ref_price: float,
    manipulation_high: float,
    manipulation_low: float,
    manipulation_close: float,
    depth: float,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    immediate_minutes: int,
) -> dict[str, bool]:
    if len(closes) == 0 or not np.isfinite(depth) or depth <= 0:
        return {name: False for name in STRICT_SPECS}

    depth = max(float(depth), 1.0)
    first_n = min(max(1, immediate_minutes), len(closes))
    final_close = float(closes[-1])
    high_max = float(np.max(highs))
    low_min = float(np.min(lows))

    if side == "low":
        recovered_arr = closes > ref_price
        recovered = bool(recovered_arr.any())
        recovery_idx = int(np.argmax(recovered_arr)) if recovered else 0
        thesis_mfe = high_max - manipulation_close
        close_on_thesis_side = final_close > ref_price
        adverse_extension = max(0.0, manipulation_low - low_min)
        immediate_extension = bool(np.min(lows[:first_n]) < manipulation_low)
        immediate_recovery = bool(np.any(closes[:first_n] > ref_price))
        if recovered:
            after_recovery_low = float(np.min(lows[recovery_idx:]))
            partial_retest = after_recovery_low <= ref_price and after_recovery_low > manipulation_low
        else:
            partial_retest = False
    elif side == "high":
        recovered_arr = closes < ref_price
        recovered = bool(recovered_arr.any())
        recovery_idx = int(np.argmax(recovered_arr)) if recovered else 0
        thesis_mfe = manipulation_close - low_min
        close_on_thesis_side = final_close < ref_price
        adverse_extension = max(0.0, high_max - manipulation_high)
        immediate_extension = bool(np.max(highs[:first_n]) > manipulation_high)
        immediate_recovery = bool(np.any(closes[:first_n] < ref_price))
        if recovered:
            after_recovery_high = float(np.max(highs[recovery_idx:]))
            partial_retest = after_recovery_high >= ref_price and after_recovery_high < manipulation_high
        else:
            partial_retest = False
    else:
        return {name: False for name in STRICT_SPECS}

    thesis_1x = thesis_mfe >= depth
    held_extreme = adverse_extension <= depth
    return {
        "sweep_failed_recovered": recovered and close_on_thesis_side,
        "sweep_succeeded_held_rejection": recovered and close_on_thesis_side and thesis_1x and held_extreme,
        "sweep_partial_retest_rejected": partial_retest and close_on_thesis_side and thesis_1x,
        "sweep_failed_immediately": immediate_extension and not immediate_recovery,
        "sweep_extended_continuation": (not recovered) and adverse_extension >= 0.5 * depth,
    }


def build_labels(df: pd.DataFrame, *, immediate_minutes: int) -> tuple[pd.DataFrame, dict[str, Any]]:
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
        refs = pd.to_numeric(sub["sweep.ed.swept_reference.level_price"], errors="coerce").to_numpy("float64")
        manip_highs = pd.to_numeric(sub["sweep.ed.manipulation_candle.high"], errors="coerce").to_numpy("float64")
        manip_lows = pd.to_numeric(sub["sweep.ed.manipulation_candle.low"], errors="coerce").to_numpy("float64")
        manip_closes = pd.to_numeric(sub["sweep.ed.manipulation_candle.close"], errors="coerce").to_numpy("float64")
        depths = pd.to_numeric(sub["sweep.ed.sweep_depth_pts"], errors="coerce").to_numpy("float64")

        for local_i, row_idx in enumerate(sub.index):
            start_i = int(np.searchsorted(ts, start_ns[local_i], side="left"))
            for window in WINDOWS:
                end_i = int(np.searchsorted(ts, start_ns[local_i] + window * NS_PER_MIN, side="left"))
                if end_i <= start_i:
                    coverage[WINDOW_NAMES[window]]["missing_bar_windows"] += 1
                    continue
                flags = _window_flags(
                    side=sides[local_i],
                    ref_price=float(refs[local_i]),
                    manipulation_high=float(manip_highs[local_i]),
                    manipulation_low=float(manip_lows[local_i]),
                    manipulation_close=float(manip_closes[local_i]),
                    depth=float(depths[local_i]),
                    highs=highs[start_i:end_i],
                    lows=lows[start_i:end_i],
                    closes=closes[start_i:end_i],
                    immediate_minutes=immediate_minutes,
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
            "builder": "backend/scripts/ml/build_sweep_strict_labels.py",
            "source_schema": str(source_schema),
            "source_matrix": str(args.matrix),
            "rows": int(len(merged)),
            "label_columns": label_columns,
            "sweep_strict_labels": {
                "windows": [WINDOW_NAMES[w] for w in WINDOWS],
                "strict_label_columns": strict_cols,
                "definitions": STRICT_SPECS,
                "immediate_minutes": args.immediate_minutes,
                "min_rate": args.min_rate,
                "max_rate": args.max_rate,
                "coverage": coverage,
                "warnings": warnings,
                "note": (
                    "These labels are computed from true 1m bars after asof.label_start_ts. "
                    "They are targets, not model inputs. High sweeps reject down; low sweeps reject up."
                ),
            },
            "notes": [
                *schema.get("notes", []),
                "label.strict.* columns are stricter clock-time liquidity-sweep reaction targets.",
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
        "# Sweep Strict Labels",
        "",
        f"_Generated `{datetime.now(UTC).isoformat()}`._",
        "",
        "These labels add strict clock-time liquidity-sweep reaction targets.",
        "They are appended to `label_columns` only. They are not features.",
        "",
        "Direction rule: high sweeps reject down; low sweeps reject up.",
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
    labels, coverage = build_labels(df, immediate_minutes=args.immediate_minutes)
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
    parser.add_argument("--immediate-minutes", type=int, default=15)
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
