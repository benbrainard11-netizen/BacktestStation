"""of_accum_v3 — exit-geometry sweep on the REVERSION (fade accumulation breakout) generator.

v2 showed reversion is a stable 62-66%-win pattern but ~0/slightly-neg EV because winners are capped at
the POC while the ~1/3 real breakouts run full to the stop. Lever = let the reversion winners RUN
(R-multiple / ride-to-close) and vary the stop. Tune on DESIGN; the holdout is SPENT (user accepts the
OOS risk) so it's reported as a weak check, NOT used for selection.

  python of_accum_v3.py
"""
from __future__ import annotations

import glob
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from of_accum import minute_delta_bars  # noqa: E402
from of_accum_v2 import box_poc  # noqa: E402
from orb_engine import get_spec, simulate_trade  # noqa: E402

MBP1 = Path(r"D:\data\raw\databento\mbp-1")
OPEN_M, CLOSE_M, CUTOFF_M = 570, 960, 720
WIN, C_RANGE, C_VOL, SLIP_TICKS = 20, 0.4, 1.0, 1
DESIGN_END, HOLD_END = "2026-02-14", "2026-06-09"
SYMS = ["RTY.c.0", "ES.c.0", "NQ.c.0", "YM.c.0"]

# exit configs: (stop_buf*ATR beyond the breakout, target spec). target: 'poc' | ('R', mult) | 'ride'
EXITS = {
    "poc_sb0.3":   (0.3, ("poc",)),
    "poc_sb0.5":   (0.5, ("poc",)),
    "1.5R_sb0.3":  (0.3, ("R", 1.5)),
    "1.5R_sb0.5":  (0.5, ("R", 1.5)),
    "3R_sb0.3":    (0.3, ("R", 3.0)),
    "3R_sb0.5":    (0.5, ("R", 3.0)),
    "ride_sb0.3":  (0.3, ("ride",)),
    "ride_sb0.5":  (0.5, ("ride",)),
}


def stats(a):
    a = np.asarray(a, float)
    if len(a) == 0:
        return None
    k = max(1, int(np.ceil(0.05 * len(a))))
    return dict(n=len(a), net_R=a.mean(), median=float(np.median(a)), win=(a > 0).mean(),
                ex_top5=np.sort(a)[:len(a) - k].mean())


def run_symbol(symbol, acc):
    spec = get_spec(symbol)
    days = sorted(glob.glob(str(MBP1 / f"symbol={symbol}" / "date=*")))
    frames, ranges = {}, {}
    for dp in days:
        date = os.path.basename(dp).split("=")[1]
        mb = minute_delta_bars(dp)
        if mb is None or len(mb) < WIN + 30:
            continue
        frames[date] = mb
        ranges[date] = mb["h"].max() - mb["l"].min()
    dates = sorted(frames)
    atr = pd.Series(ranges).reindex(dates).shift(1).rolling(14, min_periods=5).mean()

    for date in dates:
        a = atr.get(date, np.nan)
        if np.isnan(a) or a <= 0:
            continue
        split = "design" if date < DESIGN_END else ("holdout" if date <= HOLD_END else None)
        if split is None:
            continue
        mb = frames[date]
        m = mb["mod"].to_numpy(); o = mb["o"].to_numpy(); h = mb["h"].to_numpy()
        lo = mb["l"].to_numpy(); c = mb["c"].to_numpy(); v = mb["vol"].to_numpy()
        cum = np.cumsum(v)
        box = None
        for ti in range(WIN - 1, len(m)):
            if m[ti] >= CUTOFF_M:
                break
            whi = h[ti - WIN + 1:ti + 1].max(); wlo = lo[ti - WIN + 1:ti + 1].min(); rng = whi - wlo
            if 0 < rng <= C_RANGE * a and v[ti - WIN + 1:ti + 1].sum() >= C_VOL * (cum[ti] / (ti + 1)) * WIN:
                poc = box_poc(lo, h, v, ti - WIN + 1, ti)
                box = (ti, whi, wlo, poc); break
        if box is None:
            continue
        ti, whi, wlo, poc = box
        slip = SLIP_TICKS * spec.tick_size
        buf = 0.05 * a
        long_trig, short_trig = whi + buf, wlo - buf
        bk = None; up = None
        for k in range(ti + 1, len(m)):
            if h[k] >= long_trig:
                bk, up = k, True; break
            if lo[k] <= short_trig:
                bk, up = k, False; break
        if bk is None:
            continue
        for name, (sb, tgt_spec) in EXITS.items():
            if up:  # fade short
                f_long = False; entry = long_trig - slip; stop = long_trig + sb * a
            else:   # fade long
                f_long = True; entry = short_trig + slip; stop = short_trig - sb * a
            risk = abs(entry - stop)
            if risk <= 0:
                continue
            if tgt_spec[0] == "poc":
                tgt = poc; use_t = True
                if (f_long and tgt <= entry) or ((not f_long) and tgt >= entry):
                    continue
            elif tgt_spec[0] == "R":
                tgt = entry + tgt_spec[1] * risk if f_long else entry - tgt_spec[1] * risk
                use_t = True
            else:  # ride
                tgt = np.nan; use_t = False
            tr = simulate_trade(m, o, h, lo, c, bk, f_long, entry, stop, tgt, use_t, slip, spec,
                                CLOSE_M, start_at_entry=True)
            if tr:
                acc[(symbol, name, split)].append(tr["net_R"])
                acc[("POOL", name, split)].append(tr["net_R"])


def main():
    acc = defaultdict(list)
    for s in SYMS:
        run_symbol(s, acc)
    # POOL table, sorted by design net_R
    print("\n===== POOL (all 4 index futures) — reversion exit sweep =====")
    print(f"  {'exit':12s} {'dN':>4s} {'design_R':>9s} {'dMed':>7s} {'dWin':>6s} | "
          f"{'hN':>4s} {'hold_R':>8s} {'hMed':>7s} {'hWin':>6s} {'hExTop5':>8s}")
    rows = []
    for name in EXITS:
        d = stats(acc[("POOL", name, "design")]); ho = stats(acc[("POOL", name, "holdout")])
        rows.append((name, d, ho))
    rows.sort(key=lambda r: (r[1]["net_R"] if r[1] else -9), reverse=True)
    for name, d, ho in rows:
        ds = f"{d['n']:4d} {d['net_R']:+9.4f} {d['median']:+7.3f} {d['win']:6.3f}" if d else " " * 28
        hs = (f"{ho['n']:4d} {ho['net_R']:+8.4f} {ho['median']:+7.3f} {ho['win']:6.3f} {ho['ex_top5']:+8.4f}"
              if ho else " " * 36)
        print(f"  {name:12s} {ds} | {hs}")
    # best design config -> per-instrument holdout
    best = rows[0][0]
    print(f"\nBest design exit = {best}. Per-instrument holdout:")
    for s in SYMS:
        ho = stats(acc[(s, best, "holdout")])
        if ho:
            print(f"  {s:8s} n={ho['n']:3d} hold_R={ho['net_R']:+.4f} med={ho['median']:+.3f} "
                  f"win={ho['win']:.3f} ex-top5%={ho['ex_top5']:+.4f}")


if __name__ == "__main__":
    main()
