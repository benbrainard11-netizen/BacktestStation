"""Multi-instrument gamma-conditioned opening drive: NQ + ES + YM + RTY (2019-2026).

Same rule, market-wide SPX gamma conditioner (walls_v2, prior-day, causal): on short-gamma +
lo/mid vol days, FOLLOW the opening drive (09:45), run-it exit (tgt3R), risk=0.5*ATR. If it holds
across all 4 indices over 7 years, that's ~4x the frequency AND stronger evidence (market-wide
mechanism). Bar-level fills. Per-asset + pooled, per-year, controls.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\multi_asset_gamma.py
Output: out/multi_asset_gamma.parquet
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
RNG = np.random.default_rng(53)
OPEN_MS, DEC_MS, EOD_MS = 9 * 3600_000 + 30 * 60_000, 9 * 3600_000 + 45 * 60_000, 16 * 3600_000
RISK_ATR = 0.5
ASSETS = {"NQ": (C.BARS_1M_NQ, 20.0), "ES": (C.BARS_1M, 50.0),
          "YM": (C.BARS_1M_ROOT / "symbol=YM.c.0", 5.0), "RTY": (C.BARS_1M_ROOT / "symbol=RTY.c.0", 50.0)}

# SPX gamma regime, prior-day (causal)
w = pd.read_parquet(OUT / "walls_v2.parquet")
w["d"] = pd.to_datetime(w["date"].astype(int).astype(str), format="%Y%m%d")
w = w.sort_values("d")[["d", "gex_proxy"]]


def rth(root, day):
    df = D.load_bars_sym(root, day)
    if df is None:
        return None
    f = df[(df["et"] >= D.et_ts(day, OPEN_MS)) & (df["et"] < D.et_ts(day, EOD_MS))]
    return f if len(f) else None


def tgt3R(f, entry, direction, risk, comm):
    fwd = f[f["et"] >= D.et_ts(Date.fromisoformat(f["et"].iloc[0].date().isoformat()), DEC_MS)]
    hi, lo, cl = fwd["high"].to_numpy(float), fwd["low"].to_numpy(float), fwd["close"].to_numpy(float)
    if len(cl) < 5:
        return None
    if direction > 0:
        stop, tgt = entry - risk, entry + 3 * risk
        hs = np.argmax(lo <= stop) if (lo <= stop).any() else None
        ht = np.argmax(hi >= tgt) if (hi >= tgt).any() else None
        ex = cl[-1] if hs is None and ht is None else (stop if ht is None else (tgt if hs is None else (stop if hs <= ht else tgt)))
        return (ex - entry) / risk - comm / risk
    stop, tgt = entry + risk, entry - 3 * risk
    hs = np.argmax(hi >= stop) if (hi >= stop).any() else None
    ht = np.argmax(lo <= tgt) if (lo <= tgt).any() else None
    ex = cl[-1] if hs is None and ht is None else (stop if ht is None else (tgt if hs is None else (stop if hs <= ht else tgt)))
    return (entry - ex) / risk - comm / risk


rows = []
for asset, (root, pv) in ASSETS.items():
    comm = C.COMMISSION_RT / pv
    days = sorted(p.name.split("=")[1] for p in root.glob("date=*"))
    days = [d for d in days if "2019-01-01" <= d <= "2026-03-31"]
    atr_tr, prev = D.AtrTracker(), None
    n = 0
    for dstr in days:
        day = Date.fromisoformat(dstr)
        f = rth(root, day)
        if f is None:
            prev = prev
            continue
        atr = atr_tr.atr()
        if atr and prev is not None:
            o = f[f["et"] >= D.et_ts(day, OPEN_MS)]
            dec = f[f["et"] >= D.et_ts(day, DEC_MS)]
            orb = f[(f["et"] >= D.et_ts(day, OPEN_MS)) & (f["et"] < D.et_ts(day, DEC_MS))]
            if len(o) and len(dec) and len(orb) >= 5:
                open0930, entry = float(o["open"].iloc[0]), float(dec["open"].iloc[0])
                or_drive = (entry - open0930) / atr
                if abs(or_drive) > 1e-9:
                    r = tgt3R(f, entry, float(np.sign(or_drive)), RISK_ATR * atr, comm)
                    if r is not None:
                        rows.append({"asset": asset, "date": dstr, "yr": dstr[:4], "atr": atr, "r": r})
                        n += 1
        atr_tr.push_day(f); prev = f
    print(f"{asset}: {n} drive-days")

df = pd.DataFrame(rows)
df["d"] = pd.to_datetime(df["date"])
df = pd.merge_asof(df.sort_values("d"), w, on="d", direction="backward", allow_exact_matches=False).dropna(subset=["gex_proxy"])
df["short_gamma"] = df["gex_proxy"] < 0
df["vol_b"] = df.groupby("asset")["atr"].transform(lambda s: pd.qcut(s, 3, labels=["lo", "mid", "hi"]))
df.to_parquet(OUT / "multi_asset_gamma.parquet")
cell = df[df.short_gamma & (df.vol_b != "hi")]


def boot(r, dates):
    by = {d: r[dates == d] for d in np.unique(dates)}
    bm = np.array([np.concatenate([by[d] for d in RNG.choice(list(by), len(by), True)]).mean() for _ in range(4000)])
    return float(r.mean()), float((bm <= 0).mean())


print("\n### gamma-conditioned opening drive (short-gamma + lo/mid vol, tgt3R) per asset")
for a in ["NQ", "ES", "YM", "RTY"]:
    s = cell[cell.asset == a]
    if len(s) < 25:
        print(f"  {a}: n={len(s)} thin"); continue
    mean, p = boot(s.r.to_numpy(), s.date.to_numpy())
    byyr = s.groupby("yr")["r"].mean()
    print(f"  {a:4s} meanR={mean:+.4f} p={p:.3f} n={len(s)} /day~{len(s)/ s.date.nunique() if s.date.nunique() else 0:.2f} yrs+={int((byyr>0).sum())}/{len(byyr)}")
mean, p = boot(cell.r.to_numpy(), (cell.asset + cell.date).to_numpy())
byyr = cell.groupby("yr")["r"].mean()
ndays = cell.date.nunique()
print(f"\n  POOLED meanR={mean:+.4f} p={p:.3f} n={len(cell)} trades over {ndays} calendar-days "
      f"(~{len(cell)/ndays:.2f}/day) yrs+={int((byyr>0).sum())}/{len(byyr)} drop-best-2={cell[~cell.yr.isin(byyr.sort_values(ascending=False).index[:2])].r.mean():+.4f}")
print("  pooled per-year:", {k: round(v, 3) for k, v in byyr.items()})
