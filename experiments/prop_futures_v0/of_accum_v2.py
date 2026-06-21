"""of_accum_v2 — order-flow accumulation, CONTINUATION vs REVERSION, with a fresh OOS split.

Does it right (user: 'do it right, test both ways'). Detect accumulation box (tight range + volume)
from MBP-1 minute bars; read net delta (flow direction) + absorption strength |delta|/vol; compute the
box volume POC. Then test three day-flat strategies off the box, honest fills (rule-8):

  A cont_flow  : continuation — when the box breaks in the FLOW direction, go with it (ride to close).
  B rev_fade   : reversion — fade the FIRST breakout back toward the POC (stop just beyond the break).
  C rev_vsflow : reversion — fade ONLY breakouts that go AGAINST the accumulated flow (trapped-aggressor).

Fresh OOS: design = 2025-05-01 .. 2026-02-14 (~9.5 mo); holdout = 2026-02-15 .. 2026-06-09 (~3.5 mo).
Pre-register on design, read holdout once. Per-instrument AND pooled. EXPLORATORY (13-mo tape).

  python of_accum_v2.py            # RTY ES NQ YM
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from of_accum import minute_delta_bars  # noqa: E402
from orb_engine import get_spec, simulate_trade  # noqa: E402

MBP1 = Path(r"D:\data\raw\databento\mbp-1")
OPEN_M, CLOSE_M, CUTOFF_M = 570, 960, 720
WIN, C_RANGE, C_VOL, SBUF, SLIP_TICKS = 20, 0.4, 1.0, 0.4, 1
DESIGN_END = "2026-02-14"   # design < this ; holdout >= this
HOLD_END = "2026-06-09"


def box_poc(lo, hi, vol, i0, i1, nb=20):
    blo = lo[i0:i1 + 1].min(); bhi = hi[i0:i1 + 1].max()
    if bhi <= blo:
        return (bhi + blo) / 2
    centers = (np.linspace(blo, bhi, nb + 1)[:-1] + np.linspace(blo, bhi, nb + 1)[1:]) / 2
    vp = np.zeros(nb)
    for a, b, v in zip(lo[i0:i1 + 1], hi[i0:i1 + 1], vol[i0:i1 + 1]):
        lk = min(nb - 1, max(0, int((a - blo) / (bhi - blo) * nb)))
        hk = min(nb - 1, max(0, int((b - blo) / (bhi - blo) * nb)))
        vp[lk:hk + 1] += v / (hk - lk + 1)
    return float(centers[int(np.argmax(vp))])


def stats(a):
    a = np.asarray(a, float)
    if len(a) == 0:
        return None
    k = max(1, int(np.ceil(0.05 * len(a))))
    return dict(n=len(a), net_R=a.mean(), median=np.median(a), win=(a > 0).mean(),
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
    import pandas as pd
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
        lo = mb["l"].to_numpy(); c = mb["c"].to_numpy(); v = mb["vol"].to_numpy(); d = mb["delta"].to_numpy()
        cum = np.cumsum(v)
        box = None
        for ti in range(WIN - 1, len(m)):
            if m[ti] >= CUTOFF_M:
                break
            whi = h[ti - WIN + 1:ti + 1].max(); wlo = lo[ti - WIN + 1:ti + 1].min()
            volw = v[ti - WIN + 1:ti + 1].sum(); rng = whi - wlo
            if 0 < rng <= C_RANGE * a and volw >= C_VOL * (cum[ti] / (ti + 1)) * WIN:
                dw = d[ti - WIN + 1:ti + 1].sum()
                poc = box_poc(lo, h, v, ti - WIN + 1, ti)
                box = (ti, whi, wlo, np.sign(dw), poc); break
        if box is None:
            continue
        ti, whi, wlo, dsign, poc = box
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
        brk = 1 if up else -1

        # A: continuation in flow direction
        if brk == dsign:
            entry = (max(o[bk], long_trig) + slip) if up else (min(o[bk], short_trig) - slip)
            stop = wlo if up else whi
            tr = simulate_trade(m, o, h, lo, c, bk, up, entry, stop, np.nan, False, slip, spec, CLOSE_M)
            if tr:
                acc[(symbol, "cont_flow", split)].append(tr["net_R"])
                acc[("POOL", "cont_flow", split)].append(tr["net_R"])

        # B/C: reversion — fade the breakout back to POC (stop just beyond the break, entry bar checked)
        if up:
            f_long = False; entry = long_trig - slip; stop = long_trig + SBUF * a; tgt = poc
            ok = tgt < entry
        else:
            f_long = True; entry = short_trig + slip; stop = short_trig - SBUF * a; tgt = poc
            ok = tgt > entry
        if ok:
            tr = simulate_trade(m, o, h, lo, c, bk, f_long, entry, stop, tgt, True, slip, spec,
                                CLOSE_M, start_at_entry=True)
            if tr:
                acc[(symbol, "rev_fade", split)].append(tr["net_R"])
                acc[("POOL", "rev_fade", split)].append(tr["net_R"])
                if brk != dsign:  # breakout against the accumulated flow
                    acc[(symbol, "rev_vsflow", split)].append(tr["net_R"])
                    acc[("POOL", "rev_vsflow", split)].append(tr["net_R"])


def main():
    syms = sys.argv[1:] or ["RTY.c.0", "ES.c.0", "NQ.c.0", "YM.c.0"]
    from collections import defaultdict
    acc = defaultdict(list)
    for s in syms:
        run_symbol(s, acc)
    str18 = ["cont_flow", "rev_fade", "rev_vsflow"]
    for scope in syms + ["POOL"]:
        print(f"\n===== {scope} =====")
        print(f"  {'strategy':12s} {'split':8s} {'n':>4s} {'net_R':>8s} {'median':>8s} {'win':>6s} {'ex-top5%':>9s}")
        for st in str18:
            for split in ("design", "holdout"):
                s = stats(acc[(scope, st, split)])
                if s:
                    print(f"  {st:12s} {split:8s} {s['n']:4d} {s['net_R']:+8.4f} {s['median']:+8.4f} "
                          f"{s['win']:6.3f} {s['ex_top5']:+9.4f}")
                else:
                    print(f"  {st:12s} {split:8s}    0")


if __name__ == "__main__":
    main()
