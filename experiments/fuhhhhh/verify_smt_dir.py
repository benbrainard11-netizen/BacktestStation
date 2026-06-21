"""Independent verification of the NQ-vs-ES SMT direction edge on the PRE-EXISTING
struct_smt column (causal: pivots gated to <= idx-SWING_K in triggers.smt_dir).
Full decision universe (incl. timeouts) so there's no resolution-conditioning trap.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
o = pd.read_parquet(OUT / "dataset_ndx.parquet")
o["mo"] = o["date"].str.slice(0, 7)
rng = np.random.default_rng(7)


def boot(df, col):
    days = df["date"].unique()
    by = {d: df[df.date == d][col].to_numpy() for d in days}
    m = np.array([np.concatenate([by[d] for d in rng.choice(days, len(days), True)]).mean()
                  for _ in range(4000)])
    return df[col].mean(), float((m <= 0).mean())


def cell(mask, rcol, label):
    s = o[mask]
    if len(s) < 25:
        print(f"  {label:32s} n={len(s)} thin")
        return
    mean, p = boot(s, rcol)
    bymo = s.groupby("mo")[rcol].mean()
    db2 = s[~s.mo.isin(bymo.sort_values(ascending=False).index[:2])][rcol].mean()
    exfm = s[~s.mo.isin(["2026-02", "2026-03"])][rcol].mean()
    print(f"  {label:32s} R={mean:+.4f} p={p:.3f} n={len(s)} win%={(s[rcol]>0).mean()*100:.0f} "
          f"mo+={int((bymo>0).sum())}/{len(bymo)} dropBest2={db2:+.4f} exFebMar={exfm:+.4f}")


print("=== FULL decision universe (incl timeouts) — no resolution conditioning ===")
cell(o.struct_smt == -1, "r_short", "SMT bearish -> SHORT")
cell(o.struct_smt == 0, "r_short", "NO SMT -> short (control)")
cell(o.struct_smt == 1, "r_long", "SMT bullish -> LONG")
cell(o.struct_smt == 0, "r_long", "NO SMT -> long (control)")

ss = o[o.struct_smt == -1].r_short.mean()
ns = o[o.struct_smt == 0].r_short.mean()
print(f"\nDISCRIMINATING: SMT-short {ss:+.4f}  vs  noSMT-short {ns:+.4f}  (diff={ss-ns:+.4f})")
print("\nper-month SMT bearish -> SHORT (full universe):")
print(o[o.struct_smt == -1].groupby("mo")["r_short"].agg(["size", "mean"]).round(3).to_string())
print("\nstruct_smt counts:", o.struct_smt.value_counts().to_dict())
