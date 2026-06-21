"""VALUE-AREA levels (Ben's non-high/low barrier): VAH / VAL (value-area edges, where volume thins
out = barriers) + POC (point of control, the high-volume magnet). Built from the PRIOR RTH day's
volume profile (per-1m-bar VWAP bucketed, weighted by volume; value area = 70% of volume around POC).
Prior-day profile is complete at session open => legal. Injected into the reclaim engine on indices.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/value_area_legal.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "backend"))
import legal_reclaim_bars as LB  # noqa: E402
import app.data.reader as R  # noqa: E402

SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0"]
START, END = dt.date(2025, 5, 1), dt.date(2026, 6, 9)
VA_FRAC = 0.70
FAMS = ["value_area"]


def build_va(sym: str) -> dict:
    """{session_date: (vah, val, poc)} from that day's RTH volume profile (used for the NEXT day)."""
    tick = LB.TICK[sym]
    df = R.read_bars(symbol=sym, timeframe="1m",
                     start=(START - dt.timedelta(days=10)).isoformat(), end=(END + dt.timedelta(days=2)).isoformat(),
                     columns=["ts_event", "vwap", "volume", "high", "low"])
    et = pd.DatetimeIndex(pd.to_datetime(df["ts_event"], utc=True)).tz_convert(LB.ET)
    minute = et.hour * 60 + et.minute
    rth = (minute >= 570) & (minute < 960)
    df = df[rth].copy()
    df["d"] = et[rth].date
    df["px"] = np.where(df["vwap"].notna() & (df["vwap"] > 0), df["vwap"], (df["high"] + df["low"]) / 2)
    out = {}
    for d, g in df.groupby("d"):
        bucket = (np.round(g["px"].to_numpy(float) / tick)).astype(np.int64)
        vol = g["volume"].to_numpy(float)
        prof = pd.Series(vol).groupby(bucket).sum().sort_index()
        if prof.empty or prof.sum() <= 0:
            continue
        poc_b = int(prof.idxmax())
        total = prof.sum()
        # expand around POC until >= VA_FRAC of volume
        lo = hi = poc_b
        acc = prof.get(poc_b, 0.0)
        bset = set(prof.index)
        while acc < VA_FRAC * total:
            up = prof.get(hi + 1, 0.0) if (hi + 1) in bset else -1
            dn = prof.get(lo - 1, 0.0) if (lo - 1) in bset else -1
            if up < 0 and dn < 0:
                break
            if up >= dn:
                hi += 1; acc += max(up, 0.0)
            else:
                lo -= 1; acc += max(dn, 0.0)
        out[d] = (hi * tick, lo * tick, poc_b * tick)  # vah, val, poc
    return out


VA = {s: build_va(s) for s in SYMBOLS}
_ORIG = LB.day_levels


def patched_day_levels(b, daily, day, tick):
    out = _ORIG(b, daily, day, tick)
    days = daily.index
    if day not in days:
        return out
    pos = days.get_loc(day)
    if pos == 0:
        return out
    prior = days[pos - 1]
    va = VA.get(_CUR["sym"], {}).get(prior)
    if va is None:
        return out
    vah, val, poc = va
    rth_ns = LB.et_ns(day, LB.RTH_START)
    topen = float(daily.loc[day, "open"])
    for px, lt in ((vah, "vah"), (val, "val"), (poc, "poc")):
        side = "low" if px <= topen else "high"
        out.append(dict(level_family="value_area", level_type=lt, side=side,
                        level_price=float(px), known_ns=rth_ns, search_ns=rth_ns))
    return out


_CUR = {"sym": None}
LB.day_levels = patched_day_levels


def main() -> int:
    parts = []
    for sym in SYMBOLS:
        _CUR["sym"] = sym
        res = LB.run_symbol_year(sym, START, END)
        if len(res):
            res = res[res["level_family"].isin(FAMS)].copy()
            parts.append(res)
        print(f"  {sym}: {len(res) if len(res) else 0} value-area attempts ({len(VA[sym])} days w/ profile)", flush=True)
    df = pd.concat(parts, ignore_index=True)
    out = LB.RUNS / "value_area_full.parquet"
    df.to_parquet(out, index=False)
    ent = df[df["status"] == "entered"]
    print(f"\nwrote {out}: {len(df)} attempts, {len(ent)} entered")
    for lt, g in ent.groupby("level_type"):
        x = pd.to_numeric(g["trail_2R"], errors="coerce").dropna()
        print(f"  {lt:6s} entered={len(g):4d}  raw meanR={x.mean():+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
