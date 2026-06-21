"""The faithful TGIF test: expansion WEEK (Mon-Thu) -> Friday fades back into the range.

This is the user's actual setup (not the watered-down fractal). ET-session daily bars so day-of-week is
correct. For each week: Mon-Thu directional move + Mon-Thu range; on FRIDAY fade that move, target a
RETRACE back into the range, stop beyond the week's extreme. Honest fills (stop-wins-ties on Friday's
OHLC) + tick cost. Reported:
  - EXPANSION weeks (big Mon-Thu move) vs BASELINE (all weeks)  -- does expansion add anything?
  - LONG (fade down-weeks) vs SHORT (fade up-weeks) separately  -- catch index drift/beta.
  - OPEX weeks (3rd-Friday) vs non-OPEX                          -- the gamma-timing proxy, FREE.

If TGIF is real, expansion (esp. OPEX) Fridays should beat baseline on BOTH sides. Stage 1.5 of the
gamma thesis -- needs no options data; the real GEX conditioning comes next now that the data is down.

Run: backend/.venv/Scripts/python.exe experiments/tgif_v0/tgif_weekly.py
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
SYMS = {"ES.c.0": 0.25, "NQ.c.0": 0.25}
K, RETRACE, BUF = 1.5, 0.33, 0.25      # expansion mult / Friday retrace target / stop buffer (x Mon-Thu range)
COST_TICKS = 1.0


def daily_et(sym: str) -> pd.DataFrame:
    cache = OUT / f"{sym.split('.')[0]}_dailyET.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    df = read_bars(symbol=sym, timeframe="1m", start=dt.date(2018, 1, 1), end=dt.date(2026, 6, 1))
    ts = pd.to_datetime(df["ts_event"], utc=True).dt.tz_convert("America/New_York")
    s = df.assign(_ts=ts).set_index("_ts").between_time("09:30", "16:00")
    d = s.resample("1D").agg(open=("open", "first"), high=("high", "max"),
                             low=("low", "min"), close=("close", "last")).dropna()
    d.to_parquet(cache)
    return d


def weeks(d: pd.DataFrame) -> list[dict]:
    d = d.copy()
    d["dow"] = d.index.dayofweek
    iso = d.index.isocalendar()
    d["wk"] = iso.year.astype(int) * 100 + iso.week.astype(int)
    rows = []
    for _wk, g in d.groupby("wk"):
        mt = g[g["dow"] <= 3]
        fri = g[g["dow"] == 4]
        if len(mt) < 2 or len(fri) != 1:
            continue
        f = fri.iloc[0]
        move = float(mt["close"].iloc[-1] - mt["open"].iloc[0])
        rng = float(mt["high"].max() - mt["low"].min())
        if rng <= 0:
            continue
        rows.append(dict(move=move, rng=rng, mth=float(mt["high"].max()), mtl=float(mt["low"].min()),
                         fo=float(f["open"]), fh=float(f["high"]), fl=float(f["low"]), fc=float(f["close"]),
                         opex=15 <= fri.index[0].day <= 21))
    return rows


def fade_R(w: dict, tick: float) -> tuple[int, float]:
    """Return (side, net_R). side: -1 fade up-week (short), +1 fade down-week (long)."""
    side = -1 if w["move"] > 0 else 1
    entry = w["fo"]
    if side == -1:
        stop, tgt = w["mth"] + BUF * w["rng"], entry - RETRACE * w["rng"]
        risk = stop - entry
        if risk <= 0:
            return side, np.nan
        if w["fh"] >= stop:
            r = -1.0
        elif w["fl"] <= tgt:
            r = (entry - tgt) / risk
        else:
            r = (entry - w["fc"]) / risk
    else:
        stop, tgt = w["mtl"] - BUF * w["rng"], entry + RETRACE * w["rng"]
        risk = entry - stop
        if risk <= 0:
            return side, np.nan
        if w["fl"] <= stop:
            r = -1.0
        elif w["fh"] >= tgt:
            r = (tgt - entry) / risk
        else:
            r = (w["fc"] - entry) / risk
    return side, r - COST_TICKS * tick / risk


def cell(rs: list[float]) -> str:
    a = np.array([r for r in rs if np.isfinite(r)])
    if len(a) < 15:
        return f"n={len(a):3} (thin)"
    return f"E[R]={a.mean():+.3f} win={100*(a>0).mean():4.1f}% n={len(a):4}"


def main() -> int:
    print(f"TGIF weekly (expansion week -> Friday fade) | K={K} retrace={RETRACE} buf={BUF}\n")
    for sym, tick in SYMS.items():
        ws = weeks(daily_et(sym))
        amove = pd.Series([abs(w["move"]) for w in ws]).rolling(13).mean().shift(1)
        for i, w in enumerate(ws):
            w["exp"] = np.isfinite(amove.iloc[i]) and abs(w["move"]) > K * amove.iloc[i]
        res = [(w, *fade_R(w, tick)) for w in ws]
        print(f"== {sym} ==  ({len(ws)} weeks)")
        for label, filt in [("ALL weeks (baseline)", lambda w: True),
                            ("EXPANSION weeks", lambda w: w["exp"]),
                            ("EXPANSION + OPEX", lambda w: w["exp"] and w["opex"])]:
            for sd, slbl in [(1, "long "), (-1, "short")]:
                rs = [r for (w, side, r) in res if filt(w) and side == sd]
                print(f"  {label:22} {slbl}  {cell(rs)}")
        print()
    print("READ: TGIF real only if EXPANSION (esp +OPEX) beats baseline on BOTH long and short.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
