"""SHORT-side test: do earnings gap-DOWNs keep drifting down (mirror of the long PEAD)?
Setup = gap <= -7.5% AND open < prior-day LOW (mirror of the long 'open > prior high').
Market-relative drift from the gap-day open; a SHORT profits when that drift is NEGATIVE.
Model-free first read (no execution build yet). Dev window. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common as C  # noqa: E402
import loaders as L  # noqa: E402

HZ = [5, 10, 20, 40]
DEV_END = pd.Timestamp(C.DEV_END)
spy = L.load_etf("SPY").set_index("dt")
spy_open, spy_close = spy["open"], spy["close"]

earn = L.load_earnings()
rows = []
for t, ev in earn.groupby("ticker"):
    try:
        d = L.load_daily(t)
    except Exception:
        continue
    if len(d) < 130:
        continue
    dt = d["dt"].to_numpy()
    o, lo, c = d["open"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy()
    for _, e in ev.iterrows():
        E = np.datetime64(pd.Timestamp(e["earnings_dt_et"]).tz_localize(None).normalize())
        side = "right" if e["when"] == "AMC" else "left"
        gp = int(np.searchsorted(dt, E, side=side))
        if gp < 61 or gp + max(HZ) >= len(d):
            continue
        gday = pd.Timestamp(dt[gp])
        if gday > DEV_END:
            continue
        rec = {"ticker": t, "dt": gday, "gap": o[gp] / c[gp - 1] - 1,
               "below_low": o[gp] < lo[gp - 1]}
        for H in HZ:
            sp, so = spy_close.get(pd.Timestamp(dt[gp + H])), spy_open.get(gday)
            rec[f"x{H}"] = (c[gp + H] / o[gp] - 1) - (sp / so - 1) if (sp and so) else np.nan
        rows.append(rec)

df = pd.DataFrame(rows).dropna(subset=[f"x{H}" for H in HZ])
df["gap_b"] = pd.cut(df["gap"], [-9, -.15, -.075, -.03, 0, 9],
                     labels=["<-15%", "-15..-7.5%", "-7.5..-3%", "-3..0%", ">0%"])
print(f"{len(df):,} earnings events. Market-relative drift from gap-day OPEN (stock minus SPY), %:\n")
g = df.groupby("gap_b")
out = pd.DataFrame({"n": g.size()})
for H in HZ:
    out[f"x{H}d_%"] = (g[f"x{H}"].mean() * 100).round(2)
print(out.to_string())

setup = df[(df["gap"] <= -0.075) & (df["below_low"])]
rng = np.random.default_rng(0)
def ci(d, col):
    vbn = {t: g[col].to_numpy() for t, g in d.groupby("ticker")}; nm = list(vbn)
    b = [np.concatenate([vbn[nm[i]] for i in rng.choice(len(nm), len(nm), True)]).mean() for _ in range(2000)]
    return np.percentile(b, [5, 95])
print(f"\n=== SHORT setup (gap<=-7.5% & open<prior low), n={len(setup)} ===")
for H in (20, 40):
    lo, hi = ci(setup, f"x{H}")
    drift = setup[f"x{H}"].mean()
    print(f"  {H}d drift {drift*100:+.2f}% CI[{lo*100:+.2f},{hi*100:+.2f}]  ->  "
          f"SHORT edge { -drift*100:+.2f}%  ({'REAL short' if hi < 0 else 'NO short edge (bounces/flat)' if lo < 0 < hi or lo > 0 else 'check'})")
print("\nREAD: short profits only if the drift is significantly NEGATIVE (CI fully < 0).")
print("If drift is ~0 or POSITIVE, down-gaps bounce -> no short edge, stop here.")

# --- the down-gap REVERSAL as a LONG (buy the bounce): is it out-of-period robust? ---
setup = setup.copy(); setup["year"] = pd.to_datetime(setup["dt"]).dt.year
print(f"\n=== DOWN-GAP REVERSAL (buy the bounce) — robustness of the +drift, LONG ===")
for lab, sub in [("2010-2022 (out-of-period)", setup[pd.to_datetime(setup.dt) < '2023-01-01']),
                 ("2023-2025", setup[pd.to_datetime(setup.dt) >= '2023-01-01'])]:
    lo, hi = ci(sub, "x20")
    print(f"  {lab}: n={len(sub)} x20={sub['x20'].mean()*100:+.2f}% CI[{lo*100:+.2f},{hi*100:+.2f}] "
          f"{'REAL' if lo > 0 else 'not sig'}")
g = setup.groupby("year")
py = pd.DataFrame({"n": g.size(), "x20%": (g["x20"].mean() * 100).round(2),
                   "win%": (g["x20"].apply(lambda r: (r > 0).mean()) * 100).round(0)})
print(py.to_string()); print(f"positive years: {(py['x20%'] > 0).sum()}/{len(py)}")
