"""MORE LEVELS: intraday SWING highs/lows as reclaim families. Every completed 5m/15m/30m candle's
high (resistance) and low (support) becomes a level, KNOWN at the candle close (legal), searchable
after. These are frequent barrier levels (recent swing extremes = where stops rest). Injected into
the legal reclaim engine on the indices (where the edge lives), 13mo. Then flow_mbp1_stack + test.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/swing_levels_legal.py
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

SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0"]  # liquid-3 (edge is index-specific)
START, END = dt.date(2025, 5, 1), dt.date(2026, 6, 9)
SWING_TFS = {"5m": 5, "15m": 15, "30m": 30}
_NS = 1_000_000_000
_ORIG = LB.day_levels


def patched_day_levels(b, daily, day, tick):
    out = _ORIG(b, daily, day, tick)
    m = b.rth & (b.et_date == day)
    if not m.any():
        return out
    idx = pd.DatetimeIndex(pd.to_datetime(b.ts[m], utc=True))
    df = pd.DataFrame({"high": b.h[m], "low": b.l[m]}, index=idx)
    rth_end_ns = LB.et_ns(day, LB.RTH_END)
    for tf, mins in SWING_TFS.items():
        res = df.resample(f"{mins}min", label="left", closed="left").agg({"high": "max", "low": "min"}).dropna()
        for start, row in res.iterrows():
            close_ns = int(start.value) + mins * 60 * _NS  # candle close = known time
            if close_ns > rth_end_ns:
                continue
            out.append(dict(level_family=f"swing_{tf}", level_type=f"sh{tf}", side="high",
                            level_price=float(row["high"]), known_ns=close_ns, search_ns=close_ns))
            out.append(dict(level_family=f"swing_{tf}", level_type=f"sl{tf}", side="low",
                            level_price=float(row["low"]), known_ns=close_ns, search_ns=close_ns))
    return out


LB.day_levels = patched_day_levels
FAMS = [f"swing_{tf}" for tf in SWING_TFS]


def main() -> int:
    parts = []
    for sym in SYMBOLS:
        res = LB.run_symbol_year(sym, START, END)
        if len(res):
            res = res[res["level_family"].isin(FAMS)].copy()
            parts.append(res)
        n = len(res) if len(res) else 0
        print(f"  {sym}: {n} swing attempts", flush=True)
    df = pd.concat(parts, ignore_index=True)
    out = LB.RUNS / "swing_levels_full.parquet"
    df.to_parquet(out, index=False)
    ent = df[df["status"] == "entered"]
    print(f"\nwrote {out}: {len(df)} attempts, {len(ent)} entered")
    for fam, g in ent.groupby("level_family"):
        x = pd.to_numeric(g["trail_2R"], errors="coerce").dropna()
        print(f"  {fam:10s} entered={len(g):5d}  raw reaction meanR={x.mean():+.3f} (pre-selection)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
