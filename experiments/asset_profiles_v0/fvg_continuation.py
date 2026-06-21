"""Setup #2 for the alpha-discovery engine: FVG-CONTINUATION (the user's idea).

Bullish FVG (3-candle up-gap: low[i] > high[i-2]) leaves an imbalance zone [high[i-2], low[i]]. Price later
retraces DOWN into the zone (discount), then a confirmation -- a bar CLOSES back above the zone top (expansion
resuming) -- triggers a long. Stop just below the retrace low; trail 1R. A CONTINUATION setup (the FVG is
evidence of an up-impulse), the opposite character to sweep-reclaim (a fade). Invalidate if price closes through
the zone bottom before reclaiming. Same honest 4-filter validation + tick cost as the sweep-reclaim harness.

Run: backend/.venv/Scripts/python.exe experiments/asset_profiles_v0/fvg_continuation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "backend")
from app.data.reader import read_bars  # noqa: E402

START, END = "2023-01-01", "2026-04-23"
CUT = pd.Timestamp("2026-02-15", tz="UTC")
MAXWAIT, HOLD, TRAIL = 48, 48, 1.0        # FVG valid for 4h; 4h hold; 1R trail (5m bars)
TICK = {"NQ.c.0": 0.25, "RTY.c.0": 0.10, "ES.c.0": 0.25, "RB.c.0": 0.0001, "HO.c.0": 0.0001,
        "CL.c.0": 0.01, "ZN.c.0": 1 / 64, "6E.c.0": 0.00005, "GC.c.0": 0.10}
SYMS = ["RB.c.0", "HO.c.0", "NQ.c.0", "ES.c.0", "CL.c.0"]


def load(sym: str) -> pd.DataFrame:
    b = read_bars(symbol=sym, timeframe="5m", start=START, end=END)
    b = b.set_index("ts_event")[["open", "high", "low", "close"]].sort_index()
    return b[~b.index.duplicated(keep="first")]


def sim(b: pd.DataFrame, maxwait: int, hold: int, trail: float) -> pd.DataFrame:
    h, l, c = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    ts, n = b.index, len(b)
    rows = []
    for i in range(2, n):
        if not (l[i] > h[i - 2]):                          # bullish FVG (up-gap)
            continue
        zt, zb = l[i], h[i - 2]                             # zone top / bottom
        fired, tap_low, e_idx = False, np.inf, -1
        for t in range(i + 1, min(i + maxwait, n - 1) + 1):
            if l[t] <= zt:                                 # retraced into the zone
                fired = True
            if fired:
                tap_low = min(tap_low, l[t])
                if l[t] < zb:                              # closed through bottom -> FVG broken
                    break
                if c[t] > zt:                              # expansion back out -> entry
                    e_idx = t
                    break
        if e_idx < 0:
            continue
        entry, stop = c[e_idx], tap_low - 0.0              # stop at the retrace low
        risk = entry - stop
        if risk <= 0:
            continue
        end = min(e_idx + hold, n - 1)
        peak, tstop, r, xi = entry, stop, None, end
        for t in range(e_idx + 1, end + 1):
            if l[t] <= tstop:
                r, xi = (tstop - entry) / risk, t
                break
            peak = max(peak, h[t])
            tstop = max(tstop, peak - trail * risk)
        rows.append((ts[e_idx], (c[end] - entry) / risk if r is None else r, risk, entry, e_idx, xi))
    return pd.DataFrame(rows, columns=["date", "r", "risk", "entry", "ei", "xi"])


def nonoverlap(tr: pd.DataFrame) -> pd.DataFrame:
    """Greedily keep only trades that don't overlap a still-open one (one position at a time)."""
    keep, last = [], -1
    for idx, ei, xi in zip(tr.index, tr["ei"], tr["xi"]):
        if ei >= last:
            keep.append(idx)
            last = xi
    return tr.loc[keep]


def net(tr: pd.DataFrame, ct: float, tick: float) -> pd.Series:
    return tr["r"] - ct * tick / tr["risk"]


def main() -> int:
    for sym in SYMS:
        b = load(sym)
        tick = TICK[sym]
        tr = sim(b, MAXWAIT, HOLD, TRAIL)
        te = tr[tr["date"] >= CUT]
        if len(tr) < 100:
            print(f"\n===== {sym} =====  only {len(tr)} FVG trades (skip)"); continue
        ym = tr["date"].dt.tz_localize(None).dt.to_period("M")
        monthly = net(tr, 2, tick).groupby(ym).mean()
        print(f"\n===== {sym} =====  {len(tr)} trades ({len(te)} OOS)")
        print("  F1 COST (OOS):  " + "  ".join(f"{ct}tk={net(te, ct, tick).mean():+.3f}" for ct in (0, 1, 2, 3)))
        print("  F2 GRID (full net@2tk):")
        for mw in (24, 48, 96):
            cells = [f"trail{tl}={net(sim(b, mw, HOLD, tl), 2, tick).mean():+.3f}" for tl in (0.5, 1.0, 2.0)]
            print(f"    maxwait{mw:>3}: " + "   ".join(cells))
        print(f"  F3 STABILITY: {(monthly > 0).sum()}/{len(monthly)} months+ (net@2tk), mean {monthly.mean():+.3f}")
        no = nonoverlap(tr)
        no_te = no[no["date"] >= CUT]
        no_m = net(no, 2, tick).groupby(no["date"].dt.tz_localize(None).dt.to_period("M")).mean()
        print(f"  F5 NON-OVERLAP (1 position at a time): {len(no)} trades ({len(no_te)} OOS)  "
              f"E[R]={net(no, 2, tick).mean():+.3f}  months+={(no_m > 0).sum()}/{len(no_m)}  "
              f"OOS E[R]={net(no_te, 2, tick).mean():+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
