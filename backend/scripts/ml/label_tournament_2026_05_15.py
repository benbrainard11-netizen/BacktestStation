"""Label tournament — runs the v2 multi-year walk-forward across the top
candidate labels in the registry and produces a unified ranking by
multi-year robustness.

Each candidate gets the same 6-test-year walk-forward (2020-2025).
Verdict is based on top-10% precision: ROBUST if min_year >= 0.85 in
all 6 years, MIXED if 3-4 years pass, FLUKE if <= 2 years pass.

Compute budget: ~3 min per candidate label × N labels. Currently 9
candidates -> ~30 min total.
"""

from __future__ import annotations

import json
import sys
import time
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

TEST_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
TOP_DECILE = 0.10
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_label_tournament"
OUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True, slots=True)
class Candidate:
    name: str
    matrix_file: str
    snapshot: str
    side: str
    label: str


CANDIDATES: list[Candidate] = [
    # Already proven (sanity-check it lands again):
    Candidate("opening_gap_broad / gap_down / resistance_rejection_3bar (winner)",
              "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
              "at_fire", "gap_down", "label.next_60m.resistance_rejection_3bar"),
    # Mirror: gap_up + support rejection
    Candidate("opening_gap_broad / gap_up / support_rejection_3bar (mirror)",
              "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
              "at_fire", "gap_up", "label.next_60m.support_rejection_3bar"),
    # Opening gap unfilled at window end
    Candidate("opening_gap_broad / all / unfilled_at_window_end",
              "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
              "at_fire", "all", "label.next_60m.unfilled_at_window_end"),
    # Opening gap strict
    Candidate("opening_gap_strict / all / partial_touch_rejected@60m",
              "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict",
              "at_fire", "all", "label.strict.next_60m.partial_touch_rejected"),
    Candidate("opening_gap_strict / gap_down / partial_touch_rejected@60m",
              "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict",
              "at_fire", "gap_down", "label.strict.next_60m.partial_touch_rejected"),
    # SMT period_close
    Candidate("smt_previous_day / high / n1_thesis_confirmed_strict",
              "smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime",
              "at_period_close", "high", "label.n1_thesis_confirmed_strict"),
    Candidate("smt_previous_day / high / n1_close_moved_with_thesis",
              "smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime",
              "at_period_close", "high", "label.n1_close_moved_with_thesis"),
    Candidate("smt_previous_day / high / n1_primary_took_period_n_low",
              "smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime",
              "at_period_close", "high", "label.n1_primary_took_period_n_low"),
    # Forming VP
    Candidate("forming_vp / all / next_60m.took_profile_so_far_high",
              "forming_vp_snapshots_xctx_gapctx",
              "at_fire", "all", "label.next_60m.took_profile_so_far_high"),
    Candidate("forming_vp / all / next_60m.took_profile_so_far_low",
              "forming_vp_snapshots_xctx_gapctx",
              "at_fire", "all", "label.next_60m.took_profile_so_far_low"),
]


def _evaluate_candidate(cand: Candidate, device: str) -> list[dict]:
    matrix_path = ANCHORS / (cand.matrix_file + ".parquet")
    schema_path = ANCHORS / (cand.matrix_file + ".schema.json")
    schema = load_schema(schema_path)
    feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
    assert_no_label_leak(feature_pool)
    df_full = pd.read_parquet(matrix_path)
    df = filter_matrix(df_full, snapshot=cand.snapshot, side=cand.side, event_type="all")
    if cand.label not in df.columns:
        return [{"test_year": y, "status": "label_missing"} for y in TEST_YEARS]
    y_series = coerce_binary_label(df[cand.label])
    df = df.loc[y_series.notna()].copy()
    if len(df) < 200:
        return [{"test_year": y, "status": "too_few_rows", "n_total": len(df)} for y in TEST_YEARS]
    y = y_series.loc[df.index].astype(int).to_numpy()
    years = extract_years(df)
    rows = []
    for test_year in TEST_YEARS:
        result = run_fold(
            df=df, years=years, y=y, label=cand.label,
            feature_pool=feature_pool, test_year=test_year, device=device,
        )
        if result["status"] != "ok":
            rows.append({"test_year": test_year, "status": result["status"]})
            continue
        preds = result["predictions"]
        rec = result["record"]
        y_true = preds["y_true"].to_numpy()
        p_test = preds["p_test"].to_numpy()
        ranked = np.argsort(-p_test)
        k = max(1, int(round(len(ranked) * TOP_DECILE)))
        idx = ranked[:k]
        top10_prec = float(y_true[idx].mean())
        base = float(rec["base_rate_test"])
        rows.append({
            "test_year": test_year,
            "status": "ok",
            "n_test": int(rec["n_test"]),
            "test_auc": float(rec["auc_test"]),
            "base_rate": base,
            "top10_n": k,
            "top10_precision": top10_prec,
            "top10_edge": top10_prec - base,
        })
    return rows


def main() -> int:
    device_info = resolve_device("auto")
    print(f"device: {device_info.resolved}")
    overall_t0 = time.time()
    all_records = []
    for i, cand in enumerate(CANDIDATES, 1):
        print(f"\n[{i}/{len(CANDIDATES)}] === {cand.name} ===")
        t0 = time.time()
        try:
            rows = _evaluate_candidate(cand, device_info.resolved)
        except Exception as exc:
            print(f"  FAIL: {exc}")
            rows = [{"test_year": y, "status": f"error: {type(exc).__name__}"} for y in TEST_YEARS]
        for row in rows:
            row.update({"candidate_name": cand.name, "matrix": cand.matrix_file,
                        "snapshot": cand.snapshot, "side": cand.side, "label": cand.label})
            all_records.append(row)
        elapsed = time.time() - t0
        ok = [r for r in rows if r.get("status") == "ok"]
        if ok:
            top10_precs = [r["top10_precision"] for r in ok]
            edges = [r["top10_edge"] for r in ok]
            print(f"  done in {elapsed:.0f}s, {len(ok)}/{len(TEST_YEARS)} years ok")
            print(f"  top-10% prec: mean={np.mean(top10_precs):.3f} min={min(top10_precs):.3f} max={max(top10_precs):.3f}")
            print(f"  edge: mean={np.mean(edges):+.3f} min={min(edges):+.3f}")
        else:
            print(f"  done in {elapsed:.0f}s (no ok years)")

    df_all = pd.DataFrame(all_records)
    df_all.to_csv(OUT_DIR / "per_candidate_per_year.csv", index=False, float_format="%.4f")

    # Aggregate per candidate.
    ok_df = df_all[df_all["status"] == "ok"].copy()
    agg = ok_df.groupby("candidate_name").agg(
        years_ok=("test_year", "count"),
        mean_auc=("test_auc", "mean"),
        mean_base=("base_rate", "mean"),
        mean_top10_prec=("top10_precision", "mean"),
        min_top10_prec=("top10_precision", "min"),
        mean_top10_edge=("top10_edge", "mean"),
        min_top10_edge=("top10_edge", "min"),
        total_top10_signals=("top10_n", "sum"),
    ).reset_index()

    # Verdict per candidate.
    def _verdict(row) -> str:
        if row["years_ok"] < len(TEST_YEARS):
            return f"INCOMPLETE ({int(row['years_ok'])}/{len(TEST_YEARS)} years)"
        # Count years where top10_prec >= 0.85.
        sub = ok_df[ok_df["candidate_name"] == row["candidate_name"]]
        n_pass = int((sub["top10_precision"] >= 0.85).sum())
        if n_pass >= 5:
            return f"ROBUST ({n_pass}/6 years >= 0.85)"
        if n_pass >= 3:
            return f"MIXED ({n_pass}/6 years >= 0.85)"
        return f"FLUKE ({n_pass}/6 years >= 0.85)"
    agg["verdict"] = agg.apply(_verdict, axis=1)
    agg = agg.sort_values("mean_top10_prec", ascending=False).reset_index(drop=True)
    agg.to_csv(OUT_DIR / "candidate_ranking.csv", index=False, float_format="%.4f")
    print("\n=== CANDIDATE RANKING (by mean top-10% precision across 6 years) ===")
    print(agg.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Bar chart of mean top-10% precision per candidate.
    fig, ax = plt.subplots(figsize=(12, 7))
    y_pos = np.arange(len(agg))
    colors = ["green" if v.startswith("ROBUST") else "gold" if v.startswith("MIXED") else "lightgray"
              for v in agg["verdict"]]
    ax.barh(y_pos, agg["mean_top10_prec"], color=colors, edgecolor="black")
    for yi, (name, prec, base) in enumerate(zip(agg["candidate_name"], agg["mean_top10_prec"], agg["mean_base"])):
        ax.plot([base], [yi], "rD", markersize=6, label="base rate" if yi == 0 else "")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(agg["candidate_name"], fontsize=9)
    ax.set_xlabel("Mean top-10% precision (across 6 test years)")
    ax.set_title("Label tournament — multi-year robustness ranking\nGreen=ROBUST, gold=MIXED, gray=FLUKE/INCOMPLETE")
    ax.set_xlim(0, 1.05)
    ax.grid(True, alpha=0.3, axis="x")
    ax.invert_yaxis()
    plt.tight_layout()
    fig.savefig(OUT_DIR / "candidate_ranking.png", dpi=120)
    plt.close(fig)

    elapsed_total = time.time() - overall_t0
    summary = {
        "candidates_total": len(CANDIDATES),
        "verdict_counts": agg["verdict"].apply(lambda v: v.split()[0]).value_counts().to_dict(),
        "elapsed_min": round(elapsed_total / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DONE in {elapsed_total/60:.1f} min ===")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
