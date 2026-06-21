"""Is the gamma-conditioned opening-drive edge REAL gamma, or a vol confound? + robustness.

short-gamma days correlate with high vol. Test: does gamma add WITHIN vol buckets, or is it
just "momentum works when vol is high"? Plus per-year robustness of the follow-in-short-gamma rule.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(41)
od = pd.read_parquet(OUT / "open_dataset.parquet").dropna(subset=["r_long", "r_short"]).copy()
od["d"] = pd.to_datetime(od["date"])
w = pd.read_parquet(OUT / "walls_v2.parquet")
w["d"] = pd.to_datetime(w["date"].astype(int).astype(str), format="%Y%m%d")
m = pd.merge_asof(od.sort_values("d"), w[["d", "gex_proxy"]].sort_values("d"),
                  on="d", direction="backward", allow_exact_matches=False)
m = m.dropna(subset=["gex_proxy", "or_drive_atr", "fwd_eod_atr"]).reset_index(drop=True)
m["short_gamma"] = m["gex_proxy"] < 0
# causal vol bucket from prior-day ATR (already days<D)
m["vol_b"] = pd.qcut(m["atr"], 3, labels=["loVol", "midVol", "hiVol"])


def follow_R(sub):
    d = np.sign(sub["or_drive_atr"])
    return np.where(d > 0, sub["r_long"], sub["r_short"])


print(f"n={len(m)}  short-gamma days={int(m.short_gamma.sum())}")
print("\n### vol distribution within gamma regime (confound check)")
print(pd.crosstab(m.short_gamma, m.vol_b, normalize="index").round(2).to_string())

print("\n### corr(or_drive, fwd_eod) — gamma vs vol, and gamma WITHIN vol")
def c(sub):
    return np.corrcoef(sub["or_drive_atr"], sub["fwd_eod_atr"])[0, 1] if len(sub) > 30 else np.nan
print(f"  short-gamma {c(m[m.short_gamma]):+.3f}   long-gamma {c(m[~m.short_gamma]):+.3f}")
print(f"  hiVol       {c(m[m.vol_b=='hiVol']):+.3f}   loVol     {c(m[m.vol_b=='loVol']):+.3f}")
print("  --- gamma split WITHIN each vol bucket (does gamma add beyond vol?) ---")
for vb in ["loVol", "midVol", "hiVol"]:
    sub = m[m.vol_b == vb]
    print(f"  {vb}: short-gamma {c(sub[sub.short_gamma]):+.3f} (n={int(sub.short_gamma.sum())})  "
          f"long-gamma {c(sub[~sub.short_gamma]):+.3f} (n={int((~sub.short_gamma).sum())})")

print("\n### follow-drive R: gamma vs vol conditioning (does gamma beat just-high-vol?)")
for lab, sub in [("short-gamma (all vol)", m[m.short_gamma]),
                 ("hiVol (all gamma)", m[m.vol_b == "hiVol"]),
                 ("hiVol & short-gamma", m[(m.vol_b == "hiVol") & m.short_gamma]),
                 ("hiVol & long-gamma", m[(m.vol_b == "hiVol") & ~m.short_gamma]),
                 ("midVol & short-gamma", m[(m.vol_b == "midVol") & m.short_gamma])]:
    r = follow_R(sub)
    byyr = pd.Series(r).groupby(sub["yr"].values).mean()
    print(f"  {lab:24s} meanR={r.mean():+.4f} n={len(r)} yrs+={int((byyr>0).sum())}/{len(byyr)}")

print("\n### per-year: follow-drive in short-gamma")
sg = m[m.short_gamma]
print(pd.Series(follow_R(sg), index=sg.index).groupby(sg["yr"].values).agg(["size", "mean"]).round(4).to_string())
