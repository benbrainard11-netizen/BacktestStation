"""Multi-timeframe (fractal) confluence test for sweep-reclaim -- the first brick of the MTF feature library.

The LTF setup is a bullish sweep->reclaim (buy the dip). The confluence filter: only take it when the HIGHER
timeframe trend is UP -- the PO3 "HTF + LTF same direction" / buy-dips-in-uptrends idea. Question: does HTF
alignment (a) improve the validated edges (RB/HO), and (b) RESCUE the marginal/failed ones (NQ/CL/RTY)? And is
the HTF-DOWN subset clearly worse (which would confirm the HTF bias carries real signal, not noise)?

HTF bias at the reclaim bar = trailing H-bar return (12h/24h/48h on 5m bars), known at entry -> no lookahead.
Honest tick cost (net@2tk). Run on read_bars 5m, same mechanics as the validated harness.

Run: backend/.venv/Scripts/python.exe experiments/asset_profiles_v0/mtf_sweep_reclaim.py
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
LB, K, HOLD, TRAIL = 48, 6, 48, 1.0
TICK = {"NQ.c.0": 0.25, "RTY.c.0": 0.10, "RB.c.0": 0.0001, "HO.c.0": 0.0001, "CL.c.0": 0.01}
SYMS = ["RB.c.0", "HO.c.0", "NQ.c.0", "CL.c.0", "RTY.c.0"]
HTFS = [144, 288, 576]   # 12h / 24h / 48h trailing trend on 5m bars


def load(sym: str) -> pd.DataFrame:
    b = read_bars(symbol=sym, timeframe="5m", start=START, end=END)
    b = b.set_index("ts_event")[["open", "high", "low", "close"]].sort_index()
    return b[~b.index.duplicated(keep="first")]


def sim(b: pd.DataFrame) -> pd.DataFrame:
    h, l, c = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    ts, n = b.index, len(b)
    lvl = b["low"].rolling(LB, min_periods=LB // 2).min().shift(1).to_numpy()
    pen = l < lvl
    starts = np.where((pen & ~np.r_[False, pen[:-1]]) & ~np.isnan(lvl))[0]
    rows = []
    for t0 in starts:
        L = lvl[t0]
        t_r = next((t for t in range(t0, min(t0 + K, n - 1) + 1) if c[t] > L), -1)
        if t_r < 0:
            continue
        entry, stop = c[t_r], l[t0:t_r + 1].min()
        risk = entry - stop
        if risk <= 0:
            continue
        end = min(t_r + HOLD, n - 1)
        peak, tstop, r = entry, stop, None
        for t in range(t_r + 1, end + 1):
            if l[t] <= tstop:
                r = (tstop - entry) / risk
                break
            peak = max(peak, h[t])
            tstop = max(tstop, peak - TRAIL * risk)
        rows.append((ts[t_r], (c[end] - entry) / risk if r is None else r, risk, entry, t_r))
    return pd.DataFrame(rows, columns=["date", "r", "risk", "entry", "i"])


def stats(tr: pd.DataFrame, tick: float) -> str:
    if len(tr) < 30:
        return f"n={len(tr):4} (too few)"
    nr = tr["r"] - 2 * tick / tr["risk"]                       # net @ 2 ticks
    m = nr.groupby(tr["date"].dt.tz_localize(None).dt.to_period("M")).mean()
    return f"n={len(tr):4}  E[R]={nr.mean():+.3f}  months+={(m > 0).sum():2}/{len(m):2}"


def main() -> int:
    for sym in SYMS:
        b = load(sym)
        c = b["close"].to_numpy()
        tr = sim(b)
        tick = TICK[sym]
        print(f"\n===== {sym} =====")
        print(f"  base (all reclaims):  {stats(tr, tick)}")
        idx = tr["i"].to_numpy()
        for H in HTFS:
            htf = np.where(idx >= H, c[idx] - c[np.maximum(idx - H, 0)], np.nan)
            up, dn = tr[htf > 0], tr[htf <= 0]
            print(f"  HTF {H*5//60:>2}h:  UP  {stats(up, tick)}")
            print(f"           DOWN {stats(dn, tick)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
