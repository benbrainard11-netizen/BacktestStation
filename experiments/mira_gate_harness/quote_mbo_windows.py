"""A3 final step: Databento cost quote for candidate-anchored MBO windows (2025 sample week)
vs full days, extrapolated to the 2015-2026 universe. Entry shape: trig-15m..trig+2m;
management shape: trig-15m..trig+75m. Overlapping windows merged per symbol.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/quote_mbo_windows.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import databento as db
import pandas as pd

HERE = Path(__file__).resolve().parent
DS = pd.read_parquet(HERE / "data" / "sample2025.parquet")
DS["t"] = pd.to_datetime(DS["trigger_ts_utc"], utc=True)
client = db.Historical(key=os.environ["DATABENTO_API_KEY"])


def merged(pre_min: int, post_min: int) -> list:
    out = []
    for sym, g in DS.groupby(DS["symbol"].astype(str)):
        ws = sorted((t - pd.Timedelta(minutes=pre_min), t + pd.Timedelta(minutes=post_min)) for t in g["t"])
        cur = list(ws[0])
        for lo, hi in ws[1:]:
            if lo <= cur[1]:
                cur[1] = max(cur[1], hi)
            else:
                out.append((sym, *cur)); cur = [lo, hi]
        out.append((sym, *cur))
    return out


def get_cost_retry(**kw) -> float | None:
    import time
    for wait in (0, 5, 15, 30):
        if wait:
            time.sleep(wait)
        try:
            return client.metadata.get_cost(dataset="GLBX.MDP3", stype_in="continuous", schema="mbo", **kw)
        except Exception as e:
            last = e
    print(f"  SKIP window after retries: {last}", flush=True)
    return None


def quote(shape: str, pre: int, post: int) -> float:
    import time
    total, quoted = 0.0, 0
    wins = merged(pre, post)
    for sym, lo, hi in wins:
        c = get_cost_retry(symbols=[sym], start=lo.isoformat(), end=hi.isoformat())
        if c is not None:
            total += c
            quoted += 1
        time.sleep(0.4)  # throttle — their gateway is 504ing today
    share = quoted / len(wins) if wins else 1.0
    est = (total / share) if share else float("nan")
    mins = sum((hi - lo).total_seconds() / 60 for _, lo, hi in wins)
    print(f"{shape}: {quoted}/{len(wins)} windows quoted, {mins:.0f} min total, cost=${total:.2f} "
          f"(scaled ${est:.2f}) -> 2015-2026 (~560 wks): ~${est * 560:,.0f}", flush=True)
    return est


print(f"sample: {len(DS)} candidates, week 2025-03-10..14")
quote("entry  (t-15m..t+2m) ", 15, 2)
quote("manage (t-15m..t+75m)", 15, 75)
full = get_cost_retry(symbols=["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"],
                      start="2025-03-10", end="2025-03-15")
if full is not None:
    print(f"reference full-days same week: ${full:.2f} -> 2015-2026 ~${full * 560:,.0f}")
