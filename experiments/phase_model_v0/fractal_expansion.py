"""Fractal MTF expansion-alignment entry -- the user's core conviction, tested cleanly ONE time.

Idea: higher timeframes (4h + 1h) are EXPANDING in one direction, the lower timeframe (15m ~ a few 5m bars)
is CONSOLIDATING (coil), and we enter when the coil BREAKS in the HTF direction -- as early as possible.
Built on clean MBP-1 5m bars (the only trustworthy intraday data). Tested long AND short with alpha-vs-beta,
so a symmetric data/drift artifact can't fool us again. This is the book-closer/opener for the intraday
price-pattern approach: if THIS (the strongest MTF-aligned version) doesn't validate on clean data, the class
is done.

Expansion = Kaufman efficiency ratio high + directional; coil = ER low. ER windows on 5m bars: 4h=48, 1h=12,
coil=6 (~30m). Thresholds fixed/sensible (noted -- robustness would be the next check IF anything shows).

Run: backend/.venv/Scripts/python.exe experiments/phase_model_v0/fractal_expansion.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

CLEAN = Path(__file__).resolve().parents[1] / "asset_profiles_v0" / "out" / "clean_bars"
TICK = {"RB.c.0": 0.0001, "HO.c.0": 0.0001, "BZ.c.0": 0.01, "CL.c.0": 0.01, "NG.c.0": 0.001}
W4, W1, WC, HOLD, TRAIL = 48, 12, 6, 48, 1.0
THR, COIL = 0.40, 0.30        # expansion ER threshold / coil ER threshold


def er(c: pd.Series, w: int) -> pd.Series:
    return ((c - c.shift(w)).abs() / c.diff().abs().rolling(w).sum()).replace([np.inf, -np.inf], np.nan)


def trail_exit(h, l, c, e, end, entry, stop, risk, side):
    peak, tstop = entry, stop
    for t in range(e + 1, end + 1):
        if (l[t] <= tstop) if side == 1 else (h[t] >= tstop):
            return (tstop - entry) / risk if side == 1 else (entry - tstop) / risk
        if side == 1:
            peak = max(peak, h[t]); tstop = max(tstop, peak - TRAIL * risk)
        else:
            peak = min(peak, l[t]); tstop = min(tstop, peak + TRAIL * risk)
    return (c[end] - entry) / risk if side == 1 else (entry - c[end]) / risk


def sim(b: pd.DataFrame, side: int) -> pd.DataFrame:
    c = b["close"]
    mom4, mom1 = c - c.shift(W4), c - c.shift(W1)
    er4, er1, erc = er(c, W4), er(c, W1), er(c, WC)
    coiled = (erc < COIL).shift(1).fillna(False)
    if side == 1:
        regime = (mom4 > 0) & (mom1 > 0) & (er4 > THR) & (er1 > THR)
        brk = c > b["high"].rolling(WC).max().shift(1)
    else:
        regime = (mom4 < 0) & (mom1 < 0) & (er4 > THR) & (er1 > THR)
        brk = c < b["low"].rolling(WC).min().shift(1)
    sig = (regime & coiled & brk).to_numpy()
    h, l, cc, ts, n = b["high"].to_numpy(), b["low"].to_numpy(), c.to_numpy(), b.index, len(b)
    rows = []
    for e in np.where(sig)[0]:
        if e + 1 >= n:
            continue
        entry = cc[e]
        stop = l[max(0, e - WC):e + 1].min() if side == 1 else h[max(0, e - WC):e + 1].max()
        risk = (entry - stop) if side == 1 else (stop - entry)
        if risk <= 0:
            continue
        r = trail_exit(h, l, cc, e, min(e + HOLD, n - 1), entry, stop, risk, side)
        rows.append((ts[e], r, risk))
    return pd.DataFrame(rows, columns=["date", "r", "risk"])


def cell(tr, tick):
    if len(tr) < 30:
        return f"n={len(tr)} (few)"
    nr = tr["r"] - 2 * tick / tr["risk"]
    m = nr.groupby(tr["date"].dt.tz_localize(None).dt.to_period("M")).mean()
    return f"E[R]={nr.mean():+.3f} n={len(tr):4} mo+={(m > 0).sum()}/{len(m)}"


def main() -> int:
    print(f"fractal expansion (4h+1h expand, coil break) -- clean bars, ER thr={THR}/coil={COIL}\n")
    for sym in TICK:
        f = CLEAN / f"{sym}.parquet"
        if not f.exists():
            continue
        b = pd.read_parquet(f).sort_index()
        tick = TICK[sym]
        drift = float(np.log(b["close"].iloc[-1] / b["close"].iloc[0]) * 100)
        print(f"{sym:8} drift{drift:+4.0f}% | LONG  {cell(sim(b, 1), tick)}")
        print(f"{'':8}            | SHORT {cell(sim(b, -1), tick)}")
    print("\n(both-sides-+ = real; one-side-+ ~ drift = beta; else dead)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
