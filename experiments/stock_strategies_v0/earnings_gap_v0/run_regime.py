"""Apply the doc's REGIME FILTER to the earnings strategy and measure the drawdown impact.
Risk-on = SPY AND QQQ both have MA10>MA20 AND neither is >10% below its 63d high. Evaluated
on the PRIOR trading day (causal). Compares per-trade R and the portfolio curve, risk-on-only
vs all. Dev window 2010-2025. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import loaders as L  # noqa: E402
from shell import ShellConfig, Signal, run_signals  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def index_on(t):
    d = L.with_mas(L.load_etf(t)).set_index("dt")
    hi63 = d["close"].rolling(63).max()
    return (d["ma10"] > d["ma20"]) & (d["close"] >= 0.90 * hi63)


risk_on = (index_on("SPY") & index_on("QQQ")).dropna()
regime_prior = risk_on.shift(1)              # causal: yesterday's regime for today's entry

study = pd.read_parquet(OUT / "earnings_study.parquet")
setup = study[(study["gap"] >= 0.075) & (study["above_high"])].copy()
sigs = [Signal(r.ticker, r.dt, tag="earnings_gap") for r in setup.itertuples()]
tr = run_signals(sigs, ShellConfig(entry_mode="signal_open", stop_mode="pct", stop_pct=0.08,
                                   do_partial=False, move_to_be=False, trail_ma="ma20"))
tr["entry_dt"] = pd.to_datetime(tr["entry_date"])
tr["exit_dt"] = pd.to_datetime(tr["exit_date"])
tr = tr.merge(setup[["ticker", "dt", "gap"]].rename(columns={"dt": "entry_dt"}), on=["ticker", "entry_dt"], how="left")
tr["gap"] = tr["gap"].fillna(0.075)
tr["on"] = tr["entry_dt"].map(lambda d: bool(regime_prior.asof(d)) if pd.notna(regime_prior.asof(d)) else False)

on, off = tr[tr["on"]], tr[~tr["on"]]
wc = lambda r: np.clip(r, -1.5, 15).mean()
print(f"signals: {len(tr)} | risk-ON {len(on)} ({len(on)/len(tr)*100:.0f}%) | risk-OFF {len(off)}")
print(f"per-trade R:  risk-ON {wc(on['realized_r']):+.3f} (win {(on['realized_r']>0).mean()*100:.0f}%)"
      f"  |  risk-OFF {wc(off['realized_r']):+.3f} (win {(off['realized_r']>0).mean()*100:.0f}%)")


def simulate(trades, risk_frac, max_pos, max_agg, start=10_000.0):
    dates = pd.Index(sorted(set(trades["entry_dt"]) | set(trades["exit_dt"])))
    by_entry = {d: g for d, g in trades.groupby("entry_dt")}
    eq, open_pos, taken, skipped, curve = start, [], 0, 0, []
    for d in dates:
        for p in [p for p in open_pos if p[0] == d]:
            eq += p[2] * p[1]
        open_pos = [p for p in open_pos if p[0] != d]
        cand = by_entry.get(d)
        if cand is not None:
            for r in cand.sort_values("gap", ascending=False).itertuples():
                if len(open_pos) < max_pos and (sum(p[1] for p in open_pos) + risk_frac * eq) <= max_agg * eq:
                    open_pos.append((r.exit_dt, risk_frac * eq, r.realized_r)); taken += 1
                else:
                    skipped += 1
        curve.append((d, eq))
    for p in open_pos:
        eq += p[2] * p[1]
    cv = pd.Series([e for _, e in curve], index=[d for d, _ in curve])
    yrs = (cv.index[-1] - cv.index[0]).days / 365.25
    return dict(cagr=(eq / start) ** (1 / yrs) - 1, maxdd=((cv.cummax() - cv) / cv.cummax()).max(),
                end=eq, taken=taken), cv


print(f"\n{'config':28s} {'universe':10s} {'CAGR':>7} {'maxDD':>6} {'Calmar':>7} {'taken':>6}")
for name, rf, mp, ma in [("1% / 10pos / 15%", 0.01, 10, 0.15), ("0.5% / 30pos / 20%", 0.005, 30, 0.20)]:
    for lab, sub in [("ALL", tr), ("regime-ON", on)]:
        s, cv = simulate(sub, rf, mp, ma)
        cal = s["cagr"] / s["maxdd"] if s["maxdd"] > 0 else float("nan")
        print(f"{name:28s} {lab:10s} {s['cagr']*100:6.1f}% {s['maxdd']*100:5.0f}% {cal:7.2f} {s['taken']:6d}")
        if lab == "regime-ON" and name.startswith("0.5"):
            cv.to_frame("equity").to_parquet(OUT / "portfolio_curve_regime.parquet")
print("\nREAD: if regime-ON cuts maxDD more than CAGR (higher Calmar), the filter earns its keep.")
