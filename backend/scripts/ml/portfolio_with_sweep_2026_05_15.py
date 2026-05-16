"""Cross-family overlap analysis including the new strict sweep signal.

After running sweep_strict_walkforward_2026_05_15.py, this script checks
whether the strongest strict sweep label fires on the same days as the
existing SMT and OGAP signals.

The portfolio question: does adding strict_sweep give us a 5th
independent signal family, or does it overlap with what we already have?
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
ANCHORS_STRICT_REACT = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_reactions") / "data" / "ml" / "anchors"
ANCHORS_STRICT_SWEEP = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_sweep") / "data" / "ml" / "anchors"

TEST_YEAR = 2025
TOP_PCT = 0.10
SYMBOL_COL = "anchor.primary_symbol"
TIME_COL_CANDIDATES = ["ts.bar_end_utc", "anchor.bar_end_utc", "anchor.event_ts", "ts.bar_start_utc"]

OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_portfolio_with_sweep"
OUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Signal:
    name: str
    anchors_dir: Path
    matrix_file: str
    snapshot: str
    side: str
    label: str


# Six signals: 4 from yesterday's portfolio analysis + 2 from strict sweep
# (will refine after the walk-forward run picks the strongest).
SIGNALS: list[Signal] = [
    Signal("smt_pd_high_thesis", ANCHORS_STRICT_REACT,
           "smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime",
           "at_period_close", "high", "label.n1_thesis_confirmed_strict"),
    Signal("ogap_gap_down_rejection", ANCHORS_STRICT_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
           "at_fire", "gap_down", "label.next_60m.resistance_rejection_3bar"),
    Signal("ogap_gap_up_rejection", ANCHORS_STRICT_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
           "at_fire", "gap_up", "label.next_60m.support_rejection_3bar"),
    Signal("ogap_strict_partial_touch", ANCHORS_STRICT_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict",
           "at_fire", "all", "label.strict.next_60m.partial_touch_rejected"),
    Signal("sweep_failed_recovered_all", ANCHORS_STRICT_SWEEP,
           "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict",
           "at_fire", "all", "label.strict.next_60m.sweep_failed_recovered"),
    Signal("sweep_succeeded_held_rejection_low", ANCHORS_STRICT_SWEEP,
           "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict",
           "at_fire", "low", "label.strict.next_60m.sweep_succeeded_held_rejection"),
]


def _train_and_score(sig: Signal, device: str) -> pd.DataFrame:
    matrix_path = sig.anchors_dir / (sig.matrix_file + ".parquet")
    schema_path = sig.anchors_dir / (sig.matrix_file + ".schema.json")
    schema = load_schema(schema_path)
    feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
    assert_no_label_leak(feature_pool)
    df = pd.read_parquet(matrix_path)
    df = filter_matrix(df, snapshot=sig.snapshot, side=sig.side, event_type="all")
    if sig.label not in df.columns:
        return pd.DataFrame()
    y_series = coerce_binary_label(df[sig.label])
    df = df.loc[y_series.notna()].copy()
    y = y_series.loc[df.index].astype(int).to_numpy()
    years = extract_years(df)
    result = run_fold(df=df, years=years, y=y, label=sig.label,
                     feature_pool=feature_pool, test_year=TEST_YEAR, device=device)
    if result["status"] != "ok":
        return pd.DataFrame()
    preds = result["predictions"]
    test_idx = preds["row_index"].to_numpy()
    test_rows = df.loc[test_idx].copy()
    test_rows["y_true"] = preds["y_true"].to_numpy()
    test_rows["p_test"] = preds["p_test"].to_numpy()
    test_rows["signal_name"] = sig.name
    test_rows["symbol"] = test_rows.get(SYMBOL_COL, "?")
    time_col = next((c for c in TIME_COL_CANDIDATES if c in test_rows.columns), None)
    if time_col:
        test_rows["fire_ts"] = pd.to_datetime(test_rows[time_col], errors="coerce", utc=True)
        test_rows["fire_date"] = test_rows["fire_ts"].dt.date
    else:
        test_rows["fire_ts"] = pd.NaT
        test_rows["fire_date"] = "year=" + test_rows.get("ts.year", pd.Series(["?"] * len(test_rows))).astype(str)
    k = max(1, int(round(len(test_rows) * TOP_PCT)))
    test_rows["top_10pct"] = test_rows["p_test"].rank(ascending=False, method="first") <= k
    return test_rows[["signal_name", "fire_date", "symbol", "p_test", "y_true", "top_10pct"]].reset_index(drop=True)


def main() -> int:
    device_info = resolve_device("auto")
    print(f"device: {device_info.resolved}, test_year={TEST_YEAR}")
    all_preds = []
    for sig in SIGNALS:
        print(f"  {sig.name}: ", end="")
        df = _train_and_score(sig, device_info.resolved)
        if df.empty:
            print("FAILED or no data")
            continue
        n_top = int(df["top_10pct"].sum())
        n_hit = int(df.loc[df["top_10pct"], "y_true"].sum())
        prec = n_hit / max(1, n_top)
        print(f"top-10%: n={n_top} hits={n_hit} prec={prec:.3f}")
        all_preds.append(df)
    combined = pd.concat(all_preds, ignore_index=True)
    combined.to_csv(OUT_DIR / "all_signal_predictions_2025.csv", index=False, float_format="%.4f")

    # Build the date×symbol pivot of top-10% picks.
    top_only = combined[combined["top_10pct"]].copy()
    top_only["fire_key"] = top_only["fire_date"].astype(str) + " | " + top_only["symbol"].astype(str)
    pivot = top_only.pivot_table(index="fire_key", columns="signal_name",
                                  values="top_10pct", aggfunc=lambda s: True, fill_value=False)
    pivot["n_signals"] = pivot.sum(axis=1)
    pivot.to_csv(OUT_DIR / "overlap_pivot.csv")
    consensus = pivot["n_signals"].value_counts().sort_index()
    print(f"\nConsensus counts ({len(top_only)} raw top-10 picks across {len(pivot)} unique date×symbol):")
    for n, c in consensus.items():
        print(f"  {int(n)} signal(s) firing: {c}")

    # Pairwise Jaccard overlap.
    sig_names = [s.name for s in SIGNALS]
    sig_names = [s for s in sig_names if s in pivot.columns]
    matrix = np.zeros((len(sig_names), len(sig_names)))
    print(f"\nPairwise Jaccard overlap on top-10% picks (test_year={TEST_YEAR}):")
    print(f"  {'':<30}", end="")
    for s in sig_names:
        print(f"  {s[:18]:>18}", end="")
    print()
    for i, a in enumerate(sig_names):
        print(f"  {a[:30]:<30}", end="")
        for j, b in enumerate(sig_names):
            inter = int((pivot[a] & pivot[b]).sum())
            union = int((pivot[a] | pivot[b]).sum())
            jacc = inter / union if union > 0 else 0.0
            matrix[i, j] = jacc
            print(f"  {jacc:>18.3f}", end="")
        print()

    fig, ax = plt.subplots(figsize=(11, 8))
    im = ax.imshow(matrix, cmap="YlOrRd", vmin=0, vmax=1)
    ax.set_xticks(np.arange(len(sig_names)))
    ax.set_yticks(np.arange(len(sig_names)))
    ax.set_xticklabels(sig_names, rotation=30, ha="right", fontsize=8)
    ax.set_yticklabels(sig_names, fontsize=9)
    for i in range(len(sig_names)):
        for j in range(len(sig_names)):
            ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center",
                    color="white" if matrix[i, j] > 0.5 else "black", fontsize=9)
    plt.colorbar(im, ax=ax)
    ax.set_title(f"Top-10% trade overlap (Jaccard) — incl. sweep family — test_year={TEST_YEAR}")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "overlap_heatmap.png", dpi=120)
    plt.close(fig)

    summary = {
        "test_year": TEST_YEAR,
        "raw_picks": int(top_only["top_10pct"].count()),
        "unique_date_symbol_combos": len(pivot),
        "consensus_counts": {int(k): int(v) for k, v in consensus.items()},
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nSummary:")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
