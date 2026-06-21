"""rv_backtest — honest day-flat intraday relative-value (cointegration spread) backtest.

The causal diagnostic showed CL-BZ and ZN-ZF intraday spreads mean-revert (~+0.7 std/30m, ~65%).
This turns that into a real, automatable, DAY-FLAT, market-neutral strategy and charges it honestly:
  * CAUSAL hedge ratio beta: rolling OLS of leg1~leg2 on the prior BETA_LB daily closes (no future).
  * CAUSAL trailing z: spread vs prior-W-bar mean/std within the day (shift(1), no future).
  * ONE position at a time (no overlapping observations): enter |z|>ENTRY, exit |z|<EXIT or MAX_HOLD
    bars or session close (day-flat).
  * HONEST 2-leg cost: both legs cross ~1 tick on entry AND exit + per-contract commission, sized by
    the dollar-neutral hedge (h2 = beta*pv1/pv2 leg2 contracts per 1 leg1).
  * design <= 2024-12-31 ; holdout 2025-01-01 -> 2025-12-31 (sealed).

  python rv_backtest.py CL.c.0 BZ.c.0
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prop_futures_v0"))
from orb_engine import build_dataset, get_spec  # noqa: E402

START, DESIGN_END, HOLD_END = "2022-01-01", "2024-12-31", "2025-12-31"
OPEN_M, CLOSE_M = 570, 960
W, ENTRY, EXIT, MAX_HOLD, BETA_LB = 60, 2.0, 0.5, 120, 20


def prepare(a, b):
    """Load both legs, causal daily beta + causal trailing z. Returns (m, sa, sb)."""
    sa, sb = get_spec(a), get_spec(b)
    da = build_dataset(a, START, HOLD_END); db = build_dataset(b, START, HOLD_END)
    for d in (da, db):
        d.drop(d.index[(d["mod"] < OPEN_M) | (d["mod"] >= CLOSE_M)], inplace=True)
    m = da[["et", "close", "date_et", "mod"]].merge(db[["et", "close"]], on="et", suffixes=("_a", "_b"))
    daily = m.groupby("date_et").agg(a=("close_a", "last"), b=("close_b", "last"))
    betas = {}
    dts = daily.index.to_list()
    for i in range(len(dts)):
        if i < BETA_LB:
            continue
        wa = daily["a"].iloc[i - BETA_LB:i].to_numpy(); wb = daily["b"].iloc[i - BETA_LB:i].to_numpy()
        betas[dts[i]] = float(np.polyfit(wb, wa, 1)[0])
    m["beta"] = m["date_et"].map(betas)
    m = m.dropna(subset=["beta"])
    m["spread"] = m["close_a"] - m["beta"] * m["close_b"]
    g = m.groupby("date_et")["spread"]
    m["z"] = (m["spread"] - g.transform(lambda s: s.rolling(W, min_periods=20).mean().shift(1))) \
        / g.transform(lambda s: s.rolling(W, min_periods=20).std().shift(1))
    return m, sa, sb


def simulate(m, sa, sb, entry=ENTRY, exit_thr=EXIT):
    trades = []
    for date, day in m.groupby("date_et"):
        z = day["z"].to_numpy(); sp = day["spread"].to_numpy(); beta = float(day["beta"].iloc[0])
        h2 = abs(beta) * sa.contract_value / sb.contract_value
        cost = (2 * sa.tick_size * sa.contract_value + 2 * abs(beta) * sb.tick_size * sa.contract_value
                + sa.commission_per_contract + sb.commission_per_contract * h2)
        pos = 0; e_sp = 0.0; e_i = 0; n = len(day)
        for i in range(n):
            if pos == 0:
                if not np.isnan(z[i]) and abs(z[i]) > entry:
                    pos = -1 if z[i] > 0 else 1; e_sp = sp[i]; e_i = i
            else:
                if (not np.isnan(z[i]) and abs(z[i]) < exit_thr) or (i - e_i >= MAX_HOLD) or (i == n - 1):
                    pnl = pos * (sp[i] - e_sp) * sa.contract_value - cost
                    trades.append({"date": int(pd.Timestamp(date).strftime("%Y%m%d")),
                                   "pnl": pnl, "gross": pos * (sp[i] - e_sp) * sa.contract_value,
                                   "cost": cost, "held": i - e_i})
                    pos = 0
    return pd.DataFrame(trades)


def run(a, b, entry=ENTRY, exit_thr=EXIT, verbose=True):
    m, sa, sb = prepare(a, b)
    t = simulate(m, sa, sb, entry, exit_thr)
    if verbose:
        rep(a, b, t)
    return t


def split_stats(t):
    """design/holdout net$/trade summaries from a trades df."""
    de = int(DESIGN_END.replace("-", ""))
    out = {}
    for split, lo, hi in [("design", 0, de), ("holdout", de + 1, 99999999)]:
        s = t[(t.date >= lo) & (t.date <= hi)]
        net = s.pnl.to_numpy()
        out[split] = (dict(n=len(s), net=float(net.mean()), gross=float(s.gross.mean()),
                           win=float((net > 0).mean()), total=float(net.sum()))
                      if len(s) >= 10 else dict(n=len(s), net=float("nan")))
    return out


def rep(a, b, t):
    print(f"\n== {a}-{b} RV (entry|z|>{ENTRY}, exit<{EXIT}, day-flat) ==")
    for split, lo, hi in [("design", 0, int(DESIGN_END.replace("-", ""))),
                          ("holdout", int(DESIGN_END.replace("-", "")) + 1, 99999999)]:
        s = t[(t.date >= lo) & (t.date <= hi)]
        if len(s) < 10:
            print(f"  {split}: n={len(s)} too few"); continue
        net = s.pnl.to_numpy()
        shp = net.mean() / (net.std() + 1e-9) * np.sqrt(252)  # ~daily-ish Sharpe proxy (trades~/day)
        print(f"  {split:7s} n={len(s):4d} net$/trade={net.mean():+7.1f} gross={s.gross.mean():+7.1f} "
              f"cost={s.cost.mean():5.1f} win={(net>0).mean():.3f} total=${net.sum():+,.0f} "
              f"perTradeSharpe={net.mean()/(net.std()+1e-9):+.3f} held={s.held.mean():.0f}m")


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "CL.c.0"
    b = sys.argv[2] if len(sys.argv) > 2 else "BZ.c.0"
    run(a, b)
