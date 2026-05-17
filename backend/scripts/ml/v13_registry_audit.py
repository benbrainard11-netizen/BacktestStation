"""V13 — registry-driven Type A/B audit across the full label library.

Reads `data/ml/catalog/label_registry.parquet`, filters labels with AUC >=
threshold, and runs a bidirectional B/D event-bias audit per label. Skips
model training (Phase 1) -- Type B detection only needs B vs D.

Per (matrix, snapshot, side, label) the variants are:
  B_natural   : ALL events, side-determined natural direction
  B_reversed  : ALL events, REVERSED direction
  D_natural   : random 10% of events, natural direction (control)

Classification (Phase 1 focuses on Type B detection):
  - winning_dir = direction with larger |cum_R|
  - is_type_b   = cum_R_winning >= TYPE_B_MIN_CUM_R AND
                  avg_R_winning >= TYPE_B_MIN_AVG_R AND
                  cum_R_D_winning >= 0.5 * cum_R_winning  (random catches most)

Output: experiments/backtests/2026-05-16_v13_registry_audit/
  per_label_rollup.csv         one row per (matrix, snapshot, side, label, variant)
  per_label_classification.csv one row per label with type_b flag + winning dir
  summary.json                 run stats + top-N Type B candidates
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
from scripts.ml.rigorous_backtest_v7_stops import StopVariant, simulate_v7
from scripts.ml.rigorous_backtest_v9_ob import V8A_STOP
from scripts.ml.v9_ob_leak_audit import all_events_picks, simulate_picks

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
REGISTRY_PATH = ROOT / "data" / "ml" / "catalog" / "label_registry.parquet"
RELEASES_ROOT = Path(r"D:\BacktestStationData")
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_v13_registry_audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)

AUC_THRESHOLD = 0.65
TYPE_B_MIN_CUM_R = 200.0
TYPE_B_MIN_AVG_R = 0.05
SKIP_SIDES = {"balanced", "medium"}
TRADE_SYMBOLS = {"NQ.c.0", "ES.c.0"}


def find_anchors_dir(matrix: str) -> Path | None:
    """Return the newest release dir containing <matrix>.parquet."""
    releases = sorted(
        [p for p in RELEASES_ROOT.glob("strategy_lab_core_*") if p.is_dir()],
        reverse=True,
    )
    for r in releases:
        adir = r / "data" / "ml" / "anchors"
        if (adir / f"{matrix}.parquet").exists():
            return adir
    return None


def direction_rule_for_side(side: str) -> str | None:
    """Map registry filter side to a Signal.direction_rule.
    Returns None for sides where direction is ambiguous (caller skips)."""
    if side in ("high", "bearish", "gap_down", "selling"):
        return "fixed_short"
    if side in ("low", "bullish", "gap_up", "buying"):
        return "fixed_long"
    if side == "all":
        return "side_aware"
    return None


def build_signal(matrix: str, snapshot: str, side: str, label: str) -> Signal | None:
    adir = find_anchors_dir(matrix)
    if adir is None:
        return None
    rule = direction_rule_for_side(side)
    if rule is None:
        return None
    name = f"{matrix}|{snapshot}|{side}|{label}"
    return Signal(name=name, anchors_dir=adir, matrix_file=matrix,
                  snapshot=snapshot, side=side, label=label, direction_rule=rule)


def _stats(td: pd.DataFrame) -> dict:
    ex = td[td["exit_reason"].isin(["target", "stop", "time_exit"])]
    n = len(ex)
    if n == 0:
        return {"n": 0, "cum_r": 0.0, "avg_r": 0.0, "win_rate": 0.0,
                "max_dd_r": 0.0, "years_positive": 0}
    cumr = ex.sort_values("fire_ts")["pnl_r"].cumsum()
    return {
        "n": n,
        "cum_r": float(ex["pnl_r"].sum()),
        "avg_r": float(ex["pnl_r"].mean()),
        "win_rate": float((ex["pnl_r"] > 0).mean()),
        "max_dd_r": float((cumr.cummax() - cumr).max()),
        "years_positive": int(ex.groupby("test_year")["pnl_r"].sum().gt(0).sum()),
    }


def audit_one_label(sig: Signal, bars: BarsCache, variant: StopVariant) -> dict:
    """Run B_natural, B_reversed, D_natural for one label. Returns flat dict."""
    all_picks = all_events_picks(sig)
    n_events = len(all_picks)
    if n_events == 0:
        return {"n_events": 0, "skip_reason": "no_events"}

    td_nat = simulate_picks(all_picks, bars, variant, reverse_direction=False,
                            label="B_natural")
    td_rev = simulate_picks(all_picks, bars, variant, reverse_direction=True,
                            label="B_reversed")

    random_picks = all_events_picks(sig, top_pct=0.10, random_seed=42)
    td_d = simulate_picks(random_picks, bars, variant, reverse_direction=False,
                          label="D_natural")

    s_nat = _stats(td_nat)
    s_rev = _stats(td_rev)
    s_d = _stats(td_d)

    return {
        "n_events": int(n_events),
        "B_nat_n": s_nat["n"], "B_nat_cum_r": s_nat["cum_r"], "B_nat_avg_r": s_nat["avg_r"],
        "B_nat_win": s_nat["win_rate"], "B_nat_dd": s_nat["max_dd_r"],
        "B_nat_yrs_pos": s_nat["years_positive"],
        "B_rev_n": s_rev["n"], "B_rev_cum_r": s_rev["cum_r"], "B_rev_avg_r": s_rev["avg_r"],
        "B_rev_win": s_rev["win_rate"], "B_rev_dd": s_rev["max_dd_r"],
        "B_rev_yrs_pos": s_rev["years_positive"],
        "D_n": s_d["n"], "D_cum_r": s_d["cum_r"], "D_avg_r": s_d["avg_r"],
        "D_win": s_d["win_rate"],
    }


def classify(row: dict) -> dict:
    """Determine winning direction + Type B candidacy.
    Winning = whichever direction is profitable (positive cum_R). Pick by SIGN,
    not magnitude -- the goal is to find labels we can trade, not labels that
    move strongly in either direction."""
    if row.get("skip_reason"):
        return {"winning_dir": None, "winning_cum_r": 0.0, "is_type_b": False}
    nat_cum, rev_cum = row["B_nat_cum_r"], row["B_rev_cum_r"]
    # Pick the more profitable direction (handles both-pos via larger, both-neg via least-bad).
    if nat_cum >= rev_cum:
        win_dir, win_cum, win_avg, win_yrs = "natural", nat_cum, row["B_nat_avg_r"], row["B_nat_yrs_pos"]
        d_cum = row["D_cum_r"]
    else:
        win_dir, win_cum, win_avg, win_yrs = "reversed", rev_cum, row["B_rev_avg_r"], row["B_rev_yrs_pos"]
        d_cum = -row["D_cum_r"]  # D in opposite direction ≈ -D

    is_type_b = (
        win_cum >= TYPE_B_MIN_CUM_R
        and win_avg >= TYPE_B_MIN_AVG_R
        and win_yrs >= 5  # at least 5 of 6 years positive
    )
    return {
        "winning_dir": win_dir,
        "winning_cum_r": win_cum,
        "winning_avg_r": win_avg,
        "winning_yrs_pos": win_yrs,
        "D_cum_r_aligned": d_cum,
        "is_type_b": is_type_b,
    }


def main() -> int:
    t0 = time_mod.time()
    print(f"=== V13 registry audit ===")
    print(f"output: {OUT_DIR}")

    df = pd.read_parquet(REGISTRY_PATH)
    df["auc"] = df["gpu_mean_auc"].fillna(df["cpu_mean_auc"])
    df = df[df["auc"] >= AUC_THRESHOLD].copy()
    df = df[~df["side"].isin(SKIP_SIDES)].copy()
    df = df.sort_values("auc", ascending=False).reset_index(drop=True)
    print(f"  candidates: {len(df)} labels (AUC>={AUC_THRESHOLD}, side not in {SKIP_SIDES})")

    bars = BarsCache()
    results = []

    for i, r in df.iterrows():
        matrix, snapshot, side, label = r["matrix"], r["snapshot"], r["side"], r["label"]
        auc = float(r["auc"])
        print(f"\n[{i+1}/{len(df)}] {matrix}/{snapshot}/{side}/{label}  auc={auc:.3f}")

        sig = build_signal(matrix, snapshot, side, label)
        if sig is None:
            print(f"  skip: no anchors dir for {matrix} or undirected side={side}")
            results.append({"matrix": matrix, "snapshot": snapshot, "side": side,
                            "label": label, "auc": auc, "skip_reason": "no_signal"})
            continue

        try:
            audit = audit_one_label(sig, bars, V8A_STOP)
        except Exception as exc:
            print(f"  ERROR {type(exc).__name__}: {exc}")
            results.append({"matrix": matrix, "snapshot": snapshot, "side": side,
                            "label": label, "auc": auc,
                            "skip_reason": f"err:{type(exc).__name__}"})
            continue

        if audit.get("skip_reason"):
            print(f"  skip: {audit['skip_reason']}")
            results.append({"matrix": matrix, "snapshot": snapshot, "side": side,
                            "label": label, "auc": auc, **audit})
            continue

        cls = classify(audit)
        out = {"matrix": matrix, "snapshot": snapshot, "side": side, "label": label,
               "auc": auc, **audit, **cls}
        results.append(out)
        flag = " *** TYPE B ***" if cls["is_type_b"] else ""
        print(f"  n_ev={audit['n_events']:5d}  "
              f"B_nat={audit['B_nat_cum_r']:+8.1f}R ({audit['B_nat_avg_r']:+5.3f}avg)  "
              f"B_rev={audit['B_rev_cum_r']:+8.1f}R  "
              f"D={audit['D_cum_r']:+7.1f}R  win_dir={cls['winning_dir']}{flag}")

        if (i+1) % 10 == 0:
            pd.DataFrame(results).to_csv(OUT_DIR / "per_label_rollup.csv",
                                          index=False, float_format="%.4f")

    rollup = pd.DataFrame(results)
    rollup.to_csv(OUT_DIR / "per_label_rollup.csv", index=False, float_format="%.4f")

    type_b = rollup[rollup.get("is_type_b") == True].sort_values("winning_cum_r", ascending=False)
    type_b.to_csv(OUT_DIR / "type_b_candidates.csv", index=False, float_format="%.4f")

    elapsed = (time_mod.time() - t0) / 60
    summary = {
        "auc_threshold": AUC_THRESHOLD,
        "total_candidates": len(df),
        "audited": int((rollup.get("skip_reason").isna() if "skip_reason" in rollup.columns else rollup.index >= 0).sum()),
        "type_b_count": int(len(type_b)),
        "top_type_b": [
            {
                "matrix": r["matrix"], "label": r["label"], "side": r["side"],
                "winning_dir": r["winning_dir"],
                "cum_r": round(r["winning_cum_r"], 1),
                "avg_r": round(r["winning_avg_r"], 3),
                "yrs_pos": int(r["winning_yrs_pos"]),
            }
            for _, r in type_b.head(20).iterrows()
        ],
        "elapsed_min": round(elapsed, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\n=== DONE in {elapsed:.1f} min ===")
    print(f"  audited: {summary['audited']} / {summary['total_candidates']}")
    print(f"  Type B candidates: {summary['type_b_count']}")
    if not type_b.empty:
        print(f"\n  Top 10 Type B candidates by cum_R:")
        for _, r in type_b.head(10).iterrows():
            print(f"    {r['matrix']:<55} {r['label']:<55} "
                  f"side={r['side']:<10} dir={r['winning_dir']:<9} "
                  f"cum_R={r['winning_cum_r']:+8.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
