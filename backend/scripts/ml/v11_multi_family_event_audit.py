"""V11 — Type A vs Type B audit across remaining label families.

After discovering that OB strict continuation is Type B (event class bias,
no model needed -> +8,390R raw) and OGAP rejection is Type A (real model
alpha needed), we run the same A/B/C/D framework on every remaining
strict label family to find where else Type B labels are hiding.

Families audited:
  sweep_failed_recovered    (sweep family, AUC 0.91 -- highest)
  pivot_broken_through_cont (swing family, AUC 0.80)
  after_tap_failed_1x_against (FVG family, AUC 0.72)
  ob_broken_through_cont    (OB family, baseline check from v9_ob_leak_audit)

For each: A (model top-10%), B (all events), C (model REVERSED),
D (random top-10%). Same v8a trade-rule shape; same NQ+ES filter.
"""

from __future__ import annotations

import json
import sys
import time as time_mod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.rigorous_backtest_v1 import (
    BarsCache, Signal, TEST_YEARS,
    SYMBOL_COL, SIDE_COL, TIME_COL_CANDIDATES,
)
from scripts.ml.rigorous_backtest_v2_matrix import _train_and_score
from scripts.ml.rigorous_backtest_v7_stops import StopVariant, simulate_v7
from scripts.ml.rigorous_backtest_v9_ob import V8A_STOP
from scripts.ml.v9_ob_leak_audit import all_events_picks, simulate_picks, resolve_dir
from scripts.ml.gpu_train_xgb import resolve_device

ROOT = Path(r"C:\Users\benbr\BacktestStation")
ANCHORS_SWEEP = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_sweep") / "data" / "ml" / "anchors"
ANCHORS_SWING = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_swing_pivot") / "data" / "ml" / "anchors"
ANCHORS_FVG   = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_sweep") / "data" / "ml" / "anchors"  # FVG strict lives in the sweep release zip
ANCHORS_OB    = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_16_strict_order_block") / "data" / "ml" / "anchors"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_v11_multi_family_audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)
UTC = timezone.utc


# Each family is represented as two Signal objects (side-specific) so the
# direction rule can be fixed per side. For all-side labels we wrap them
# as two signals using fixed direction by side semantics.

# SWEEP: failed_recovered means swept then reversed
#   side=high  -> swept the high, failed -> reverse DOWN -> SHORT
#   side=low   -> swept the low, failed -> reverse UP -> LONG
SWEEP_SIGNALS = [
    Signal("sweep_failed_recovered_high",
           ANCHORS_SWEEP, "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict",
           "at_fire", "high", "label.strict.next_60m.sweep_failed_recovered", "fixed_short"),
    Signal("sweep_failed_recovered_low",
           ANCHORS_SWEEP, "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict",
           "at_fire", "low", "label.strict.next_60m.sweep_failed_recovered", "fixed_long"),
]

# SWING: pivot_broken_through_continuation means pivot was broken in the direction
#   side=high  -> pivot at high broken upward -> LONG continuation
#   side=low   -> pivot at low broken downward -> SHORT continuation
SWING_SIGNALS = [
    Signal("swing_continuation_high",
           ANCHORS_SWING, "swing_snapshots_strict",
           "at_fire", "high", "label.strict.next_60m.pivot_broken_through_continuation", "fixed_long"),
    Signal("swing_continuation_low",
           ANCHORS_SWING, "swing_snapshots_strict",
           "at_fire", "low", "label.strict.next_60m.pivot_broken_through_continuation", "fixed_short"),
]

# FVG: after_tap_failed_1x_against means FVG tapped + price moved 1x ATR AGAINST the FVG
#   The label is "against the FVG fill direction"
#   side=bullish_fvg -> FVG below current price, tap failed = price stayed UP -> LONG  (against fill = continuing up)
#   side=bearish_fvg -> FVG above current price, tap failed = price stayed DOWN -> SHORT
# Need to inspect actual side values in the FVG matrix to set this correctly. Using side="all" with side-aware.
# We'll check 'fvg.side' or 'anchor.side' once we load the matrix.
FVG_SIGNALS = [
    Signal("fvg_tap_failed_1x_all",
           ANCHORS_FVG, "fvg_snapshots_xctx_fvggeom_obgeom_strict",
           "at_fire", "all", "label.strict.forward_10c.after_tap_failed_1x_against", "side_aware"),
]

# OB baseline (re-run for comparison)
from scripts.ml.rigorous_backtest_v9_ob import OB_SIGNALS

FAMILIES = {
    "sweep_failed_recovered": SWEEP_SIGNALS,
    "swing_continuation":     SWING_SIGNALS,
    "fvg_tap_failed_1x":      FVG_SIGNALS,
    "ob_continuation":        OB_SIGNALS,
}


def audit_one_family(name: str, signals: list[Signal], bars: BarsCache,
                     device: str, variant: StopVariant) -> list[dict]:
    """Run A/B/C/D variants for one family. Returns list of rollup dicts."""
    print(f"\n--- Family: {name} ---")

    # Train + score (variants A, C)
    model_picks_frames = []
    for sig in signals:
        for ty in TEST_YEARS:
            df = _train_and_score(sig, device, ty)
            if not df.empty:
                model_picks_frames.append(df)
    model_picks = pd.concat(model_picks_frames, ignore_index=True) if model_picks_frames else pd.DataFrame()
    print(f"  model top-10% picks: {len(model_picks):,}")

    # All-event picks (B)
    all_frames = [all_events_picks(sig) for sig in signals]
    all_picks = pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()
    print(f"  all-event picks: {len(all_picks):,}")

    # Random 10% picks (D)
    random_frames = [all_events_picks(sig, top_pct=0.10, random_seed=42) for sig in signals]
    random_picks = pd.concat(random_frames, ignore_index=True) if random_frames else pd.DataFrame()
    print(f"  random 10% picks: {len(random_picks):,}")

    variants = [
        ("A_model_correct",  model_picks,  False, "A: model top-10%, correct direction"),
        ("B_all_correct",    all_picks,    False, "B: ALL events, correct direction"),
        ("C_model_REVERSED", model_picks,  True,  "C: model top-10%, REVERSED direction"),
        ("D_random_correct", random_picks, False, "D: random 10%, correct direction"),
    ]
    results = []
    for vn, picks, reverse, desc in variants:
        if picks.empty:
            print(f"  [{vn:<18}] empty picks")
            results.append({"family": name, "variant": vn, "n": 0, "cum_r": 0.0,
                            "avg_r": 0.0, "win_rate": 0.0, "max_dd_r": 0.0, "years_positive": 0})
            continue
        td = simulate_picks(picks, bars, variant, reverse_direction=reverse, label=f"{name}_{vn}")
        ex = td[td["exit_reason"].isin(["target", "stop", "time_exit"])]
        n = len(ex)
        cum_r = float(ex["pnl_r"].sum()) if n else 0.0
        avg_r = float(ex["pnl_r"].mean()) if n else 0.0
        win_rate = float((ex["pnl_r"] > 0).mean()) if n else 0.0
        cumr = ex.sort_values("fire_ts")["pnl_r"].cumsum() if n else pd.Series([0.0])
        max_dd = float((cumr.cummax() - cumr).max()) if n else 0.0
        years_pos = int(ex.groupby("test_year")["pnl_r"].sum().gt(0).sum()) if n else 0
        print(f"  [{vn:<18}] n={n:5d} cum_R={cum_r:+8.1f} avg_R={avg_r:+5.3f} win%={win_rate:.3f} DD={max_dd:5.1f} yrs+={years_pos}/6")
        results.append({"family": name, "variant": vn, "n_trades": n, "cum_r": cum_r,
                        "avg_r": avg_r, "win_rate": win_rate, "max_dd_r": max_dd,
                        "years_positive": years_pos})
    return results


def main() -> int:
    device_info = resolve_device("auto")
    print(f"=== V11 multi-family event-bias audit ===  device={device_info.resolved}")
    print(f"output: {OUT_DIR}")
    t0 = time_mod.time()

    bars = BarsCache()
    all_results = []
    for name, signals in FAMILIES.items():
        try:
            results = audit_one_family(name, signals, bars, device_info.resolved, V8A_STOP)
            all_results.extend(results)
        except Exception as exc:
            print(f"  family {name} FAILED: {type(exc).__name__}: {exc}")
            all_results.append({"family": name, "variant": "ERROR", "error": str(exc)})

    df = pd.DataFrame(all_results)
    df.to_csv(OUT_DIR / "all_families_rollup.csv", index=False, float_format="%.4f")

    # Pivot: rows = family, cols = variant, values = cum_r
    print("\n=== Cross-family rollup (cum_R) ===")
    if "cum_r" in df.columns:
        cum_pivot = df.pivot_table(index="family", columns="variant", values="cum_r", aggfunc="sum")
        cum_pivot.to_csv(OUT_DIR / "cross_family_cum_r.csv", float_format="%.2f")
        print(cum_pivot.to_string(float_format=lambda x: f"{x:+8.1f}"))
        print("\n=== Cross-family rollup (avg_R per trade) ===")
        avg_pivot = df.pivot_table(index="family", columns="variant", values="avg_r", aggfunc="sum")
        avg_pivot.to_csv(OUT_DIR / "cross_family_avg_r.csv", float_format="%.4f")
        print(avg_pivot.to_string(float_format=lambda x: f"{x:+6.3f}"))
        print("\n=== Cross-family rollup (n_trades) ===")
        n_pivot = df.pivot_table(index="family", columns="variant", values="n_trades", aggfunc="sum")
        print(n_pivot.to_string(float_format=lambda x: f"{x:>6.0f}"))

    # Type classification: Type B (event class) vs Type A (real ML)
    print("\n=== Type classification per family ===")
    classifications = []
    for family in df["family"].unique():
        sub = df[df["family"] == family]
        a = sub[sub["variant"] == "A_model_correct"]["cum_r"].iloc[0] if (sub["variant"] == "A_model_correct").any() else 0
        b = sub[sub["variant"] == "B_all_correct"]["cum_r"].iloc[0] if (sub["variant"] == "B_all_correct").any() else 0
        d = sub[sub["variant"] == "D_random_correct"]["cum_r"].iloc[0] if (sub["variant"] == "D_random_correct").any() else 0
        a_avg = sub[sub["variant"] == "A_model_correct"]["avg_r"].iloc[0] if (sub["variant"] == "A_model_correct").any() else 0
        b_avg = sub[sub["variant"] == "B_all_correct"]["avg_r"].iloc[0] if (sub["variant"] == "B_all_correct").any() else 0
        d_avg = sub[sub["variant"] == "D_random_correct"]["avg_r"].iloc[0] if (sub["variant"] == "D_random_correct").any() else 0
        # Type B if B has big positive cum_r AND random ~ model
        type_b = (b > 500 and abs(b_avg) > 0.2 and (abs(d_avg) > 0.7 * abs(a_avg) or d > 0.5 * a))
        # Type A if model >> random/all
        type_a = (a > 30 and (b < 0.3 * a or abs(d_avg) < 0.3 * abs(a_avg)))
        label = "TYPE B (event class)" if type_b else "TYPE A (real ML)" if type_a else "MIXED/UNCLEAR"
        print(f"  {family:<28}  A=+{a:7.1f}R  B=+{b:7.1f}R  D=+{d:7.1f}R  -->  {label}")
        classifications.append({"family": family, "A_cum_r": a, "B_cum_r": b, "D_cum_r": d,
                                "A_avg_r": a_avg, "B_avg_r": b_avg, "D_avg_r": d_avg,
                                "classification": label})

    cls_df = pd.DataFrame(classifications)
    cls_df.to_csv(OUT_DIR / "type_classifications.csv", index=False, float_format="%.4f")

    summary = {
        "classifications": {row["family"]: row["classification"] for _, row in cls_df.iterrows()},
        "type_b_families": cls_df[cls_df["classification"].str.startswith("TYPE B")]["family"].tolist(),
        "type_a_families": cls_df[cls_df["classification"].str.startswith("TYPE A")]["family"].tolist(),
        "elapsed_min": round((time_mod.time() - t0) / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DONE in {(time_mod.time()-t0)/60:.1f} min ===")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
