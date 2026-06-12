"""HOLDOUT SHOT #1 — the one screen survivor, pre-registered, fired once.

Survivor (screen_v0: net +16.9 bps/day, week-block p5 +5.6, consistent in both
halves +23.0/+9.7): LONG BTC.c.0 when close > 50-day MA, flat otherwise. Daily
evaluation at the Globex roll; 60-pt round-trip cost charged on each flip.
No other config from the screen is tested on the holdout, ever.

Holdout: 2025-06-10 -> 2026-06-09 (sealed until this run). Also reports design-window
buy-and-hold for context (is the filter beating raw drift or just riding it?).

Run: backend/.venv/Scripts/python.exe experiments/btc_edge_v0/holdout_shot.py
Result is appended to README.md win or lose.
"""

from __future__ import annotations

import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

MODULE = Path(__file__).resolve().parent
ET = ZoneInfo("America/New_York")
HOLDOUT_START = pd.Timestamp("2025-06-10")
COST_PTS = 60.0
N_BOOT = 2000

sys.stdout.reconfigure(encoding="utf-8")


def week_boot(vals, weeks, q, seed=0):
    uniq, inv = np.unique(weeks, return_inverse=True)
    sums = np.zeros(len(uniq))
    cnts = np.zeros(len(uniq))
    np.add.at(sums, inv, vals)
    np.add.at(cnts, inv, 1.0)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(uniq), size=(N_BOOT, len(uniq)))
    means = sums[draws].sum(axis=1) / np.maximum(cnts[draws].sum(axis=1), 1.0)
    return float(np.percentile(means, q))


def main() -> int:
    b = pd.read_parquet(MODULE / "data" / "btc_1m.parquet")
    ts = b.index.tz_convert(ET)
    df = pd.DataFrame({"c": b["close"].to_numpy(float)}, index=ts).sort_index()
    tod = df.index.hour * 60 + df.index.minute
    td = df.index.normalize() + pd.to_timedelta((tod >= 1080).astype(int), unit="D")
    wd = td.weekday
    td = td + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D")
    df["td"] = td.date
    day = df.groupby("td").agg(c=("c", "last"), n=("c", "size"))
    day = day[day["n"] > 200]
    day.index = pd.to_datetime(day.index)
    day["ret"] = day["c"].pct_change()
    day["week"] = day.index.to_period("W").astype(str)
    # signal computed on the FULL series (MA at holdout start legally uses design data)
    sig = (day["c"] > day["c"].rolling(50).mean()).astype(float)
    pnl = sig.shift(1) * day["ret"] * 1e4
    flips = (sig != sig.shift(1)).astype(float)
    net = pnl - flips.shift(1).fillna(0) * (COST_PTS / day["c"] * 1e4)

    hold = net[net.index >= HOLDOUT_START].dropna()
    w = day.loc[hold.index, "week"].to_numpy()
    in_pos = float(sig.reindex(hold.index).mean())
    bh = (day["ret"][day.index >= HOLDOUT_START] * 1e4).dropna()
    bh_design = (day["ret"][day.index < HOLDOUT_START] * 1e4).dropna()

    print("=== HOLDOUT SHOT #1: above_50dma_long ===")
    print(f"holdout days: {len(hold)} ({hold.index.min().date()} -> {hold.index.max().date()})")
    print(f"net mean: {hold.mean():+.1f} bps/day | week-block p5: {week_boot(hold.to_numpy(), w, 5):+.1f} "
          f"| p25: {week_boot(hold.to_numpy(), w, 25):+.1f}")
    print(f"cumulative: {hold.sum() / 100:+.1f}% | in-position share: {in_pos:.0%} | flips: {int(flips[flips.index >= HOLDOUT_START].sum())}")
    print(f"buy-and-hold holdout: {bh.mean():+.1f} bps/day (cum {bh.sum() / 100:+.1f}%)")
    print(f"context — design-window buy-and-hold: {bh_design.mean():+.1f} bps/day "
          f"(strategy design net was +16.9)")
    verdict = "PASS" if week_boot(hold.to_numpy(), w, 25) > 0 and hold.mean() > 0 else (
        "WEAK PASS" if hold.mean() > 0 else "FAIL")
    print(f"VERDICT: {verdict} (bar: mean > 0 and week-block p25 > 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
