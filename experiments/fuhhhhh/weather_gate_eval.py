"""Weather x Compass: does gating the cross-asset SHORT signal to 'move expected'
(low p_chop from the move model) sharpen it? All OOS (p_chop is walk-forward).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(13)
o = pd.read_parquet(OUT / "dataset_ndx.parquet").merge(
    pd.read_parquet(OUT / "xasset_dir_ndx.parquet"), on=["date", "ms"], how="left")
oo = pd.read_parquet(OUT / "oos_ndx.parquet")[["date", "ms", "p_chop"]]
o = o.merge(oo, on=["date", "ms"], how="inner")     # OOS rows only (weather is causal/walk-forward)
o["mo"] = o["date"].str.slice(0, 7)
NDAYS = o["date"].nunique()
thr = o["p_chop"].median()


def boot(s):
    days = s["date"].unique(); by = {d: s[s.date == d]["r"].to_numpy() for d in days}
    m = np.array([np.concatenate([by[d] for d in RNG.choice(days, len(days), True)]).mean() for _ in range(3000)])
    return s["r"].mean(), float((m <= 0).mean())


def cell(mask, label):
    s = o[mask].copy(); s["r"] = s["r_short"]
    if len(s) < 20:
        print(f"  {label:34s} n={len(s)} thin"); return
    mean, p = boot(s); bymo = s.groupby("mo")["r"].mean()
    print(f"  {label:34s} R={mean:+.4f} p={p:.3f} n={len(s):4d} /day={len(s)/NDAYS:.1f} win={(s['r']>0).mean()*100:3.0f}% mo+={int((bymo>0).sum())}/{len(bymo)}")


print(f"=== weather-gated cross-asset SHORT (OOS, {NDAYS} days, p_chop median={thr:.2f}) ===")
for nm, m in [("5m SMT", o.xsmt_5m == -1), ("vote<=-2", o.xsmt_vote <= -2), ("1m SMT", o.struct_smt == -1)]:
    print(f"\n-- {nm} short --")
    cell(m, f"{nm} ALL (OOS)")
    cell(m & (o.p_chop <= thr), f"{nm} + MOVE expected (p_chop<=med)")
    cell(m & (o.p_chop > thr), f"{nm} + CHOP expected (p_chop>med)")
