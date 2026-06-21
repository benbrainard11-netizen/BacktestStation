"""Sector-rotation / sector-momentum probe — clean (ETFs, no survivorship issue). Do the
strongest-trailing sectors keep outperforming next month? Ranks the 11 SPDR sectors by
trailing return over several lookbacks; measures rank-IC vs next-month return + the
top-minus-equal-weight spread. Monthly, 2010-2026. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

import loaders as L  # noqa: E402

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]  # 9 w/ 2010+ history (drop XLC 2018, XLRE 2015)
LOOKBACKS = {"1mo": 1, "3mo": 3, "6mo": 6, "12mo": 12, "12-1mo": 12}

px = {}
for t in SECTORS:
    try:
        d = L.load_etf(t).set_index("dt")["close"]
        px[t] = d
    except Exception:
        pass
P = pd.DataFrame(px).dropna(how="any")
M = P.resample("ME").last()              # month-end prices
ret1 = M.pct_change()                    # monthly returns
print(f"{len(M)} months, {M.shape[1]} sectors ({M.index[0].date()} -> {M.index[-1].date()})\n")
print(f"{'lookback':9s} {'rank-IC':>8} {'top-EW/mo':>10} {'top-EW ann':>11} {'top win%':>9}")

for name, L_ in LOOKBACKS.items():
    skip = 1 if name == "12-1mo" else 0
    trail = M.shift(skip) / M.shift(L_) - 1     # trailing return at formation (causal: known at t)
    fwd = ret1.shift(-1)                          # next-month return
    ics, tops = [], []
    for t in M.index:
        tr, fr = trail.loc[t], fwd.loc[t]
        ok = tr.notna() & fr.notna()
        if ok.sum() < 6:
            continue
        ics.append(spearmanr(tr[ok], fr[ok]).correlation)
        top = tr[ok].idxmax()
        tops.append(fr[top] - fr[ok].mean())     # top sector minus equal-weight
    ic = np.nanmean(ics)
    te = np.nanmean(tops)
    print(f"{name:9s} {ic:+8.3f} {te*100:+9.2f}% {((1+te)**12-1)*100:+10.1f}% "
          f"{np.mean(np.array(tops)>0)*100:8.0f}%")
print("\nREAD: positive rank-IC + positive top-minus-equal-weight = sector momentum/rotation")
print("works (strong sectors keep leading). ~0 => no clean sector-rotation edge here.")
