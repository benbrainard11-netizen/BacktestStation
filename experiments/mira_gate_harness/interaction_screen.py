"""ORDERFLOW-FEATURE x LEVEL-FAMILY interaction screen (Ben: "maybe some levels use different
interactions"). For each (level_family x feature), fit the favorable DIRECTION on DESIGN (2026) only,
freeze it, evaluate the lift ONCE on OOS (2025). Multiple-testing is the recurring killer here, so the
HEADLINE is the binomial test across the whole grid (are more cells design->OOS consistent than the 50%
chance rate?), NOT any single cell. Survivors get a per-cell shuffle null. This is a HYPOTHESIS SCREEN,
not a validation — survivors need an independent one-shot.

Universes: working levels (mbp1_stack_legal_bars_full.parquet, 9 families) + gamma walls
(mbp1_stack_legal_bars_wall_mbp1.parquet, gwc/gwp). Outcome trail_2R. 9 orderflow features.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
POL = "trail_2R"
FEATURES = ["w90_drift_dir_ticks", "w90_aggr_imb_dir", "w90_delta_dir", "w90_vol", "w90_absorption",
            "w30_late_drift_dir", "app_drift_dir", "app_aggr_imb_dir", "app_absorption"]
MIN_DESIGN, MIN_OOS = 40, 40


def load(panel, universe, fam_col="level_family"):
    fc = pd.read_parquet(RUNS / panel)
    if POL not in fc.columns or fam_col not in fc.columns or "level_type" not in fc.columns:
        u = pd.read_parquet(RUNS / universe)
        key = ["symbol", "session_date", "level_price", "side"]
        add = [c for c in ["trail_2R", "fixed_3R", "level_type", "level_family"] if c not in fc.columns]
        fc = fc.merge(u[key + add].drop_duplicates(key), on=key, how="left")
    fc["R"] = pd.to_numeric(fc[POL], errors="coerce")
    fc = fc[fc["R"].abs() < 50].copy()
    fc["yr"] = pd.to_datetime(fc["session_date"]).dt.year
    return fc


def cell(d, feat):
    """Fit favorable direction on 2026 (median split), eval lift on 2025. Returns (design_spread, oos_lift, n_oos)."""
    des = d[d["yr"] == 2026][[feat, "R"]].dropna()
    oos = d[d["yr"] == 2025][[feat, "R"]].dropna()
    if len(des) < MIN_DESIGN or len(oos) < MIN_OOS:
        return None
    thr = des[feat].median()
    hi_des, lo_des = des[des[feat] >= thr]["R"], des[des[feat] < thr]["R"]
    if len(hi_des) < 8 or len(lo_des) < 8:
        return None
    direction = np.sign(hi_des.mean() - lo_des.mean())  # +1 => high feature favorable
    if direction == 0:
        return None
    take = oos[oos[feat] >= thr] if direction > 0 else oos[oos[feat] < thr]
    rest = oos[oos[feat] < thr] if direction > 0 else oos[oos[feat] >= thr]
    if len(take) < 8 or len(rest) < 8:
        return None
    oos_lift = take["R"].mean() - rest["R"].mean()  # in the design-frozen direction
    return (hi_des.mean() - lo_des.mean(), oos_lift, len(take), direction, thr)


def run():
    wl = load("mbp1_stack_legal_bars_full.parquet", "legal_bars_full.parquet")
    wa = load("mbp1_stack_legal_bars_wall_mbp1.parquet", "legal_bars_wall_mbp1.parquet")
    wa["level_family"] = "gamma_wall_" + wa["level_type"].map({"gwc": "call", "gwp": "put"})
    d = pd.concat([wl, wa], ignore_index=True)
    fams = [f for f in d["level_family"].unique() if (d["level_family"] == f).sum() >= 60]
    print(f"families ({len(fams)}): {sorted(fams)}")
    print(f"features ({len(FEATURES)}): {FEATURES}\n")

    results = []
    hdr = f"{'family':16s} " + " ".join(f"{f.replace('w90_','').replace('_dir','')[:7]:>8s}" for f in FEATURES)
    print(hdr); print("-" * len(hdr))
    for fam in sorted(fams):
        g = d[d["level_family"] == fam]
        cells = []
        for feat in FEATURES:
            r = cell(g, feat)
            cells.append(r)
            if r is not None:
                results.append((fam, feat, r[0], r[1], r[2]))
        row = f"{fam:16s} " + " ".join(
            (f"{c[1]:+8.2f}" if c is not None else f"{'·':>8s}") for c in cells)
        print(row)

    # ---- DISCIPLINE: multiple-testing guard ----
    res = pd.DataFrame(results, columns=["fam", "feat", "design_spread", "oos_lift", "n"])
    res = res[res["n"] >= MIN_OOS]
    k = len(res)
    pos = int((res["oos_lift"] > 0).sum())
    from math import comb
    p_binom = sum(comb(k, i) for i in range(pos, k + 1)) / 2**k if k else np.nan
    print(f"\n{'='*70}\nMULTIPLE-TESTING GUARD: {k} cells tested (design-fit dir, OOS-eval).")
    print(f"  {pos}/{k} cells OOS-positive in design direction (chance=50%); binomial p={p_binom:.3f}")
    print(f"  mean OOS lift across cells: {res['oos_lift'].mean():+.4f} (null E=0)")
    print(f"  -> {'SIGNAL: more consistent than chance' if p_binom < 0.05 else 'NO grid-level signal (consistent with all-noise)'}")

    print(f"\nTOP design->OOS cells (hypotheses, NOT validated — need one-shot + shuffle):")
    for _, r in res.sort_values("oos_lift", ascending=False).head(10).iterrows():
        print(f"  {r['fam']:16s} {r['feat']:20s} design_spread {r['design_spread']:+.3f} "
              f"OOS_lift {r['oos_lift']:+.3f} (n={int(r['n'])})")
    print(f"\nWORST (feature HURTS in OOS despite design):")
    for _, r in res.sort_values("oos_lift").head(4).iterrows():
        print(f"  {r['fam']:16s} {r['feat']:20s} OOS_lift {r['oos_lift']:+.3f}")
    res.to_parquet(RUNS / "interaction_screen_results.parquet", index=False)
    print(f"\nwrote runs/interaction_screen_results.parquet ({k} cells)")


if __name__ == "__main__":
    run()
