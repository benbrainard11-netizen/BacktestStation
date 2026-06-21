"""New level FAMILIES through the honest reclaim engine, to raise frequency at the same quality bar.
Wave 1: weekly_open + monthly_open (Ben weights opens heavily). Bar-computable, legal: the W/M open
is the 09:30 open of the first session of the week/month (known once that session opened); the SIDE
is set by today's 09:30 open vs the W/M open (causal, same logic as daily_gap). Produces reclaim
entries with the SAME schema as legal_bars_full so flow_at_scale/zone can extract MBO flow on them.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/new_levels_legal.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "backend"))
import legal_reclaim_bars as LB  # noqa: E402

SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0"]  # liquid-3 (RTY edge fails, thin book)
START, END = dt.date(2026, 1, 1), dt.date(2026, 6, 9)
_ORIG = LB.day_levels


def patched_day_levels(b, daily, day, tick):
    out = _ORIG(b, daily, day, tick)
    days = daily.index
    if day not in days:
        return out
    rth_ns = LB.et_ns(day, LB.RTH_START)
    topen = float(daily.loc[day, "open"])
    # weekly open = 09:30 open of the first session of this ISO week (Mon-anchored)
    wk_start = day - dt.timedelta(days=day.weekday())
    wk = [d for d in days if wk_start <= d <= day]
    if wk:
        wopen = float(daily.loc[wk[0], "open"])
        side = "low" if topen > wopen else "high"  # level is below today's open => support
        out.append(dict(level_family="weekly_open", level_type="wopen", side=side,
                        level_price=wopen, known_ns=rth_ns, search_ns=rth_ns))
    # monthly open = 09:30 open of the first session of this calendar month
    mo = [d for d in days if d.year == day.year and d.month == day.month and d <= day]
    if mo:
        mopen = float(daily.loc[mo[0], "open"])
        side = "low" if topen > mopen else "high"
        out.append(dict(level_family="monthly_open", level_type="mopen", side=side,
                        level_price=mopen, known_ns=rth_ns, search_ns=rth_ns))
    return out


LB.day_levels = patched_day_levels


def main() -> int:
    parts = []
    for sym in SYMBOLS:
        res = LB.run_symbol_year(sym, START, END)
        if len(res):
            res = res[res["level_family"].isin(["weekly_open", "monthly_open"])].copy()
            parts.append(res)
        n = int((res["level_family"].isin(["weekly_open", "monthly_open"])).sum()) if len(res) else 0
        print(f"  {sym}: {n} new-open attempts", flush=True)
    df = pd.concat(parts, ignore_index=True)
    out = LB.RUNS / "new_levels_full.parquet"
    df.to_parquet(out, index=False)
    ent = df[df["status"] == "entered"]
    print(f"\nwrote {out}: {len(df)} attempts, {len(ent)} entered")
    for fam, g in ent.groupby("level_family"):
        x = pd.to_numeric(g["trail_2R"], errors="coerce").dropna()
        print(f"  {fam:14s} entered={len(g):4d}  raw reaction meanR={x.mean():+.3f} (pre-orderflow)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
