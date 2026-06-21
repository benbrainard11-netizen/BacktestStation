"""How accurate is the long-history reconstruction? Quantify the two error sources.

(1) BASIS error — the long-history method maps an SPX wall to ES using ONE prior-day
    basis for the whole next day; the true ES-SPX basis drifts intraday. Measure
    |prior-day basis  -  true intraday basis| in points on the overlap window.
(2) WALL consistency — deep EOD walls vs the audited intraday-repriced walls, points.
Both compared against a ~19pt typical target, so an error of N pts ~ N/19 of a target.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import data_io as D

panels = D.load_panels()
gex = panels["gex"]
gex["dprev"] = None
walls = pd.read_parquet(C.WALLS_DEEP)
walls["d"] = pd.to_datetime(walls["date"].astype(int).astype(str), format="%Y%m%d").dt.date
wl = walls.set_index("d")

# ---- (1) BASIS error: prior-day-close basis vs true intraday basis ----
days = sorted(gex["d"].unique())
errs = []
for i in range(1, len(days)):
    day, prev = days[i], days[i - 1]
    gd = gex[gex["d"] == day]
    gp = gex[gex["d"] == prev]
    if gd.empty or gp.empty:
        continue
    # prior-day basis at ~16:00: prior ES close - prior SPX spot
    pbar = D.load_bars(prev)
    if pbar is None:
        continue
    p16 = pbar[pbar["et"] <= D.et_ts(prev, 16 * 3600_000) - pd.Timedelta(minutes=1)]
    pspot = gp[gp["ms_of_day"] <= 16 * 3600_000]
    if p16.empty or pspot.empty:
        continue
    prior_basis = float(p16["close"].iloc[-1]) - float(pspot["spot"].iloc[-1])
    # true intraday basis at 10/12/14 ET on `day`
    ebar = D.load_bars(day)
    if ebar is None:
        continue
    for hh in (10, 12, 14):
        ms = hh * 3600_000
        g = gd[gd["ms_of_day"] <= ms]
        eb = ebar[ebar["et"] <= D.et_ts(day, ms) - pd.Timedelta(minutes=1)]
        if g.empty or eb.empty:
            continue
        true_basis = float(eb["close"].iloc[-1]) - float(g["spot"].iloc[-1])
        errs.append(abs(true_basis - prior_basis))

errs = np.array(errs)
print(f"(1) BASIS mapping error |prior-day basis - true intraday basis|, n={len(errs)}:")
print(f"    median {np.median(errs):.1f} pts | mean {errs.mean():.1f} | p75 {np.percentile(errs,75):.1f} "
      f"| p90 {np.percentile(errs,90):.1f} | p95 {np.percentile(errs,95):.1f} | max {errs.max():.1f}")
print(f"    >5pt: {(errs>5).mean():.0%}   >10pt: {(errs>10).mean():.0%}   (typical target ~19pt)")

# ---- (2) WALL consistency: deep EOD wall vs intraday-repriced wall (same day) ----
diffs_cw, diffs_pw = [], []
for day in days:
    if day not in wl.index:
        continue
    gd = gex[gex["d"] == day]
    if gd.empty:
        continue
    last = gd.iloc[-1]   # near-EOD intraday wall
    diffs_cw.append(abs(float(last["call_wall"]) - float(wl.loc[day, "call_wall"])))
    diffs_pw.append(abs(float(last["put_wall"]) - float(wl.loc[day, "put_wall"])))
dc, dp = np.array(diffs_cw), np.array(diffs_pw)
print(f"\n(2) WALL consistency (deep EOD vs intraday-repriced, same day), n={len(dc)}:")
print(f"    call_wall |diff| median {np.median(dc):.1f} pts | p90 {np.percentile(dc,90):.1f}")
print(f"    put_wall  |diff| median {np.median(dp):.1f} pts | p90 {np.percentile(dp,90):.1f}")
print(f"    call_wall exact match: {(dc==0).mean():.0%}   within 5pt: {(dc<=5).mean():.0%}")
