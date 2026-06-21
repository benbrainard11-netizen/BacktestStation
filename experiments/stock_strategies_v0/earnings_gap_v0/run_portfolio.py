"""Portfolio simulation for the earnings strategy — the HONEST equity curve the sequential
MC couldn't give: real concurrency. Walks calendar time, opens positions only within a
position-count cap AND an aggregate-open-risk cap, sizes each at a fixed % of CURRENT equity,
realizes P&L on exit. When capacity-limited, prioritizes the BIGGEST gaps.

Reveals the capacity reality: ~300 setups/yr with multi-week holds => many want in at once;
you can't risk 1% on all of them. Dev window 2010-2025 (holdout sealed).
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from shell import ShellConfig, Signal, run_signals  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
study = pd.read_parquet(OUT / "earnings_study.parquet")
setup = study[(study["gap"] >= 0.075) & (study["above_high"])].copy()
sigs = [Signal(r.ticker, r.dt, tag="earnings_gap") for r in setup.itertuples()]
tr = run_signals(sigs, ShellConfig(entry_mode="signal_open", stop_mode="pct", stop_pct=0.08,
                                   do_partial=False, move_to_be=False, trail_ma="ma20"))
tr["entry_dt"] = pd.to_datetime(tr["entry_date"])
tr["exit_dt"] = pd.to_datetime(tr["exit_date"])
tr = tr.merge(setup[["ticker", "dt", "gap"]].rename(columns={"dt": "entry_dt"}),
              on=["ticker", "entry_dt"], how="left")
tr["gap"] = tr["gap"].fillna(0.075)


def simulate(trades, risk_frac, max_pos, max_agg, start=10_000.0):
    dates = pd.Index(sorted(set(trades["entry_dt"]) | set(trades["exit_dt"])))
    by_entry = {d: g for d, g in trades.groupby("entry_dt")}
    eq = start
    open_pos = []                       # (exit_dt, risk_dollars, R)
    taken = skipped = 0
    conc, curve = [], []
    for d in dates:
        for p in [p for p in open_pos if p[0] == d]:
            eq += p[2] * p[1]           # realize R * risk_$
        open_pos = [p for p in open_pos if p[0] != d]
        cand = by_entry.get(d)
        if cand is not None:
            for r in cand.sort_values("gap", ascending=False).itertuples():  # best gaps first
                open_risk = sum(p[1] for p in open_pos)
                new_risk = risk_frac * eq
                if len(open_pos) < max_pos and (open_risk + new_risk) <= max_agg * eq:
                    open_pos.append((r.exit_dt, new_risk, r.realized_r)); taken += 1
                else:
                    skipped += 1
        conc.append(len(open_pos)); curve.append((d, eq))
    for p in open_pos:
        eq += p[2] * p[1]
    cv = pd.Series([e for _, e in curve], index=[d for d, _ in curve])
    yrs = (cv.index[-1] - cv.index[0]).days / 365.25
    cagr = (eq / start) ** (1 / yrs) - 1
    dd = ((cv.cummax() - cv) / cv.cummax()).max()
    return dict(end=eq, cagr=cagr, maxdd=dd, taken=taken, skipped=skipped,
                avg_conc=np.mean(conc), max_conc=max(conc), yrs=yrs), cv


print(f"{len(tr)} trades, {tr['entry_dt'].min().date()}..{tr['exit_dt'].max().date()}\n")
print(f"{'config':38s} {'CAGR':>7} {'maxDD':>6} {'end$':>9} {'taken':>6} {'skip%':>6} {'avgPos':>7} {'maxPos':>7}")
configs = [
    ("1% risk, 10 pos, 15% agg", 0.01, 10, 0.15),
    ("1% risk, 20 pos, 25% agg", 0.01, 20, 0.25),
    ("0.5% risk, 30 pos, 20% agg", 0.005, 30, 0.20),
    ("0.5% risk, 50 pos, 30% agg", 0.005, 50, 0.30),
]
best = None
for name, rf, mp, ma in configs:
    s, cv = simulate(tr, rf, mp, ma)
    skp = s["skipped"] / (s["taken"] + s["skipped"]) * 100
    print(f"{name:38s} {s['cagr']*100:6.1f}% {s['maxdd']*100:5.0f}% {s['end']:9,.0f} "
          f"{s['taken']:6d} {skp:5.0f}% {s['avg_conc']:7.1f} {s['max_conc']:7d}")
    if best is None:
        best = cv
best.to_frame("equity").to_parquet(OUT / "portfolio_curve.parquet")
print("\nNOTE: closed-trade equity (intra-trade DD not marked). Holdout sealed (<=2025-09).")
print("Capacity rationing is real: high skip% = the strategy wants more slots than risk allows.")
