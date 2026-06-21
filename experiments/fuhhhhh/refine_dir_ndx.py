"""Refine the dev spec: (1) combine 5m-SMT + RS-fade (stack vs overlap), (2) long side.
All full-universe, net cost, with controls. Weather (p_chop) gating where OOS preds exist.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(17)
o = pd.read_parquet(OUT / "dataset_ndx.parquet").merge(
    pd.read_parquet(OUT / "xasset_dir_ndx.parquet"), on=["date", "ms"], how="left")
oo = pd.read_parquet(OUT / "oos_ndx.parquet")[["date", "ms", "p_chop"]]
o = o.merge(oo, on=["date", "ms"], how="left")
o["mo"] = o["date"].str.slice(0, 7)
NDAYS = o["date"].nunique()
q80 = o["rs_div_30m"].quantile(0.8)
q20 = o["rs_div_30m"].quantile(0.2)

# signal masks
smt5_s = o.xsmt_5m == -1
rsf_s = o.rs_div_30m >= q80        # NQ outperforming -> fade short
smt5_l = o.xsmt_5m == 1
rss_l = o.rs_div_30m <= q20        # NQ underperforming -> fade long
movex = o.p_chop <= o["p_chop"].median()


def boot(s):
    days = s["date"].unique(); by = {d: s[s.date == d]["r"].to_numpy() for d in days}
    m = np.array([np.concatenate([by[d] for d in RNG.choice(days, len(days), True)]).mean() for _ in range(3000)])
    return s["r"].mean(), float((m <= 0).mean())


def cell(mask, side, label):
    s = o[mask].copy(); s["r"] = s["r_short"] if side == "S" else s["r_long"]
    s = s[np.isfinite(s["r"])]
    if len(s) < 20:
        print(f"  {label:30s} n={len(s)} thin"); return
    mean, p = boot(s); bymo = s.groupby("mo")["r"].mean()
    db2 = s[~s.mo.isin(bymo.sort_values(ascending=False).index[:2])]["r"].mean()
    exfm = s[~s.mo.isin(["2026-02", "2026-03"])]["r"].mean()
    print(f"  {label:30s} R={mean:+.4f} p={p:.3f} n={len(s):4d} /day={len(s)/NDAYS:.1f} "
          f"mo+={int((bymo>0).sum())}/{len(bymo)} db2={db2:+.4f} exFM={exfm:+.4f}")


print(f"=== signal overlap (short) === ({NDAYS} days)")
print(f"  5m-SMT-short n={smt5_s.sum()}  RS-fade-short n={rsf_s.sum()}  "
      f"BOTH n={(smt5_s & rsf_s).sum()}  EITHER n={(smt5_s | rsf_s).sum()}  "
      f"corr={np.corrcoef(smt5_s.astype(int), rsf_s.astype(int))[0,1]:+.3f}")

print("\n=== COMBINE short side ===")
cell(smt5_s, "S", "5m-SMT only")
cell(rsf_s, "S", "RS-fade only")
cell(smt5_s & rsf_s, "S", "BOTH (intersection)")
cell(smt5_s | rsf_s, "S", "EITHER (union)")
cell(smt5_s & ~rsf_s, "S", "5m-SMT & NOT rs-fade")
cell(smt5_s & rsf_s & movex, "S", "BOTH + weather(move)")
cell((smt5_s | rsf_s) & movex, "S", "EITHER + weather(move)")

print("\n=== LONG side — is anything real? ===")
cell(smt5_l, "L", "5m-SMT long")
cell(o.struct_smt == 1, "L", "1m-SMT long")
cell(rss_l, "L", "RS-weak fade long")
cell(smt5_l & rss_l, "L", "5m-SMT-long & RS-weak")
cell(smt5_l & movex, "L", "5m-SMT-long + weather")
cell((o.struct_smt == 1) & movex, "L", "1m-SMT-long + weather")
print("\n  up-regime check: long only in months with net up-tilt")
upmos = o.groupby("mo")["y"].apply(lambda s: (s == 1).mean() > (s == 0).mean())
upmask = o["mo"].isin(upmos[upmos].index)
cell(smt5_l & upmask, "L", "5m-SMT-long in up-months")
