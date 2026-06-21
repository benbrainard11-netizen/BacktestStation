"""of_accum — ORDER-FLOW accumulation -> breakout study (the real 'model accumulating orders').

Uses the MBP-1 trade tape (aggressor side: 'B'=buy-aggressor lifts ask, 'A'=sell-aggressor hits bid)
to detect ACCUMULATION = a window where heavy volume trades in a tight range WITH a net delta imbalance
(one side being absorbed). Then asks the key question: does the breakout in the ACCUMULATED-FLOW
direction beat a flow-blind breakout? If order flow predicts the break, flow-aligned >> baseline.

EXPLORATORY: MBP-1 is only ~2025-05 -> 2026-06 (~13 mo), so this is a proof-of-signal, not a walk-
forward-validated edge. If a clean signal shows here, it justifies pulling more history / forward testing.

Honest fills via orb_engine.simulate_trade (rule-8 stop-wins, slip, commission). Day-flat.

  python of_accum.py            # RTY + ES
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orb_engine import get_spec, simulate_trade  # noqa: E402

ET = "America/New_York"
MBP1 = Path(r"D:\data\raw\databento\mbp-1")
OUT = Path(__file__).resolve().parent / "out"
OPEN_M, CLOSE_M = 570, 960          # 09:30, 16:00 ET
CUTOFF_M = OPEN_M + 150             # accumulation box must close before 12:00
WIN = 20                            # accumulation window (minutes)
C_RANGE = 0.4                       # box range <= C_RANGE * ATR
C_VOL = 1.0                         # box volume >= C_VOL * causal expanding baseline
D_MIN = 0.15                        # |delta| >= D_MIN * volume  (flow imbalance to call it accumulation)
SLIP_TICKS = 1


def minute_delta_bars(day_path: str):
    df = pd.read_parquet(day_path, columns=["ts_event", "action", "side", "price", "size"])
    df = df[df["action"] == "T"]
    if df.empty:
        return None
    ts = pd.to_datetime(df["ts_event"], utc=True).dt.tz_convert(ET)
    mod = ts.dt.hour * 60 + ts.dt.minute
    df = df.assign(mod=mod.values)
    df = df[(df["mod"] >= OPEN_M) & (df["mod"] < CLOSE_M)]
    if df.empty:
        return None
    signed = np.where(df["side"].values == "B", df["size"].values, -df["size"].values.astype(float))
    df = df.assign(signed=signed)
    g = df.groupby("mod")
    out = pd.DataFrame({
        "mod": g.size().index.values,
        "o": g["price"].first().values, "h": g["price"].max().values,
        "l": g["price"].min().values, "c": g["price"].last().values,
        "vol": g["size"].sum().values, "delta": g["signed"].sum().values,
    })
    return out


def run_symbol(symbol: str):
    spec = get_spec(symbol)
    base = MBP1 / f"symbol={symbol}"
    days = sorted(glob.glob(str(base / "date=*")))
    # build per-day minute frames + per-day RTH range for ATR
    frames = {}
    ranges = {}
    for dp in days:
        date = os.path.basename(dp).split("=")[1]
        mb = minute_delta_bars(dp)
        if mb is None or len(mb) < WIN + 30:
            continue
        frames[date] = mb
        ranges[date] = mb["h"].max() - mb["l"].min()
    dates = sorted(frames)
    rs = pd.Series(ranges).reindex(dates)
    atr = rs.shift(1).rolling(14, min_periods=5).mean()

    variants = {"baseline": [], "flow_aligned": [], "flow_against": [], "flow_aligned_strong": []}
    n_boxes = 0
    for date in dates:
        a = atr.get(date, np.nan)
        if np.isnan(a) or a <= 0:
            continue
        mb = frames[date]
        m = mb["mod"].to_numpy(); o = mb["o"].to_numpy(); h = mb["h"].to_numpy()
        l = mb["l"].to_numpy(); c = mb["c"].to_numpy(); v = mb["vol"].to_numpy(); d = mb["delta"].to_numpy()
        cum = np.cumsum(v)
        # detect first accumulation box
        box = None
        for ti in range(WIN - 1, len(m)):
            if m[ti] >= CUTOFF_M:
                break
            whi = h[ti - WIN + 1:ti + 1].max(); wlo = l[ti - WIN + 1:ti + 1].min()
            rng = whi - wlo
            volw = v[ti - WIN + 1:ti + 1].sum()
            dw = d[ti - WIN + 1:ti + 1].sum()
            base = (cum[ti] / (ti + 1)) * WIN
            # detect the accumulation box by tight-range + elevated volume (fires often). The net
            # delta is recorded as the FLOW DIRECTION signal, not a detection gate (requiring a big
            # imbalance to detect collapsed the sample to ~9 boxes). D_MIN now classifies strength.
            if 0 < rng <= C_RANGE * a and volw >= C_VOL * base:
                strong = abs(dw) >= D_MIN * volw
                box = (ti, whi, wlo, np.sign(dw), strong); break
        if box is None:
            continue
        n_boxes += 1
        ti, whi, wlo, dsign, strong = box
        slip = SLIP_TICKS * spec.tick_size
        buf = 0.05 * a
        long_trig, short_trig = whi + buf, wlo - buf
        # first breakout either side
        bk = None; is_long = None
        for k in range(ti + 1, len(m)):
            if h[k] >= long_trig:
                bk, is_long = k, True; break
            if l[k] <= short_trig:
                bk, is_long = k, False; break
        if bk is None:
            continue
        entry = (max(o[bk], long_trig) + slip) if is_long else (min(o[bk], short_trig) - slip)
        stop = wlo if is_long else whi
        tr = simulate_trade(m, o, h, l, c, bk, is_long, entry, stop, np.nan, False, slip, spec, CLOSE_M)
        if tr is None:
            continue
        nr = tr["net_R"]
        variants["baseline"].append(nr)
        brk_dir = 1 if is_long else -1
        if brk_dir == dsign:
            variants["flow_aligned"].append(nr)
            if strong:
                variants["flow_aligned_strong"].append(nr)
        else:
            variants["flow_against"].append(nr)

    print(f"\n===== {symbol}  days={len(dates)}  accumulation boxes detected={n_boxes} =====")
    for name, arr in variants.items():
        a = np.array(arr)
        if len(a):
            k = max(1, int(np.ceil(0.05 * len(a))))
            extop = np.sort(a)[:len(a) - k].mean()
            print(f"  {name:13s} n={len(a):4d}  net_R={a.mean():+.4f}  median={np.median(a):+.4f}  "
                  f"win={(a>0).mean():.3f}  ex-top5%={extop:+.4f}")
        else:
            print(f"  {name:13s} n=0")
    return variants


if __name__ == "__main__":
    syms = sys.argv[1:] or ["RTY.c.0", "ES.c.0"]
    for s in syms:
        run_symbol(s)
