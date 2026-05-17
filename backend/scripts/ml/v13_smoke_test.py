"""Tiny smoke test for v13_registry_audit -- just audits the top 3 smt
labels to verify the pipeline works end-to-end."""

from __future__ import annotations

import sys
import time as time_mod
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.v13_registry_audit import (
    REGISTRY_PATH, AUC_THRESHOLD, SKIP_SIDES, audit_one_label, build_signal,
    classify, V8A_STOP,
)
from scripts.ml.rigorous_backtest_v1 import BarsCache


def main() -> int:
    t0 = time_mod.time()
    df = pd.read_parquet(REGISTRY_PATH)
    df["auc"] = df["gpu_mean_auc"].fillna(df["cpu_mean_auc"])
    df = df[df["auc"] >= AUC_THRESHOLD].copy()
    df = df[~df["side"].isin(SKIP_SIDES)].copy()
    # Just take top 3 by AUC for smoke
    df = df.sort_values("auc", ascending=False).head(3).reset_index(drop=True)

    bars = BarsCache()
    print("=== V13 smoke test (top 3 labels by AUC) ===")
    for i, r in df.iterrows():
        print(f"\n[{i+1}/3] {r['matrix']} / {r['snapshot']} / side={r['side']} / {r['label']}  auc={r['auc']:.3f}")
        sig = build_signal(r["matrix"], r["snapshot"], r["side"], r["label"])
        if sig is None:
            print("  SKIPPED: build_signal returned None")
            continue
        audit = audit_one_label(sig, bars, V8A_STOP)
        if audit.get("skip_reason"):
            print(f"  SKIPPED: {audit['skip_reason']}")
            continue
        cls = classify(audit)
        print(f"  n_events={audit['n_events']:5d}")
        print(f"  B_natural  n={audit['B_nat_n']:5d}  cum_R={audit['B_nat_cum_r']:+8.1f}  avg_R={audit['B_nat_avg_r']:+5.3f}  win={audit['B_nat_win']:.3f}  yrs+={audit['B_nat_yrs_pos']}/6")
        print(f"  B_reversed n={audit['B_rev_n']:5d}  cum_R={audit['B_rev_cum_r']:+8.1f}  avg_R={audit['B_rev_avg_r']:+5.3f}  win={audit['B_rev_win']:.3f}  yrs+={audit['B_rev_yrs_pos']}/6")
        print(f"  D_natural  n={audit['D_n']:5d}  cum_R={audit['D_cum_r']:+8.1f}  avg_R={audit['D_avg_r']:+5.3f}")
        flag = " *** TYPE B ***" if cls["is_type_b"] else ""
        print(f"  --> winning_dir={cls['winning_dir']}  cum_R={cls['winning_cum_r']:+8.1f}  is_type_b={cls['is_type_b']}{flag}")
    print(f"\nelapsed: {(time_mod.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
