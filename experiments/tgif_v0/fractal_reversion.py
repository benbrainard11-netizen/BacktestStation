"""Fractal expansion -> REVERSION test (the TGIF generalization, fade an expansion candle).

User's idea: after ANY expansion candle (large directional range), price tends to retrace back into
the range -- fractal across timeframes. This FADES the move (opposite of fractal_expansion.py, which
tested continuation and died). Honest design:
  - expansion candle = true range > K x trailing-20 avg TR, with a directional close.
  - fade trade: at the expansion candle's close, enter against it; target = RETRACE x range back toward
    its open; stop = beyond the candle extreme + BUF x range. hold HOLD bars. stop-wins-ties, tick cost.
  - LONG and SHORT reported separately (a symmetric drift artifact can't fool us).
  - **BASELINE = the same fade on EVERY candle.** The only thing that matters is whether the expansion
    condition BEATS the baseline -- mean-reversion itself is a known baseline, not an edge.
Multi-timeframe (fractal). No-lookahead: expansion known at its close; trade after. ES + NQ.

Stage 1 of the TGIF/gamma test (needs NO options data). Stage 2 (when GEX lands): does the edge
concentrate on Fridays / around OPEX / in positive-gamma regimes?

Run: backend/.venv/Scripts/python.exe experiments/tgif_v0/fractal_reversion.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "backend")
from app.data.reader import read_bars  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)
SYMS = {"ES.c.0": 0.25, "NQ.c.0": 0.25}          # tick size
TFS = {"60min": 60, "240min": 240, "1D": 1440}
K, RETRACE, BUF, HOLD = 1.5, 0.5, 0.5, 4          # expansion mult / target retrace / stop buffer / hold bars
COST_TICKS = 1.0


def load_tf(sym: str, tf: str) -> pd.DataFrame:
    cache = OUT / f"{sym.split('.')[0]}_{tf}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    df = read_bars(symbol=sym, timeframe="1m", start=dt.date(2018, 1, 1), end=dt.date(2026, 6, 1))
    ts = pd.to_datetime(df["ts_event"], utc=True)
    s = df.assign(_ts=ts).set_index("_ts")
    o = s["open"].resample(tf).first()
    h = s["high"].resample(tf).max()
    low = s["low"].resample(tf).min()
    c = s["close"].resample(tf).last()
    b = pd.DataFrame({"open": o, "high": h, "low": low, "close": c}).dropna()
    b.to_parquet(cache)
    return b


def simulate(b: pd.DataFrame, tick: float, expansion_only: bool, side: int) -> np.ndarray:
    o, h, l, c = (b[x].to_numpy() for x in ["open", "high", "low", "close"])
    tr = np.maximum(h - l, np.maximum(abs(h - np.roll(c, 1)), abs(l - np.roll(c, 1))))
    avgtr = pd.Series(tr).rolling(20).mean().shift(1).to_numpy()
    rng = h - l
    up = c > o                          # candle direction
    n = len(b)
    out = []
    for e in range(20, n - 1):
        if not np.isfinite(avgtr[e]) or rng[e] <= 0:
            continue
        is_exp = tr[e] > K * avgtr[e]
        if expansion_only and not is_exp:
            continue
        # fade: up candle -> short; down candle -> long. side filters which we count.
        s = -1 if up[e] else 1
        if s != side:
            continue
        entry = c[e]
        if s == 1:  # long: stop below the low, target up toward open (retrace of the down move)
            stop = l[e] - BUF * rng[e]
            tgt = entry + RETRACE * rng[e]
        else:       # short
            stop = h[e] + BUF * rng[e]
            tgt = entry - RETRACE * rng[e]
        risk = abs(entry - stop)
        if risk <= 0:
            continue
        r = _walk(h, l, c, e, min(e + HOLD, n - 1), entry, stop, tgt, risk, s)
        out.append(r - COST_TICKS * tick / risk)        # honest cost in R
    return np.array(out)


def _walk(h, l, c, e, end, entry, stop, tgt, risk, s) -> float:
    for t in range(e + 1, end + 1):
        hit_stop = (l[t] <= stop) if s == 1 else (h[t] >= stop)
        hit_tgt = (h[t] >= tgt) if s == 1 else (l[t] <= tgt)
        if hit_stop:                                     # stop wins ties (honest)
            return -1.0
        if hit_tgt:
            return abs(tgt - entry) / risk
    return (c[end] - entry) / risk if s == 1 else (entry - c[end]) / risk


def stat(r: np.ndarray) -> str:
    if len(r) < 30:
        return f"n={len(r):4} (thin)"
    return f"E[R]={r.mean():+.3f}  win={100*(r>0).mean():4.1f}%  n={len(r):5}"


def main() -> int:
    print(f"Fractal expansion->reversion (fade) | K={K} retrace={RETRACE} buf={BUF} hold={HOLD} | "
          f"EXPANSION vs BASELINE(fade-any)\n")
    for sym, tick in SYMS.items():
        print(f"== {sym} ==")
        for tf in TFS:
            b = load_tf(sym, tf)
            for side, lbl in [(1, "long "), (-1, "short")]:
                exp = simulate(b, tick, True, side)
                base = simulate(b, tick, False, side)
                print(f"  {tf:6} {lbl}  EXP {stat(exp):42}  | BASE {stat(base)}")
        print()
    print("READ: edge only if EXP clearly beats BASE on BOTH sides. Else it's just (weak) mean-reversion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
