"""V8a OGAP event audit — same A/B/C/D framework as v9_ob_leak_audit.

Question: is v8a's +79R from real ML edge, or is it the same kind of
"event population edge" we just discovered for OB?

Variants on v8a's 3 OGAP signals:
  A: model top-10% picks, correct direction, 2+ consensus filter (= v8a / v9a baseline)
  B: ALL OGAP events in test years, correct direction, NO consensus
  C: model top-10%, REVERSED direction, 2+ consensus
  D: RANDOM top-10% picks, correct direction, 2+ consensus
  E: ALL events, correct direction, 2+ consensus  (event bias with consensus filter)

If A ~ D and B is positive: same finding as OB — event itself is the edge.
If A > D and A > E: model + consensus both add real value on OGAP.
"""

from __future__ import annotations

import json
import sys
import time as time_mod
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.rigorous_backtest_v1 import (
    BarsCache, Signal, TEST_YEARS, TOP_PCT,
    SYMBOL_COL, SIDE_COL, TIME_COL_CANDIDATES,
)
from scripts.ml.rigorous_backtest_v2_matrix import _train_and_score, _apply_consensus_filter
from scripts.ml.rigorous_backtest_v7_stops import StopVariant, simulate_v7, V5_SIGNALS
from scripts.ml.rigorous_backtest_v9_ob import V8A_STOP
from scripts.ml.v9_ob_leak_audit import all_events_picks, simulate_picks, resolve_dir

ROOT = Path(r"C:\Users\benbr\BacktestStation")
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_v8a_ogap_event_audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)
UTC = timezone.utc


def main() -> int:
    from scripts.ml.gpu_train_xgb import resolve_device
    device_info = resolve_device("auto")
    print(f"=== V8a OGAP event audit ===  device={device_info.resolved}")
    print(f"output: {OUT_DIR}")
    t0 = time_mod.time()

    # Step 1: model top-10% picks for all 3 OGAP signals.
    print("\nStep 1: train + score 3 OGAP signals (variants A, C)...")
    model_picks_frames = []
    for sig in V5_SIGNALS:
        for ty in TEST_YEARS:
            df = _train_and_score(sig, device_info.resolved, ty)
            if not df.empty:
                model_picks_frames.append(df)
    model_picks = pd.concat(model_picks_frames, ignore_index=True)
    print(f"  model top-10% picks (all 3 signals): {len(model_picks):,}")

    # Step 2: all events across all 3 OGAP signals (variant B/E).
    print("Step 2: gather ALL OGAP events in test years...")
    all_frames = [all_events_picks(sig) for sig in V5_SIGNALS]
    all_picks = pd.concat(all_frames, ignore_index=True)
    print(f"  all-event picks: {len(all_picks):,}")

    # Step 3: random top-10% picks per signal × year.
    print("Step 3: random top-10% picks (variant D, seed=42)...")
    random_frames = [all_events_picks(sig, top_pct=0.10, random_seed=42) for sig in V5_SIGNALS]
    random_picks = pd.concat(random_frames, ignore_index=True)
    print(f"  random top-10%: {len(random_picks):,}")

    bars = BarsCache()
    print("\nStep 4: simulate variants...")
    # Configurations: (name, picks, reverse, apply_consensus, description)
    variants = [
        ("A_model_consensus",        model_picks,  False, True,  "A: model top-10%, correct dir, 2+ consensus (= v8a)"),
        ("B_all_no_consensus",       all_picks,    False, False, "B: ALL events, correct dir, NO consensus"),
        ("C_model_REVERSED",         model_picks,  True,  True,  "C: model top-10%, REVERSED dir, 2+ consensus"),
        ("D_random_consensus",       random_picks, False, True,  "D: random top-10%, correct dir, 2+ consensus"),
        ("E_all_consensus",          all_picks,    False, True,  "E: ALL events, correct dir, 2+ consensus"),
    ]

    rollup = []
    all_trades = []
    for name, picks_input, reverse, apply_consensus, desc in variants:
        picks = picks_input.copy()
        if apply_consensus:
            picks = _apply_consensus_filter(picks)
        td = simulate_picks(picks, bars, V8A_STOP, reverse_direction=reverse, label=name)
        ex = td[td["exit_reason"].isin(["target", "stop", "time_exit"])]
        n = len(ex)
        cum_r = float(ex["pnl_r"].sum()) if n else 0.0
        avg_r = float(ex["pnl_r"].mean()) if n else 0.0
        win_rate = float((ex["pnl_r"] > 0).mean()) if n else 0.0
        cumr = ex.sort_values("fire_ts")["pnl_r"].cumsum() if n else pd.Series([0.0])
        max_dd = float((cumr.cummax() - cumr).max()) if n else 0.0
        years_pos = int(ex.groupby("test_year")["pnl_r"].sum().gt(0).sum()) if n else 0
        print(f"  [{name:<22}] n={n:5d} cum_R={cum_r:+8.1f} avg_R={avg_r:+5.3f} win%={win_rate:.3f} DD={max_dd:5.1f} yrs+={years_pos}/6")
        all_trades.append(td)
        rollup.append({"variant": name, "description": desc, "n_trades": n,
                       "cum_r": cum_r, "avg_r": avg_r, "win_rate": win_rate,
                       "max_dd_r": max_dd, "years_positive": years_pos})

    combined = pd.concat(all_trades, ignore_index=True)
    combined.to_csv(OUT_DIR / "trades_all_variants.csv", index=False, float_format="%.4f")
    rollup_df = pd.DataFrame(rollup)
    rollup_df.to_csv(OUT_DIR / "rollup.csv", index=False, float_format="%.4f")
    print("\n=== Rollup ===")
    print(rollup_df.drop(columns=["description"]).to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    ex_all = combined[combined["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    pivot = ex_all.pivot_table(index="variant", columns="test_year", values="pnl_r",
                                aggfunc="sum", fill_value=0)
    pivot["total"] = pivot.sum(axis=1)
    pivot.to_csv(OUT_DIR / "per_variant_per_year.csv", float_format="%.4f")
    print("\n=== Per-variant per-year cum_R ===")
    print(pivot.to_string(float_format=lambda x: f"{x:.2f}"))

    # Per-signal contribution within each variant.
    per_sv = ex_all.groupby(["variant", "signal"]).agg(
        n=("pnl_r", "count"),
        cum_r=("pnl_r", "sum"),
        avg_r=("pnl_r", "mean"),
        win_rate=("pnl_r", lambda s: float((s > 0).mean())),
    ).reset_index()
    per_sv.to_csv(OUT_DIR / "per_variant_per_signal.csv", index=False, float_format="%.4f")
    print("\n=== Per-variant × per-signal ===")
    print(per_sv.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    summary = {v["variant"]: {"cum_r": v["cum_r"], "avg_r": v["avg_r"], "n": v["n_trades"]} for v in rollup}
    # Verdict logic
    a = rollup[0]; b = rollup[1]; c = rollup[2]; d = rollup[3]; e = rollup[4]
    same_as_ob = (
        d["avg_r"] >= 0.7 * a["avg_r"] and  # random nearly as good as model
        e["avg_r"] >= 0.7 * a["avg_r"]      # all-with-consensus nearly as good
    )
    summary["verdict"] = (
        "SAME AS OB — event population is the edge; model + consensus add little" if same_as_ob
        else "DIFFERENT FROM OB — model and/or consensus add real value on OGAP"
    )
    summary["elapsed_min"] = round((time_mod.time() - t0) / 60, 1)
    summary["generated_at"] = datetime.now(UTC).isoformat()
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DONE in {(time_mod.time()-t0)/60:.1f} min ===")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
