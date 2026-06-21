"""Quick bracket/horizon eval of the 5m-SMT + RS-fade direction rule on the CURRENT
dataset_ndx labels (called by the bracket sweep after each rebuild). Fast: R/n/mo+, no boot.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
o = pd.read_parquet(OUT / "dataset_ndx.parquet").merge(
    pd.read_parquet(OUT / "xasset_dir_ndx.parquet"), on=["date", "ms"], how="left")
o["mo"] = o["date"].str.slice(0, 7)
nd = o["date"].nunique()
q80, q20 = o["rs_div_30m"].quantile(0.8), o["rs_div_30m"].quantile(0.2)
smt5_s, rsf_s = o.xsmt_5m == -1, o.rs_div_30m >= q80
smt5_l, rss_l = o.xsmt_5m == 1, o.rs_div_30m <= q20


def line(mask, rcol, label):
    s = o[mask]
    r = s[rcol]
    bymo = s.groupby("mo")[rcol].mean()
    db2 = s[~s.mo.isin(bymo.sort_values(ascending=False).index[:2])][rcol].mean()
    print(f"    {label:24s} R={r.mean():+.4f} n={len(s):4d} /day={len(s)/nd:.1f} mo+={int((bymo>0).sum())}/{len(bymo)} db2={db2:+.4f}")


line(smt5_s | rsf_s, "r_short", "UNION short")
line(smt5_s & rsf_s, "r_short", "INTERSECT short")
line(smt5_s, "r_short", "5m-SMT short")
line(smt5_l & rss_l, "r_long", "INTERSECT long")
