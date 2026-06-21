"""Validation battery for the sweep-reclaim-runner -- turn a profile LEAD into a verdict.

Runs the 4 filters that separate a real edge from a backtest mirage, on read_bars data (any symbol, at the
profile's 5m / 4h scale by default):
  F1  COST       -- gross vs a basis-point cost sweep (does it survive realistic crossing?)
  F2  ROBUSTNESS -- grid over level-lookback x trail (BROAD-positive = real; a lone spike = overfit-by-search)
  F3  STABILITY  -- % of months positive over the full history (durable vs one lucky stretch)
  F4  STOP SCALE -- the stop size in price units (does it match a tradeable scale?)
Mechanics (proven): confirmed sweep -> reclaim -> tight wick stop -> 1R trailing exit, honest fills (stop wins
ties), R-normalized so it's comparable across instruments. Cost charged as bps-of-price / risk per trade.

Run: backend/.venv/Scripts/python.exe experiments/asset_profiles_v0/validate_sweep_reclaim.py --symbol RB.c.0
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "backend")
from app.data.reader import read_bars  # noqa: E402

START, END = "2023-01-01", "2026-04-23"
CUT = pd.Timestamp("2026-02-15", tz="UTC")
# Futures cost is ~constant in TICKS (spread crossing), NOT in bps-of-price. bps over-penalizes high-priced
# instruments (1bp of NQ ~= 7 ticks vs a ~1-tick real spread). Charge round-trip ticks instead.
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10, "CL.c.0": 0.01, "BZ.c.0": 0.01,
        "RB.c.0": 0.0001, "HO.c.0": 0.0001, "NG.c.0": 0.001, "6E.c.0": 0.00005, "6A.c.0": 0.00005,
        "ZN.c.0": 1 / 64, "ZB.c.0": 1 / 32, "GC.c.0": 0.10, "SI.c.0": 0.005, "ZC.c.0": 0.25, "ZS.c.0": 0.25}


def load(sym: str, tf: str) -> pd.DataFrame:
    b = read_bars(symbol=sym, timeframe=tf, start=START, end=END)
    b = b.set_index("ts_event")[["open", "high", "low", "close"]].sort_index()
    return b[~b.index.duplicated(keep="first")]


def sim(b: pd.DataFrame, lb: int, k: int, hold: int, trail: float) -> pd.DataFrame:
    h, l, c = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    ts, n = b.index, len(b)
    lvl = b["low"].rolling(lb, min_periods=lb // 2).min().shift(1).to_numpy()
    pen = l < lvl
    starts = np.where((pen & ~np.r_[False, pen[:-1]]) & ~np.isnan(lvl))[0]
    rows = []
    for t0 in starts:
        L = lvl[t0]
        t_r = next((t for t in range(t0, min(t0 + k, n - 1) + 1) if c[t] > L), -1)
        if t_r < 0:
            continue
        entry, stop = c[t_r], l[t0:t_r + 1].min()
        risk = entry - stop
        if risk <= 0:
            continue
        end = min(t_r + hold, n - 1)
        peak, tstop, r = entry, stop, None
        for t in range(t_r + 1, end + 1):
            if l[t] <= tstop:
                r = (tstop - entry) / risk
                break
            peak = max(peak, h[t])
            tstop = max(tstop, peak - trail * risk)
        rows.append((ts[t_r], (c[end] - entry) / risk if r is None else r, risk, entry))
    return pd.DataFrame(rows, columns=["date", "r", "risk", "entry"])


def net(tr: pd.DataFrame, cost_ticks: float, tick: float) -> pd.Series:
    return tr["r"] - cost_ticks * tick / tr["risk"]                 # round-trip cost in ticks / risk (in R)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--tf", default="5m")
    ap.add_argument("--lb", type=int, default=48)      # 48 x 5m = 4h level (the profile scale)
    ap.add_argument("--k", type=int, default=6)        # 30m reclaim window
    ap.add_argument("--hold", type=int, default=48)    # 4h hold
    a = ap.parse_args(argv)
    b = load(a.symbol, a.tf)
    tr = sim(b, a.lb, a.k, a.hold, 1.0)
    te = tr[tr["date"] >= CUT]
    print(f"\n===== {a.symbol} {a.tf} (lb{a.lb}/k{a.k}/hold{a.hold}/trail1) =====")
    tick = TICK.get(a.symbol, 0.25)
    cR = 2 * tick / tr["risk"].median()
    print(f"  {len(b):,} bars {b.index.min().date()}..{b.index.max().date()} | {len(tr)} trades ({len(te)} OOS) | "
          f"tick={tick:g}, 2-tick cost ~= {cR:.3f}R at median risk")

    print("  F1 COST (OOS E[R/trade]):  " + "  ".join(f"{ct}tk={net(te, ct, tick).mean():+.3f}" for ct in (0, 1, 2, 3)))

    print("  F2 ROBUSTNESS grid (full-sample E[R] net@2tk; broad-+ = real, spike = overfit):")
    for lb in (24, 48, 96):
        cells = [f"trail{tl}={net(sim(b, lb, a.k, a.hold, tl), 2, tick).mean():+.3f}" for tl in (0.5, 1.0, 2.0)]
        print(f"    lb{lb:>3} ({lb*5//60}h): " + "   ".join(cells))

    ym = tr["date"].dt.tz_localize(None).dt.to_period("M")
    monthly = net(tr, 2, tick).groupby(ym).mean()
    print(f"  F3 STABILITY: {(monthly > 0).sum()}/{len(monthly)} months positive (net@2tk), mean {monthly.mean():+.3f}")

    print(f"  F4 STOP SCALE (price units): median {tr['risk'].median():.3f}  75th {tr['risk'].quantile(.75):.3f}  "
          f"90th {tr['risk'].quantile(.9):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
