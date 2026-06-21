"""intraday_gamma — the "1h gamma" trajectory: how net dealer GEX evolves through the session.

Shows the mechanism live: net GEX per minute (all-DTE + 0DTE), the zero-gamma flip level vs spot, and the
0DTE share growing into the close (near-expiry gamma concentrates ATM → pin/accel pressure intensifies).
This is the intraday view behind the validated "short-gamma → bigger range, stronger later in the day" read.

  python intraday_gamma.py NDX 20251121
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data_io import load_option_panel  # noqa: E402
from build_regime import zero_gamma  # noqa: E402

ROOTS = {"NDX": "NDXP", "SPX": "SPXW", "RUT": "RUTW"}
SNAPS = [600, 660, 720, 780, 840, 900, 955]   # 10:00..15:55 ET


def trajectory(index, date):
    df = load_option_panel(ROOTS[index.upper()], int(date))
    df = df[df.gamma.notna() & df.oi_prior.notna() & df.underlying_price.notna()]
    if not len(df):
        return None
    df = df.assign(min=(df.ms_of_day // 60000).astype(int),
                   sgn=np.where(df.right.astype(str).str.upper().str[0] == "C", 1.0, -1.0))
    df["g_oi"] = df.gamma * df.oi_prior * df.sgn
    spot = df.groupby("min").underlying_price.median()
    rows = []
    for t in SNAPS:
        if t not in spot.index:
            continue
        ch = df[df["min"] == t]; s = float(spot.loc[t])
        gex = float(ch.g_oi.sum()) * s * s / 1e9
        z = ch[ch.dte <= 0.6]
        gex0 = float(z.g_oi.sum()) * s * s / 1e9 if len(z) else np.nan
        zg = zero_gamma(ch.groupby("strike").g_oi.sum())
        rows.append(dict(t=t, spot=s, gex=gex, gex0=gex0,
                         share0=abs(gex0) / (abs(gex) + 1e-9) if np.isfinite(gex0) else np.nan, zg=zg))
    tr = pd.DataFrame(rows)
    print(f"\n=== {index.upper()} {date} — intraday gamma trajectory ===")
    print(f"  {'time':>6} {'spot':>9} {'GEX($bn)':>9} {'0DTE GEX':>9} {'0DTE%':>6} {'zero-γ':>9} {'spot vs 0γ':>11}")
    for r in tr.itertuples(index=False):
        sv = ("above" if (np.isfinite(r.zg) and r.spot > r.zg) else "below" if np.isfinite(r.zg) else "—")
        zgs = f"{r.zg:.0f}" if np.isfinite(r.zg) else "none"
        print(f"  {r.t//60:>2}:{r.t%60:02d} {r.spot:>9.0f} {r.gex:>+9.2f} {r.gex0:>+9.2f} "
              f"{(r.share0*100 if np.isfinite(r.share0) else 0):>5.0f}% {zgs:>9} {sv:>11}")
    o, c = tr.iloc[0], tr.iloc[-1]
    flips = ((tr.gex.values[:-1] * tr.gex.values[1:]) < 0).sum()
    print(f"  ── dynamics: GEX {o.gex:+.2f}→{c.gex:+.2f} ({'SHORT-gamma all day' if (tr.gex<0).all() else 'LONG-gamma all day' if (tr.gex>0).all() else f'{flips} regime flip(s)'}) | "
          f"0DTE share peaks midday ~{tr.share0.max()*100:.0f}% then expires by close | "
          f"realized range {(spot.max()-spot.min())/spot.iloc[0]*100:.2f}%")
    return tr


if __name__ == "__main__":
    idx = sys.argv[1] if len(sys.argv) > 1 else "NDX"
    date = int(sys.argv[2]) if len(sys.argv) > 2 else 20251121
    trajectory(idx, date)
