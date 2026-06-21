"""Diagnose why the LIVE Mira bot (long-only) under-trades vs the Jan OOS replay.

HARD DATA LIMIT: on-disk data ends 2026-05-22 (MBO 05-21, bars 05-22, SMT 05-22). The recent
window the bot actually traded (~May 23-Jun 5) is NOT replayable here. So instead of replaying the
recent window (impossible), this:
  A) characterizes the May-2026 regime from the bars I DO have (through 05-22), and
  B) measures the Jan-OOS LONG-arming RATE conditioned on day regime (down vs up) -> the estimator
     for how many longs a long-only bot SHOULD arm in a down-trending stretch.

Compare (B, down-day long rate x recent trading days) to the live bot's 2 entries.
No gate retuning. No live connection.

Run: backend/.venv/Scripts/python.exe experiments/sizing_v1/mira_recent_diagnosis.py
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BARS = Path(r"D:\data\processed\bars\timeframe=1m")
JAN = Path(r"C:\Users\benbr\bs-mira-v15\experiments\mira_v15_gate_validation"
          r"\out\mira_2026jan_real_mbo_oos_model_reclaim_2r_entries.parquet")
SYMS = ["ES.c.0", "NQ.c.0", "RTY.c.0", "YM.c.0"]
NOYM = ["ES.c.0", "NQ.c.0", "RTY.c.0"]


def bar_dates(symbol: str, lo: str, hi: str) -> list[str]:
    d = BARS / f"symbol={symbol}"
    if not d.exists():
        return []
    out = []
    for p in d.iterdir():
        if p.name.startswith("date="):
            ds = p.name.split("=", 1)[1]
            if lo <= ds <= hi:
                out.append(ds)
    return sorted(out)


def day_ret(symbol: str, date: str) -> float:
    p = BARS / f"symbol={symbol}" / f"date={date}"
    try:
        b = pd.read_parquet(p, columns=["ts_event", "open", "close"]).sort_values("ts_event")
    except Exception:
        return np.nan
    if b.empty:
        return np.nan
    o, c = float(b["open"].iloc[0]), float(b["close"].iloc[-1])
    return (c - o) / o if o else np.nan


def part_a_regime():
    print("=" * 80)
    print("A) MAY-2026 REGIME (from on-disk bars; last data = 2026-05-22). Recent tape continues past this.")
    print("=" * 80)
    dates = bar_dates("ES.c.0", "2026-05-01", "2026-05-31")
    print(f"   {'date':12s} " + "  ".join(f"{s.split('.')[0]:>7s}" for s in NOYM) + "   avg%")
    cum = {s: 0.0 for s in NOYM}
    downs = 0
    for d in dates:
        rs = {s: day_ret(s, d) for s in NOYM}
        for s in NOYM:
            if np.isfinite(rs[s]):
                cum[s] += rs[s]
        avg = np.nanmean([rs[s] for s in NOYM])
        downs += int(avg < 0)
        print(f"   {d:12s} " + "  ".join(f"{100*rs[s]:+6.2f}%" if np.isfinite(rs[s]) else '    n/a' for s in NOYM)
              + f"  {100*avg:+5.2f}%")
    print(f"   ---- cumulative open->close sum: " + "  ".join(f"{s.split('.')[0]}={100*cum[s]:+.1f}%" for s in NOYM))
    print(f"   down days (avg<0): {downs}/{len(dates)}")
    # late-May trend (the run-up to the cutoff / into the live window)
    late = [d for d in dates if d >= "2026-05-15"]
    lc = {s: sum(day_ret(s, d) for d in late if np.isfinite(day_ret(s, d))) for s in NOYM}
    print(f"   late-May (>=05-15) cum: " + "  ".join(f"{s.split('.')[0]}={100*lc[s]:+.1f}%" for s in NOYM))


def part_b_jan_armrate():
    print("\n" + "=" * 80)
    print("B) JAN-OOS LONG-ARMING RATE by day regime (estimator for the recent down-trend)")
    print("=" * 80)
    e = pd.read_parquet(JAN)
    e["entry_ts"] = pd.to_datetime(e["entry_ts"], utc=True)
    e["date"] = e["entry_ts"].dt.date.astype(str)
    e["direction"] = e["direction"].astype(int)

    # denominator: every (symbol, trading day) in the Jan OOS window
    rows = []
    for s in SYMS:
        for d in bar_dates(s, "2026-01-02", "2026-02-05"):
            g = e[(e.symbol == s) & (e.date == d)]
            rows.append({"symbol": s, "date": d, "dret": day_ret(s, d),
                         "longs": int((g.direction == 1).sum()),
                         "shorts": int((g.direction == -1).sum())})
    sd = pd.DataFrame(rows)
    sd["regime"] = np.where(sd["dret"] < 0, "down", "up")

    def block(name, df):
        n_sd = len(df)
        print(f"\n   [{name}]  symbol-days={n_sd}")
        print(f"   {'regime':8s} {'symDays':>7s} {'longs':>6s} {'shorts':>7s} "
              f"{'long/symday':>11s} {'short/symday':>12s} {'days>=1long%':>11s}")
        for rg in ["down", "up", "ALL"]:
            d = df if rg == "ALL" else df[df.regime == rg]
            if len(d) == 0:
                continue
            print(f"   {rg:8s} {len(d):>7d} {d.longs.sum():>6d} {d.shorts.sum():>7d} "
                  f"{d.longs.mean():>11.3f} {d.shorts.mean():>12.3f} {100*(d.longs>0).mean():>10.1f}%")

    block("ALL 4 symbols", sd)
    block("no-YM (live ES/NQ/RTY)", sd[sd.symbol.isin(NOYM)])

    # estimator: expected longs-only arms over a recent down-trending window
    noym = sd[sd.symbol.isin(NOYM)]
    down_rate = noym[noym.regime == "down"].longs.mean()
    all_rate = noym.longs.mean()
    print("\n   --- ESTIMATOR vs live bot's 2 entries ---")
    for ndays in [5, 7, 9]:
        print(f"   {ndays} recent trading days x 3 symbols: "
              f"expected longs @down-day-rate({down_rate:.3f})={ndays*3*down_rate:.1f}  "
              f"@all-rate({all_rate:.3f})={ndays*3*all_rate:.1f}")


def main() -> int:
    part_a_regime()
    part_b_jan_armrate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
