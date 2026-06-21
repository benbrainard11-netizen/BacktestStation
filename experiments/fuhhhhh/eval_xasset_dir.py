"""Evaluate multi-TF cross-asset direction signals for a robust NQ edge.

Each signal scored on the FULL decision universe (no resolution conditioning), net cost,
with the mandated controls: bootstrap p, per-month, drop-best-2, ex-Feb/Mar (recent-regime).
Compares: 1m SMT (the verified baseline) vs 5/15/30/60m SMT vs multi-TF agreement vs RS
divergence. Short leg, long leg, and the combined both-side book per signal.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\eval_xasset_dir.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(11)
o = pd.read_parquet(OUT / "dataset_ndx.parquet")
xa = pd.read_parquet(OUT / "xasset_dir_ndx.parquet")
o = o.merge(xa, on=["date", "ms"], how="left")
o["mo"] = o["date"].str.slice(0, 7)
NDAYS = o["date"].nunique()


def boot(s):
    days = s["date"].unique()
    by = {d: s[s.date == d]["r"].to_numpy() for d in days}
    m = np.array([np.concatenate([by[d] for d in RNG.choice(days, len(days), True)]).mean()
                  for _ in range(3000)])
    return s["r"].mean(), float((m <= 0).mean())


def cell(df, label):
    if len(df) < 25:
        print(f"  {label:26s} n={len(df):4d} thin")
        return
    mean, p = boot(df)
    bymo = df.groupby("mo")["r"].mean()
    db2 = df[~df.mo.isin(bymo.sort_values(ascending=False).index[:2])]["r"].mean()
    exfm = df[~df.mo.isin(["2026-02", "2026-03"])]["r"].mean()
    rob = "ROBUST" if (mean > 0 and p < 0.05 and db2 > 0 and exfm > 0 and (bymo > 0).sum() >= 5) else ""
    print(f"  {label:26s} R={mean:+.4f} p={p:.3f} n={len(df):4d} /day={len(df)/NDAYS:.1f} "
          f"win={ (df['r']>0).mean()*100:3.0f}% mo+={int((bymo>0).sum())}/{len(bymo)} db2={db2:+.4f} exFM={exfm:+.4f} {rob}")


def short(mask):
    d = o[mask].copy(); d["r"] = d["r_short"]; return d
def long_(mask):
    d = o[mask].copy(); d["r"] = d["r_long"]; return d
def book(short_mask, long_mask):   # both-side combined rule
    a = o[short_mask].copy(); a["r"] = a["r_short"]
    b = o[long_mask].copy(); b["r"] = b["r_long"]
    return pd.concat([a, b])


print(f"=== cross-asset direction signals (full universe, {NDAYS} days) ===")
print("\n-- 1m SMT (verified baseline) --")
cell(short(o.struct_smt == -1), "1m SMT SHORT")
cell(long_(o.struct_smt == 1), "1m SMT LONG")
cell(book(o.struct_smt == -1, o.struct_smt == 1), "1m SMT BOTH")

for tf in [5, 15, 30, 60]:
    c = f"xsmt_{tf}m"
    print(f"\n-- {tf}m SMT --")
    cell(short(o[c] == -1), f"{tf}m SMT SHORT")
    cell(long_(o[c] == 1), f"{tf}m SMT LONG")
    cell(book(o[c] == -1, o[c] == 1), f"{tf}m SMT BOTH")

print("\n-- multi-TF agreement (vote = sum of TF signs) --")
cell(book(o.xsmt_vote <= -1, o.xsmt_vote >= 1), "vote |>=1| BOTH")
cell(book(o.xsmt_vote <= -2, o.xsmt_vote >= 2), "vote |>=2| BOTH")
cell(short(o.xsmt_vote <= -2), "vote<=-2 SHORT")
cell(long_(o.xsmt_vote >= 2), "vote>=2 LONG")

print("\n-- relative-strength divergence (30m) --")
q = o["rs_div_30m"].quantile([0.2, 0.8])
cell(short(o.rs_div_30m <= q[0.2]), "RS weak->SHORT")
cell(long_(o.rs_div_30m >= q[0.8]), "RS strong->LONG")
cell(short(o.rs_div_30m >= q[0.8]), "RS strong->SHORT(fade)")
cell(long_(o.rs_div_30m <= q[0.2]), "RS weak->LONG(fade)")
