"""Can we find the explosion regime BEFORE it happens? The trailing gate misses the turns (the best
months erupt out of cold). Hypothesis: explosions are the rocket off a market WASHOUT -> a LEADING
signal = market washed out + turning up + breadth thrust. Compute real market internals (SPY washout/
recovery/vol + UNIVERSE breadth) at end of each month, LAG them 1 month, and test whether they predict
NEXT month's explosion regime -- and crucially whether they fire before the big turns (2020-03, 2023-11,
2025-04) while staying QUIET through 2022's fake bounces. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

POLY = Path(r"D:\data\processed\stocks\polygon")
HERE = Path(__file__).resolve().parent

# --- explosion monthly target (top-decile R + explosion rate) ---
oos = pd.read_parquet(HERE / "out" / "explosion_oos.parquet")
top = oos[oos["dec"] == 9].copy()
top["ym"] = pd.to_datetime(top["date"].astype(int).astype(str), format="%Y%m%d").dt.to_period("M")
expl = top.groupby("ym").agg(R=("trade_R", "mean"), rate=("expl40", "mean"), n=("trade_R", "size"))
expl = expl[expl["n"] >= 15]

# --- internals from daily ---
print("computing market internals...")
df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
df["dt"] = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d")
spy = df[df["ticker"] == "SPY"].set_index("dt")["close"].sort_index()
S = pd.DataFrame(index=spy.index)
S["spy_dd"] = spy / spy.rolling(126).max() - 1
S["spy_ret21"] = spy / spy.shift(21) - 1
S["spy_above20"] = (spy > spy.rolling(20).mean()).astype(int)
vol21 = spy.pct_change().rolling(21).std() * np.sqrt(252)
S["spy_vol21"] = vol21
S["vol_falling"] = (vol21 < vol21.shift(10)).astype(int)

# universe breadth (liquid stocks)
cs = set(pd.read_parquet(POLY / "meta.parquet")["ticker"])
u = df[df["ticker"].isin(cs)].copy()
u["dvol"] = u["close"] * u["volume"]
parts = []
for t, g in u.sort_values("dt").groupby("ticker", sort=False):
    c = g["close"]; h = g["high"]
    liq = (c >= 5) & ((c * g["volume"]).rolling(20).mean() >= 5e6)
    parts.append(pd.DataFrame({"dt": g["dt"], "above50": (c > c.rolling(50).mean()).astype(float),
                               "nh20": (h >= h.rolling(20).max()).astype(float),
                               "ret21": c / c.shift(21) - 1, "liq": liq.astype(float)}))
B = pd.concat(parts, ignore_index=True)
B = B[B["liq"] == 1]
br = B.groupby("dt").agg(breadth50=("above50", "mean"), breadth_nh=("nh20", "mean"),
                         breadth_ret=("ret21", "median"))
S = S.join(br)

# end-of-month snapshot of internals; lag 1 month -> predicts NEXT month explosion
M = S.resample("ME").last()
M.index = M.index.to_period("M")
INT = ["spy_dd", "spy_ret21", "spy_above20", "spy_vol21", "vol_falling", "breadth50", "breadth_nh", "breadth_ret"]
lead = M[INT].shift(1)                                # signal available at start of the month it predicts
J = lead.join(expl[["R", "rate"]], how="inner").dropna()

print(f"\n=== do LAGGED internals predict NEXT-month explosion regime? (n={len(J)} months) ===")
for c in INT:
    rR = spearmanr(J[c], J["R"]).correlation
    rr = spearmanr(J[c], J["rate"]).correlation
    print(f"  {c:13s} -> next-mo R rho {rR:+.2f}   next-mo explosion-rate rho {rr:+.2f}")

print(f"\n=== the TELL: internals at END of the month BEFORE each big explosion month ===")
big = ["2020-03", "2020-11", "2023-11", "2025-04"]
fake22 = ["2022-04", "2022-08", "2022-11"]   # 2022 fake bounces (should stay quiet)
show = ["spy_dd", "spy_ret21", "spy_vol21", "vol_falling", "breadth50", "breadth_nh"]
hdr = "  month(entry)  nextR  " + " ".join(f"{c[:8]:>8s}" for c in show)
print(hdr)
for lbl, months in [("BIG explosion months", big), ("2022 fake bounces", fake22)]:
    print(f"  -- {lbl} --")
    for ym in months:
        p = pd.Period(ym, "M")
        if p not in J.index:
            print(f"  {ym}: (no data)"); continue
        r = J.loc[p]
        print(f"  {ym}   {r['R']:+5.2f}   " + " ".join(f"{r[c]:+8.2f}" for c in show))

# simple leading gate: washed out (dd deep) + recovering (ret21>0 or above20) + breadth not collapsing
g = J.copy()
g["gate"] = ((g["spy_dd"] < -0.05) & (g["spy_ret21"] > 0)) | (g["breadth50"] > 0.6)
on, off = g[g["gate"]], g[~g["gate"]]
print(f"\n=== a simple LEADING gate (washed-out+recovering OR strong breadth), decided BEFORE the month ===")
print(f"  GATE ON : next-mo R {on['R'].mean():+.3f}  ({len(on)} mo, {len(on)/len(g)*100:.0f}% of time)  hot-rate {(on['R']>0).mean()*100:.0f}%")
print(f"  gate OFF: next-mo R {off['R'].mean():+.3f}  ({len(off)} mo)  hot-rate {(off['R']>0).mean()*100:.0f}%")
print(f"  big months caught: {sum(pd.Period(b,'M') in on.index for b in big)}/{sum(pd.Period(b,'M') in J.index for b in big)}")
print("\nREAD: leading internals with rho>~0.3 + gate fires before big months + quiet in 2022 => catchable.")
print("near-zero rho + gate misses the turns / fires in 2022 => the turn isn't predictable (hard wins).")
