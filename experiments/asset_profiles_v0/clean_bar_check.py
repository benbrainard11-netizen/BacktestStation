"""Foundation check: is the RB/HO FVG edge real, or a legacy-5m-bar-construction artifact?

Rebuilds 5-min bars from the DENSE local MBP-1 tick data (clean mid = (bid+ask)/2, resampled), then re-runs the
FVG long+short alpha-vs-beta on those clean bars -- and on the LEGACY read_bars 5m over the SAME window. If the
two agree, the bars are fine and the edge is trustworthy; if the legacy bars show an edge the clean bars don't,
it was an artifact. MBP-1 covers ~1yr (2025-05+), so this is a recent-window confirmation, not the full history.

Run (background): backend/.venv/Scripts/python.exe experiments/asset_profiles_v0/clean_bar_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "backend")
from app.core.paths import warehouse_root  # noqa: E402
from app.data.reader import read_bars, read_mbp1  # noqa: E402

MAXWAIT, HOLD, TRAIL = 48, 48, 1.0
TICK = {"RB.c.0": 0.0001, "HO.c.0": 0.0001}
SYMS = ["RB.c.0", "HO.c.0"]


def mbp1_5m(sym: str) -> pd.DataFrame:
    """Clean 5m OHLC bars built from MBP-1 mid, read month-by-month to bound memory."""
    p = warehouse_root() / "raw/databento/mbp-1" / f"symbol={sym}"
    dates = sorted(d.name.split("=")[1] for d in p.iterdir() if d.is_dir())
    months = sorted({d[:7] for d in dates})
    out = []
    for m in months:
        s = pd.Timestamp(m + "-01")
        e = (s + pd.offsets.MonthBegin(1)).date().isoformat()
        try:
            t = read_mbp1(symbol=sym, start=s.date().isoformat(), end=e, columns=["ts_event", "bid_px", "ask_px"])
        except Exception:  # noqa: BLE001
            continue
        if len(t) == 0:
            continue
        t = t.dropna(subset=["bid_px", "ask_px"])
        mid = pd.Series(((t["bid_px"] + t["ask_px"]) / 2.0).to_numpy(),
                        index=pd.to_datetime(t["ts_event"].to_numpy(), utc=True))
        out.append(mid.resample("5min").ohlc().dropna())
    b = pd.concat(out)
    b.columns = ["open", "high", "low", "close"]
    return b


def sim(b: pd.DataFrame, side: int) -> pd.DataFrame:
    h, l, c = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    n = len(b)
    rows = []
    for i in range(2, n):
        if side == 1 and not (l[i] > h[i - 2]):
            continue
        if side == -1 and not (h[i] < l[i - 2]):
            continue
        ztrig = l[i] if side == 1 else h[i]
        zbreak = h[i - 2] if side == 1 else l[i - 2]
        fired, tap, e = False, None, -1
        for t in range(i + 1, min(i + MAXWAIT, n - 1) + 1):
            fired = fired or (l[t] <= ztrig if side == 1 else h[t] >= ztrig)
            if not fired:
                continue
            tap = (l[t] if side == 1 else h[t]) if tap is None else (min(tap, l[t]) if side == 1 else max(tap, h[t]))
            if (l[t] < zbreak) if side == 1 else (h[t] > zbreak):
                break
            if (c[t] > ztrig) if side == 1 else (c[t] < ztrig):
                e = t
                break
        if e < 0:
            continue
        entry = c[e]
        risk = (entry - tap) if side == 1 else (tap - entry)
        if risk <= 0:
            continue
        end = min(e + HOLD, n - 1)
        peak, tstop, r = entry, tap, None
        for t in range(e + 1, end + 1):
            if (l[t] <= tstop) if side == 1 else (h[t] >= tstop):
                r = (tstop - entry) / risk if side == 1 else (entry - tstop) / risk
                break
            if side == 1:
                peak = max(peak, h[t]); tstop = max(tstop, peak - TRAIL * risk)
            else:
                peak = min(peak, l[t]); tstop = min(tstop, peak + TRAIL * risk)
        if r is None:
            r = (c[end] - entry) / risk if side == 1 else (entry - c[end]) / risk
        rows.append((r, risk))
    return pd.DataFrame(rows, columns=["r", "risk"])


def er(tr: pd.DataFrame, tick: float) -> float:
    return float((tr["r"] - 2 * tick / tr["risk"]).mean()) if len(tr) else float("nan")


def main() -> int:
    for sym in SYMS:
        tick = TICK[sym]
        clean = mbp1_5m(sym)
        lo, hi = clean.index.min(), clean.index.max()
        leg = read_bars(symbol=sym, timeframe="5m", start=lo.date().isoformat(), end=hi.date().isoformat())
        leg = leg.set_index("ts_event")[["open", "high", "low", "close"]].sort_index()
        leg = leg[~leg.index.duplicated(keep="first")]
        print(f"\n===== {sym}  {lo.date()}..{hi.date()} =====")
        print(f"  clean MBP-1 bars: {len(clean):,}   legacy bars: {len(leg):,}")
        for name, b in (("CLEAN(mbp1)", clean), ("LEGACY(read_bars)", leg)):
            el, es = er(sim(b, 1), tick), er(sim(b, -1), tick)
            print(f"  {name:18} LONG E[R]={el:+.3f}  SHORT E[R]={es:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
