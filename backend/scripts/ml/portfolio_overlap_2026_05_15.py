"""Cross-signal overlap analysis on the 5 effective-independent robust signals.

Trains each signal for test year 2025 only, captures the top-10% picks,
and computes how often two signals fire on the same days. Tells us
whether the portfolio is diversified (different signals trigger on
different days) or correlated (same days, just different labels).

Also runs per-symbol breakdown on the SMT winner (n1_thesis_confirmed_strict).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.gpu_train_pipeline import filter_matrix, run_fold
from scripts.ml.gpu_train_schema_safe import (
    assert_no_label_leak,
    coerce_binary_label,
    load_schema,
    schema_safe_feature_columns,
)
from scripts.ml.gpu_train_walk_forward import extract_years
from scripts.ml.gpu_train_xgb import resolve_device

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
EXPORT = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_reactions")
ANCHORS = EXPORT / "data" / "ml" / "anchors"

OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_portfolio_overlap"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TEST_YEAR = 2025
TOP_PCT = 0.10
SYMBOL_COL = "anchor.primary_symbol"
TIME_COL_CANDIDATES = ["ts.bar_end_utc", "anchor.bar_end_utc", "anchor.event_ts", "ts.bar_start_utc"]


@dataclass(frozen=True)
class Signal:
    name: str
    matrix_file: str
    snapshot: str
    side: str
    label: str


# Five effective signals after correlation dedup (n1_primary_took_period_n_low
# was identical to n1_thesis_confirmed_strict, so we drop it).
SIGNALS: list[Signal] = [
    Signal("smt_pd_high_thesis",
           "smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime",
           "at_period_close", "high", "label.n1_thesis_confirmed_strict"),
    Signal("smt_pd_high_close_moved",
           "smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime",
           "at_period_close", "high", "label.n1_close_moved_with_thesis"),
    Signal("ogap_gap_down_rejection",
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
           "at_fire", "gap_down", "label.next_60m.resistance_rejection_3bar"),
    Signal("ogap_gap_up_rejection",
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
           "at_fire", "gap_up", "label.next_60m.support_rejection_3bar"),
    Signal("ogap_strict_partial_touch",
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict",
           "at_fire", "all", "label.strict.next_60m.partial_touch_rejected"),
]


def _train_and_score(sig: Signal, device: str, test_year: int) -> pd.DataFrame:
    """Returns DataFrame with cols: signal_name, fire_date, symbol, p_test, y_true, top_10pct."""
    matrix_path = ANCHORS / (sig.matrix_file + ".parquet")
    schema_path = ANCHORS / (sig.matrix_file + ".schema.json")
    schema = load_schema(schema_path)
    feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
    assert_no_label_leak(feature_pool)
    df_full = pd.read_parquet(matrix_path)
    df = filter_matrix(df_full, snapshot=sig.snapshot, side=sig.side, event_type="all")
    y_series = coerce_binary_label(df[sig.label])
    df = df.loc[y_series.notna()].copy()
    y = y_series.loc[df.index].astype(int).to_numpy()
    years = extract_years(df)
    result = run_fold(df=df, years=years, y=y, label=sig.label,
                     feature_pool=feature_pool, test_year=test_year, device=device)
    if result["status"] != "ok":
        return pd.DataFrame()
    preds = result["predictions"]
    test_idx = preds["row_index"].to_numpy()
    test_rows = df.loc[test_idx].copy()
    test_rows["y_true"] = preds["y_true"].to_numpy()
    test_rows["p_test"] = preds["p_test"].to_numpy()
    test_rows["signal_name"] = sig.name
    test_rows["symbol"] = test_rows[SYMBOL_COL]
    # Find a usable time column.
    time_col = next((c for c in TIME_COL_CANDIDATES if c in test_rows.columns), None)
    if time_col:
        test_rows["fire_ts"] = pd.to_datetime(test_rows[time_col], errors="coerce", utc=True)
        test_rows["fire_date"] = test_rows["fire_ts"].dt.date
    else:
        # Fall back to ts.year * 1000 + row position. Coarse but lets overlap work per-year.
        test_rows["fire_ts"] = pd.NaT
        test_rows["fire_date"] = "year=" + test_rows.get("ts.year", pd.Series(["?"] * len(test_rows))).astype(str) + "_idx=" + np.arange(len(test_rows)).astype(str)
    # Top-10% mask.
    k = max(1, int(round(len(test_rows) * TOP_PCT)))
    ranked = test_rows["p_test"].rank(ascending=False, method="first") <= k
    test_rows["top_10pct"] = ranked
    return test_rows[["signal_name", "fire_date", "symbol", "p_test", "y_true", "top_10pct"]].reset_index(drop=True)


def main() -> int:
    device_info = resolve_device("auto")
    print(f"device: {device_info.resolved}")
    all_preds = []
    print(f"\nTraining all 5 signals for test_year={TEST_YEAR}...")
    for sig in SIGNALS:
        print(f"  {sig.name}: ", end="")
        df = _train_and_score(sig, device_info.resolved, TEST_YEAR)
        if df.empty:
            print("FAILED")
            continue
        n_top = int(df["top_10pct"].sum())
        n_hit_top = int(df.loc[df["top_10pct"], "y_true"].sum())
        prec_top = n_hit_top / max(1, n_top)
        print(f"top-10% n={n_top} hits={n_hit_top} prec={prec_top:.3f}")
        all_preds.append(df)
    combined = pd.concat(all_preds, ignore_index=True)
    combined.to_csv(OUT_DIR / "all_signal_predictions_2025.csv", index=False, float_format="%.4f")

    # === Per-symbol breakdown of the SMT winner ===
    smt = combined[combined["signal_name"] == "smt_pd_high_thesis"].copy()
    print(f"\nSMT 'n1_thesis_confirmed_strict' top-10% by symbol (test_year=2025):")
    print(f"  {'symbol':<10} {'n_total':>8} {'n_top10':>8} {'n_hit':>6} {'precision':>10}")
    for sym in ["NQ.c.0", "ES.c.0", "YM.c.0"]:
        sub = smt[smt["symbol"] == sym]
        if len(sub) == 0:
            continue
        n_total = len(sub)
        top = sub[sub["top_10pct"]]
        n_top = len(top)
        n_hit = int(top["y_true"].sum())
        prec = n_hit / max(1, n_top)
        print(f"  {sym:<10} {n_total:>8} {n_top:>8} {n_hit:>6} {prec:>10.3f}")

    # === Cross-signal overlap on top-10% picks ===
    # Build a "per-date per-symbol" matrix: rows=date+symbol, cols=signal_name, value=1 if top-10% fired.
    top_only = combined[combined["top_10pct"]].copy()
    top_only["fire_key"] = top_only["fire_date"].astype(str) + " | " + top_only["symbol"].astype(str)
    pivot = top_only.pivot_table(index="fire_key", columns="signal_name",
                                  values="top_10pct", aggfunc=lambda s: True, fill_value=False)
    # Pair-wise overlap counts.
    print(f"\nCross-signal overlap on top-10% picks ({len(top_only)} total top-10% trades across all signals):")
    print(f"Pivot rows (unique date×symbol combinations where AT LEAST one signal fired top-10%): {len(pivot)}")
    print()
    # How many trades fire with exactly N signals?
    pivot["n_signals"] = pivot.sum(axis=1)
    consensus = pivot["n_signals"].value_counts().sort_index()
    print("Trades by # of signals firing top-10% on same date+symbol:")
    for n, count in consensus.items():
        print(f"  {int(n)} signal(s) firing: {count} date×symbol combos")
    pivot.to_csv(OUT_DIR / "overlap_pivot.csv")

    # Compute pairwise Jaccard overlap.
    sigs = [s.name for s in SIGNALS]
    print(f"\nPairwise Jaccard overlap on top-10% picks (intersection / union):")
    print(f"  {'':<28}", end="")
    for s in sigs:
        print(f"  {s[:18]:>18}", end="")
    print()
    matrix_data = np.zeros((len(sigs), len(sigs)))
    for i, a in enumerate(sigs):
        print(f"  {a[:28]:<28}", end="")
        for j, b in enumerate(sigs):
            if a not in pivot.columns or b not in pivot.columns:
                print(f"  {'n/a':>18}", end="")
                continue
            inter = int((pivot[a] & pivot[b]).sum())
            union = int((pivot[a] | pivot[b]).sum())
            jacc = inter / union if union > 0 else 0.0
            matrix_data[i, j] = jacc
            print(f"  {jacc:>18.3f}", end="")
        print()

    # === Plot overlap heatmap ===
    fig, ax = plt.subplots(figsize=(9, 7))
    im = ax.imshow(matrix_data, cmap="YlOrRd", vmin=0, vmax=1)
    ax.set_xticks(np.arange(len(sigs)))
    ax.set_yticks(np.arange(len(sigs)))
    ax.set_xticklabels(sigs, rotation=30, ha="right", fontsize=9)
    ax.set_yticklabels(sigs, fontsize=9)
    for i in range(len(sigs)):
        for j in range(len(sigs)):
            ax.text(j, i, f"{matrix_data[i, j]:.2f}", ha="center", va="center",
                    color="white" if matrix_data[i, j] > 0.5 else "black", fontsize=10)
    plt.colorbar(im, ax=ax)
    ax.set_title(f"Top-10% trade overlap (Jaccard) — test_year={TEST_YEAR}\nHigh = same dates fire on both signals")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "overlap_heatmap.png", dpi=120)
    plt.close(fig)

    # === Verdict ===
    # Distinct trade count = how many unique date×symbol combos had at least one top-10% fire.
    distinct_trades = len(pivot)
    # Naive sum of all top-10% picks (no dedup).
    raw_count = int(top_only["top_10pct"].count())
    portfolio_efficiency = distinct_trades / max(1, raw_count)
    verdict = {
        "test_year": TEST_YEAR,
        "signals_in_portfolio": len(SIGNALS),
        "raw_top10_picks_total": raw_count,
        "distinct_date_symbol_combos": distinct_trades,
        "portfolio_efficiency": portfolio_efficiency,
        "consensus_counts": {int(k): int(v) for k, v in consensus.items()},
        "interpretation": (
            "Highly diversified — most trades unique to one signal"
            if portfolio_efficiency > 0.8
            else "Partially overlapping — some signals fire on same days"
            if portfolio_efficiency > 0.5
            else "Highly correlated — signals largely fire on same days"
        ),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "verdict.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    print("\n=== VERDICT ===")
    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
