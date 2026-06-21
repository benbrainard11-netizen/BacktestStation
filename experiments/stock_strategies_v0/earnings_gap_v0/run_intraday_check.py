"""Intraday fill-realism check: does our daily proxy (buy gap-day OPEN, fixed-8% stop) fairly
represent the doc's REAL mechanic (enter when a 1-min candle breaks the FIRST candle's high;
stop = low-of-day at entry)? Runs on the NDX names that have 1-min data, 2023-06+ (the theta
floor). Reconciles raw m1 prices into the adjusted-daily space via the gap-day factor.
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common as C  # noqa: E402
import loaders as L  # noqa: E402

COST = 0.015
BUF = 0.02
m1_names = {p.stem for p in C.STOCKS_M1.glob("*.parquet")}
feat = pd.read_parquet(Path(__file__).resolve().parent / "out" / "features.parquet")
feat["entry_dt"] = pd.to_datetime(feat["entry_dt"])
gaps = feat[(feat["ticker"].isin(m1_names)) & (feat["entry_dt"] >= "2023-06-01")].copy()
print(f"NDX doc-setup gaps with 1-min data (2023-06+): {len(gaps)} over {gaps['ticker'].nunique()} names\n")


def forward_R(d, gi, entry, stop, trail="ma20"):
    risk = entry - stop
    if risk <= 0:
        return None
    o, c, lo, ma = d["open"].to_numpy(), d["close"].to_numpy(), d["low"].to_numpy(), d[trail].to_numpy()
    for j in range(gi + 1, len(d)):
        if lo[j] <= stop:
            fill = o[j] if o[j] < stop else stop
            return (fill - COST - entry) / risk
        if (j - gi) >= 3 and not np.isnan(ma[j]) and c[j] < ma[j]:
            return (c[j] - COST - entry) / risk
    return (c[-1] - COST - entry) / risk


rows = []
for r in gaps.itertuples():
    try:
        d = L.with_mas(L.load_daily(r.ticker)).reset_index(drop=True)
        bars = L.load_m1(r.ticker, day=r.entry_dt)
    except Exception:
        continue
    gi = d.index[d["dt"] == r.entry_dt]
    if not len(gi) or len(bars) < 5:
        continue
    gi = int(gi[0])
    sess_open = float(bars["open"].iloc[0])
    factor = float(d["open"].iloc[gi]) / sess_open if sess_open else 1.0
    # daily proxy: enter at adjusted open, fixed 8% stop
    e_d = float(d["open"].iloc[gi]) + COST
    R_daily = forward_R(d, gi, e_d, e_d * 0.92)
    # intraday: first 1-min candle high -> trigger; stop = LOD at entry
    fc_high = float(bars["high"].iloc[0])
    after = bars.iloc[1:]
    trig = after[after["high"] >= fc_high]
    triggered = len(trig) > 0
    R_intra, payup, stop_pct = None, np.nan, np.nan
    if triggered:
        k = trig.index[0]
        entry_raw = fc_high
        lod_raw = float(bars.loc[:k, "low"].min())
        payup = entry_raw / sess_open - 1
        stop_pct = (entry_raw - lod_raw) / entry_raw
        # same-day stop? any bar after entry with low <= lod-buf
        same_day = (bars.loc[k:, "low"] <= lod_raw - BUF).any()
        e_i = entry_raw * factor + COST
        s_i = (lod_raw - BUF) * factor
        if same_day:
            R_intra = (s_i - COST - e_i) / (e_i - s_i)
        else:
            R_intra = forward_R(d, gi, e_i, s_i)
    rows.append(dict(ticker=r.ticker, triggered=triggered, payup=payup, stop_pct=stop_pct,
                     R_daily=R_daily, R_intra=R_intra))

df = pd.DataFrame(rows)
wc = lambda s: np.clip(s.dropna(), -1.5, 15).mean()
tg = df[df["triggered"]]
print(f"=== entry filter ===")
print(f"  triggered (broke 1st-candle high): {df['triggered'].mean()*100:.0f}%  "
      f"({(~df['triggered']).sum()} gaps faded -> no entry)")
print(f"  avg pay-up vs open: {tg['payup'].mean()*100:+.2f}%  | avg intraday stop: {tg['stop_pct'].mean()*100:.1f}% (vs fixed 8%)")
print(f"\n=== realized R (winsorized mean) ===")
print(f"  DAILY proxy (all {len(df)} gaps, open entry + 8% stop): {wc(df['R_daily']):+.3f}")
print(f"  DAILY proxy on the TRIGGERED subset:                    {wc(tg['R_daily']):+.3f}")
print(f"  INTRADAY (triggered, 1st-candle entry + LOD stop):      {wc(tg['R_intra']):+.3f}")
print(f"\nREAD: compare INTRADAY vs DAILY-on-triggered (same gaps). 'triggered' filter effect =")
print("daily-triggered vs daily-all. If intraday >= daily proxy, the daily test wasn't flattering.")
