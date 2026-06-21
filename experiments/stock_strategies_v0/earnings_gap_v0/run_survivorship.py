"""SURVIVORSHIP TEST on the clean Polygon universe (delisted-INCLUDED, common-stock-filtered).
Detects the earnings-gap PROXY (gap 7.5-50% + volume spike + open>prior-high) and compares
forward MARKET-RELATIVE drift (vs SPY) for ACTIVE (survivors) vs DELISTED names. If delisted
gaps drift worse, the survivors-only edge was inflated; the corrected number = the full
(active+delisted) universe. 2021-2026 (Starter 5yr). Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HZ = [5, 10, 20, 40]
POLY = Path(r"D:\data\processed\stocks\polygon")

df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
meta = pd.read_parquet(POLY / "meta.parquet")
cs = set(meta["ticker"])
active = dict(zip(meta["ticker"], meta["active"]))
spy = df[df["ticker"] == "SPY"].set_index("date")["close"].to_dict()   # date_int -> SPY close
df = df[df["ticker"].isin(cs)].sort_values(["ticker", "date"]).reset_index(drop=True)
print(f"common stocks: {df['ticker'].nunique()} ({sum(active.get(t,False) for t in df['ticker'].unique())} active) "
      f"| rows {len(df):,} | {df['date'].min()}..{df['date'].max()}")

rows = []
for t, g in df.groupby("ticker", sort=False):
    if len(g) < 80:
        continue
    o = g["open"].to_numpy(); c = g["close"].to_numpy(); hi = g["high"].to_numpy()
    vol = g["volume"].to_numpy(); dts = g["date"].to_numpy()
    pc, ph = np.roll(c, 1), np.roll(hi, 1)
    gap = o / pc - 1
    avgv = pd.Series(vol).rolling(20).mean().shift(1).to_numpy()
    dvol = pd.Series(c * vol).rolling(20).mean().shift(1).to_numpy()   # 20d avg dollar volume
    act = active.get(t, False)
    for i in range(21, len(g) - max(HZ)):
        # LIQUID-large/mid-cap filter -> closer to the earnings-gap population (drop penny pumps)
        if not (0.075 <= gap[i] <= 0.50) or o[i] <= ph[i] or c[i-1] < 20 or dvol[i] < 1e7 or not (vol[i] >= 1.5 * avgv[i]):
            continue
        sp0 = spy.get(int(dts[i]))
        if not sp0:
            continue
        rec = {"ticker": t, "active": act}
        for H in HZ:
            spH = spy.get(int(dts[i + H]))
            rec[f"x{H}"] = (c[i + H] / o[i] - 1) - (spH / sp0 - 1) if spH else np.nan
        rows.append(rec)

R = pd.DataFrame(rows).dropna(subset=[f"x{H}" for H in HZ])
rng = np.random.default_rng(0)
def ci(d, col):
    vbn = {t: gg[col].to_numpy() for t, gg in d.groupby("ticker")}
    nm = list(vbn)
    if not nm:
        return (np.nan, np.nan)
    b = [np.concatenate([vbn[nm[i]] for i in rng.choice(len(nm), len(nm), True)]).mean() for _ in range(2000)]
    return np.percentile(b, [5, 95])

print(f"\ntotal proxy-gaps: {len(R)}  (active {R['active'].sum()}, delisted {(~R['active']).sum()})\n")
print(f"{'group':18s} {'n':>6} " + " ".join(f"x{H}d_%" for H in HZ) + "  win20%")
for lab, d in [("ALL (clean univ)", R), ("ACTIVE (survivors)", R[R['active']]), ("DELISTED", R[~R['active']])]:
    if not len(d):
        print(f"{lab:18s} 0"); continue
    print(f"{lab:18s} {len(d):6d} " + " ".join(f"{d[f'x{H}'].mean()*100:+5.2f}" for H in HZ)
          + f"  {(d['x20']>0).mean()*100:4.0f}%")
lo, hi = ci(R, "x20"); loa, hia = ci(R[R['active']], "x20")
print(f"\nclean-universe 20d drift: {R['x20'].mean()*100:+.2f}% CI[{lo*100:+.2f},{hi*100:+.2f}]")
print(f"survivors-only  20d drift: {R[R['active']]['x20'].mean()*100:+.2f}% CI[{loa*100:+.2f},{hia*100:+.2f}]")
print(f"SURVIVORSHIP INFLATION (survivors - clean): {(R[R['active']]['x20'].mean()-R['x20'].mean())*100:+.2f}%")
print("\n(compare clean-universe drift to the yfinance survivors-only +1.5%/20d we had.)")
