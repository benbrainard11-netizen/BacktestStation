"""STACKED FAILURE SWINGS (Ben's idea): over the past 4 30m candles, if the lows fail to make new
lows AND stack close together, that cluster is a liquidity shelf (stops sit just under it) -> a
stop-run/target where sweep+reclaim fires. Mirror for highs. Dynamic (rolls each candle), legal
(uses only completed candles). Injected into the reclaim engine on the indices.

"close together" = the 4 lows span <= STACK_FRAC * (median 30m candle range) -> adapts per symbol/regime.
Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/stacked_failure_legal.py
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

SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0"]
START, END = dt.date(2025, 5, 1), dt.date(2026, 6, 9)
TF_MIN = 30        # candle TF
N_BACK = 4         # past N candles
STACK_FRAC = 0.5   # stacked if span <= this * median 30m range
_NS = 1_000_000_000
_ORIG = LB.day_levels
FAMS = ["eqlow_stack", "eqhigh_stack"]


def patched_day_levels(b, daily, day, tick):
    out = _ORIG(b, daily, day, tick)
    m = b.rth & (b.et_date == day)
    if m.sum() < 40:
        return out
    idx = pd.DatetimeIndex(pd.to_datetime(b.ts[m], utc=True))
    df = pd.DataFrame({"high": b.h[m], "low": b.l[m]}, index=idx)
    c = df.resample(f"{TF_MIN}min", label="left", closed="left").agg({"high": "max", "low": "min"}).dropna()
    if len(c) < N_BACK:
        return out
    tol = STACK_FRAC * (c["high"] - c["low"]).median()
    h, l = c["high"].to_numpy(float), c["low"].to_numpy(float)
    starts = c.index.asi8
    rth_end_ns = LB.et_ns(day, LB.RTH_END)
    seen_lo, seen_hi = set(), set()
    for i in range(N_BACK - 1, len(c)):
        close_ns = int(starts[i]) + TF_MIN * 60 * _NS
        if close_ns > rth_end_ns:
            continue
        lows, highs = l[i - N_BACK + 1:i + 1], h[i - N_BACK + 1:i + 1]
        if lows.max() - lows.min() <= tol:  # stacked failure LOWS -> liquidity shelf below
            px = float(lows.min())
            k = round(px / tick)
            if k not in seen_lo:
                seen_lo.add(k)
                out.append(dict(level_family="eqlow_stack", level_type="eqlow", side="low",
                                level_price=px, known_ns=close_ns, search_ns=close_ns))
        if highs.max() - highs.min() <= tol:  # stacked failure HIGHS -> liquidity shelf above
            px = float(highs.max())
            k = round(px / tick)
            if k not in seen_hi:
                seen_hi.add(k)
                out.append(dict(level_family="eqhigh_stack", level_type="eqhigh", side="high",
                                level_price=px, known_ns=close_ns, search_ns=close_ns))
    return out


LB.day_levels = patched_day_levels


def main() -> int:
    parts = []
    for sym in SYMBOLS:
        res = LB.run_symbol_year(sym, START, END)
        if len(res):
            res = res[res["level_family"].isin(FAMS)].copy()
            parts.append(res)
        print(f"  {sym}: {len(res) if len(res) else 0} stacked-failure attempts", flush=True)
    df = pd.concat(parts, ignore_index=True)
    out = LB.RUNS / "stacked_failure_full.parquet"
    df.to_parquet(out, index=False)
    ent = df[df["status"] == "entered"]
    print(f"\nwrote {out}: {len(df)} attempts, {len(ent)} entered")
    for fam, g in ent.groupby("level_family"):
        x = pd.to_numeric(g["trail_2R"], errors="coerce").dropna()
        print(f"  {fam:14s} entered={len(g):5d}  raw meanR={x.mean():+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
