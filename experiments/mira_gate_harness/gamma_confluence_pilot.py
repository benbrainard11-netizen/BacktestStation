"""WALL-BEYOND-LEVEL pilot (Ben's headline): a reclaim is stronger when a gamma WALL rests just
BEYOND the swept level — call wall just ABOVE a swept high (short), put wall just BELOW a swept low
(long). The sweep grabs the stops AND hits the dealer barrier at one price. Mechanistically distinct
from generic confluence (which failed, NIGHT_REPORT §32). PILOT: gamma walls cover ES 2025-05+,
YM/RTY 2025-12+ (NQ sparse) -> small n, a DIRECTION check, not a validation. Reuses gamma_wall_legal
walls (prior-day, futures-mapped, legal)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gamma_wall_legal as GW  # noqa: E402  (builds GW.WALLS {sym: {date: (cw_fut, pw_fut)}})

R = HERE / "runs"
TICK = GW.LB.TICK
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]

d = pd.read_parquet(R / "confluence_scored.parquet")
import datetime as dt


def wall_beyond(row, band_tk):
    """1 if a wall sits within band_tk ticks BEYOND the swept level on the correct side."""
    sym = row.symbol
    walls = GW.WALLS.get(sym, {}).get(dt.date.fromisoformat(str(row.session_date)))
    if walls is None:
        return -1  # no wall data this day
    cw, pw = walls
    tick = TICK[sym]
    lvl = float(row.level_price)
    band = band_tk * tick
    if row.side == "high":   # short: want call wall just ABOVE the swept high
        return 1 if (np.isfinite(cw) and lvl <= cw <= lvl + band) else 0
    else:                     # long: want put wall just BELOW the swept low
        return 1 if (np.isfinite(pw) and lvl - band <= pw <= lvl) else 0


for b in (10, 20, 40):
    d[f"wb{b}"] = [wall_beyond(r, b) for r in d.itertuples()]
cov = d[d["wb20"] >= 0]
print(f"wall-data coverage: {len(cov)}/{len(d)} reclaims have walls (by symbol "
      f"{cov['symbol'].value_counts().to_dict()})")


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=0"


print("\n=== (1) does a wall-beyond raise reaction-R on its own? (reclaims with wall data) ===")
for b in (10, 20, 40):
    has = cov[cov[f"wb{b}"] == 1]
    no = cov[cov[f"wb{b}"] == 0]
    print(f"  band {b:2d}tk: wall-beyond {st(has['Rr'])}  | no-wall-beyond {st(no['Rr'])}")

print("\n=== (2) wall-beyond x drift-zone STACK (does it lift the edge?) ===")
s = cov[cov["stk"]]
for b in (20, 40):
    print(f"  band {b}tk: stack & wall-beyond {st(s[s[f'wb{b}']==1]['Rr'])}  | stack no-wall {st(s[s[f'wb{b}']==0]['Rr'])}")
print(f"  (stack baseline, wall-covered: {st(s['Rr'])})")
print("\n=== wall-beyond by symbol (band 20tk, all reclaims) ===")
for sym, g in cov.groupby("symbol"):
    print(f"  {sym:8s} wall-beyond {st(g[g['wb20']==1]['Rr'])}")
