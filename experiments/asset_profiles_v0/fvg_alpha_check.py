"""Alpha-vs-beta check for the FVG-continuation edge -- the most important skeptic test.

The setup is LONG-only. If RB/HO simply trended UP 2023-26, a long dip-buy setup prints money by capturing
DRIFT (beta), not timing skill (alpha). Two tells:
  1. buy-and-hold drift (did the asset just go up?)
  2. the SHORT mirror (bearish FVG -> continuation down). If shorts ALSO profit -> real both-ways edge (alpha).
     If only longs win -> it's directional beta wearing a setup costume.
Same FVG mechanics, mirrored. Net @ 2 ticks.

Run: backend/.venv/Scripts/python.exe experiments/asset_profiles_v0/fvg_alpha_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "backend")
from app.data.reader import read_bars  # noqa: E402

START, END = "2023-01-01", "2026-04-23"
MAXWAIT, HOLD, TRAIL = 48, 48, 1.0
TICK = {"NQ.c.0": 0.25, "ES.c.0": 0.25, "RB.c.0": 0.0001, "HO.c.0": 0.0001, "CL.c.0": 0.01}
SYMS = ["RB.c.0", "HO.c.0", "NQ.c.0", "ES.c.0", "CL.c.0"]


def load(sym: str) -> pd.DataFrame:
    b = read_bars(symbol=sym, timeframe="5m", start=START, end=END)
    b = b.set_index("ts_event")[["open", "high", "low", "close"]].sort_index()
    return b[~b.index.duplicated(keep="first")]


def sim(b: pd.DataFrame, side: int) -> pd.DataFrame:
    h, l, c = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    n = len(b)
    rows = []
    for i in range(2, n):
        if side == 1 and not (l[i] > h[i - 2]):            # bullish FVG (up-gap)
            continue
        if side == -1 and not (h[i] < l[i - 2]):           # bearish FVG (down-gap)
            continue
        ztrig = l[i] if side == 1 else h[i]                # the level price must reclaim back across
        zbreak = h[i - 2] if side == 1 else l[i - 2]       # invalidation (far side of the gap)
        fired, tap, e = False, None, -1
        for t in range(i + 1, min(i + MAXWAIT, n - 1) + 1):
            into = l[t] <= ztrig if side == 1 else h[t] >= ztrig
            fired = fired or into
            if not fired:
                continue
            tap = (l[t] if side == 1 else h[t]) if tap is None else (
                min(tap, l[t]) if side == 1 else max(tap, h[t]))
            broke = l[t] < zbreak if side == 1 else h[t] > zbreak
            if broke:
                break
            if (c[t] > ztrig) if side == 1 else (c[t] < ztrig):
                e = t
                break
        if e < 0:
            continue
        entry = c[e]
        risk = (entry - tap) if side == 1 else (tap - entry)
        if risk <= 0:
            continue
        end = min(e + HOLD, n - 1)
        peak, tstop, r = entry, tap, None
        for t in range(e + 1, end + 1):
            hit = l[t] <= tstop if side == 1 else h[t] >= tstop
            if hit:
                r = (tstop - entry) / risk if side == 1 else (entry - tstop) / risk
                break
            if side == 1:
                peak = max(peak, h[t])
                tstop = max(tstop, peak - TRAIL * risk)
            else:
                peak = min(peak, l[t])
                tstop = min(tstop, peak + TRAIL * risk)
        if r is None:
            r = (c[end] - entry) / risk if side == 1 else (entry - c[end]) / risk
        rows.append((r, risk, entry))
    return pd.DataFrame(rows, columns=["r", "risk", "entry"])


def er(tr: pd.DataFrame, tick: float) -> float:
    return float((tr["r"] - 2 * tick / tr["risk"]).mean()) if len(tr) else float("nan")


def main() -> int:
    print(f"{'sym':8} {'drift%':>8} {'LONG E[R]':>10} {'nL':>6} {'SHORT E[R]':>11} {'nS':>6}   verdict")
    for sym in SYMS:
        b = load(sym)
        tick = TICK[sym]
        drift = float(np.log(b["close"].iloc[-1] / b["close"].iloc[0]) * 100)
        lo, sh = sim(b, 1), sim(b, -1)
        elo, esh = er(lo, tick), er(sh, tick)
        verdict = ("REAL (both sides +)" if elo > 0.03 and esh > 0.03 else
                   "BETA (long-only)" if elo > 0.03 >= esh else
                   "no edge")
        print(f"{sym:8} {drift:+8.0f} {elo:+10.3f} {len(lo):6} {esh:+11.3f} {len(sh):6}   {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
