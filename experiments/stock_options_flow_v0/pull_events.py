"""Step-A targeted pull: options around the top-N liquid earnings UP-GAP events, for the convex-call
scale test. Pulls ONLY the expirations that matter per event (the monthly a ~30-DTE call would use),
not full history -> tractable (~150 events -> a couple hours). Resumable (theta_store cache skip).

Self-contained: builds the event list from earnings_clean (gap>=10%, above prior high, liquid, 2023-2026),
then pulls eod_greeks + OI for each event's target expiration(s). Single sequential worker (concurrency
wedges the terminals). Writes the frozen event list to out/event_list_topN.parquet for the backtest.

Run (via the watchdog, MINIMIZE the window): THETA_PORT=25510 python pull_events.py [N=30]
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "options_signals_v0"))
import theta_store as TS  # noqa: E402
from gex_pull import _ymd  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
DTE_LO, DTE_HI = 15, 49          # next monthly is always <=~44 DTE away -> full event coverage (no DTE-gap bias)
WINDOW = 49                      # per-exp fetch window; the Step-A backtest loader uses the SAME so keys ALIGN
BT_START, BT_END = "2023-01-01", "2026-06-30"  # same bounds the backtest uses
OUT = HERE / "out"
EARN = ROOT / "experiments" / "stock_strategies_v0" / "earnings_gap_v0" / "out" / "earnings_clean.parquet"


def event_list(n: int) -> pd.DataFrame:
    df = pd.read_parquet(EARN)
    up = df[(df["above_high"] == 1) & (df["gap"] >= 0.10) &
            (df["date"] >= 20230101) & (df["date"] <= 20260301)].copy()
    liq = (up.groupby("ticker").agg(events=("gap", "size"), dvol=("dvol", "median")).reset_index())
    liq = liq[liq["dvol"] > 5e6].sort_values(["events", "dvol"], ascending=False)
    names = list(liq.head(n)["ticker"])
    ev = up[up["ticker"].isin(names)][["ticker", "date", "gap", "x20"]].sort_values(["ticker", "date"])
    OUT.mkdir(parents=True, exist_ok=True)
    ev.to_parquet(OUT / f"event_list_top{n}.parquet")
    print(f"event list: {len(ev)} events across {ev['ticker'].nunique()} names -> event_list_top{n}.parquet", flush=True)
    return ev


def monthly_exps_after(d_int: int) -> list[int]:
    """3rd-Friday monthlies whose DTE from d is in [DTE_LO, DTE_HI] (local calendar gen, no terminal call)."""
    d = pd.Timestamp(str(d_int))
    out = []
    m = pd.Timestamp(year=d.year, month=d.month, day=1)
    for _ in range(4):                                    # this month + next 3
        fris = [x for x in pd.date_range(m, m + pd.offsets.MonthEnd(0)) if x.weekday() == 4]
        if len(fris) >= 3:
            e = fris[2]
            dte = (e - d).days
            if DTE_LO <= dte <= DTE_HI:
                out.append(int(e.strftime("%Y%m%d")))
        m = m + pd.offsets.MonthBegin(1)
    return out


def main() -> int:
    t0 = time.time()
    ev = event_list(N)
    # de-dup (ticker, target-exp, window) fetches across events that share a monthly
    jobs = {}
    for _, e in ev.iterrows():
        for exp in monthly_exps_after(int(e["date"])):
            s = max(_ymd(BT_START), _ymd(pd.Timestamp(str(exp)) - pd.Timedelta(days=WINDOW)))
            en = min(_ymd(BT_END), exp)
            jobs[(e["ticker"], exp, s, en)] = True
    jobs = list(jobs)
    print(f"{len(jobs)} expiration-fetches to pull (resumable; cached ones skip instantly)", flush=True)
    ok = empty = err = 0
    for i, (root, exp, s, en) in enumerate(jobs, 1):
        try:
            gk = TS.fetch("bulk_hist/option/eod_greeks", root=root, exp=exp, start_date=s, end_date=en)
            TS.fetch("bulk_hist/option/open_interest", root=root, exp=exp, start_date=s, end_date=en)
            ok += 1 if (gk is not None and not gk.empty) else 0
            empty += 1 if (gk is None or gk.empty) else 0
        except Exception as ex:
            err += 1
            print(f"  [{root} {exp}] ERR {type(ex).__name__}: {str(ex)[:50]}", flush=True)
        if i % 10 == 0 or i == len(jobs):
            print(f"  {i}/{len(jobs)} ok={ok} empty={empty} err={err}  {(time.time()-t0)/60:.0f}min", flush=True)
    print(f"DONE: ok={ok} empty={empty} err={err}  {(time.time()-t0)/60:.1f}min", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
