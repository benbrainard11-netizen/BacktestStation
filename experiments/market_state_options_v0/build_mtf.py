"""build_mtf — multi-timeframe options market-state: regime at T -> projected range over 1h/4h/EOD.

Extends build_regime to (a) read the gamma regime at MULTIPLE intraday decision times (the "1h gamma"
evolution) and (b) project expected RANGE over multiple forward HORIZONS (1h, 4h, rest-of-day). Honest
CONTEXT: regime -> typical forward range (for sizing/targets), additive over trailing vol; NOT direction.

Output = a projection table {regime x decision-time x horizon -> median realized range}, the numbers a
live readout shows: "10:00 short-gamma -> proj 1h X% / 4h Y% / EOD Z%". + the additive-over-vol check.

  python build_mtf.py NDXP     (or SPXW / RUTW)
"""
from __future__ import annotations

import gc
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data_io import load_option_panel  # noqa: E402
from build_regime import _panel_base  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
DEC_TIMES = [600, 690, 780, 870]          # 10:00, 11:30, 13:00, 14:30 ET
HORIZONS = {"1h": 60, "4h": 240, "EOD": 999}
CLOSE_M = 960


def day_rows(root, date):
    df = load_option_panel(root, int(date))
    df = df[df.gamma.notna() & df.oi_prior.notna() & df.underlying_price.notna()]
    if len(df) < 1000:
        return []
    df = df.assign(min=(df.ms_of_day // 60000).astype(int),
                   sgn=np.where(df.right.astype(str).str.upper().str[0] == "C", 1.0, -1.0))
    df["g_oi"] = df.gamma * df.oi_prior * df.sgn
    spot = df.groupby("min").underlying_price.median()
    out = []
    for T in DEC_TIMES:
        if T not in spot.index:
            continue
        chain = df[df["min"] == T]
        sT = float(spot.loc[T])
        gex = float(chain["g_oi"].sum()) * sT * sT / 1e9
        trail = spot.loc[(spot.index >= T - 60) & (spot.index <= T)]
        trail_rng = (trail.max() - trail.min()) / sT * 100 if len(trail) > 5 else np.nan
        for hn, hm in HORIZONS.items():
            w = spot.loc[(spot.index >= T) & (spot.index <= min(T + hm, CLOSE_M))]
            if len(w) < 5:
                continue
            out.append(dict(date=int(date), T=T, horizon=hn, gex=gex, short_gamma=int(gex < 0),
                            spot=sT, trail_rng=trail_rng,
                            fwd_range=(w.max() - w.min()) / sT * 100))
    return out


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "NDXP"
    base = _panel_base(root)
    dates = sorted(int(p.name.split("=")[1]) for p in base.glob("date=*"))
    rows = []
    for i, d in enumerate(dates):
        try:
            rows += day_rows(root, d)
        except Exception as e:
            print(f"  {d} ERR {type(e).__name__}: {str(e)[:40]}", flush=True)
        gc.collect()  # free each day's panel (SPX panels are big; avoids memory hang)
        if i % 50 == 0:
            print(f"  {i}/{len(dates)}", flush=True)
    df = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    df.to_csv(OUT / f"mtf_{root}.csv", index=False)
    print(f"\n== {root} multi-timeframe range projections by gamma regime ({df.date.nunique()} days) ==")
    print(f"  {'decision':>9} {'horizon':>7} | {'SHORT-g med range%':>18} {'LONG-g med range%':>18} {'corr(GEX,rng)':>13} {'partial|vol':>11}")
    for T in DEC_TIMES:
        for hn in HORIZONS:
            s = df[(df["T"] == T) & (df["horizon"] == hn)]
            if len(s) < 30:
                continue
            sg = s[s.short_gamma == 1].fwd_range.median()
            lg = s[s.short_gamma == 0].fwd_range.median()
            c = s.gex.corr(s.fwd_range)
            v = s.dropna(subset=["trail_rng"])
            # partial corr(GEX, fwd | trail) via residuals
            if len(v) > 30 and v.trail_rng.std() > 0:
                def rz(y, x):
                    X = np.c_[np.ones(len(x)), x]; b = np.linalg.lstsq(X, y, rcond=None)[0]; return y - X @ b
                pc = np.corrcoef(rz(v.gex.values, v.trail_rng.values), rz(v.fwd_range.values, v.trail_rng.values))[0, 1]
            else:
                pc = np.nan
            tt = f"{T//60}:{T%60:02d}"
            print(f"  {tt:>9} {hn:>7} | {sg:>17.2f}% {lg:>17.2f}% {c:>+13.3f} {pc:>+11.3f}")
    print(f"  written: out/mtf_{root}.csv")


if __name__ == "__main__":
    main()
