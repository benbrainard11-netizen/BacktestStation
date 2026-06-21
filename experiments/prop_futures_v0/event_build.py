"""event_build — one row per accumulation-breakout EVENT, with order-flow features + outcomes.

Foundation for the disciplined "test many ways" push: instead of spraying strategy variants, build a
clean event table and ANALYZE it (which features predict reverse-vs-continue; where's the best entry).
Each detected accumulation box (tight range + heavy volume, from MBP-1 minute bars w/ signed delta) that
breaks out becomes an event with FEATURES known at the breakout and OUTCOMES of what happened next.

Honest fills (orb_engine.simulate_trade). Day-flat. Writes out/events_<SYM>.parquet.

  python event_build.py ES.c.0 NQ.c.0 ...     # default = liquid complex
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from of_accum import minute_delta_bars  # noqa: E402
from of_accum_v2 import box_poc  # noqa: E402
from orb_engine import get_spec, simulate_trade  # noqa: E402

MBP1 = Path(r"D:\data\raw\databento\mbp-1")
OUT = Path(__file__).resolve().parent / "out"
OPEN_M, CLOSE_M, CUTOFF_M = 570, 960, 720
WIN, C_RANGE, C_VOL, SLIP_TICKS = 20, 0.4, 1.0, 1
DESIGN_END, HOLD_END = "2026-02-14", "2026-06-09"
LIQUID = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0", "CL.c.0", "NG.c.0", "GC.c.0", "ZS.c.0", "ZN.c.0", "6E.c.0"]


def build_events(symbol):
    spec = get_spec(symbol)
    tick = spec.tick_size
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

    rows = []
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
        cum = np.cumsum(v); cumd = np.cumsum(d)
        # session VWAP (typical price) up to each bar
        typ = (h + lo + c) / 3.0
        vwap = np.cumsum(typ * np.where(v > 0, v, 1)) / np.cumsum(np.where(v > 0, v, 1))
        box = None
        for ti in range(WIN - 1, len(m)):
            if m[ti] >= CUTOFF_M:
                break
            sl = slice(ti - WIN + 1, ti + 1)
            whi = h[sl].max(); wlo = lo[sl].min(); rng = whi - wlo
            volw = v[sl].sum()
            if 0 < rng <= C_RANGE * a and volw >= C_VOL * (cum[ti] / (ti + 1)) * WIN:
                dw = d[sl].sum()
                poc = box_poc(lo, h, v, ti - WIN + 1, ti)
                box = (ti, whi, wlo, poc, dw, volw, rng); break
        if box is None:
            continue
        ti, whi, wlo, poc, dw, volw, rng = box
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
        # ---- features known AT the breakout ----
        brk_dir = 1 if up else -1
        box_dsign = int(np.sign(dw))
        edge = long_trig if up else short_trig
        feat = dict(
            symbol=symbol, date=date, split=split, tod=int(m[bk]),
            box_width_atr=rng / a,
            box_vol_rel=volw / ((cum[ti] / (ti + 1)) * WIN),
            box_absorption=abs(dw) / volw,                 # |net delta| / volume (flow imbalance)
            box_delta_sign=box_dsign,
            poc_loc=(poc - wlo) / rng,                     # 0=low edge,1=high edge
            brk_up=int(up),
            brk_aligned_flow=int(brk_dir == box_dsign),    # breakout same side as accumulated flow
            brk_bar_delta_rel=float(d[bk] / v[bk]) if v[bk] > 0 else 0.0,
            box_vs_vwap_atr=((whi + wlo) / 2 - vwap[ti]) / a,
            cum_delta_rel=float(cumd[ti] / cum[ti]) if cum[ti] > 0 else 0.0,
            mins_to_close=int(CLOSE_M - m[bk]),
        )
        # ---- outcomes after the breakout (post bars, day-flat) ----
        post = slice(bk + 1, np.flatnonzero(m < CLOSE_M)[-1] + 1)
        ph, pl = h[post], lo[post]
        if len(ph) == 0:
            continue
        if up:  # breakout up; FADE = short toward poc
            feat["reverted_to_poc"] = int(pl.min() <= poc)
            feat["mfe_fade_atr"] = (edge - pl.min()) / a        # favorable for the fade-short
            feat["mae_fade_atr"] = (ph.max() - edge) / a        # adverse (continuation)
            feat["overshoot_atr"] = (ph.max() - whi) / a
        else:   # breakout down; FADE = long toward poc
            feat["reverted_to_poc"] = int(ph.max() >= poc)
            feat["mfe_fade_atr"] = (ph.max() - edge) / a
            feat["mae_fade_atr"] = (edge - pl.min()) / a
            feat["overshoot_atr"] = (wlo - pl.min()) / a
        # honest terminal R for the two base trades
        slip = SLIP_TICKS * tick
        if up:
            fr = simulate_trade(m, o, h, lo, c, bk, False, long_trig - slip, long_trig + 0.5 * a,
                                poc, True, slip, spec, CLOSE_M, start_at_entry=True)
            cr = simulate_trade(m, o, h, lo, c, bk, True, long_trig + slip, wlo, np.nan, False, slip, spec, CLOSE_M)
        else:
            fr = simulate_trade(m, o, h, lo, c, bk, True, short_trig + slip, short_trig - 0.5 * a,
                                poc, True, slip, spec, CLOSE_M, start_at_entry=True)
            cr = simulate_trade(m, o, h, lo, c, bk, False, short_trig - slip, whi, np.nan, False, slip, spec, CLOSE_M)
        feat["fade_R"] = fr["net_R"] if fr else np.nan
        feat["chase_R"] = cr["net_R"] if cr else np.nan
        rows.append(feat)
    df = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    path = OUT / f"events_{symbol.split('.')[0]}.parquet"
    df.to_parquet(path)
    nd = (df.split == "design").sum() if len(df) else 0
    print(f"  {symbol}: {len(df)} events ({nd} design) -> {path.name}")
    return df


if __name__ == "__main__":
    syms = sys.argv[1:] or LIQUID
    for s in syms:
        build_events(s)
