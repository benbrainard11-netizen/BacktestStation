"""Robustness battery for the gamma-conditioned opening-drive edge (best cell).

Best cell = short-gamma (prior-day SPX gex<0) + lo/mid vol, FOLLOW the opening drive, run-it exit.
Checks: per-year, drop-best, day-block bootstrap, PERMUTATION control (does short-gamma day-
selection beat random same-vol days?), and the long-gamma discriminating control.
"""
import sys
from datetime import date as Date
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import data_io as D

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(47)
DEC_MS, EOD_MS = 9 * 3600_000 + 45 * 60_000, 16 * 3600_000
RISK_ATR = 0.5
COMM = C.COMMISSION_RT / C.POINT_VALUE_NQ

od = pd.read_parquet(OUT / "open_dataset.parquet").dropna(subset=["or_drive_atr"]).copy()
od["d"] = pd.to_datetime(od["date"])
w = pd.read_parquet(OUT / "walls_v2.parquet")
w["d"] = pd.to_datetime(w["date"].astype(int).astype(str), format="%Y%m%d")
m = pd.merge_asof(od.sort_values("d"), w[["d", "gex_proxy"]].sort_values("d"),
                  on="d", direction="backward", allow_exact_matches=False).dropna(subset=["gex_proxy"])
m = m[m.or_drive_atr.abs() > 1e-9].reset_index(drop=True)
m["short_gamma"] = m["gex_proxy"] < 0
m["vol_b"] = pd.qcut(m["atr"], 3, labels=["lo", "mid", "hi"])


def sim(day, entry, direction, risk):
    df = D.load_bars_sym(C.BARS_1M_NQ, day)
    if df is None:
        return None
    f = df[(df["et"] >= D.et_ts(day, DEC_MS)) & (df["et"] < D.et_ts(day, EOD_MS))]
    if len(f) < 5:
        return None
    hi, lo, cl = f["high"].to_numpy(float), f["low"].to_numpy(float), f["close"].to_numpy(float)
    res = {}
    for nm, tgtR in [("tgt3R", 3.0), ("holdEOD", None)]:
        if direction > 0:
            stop, tgt = entry - risk, (entry + tgtR * risk if tgtR else np.inf)
            hs = np.argmax(lo <= stop) if (lo <= stop).any() else None
            ht = np.argmax(hi >= tgt) if (hi >= tgt).any() else None
            ex = cl[-1] if hs is None and ht is None else (stop if ht is None else (tgt if hs is None else (stop if hs <= ht else tgt)))
            res[nm] = (ex - entry) / risk - COMM / risk
        else:
            stop, tgt = entry + risk, (entry - tgtR * risk if tgtR else -np.inf)
            hs = np.argmax(hi >= stop) if (hi >= stop).any() else None
            ht = np.argmax(lo <= tgt) if (lo <= tgt).any() else None
            ex = cl[-1] if hs is None and ht is None else (stop if ht is None else (tgt if hs is None else (stop if hs <= ht else tgt)))
            res[nm] = (entry - ex) / risk - COMM / risk
    return res


rows = []
for _, s in m.iterrows():
    r = sim(Date.fromisoformat(s.date), float(s.entry), float(np.sign(s.or_drive_atr)), RISK_ATR * float(s.atr))
    if r:
        rows.append({"date": s.date, "yr": s.yr, "vol_b": str(s.vol_b), "short_gamma": bool(s.short_gamma), **r})
f = pd.DataFrame(rows)
f.to_parquet(OUT / "rob_gamma_trades.parquet")
lomid = f[f.vol_b != "hi"]
cell = lomid[lomid.short_gamma]


def boot(r, dates):
    by = {d: r[dates == d] for d in np.unique(dates)}
    bm = np.array([np.concatenate([by[d] for d in RNG.choice(list(by), len(by), True)]).mean() for _ in range(4000)])
    return float(r.mean()), float((bm <= 0).mean())


for ex in ["tgt3R", "holdEOD"]:
    r = cell[ex].to_numpy(); mean, p = boot(r, cell.date.to_numpy())
    byyr = cell.groupby("yr")[ex].mean()
    db1 = cell[~cell.yr.isin(byyr.sort_values(ascending=False).index[:1])][ex].mean()
    db2 = cell[~cell.yr.isin(byyr.sort_values(ascending=False).index[:2])][ex].mean()
    print(f"\n### BEST CELL exit={ex}: short-gamma + lo/mid vol (n={len(cell)})")
    print(f"  meanR={mean:+.4f} p={p:.3f}  drop-best-1={db1:+.4f} drop-best-2={db2:+.4f}  yrs+={int((byyr>0).sum())}/{len(byyr)}")
    print("  per-year:", {k: round(v, 3) for k, v in byyr.items()})
    # permutation: does short-gamma selection beat random same-size selection WITHIN lo/mid vol?
    pool = lomid[ex].to_numpy(); k = len(cell)
    perm = np.array([RNG.choice(pool, k, replace=False).mean() for _ in range(3000)])
    print(f"  PERMUTATION (random lo/mid-vol days): real={mean:+.4f} vs null mean={perm.mean():+.4f} "
          f"p(null>=real)={ (perm>=mean).mean():.3f}")
    # discriminating: long-gamma + lo/mid vol
    lg = lomid[~lomid.short_gamma][ex]
    print(f"  DISCRIMINATING long-gamma+lo/mid vol meanR={lg.mean():+.4f} (n={len(lg)})  -> short-gamma should beat it")
