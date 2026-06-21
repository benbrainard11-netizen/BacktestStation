"""Cross-sectional relative-value scan across the broad futures universe (options 2+3).

Market-neutral: each day rank assets by vol-adjusted trailing return, go long the
top-k / short the bottom-k, inverse-vol weighted within each leg (risk-balanced),
dollar-neutral. No market-direction bet. Scans the lookback term-structure to find
momentum (long winners) vs short-term reversal (long losers), reports gross + net
(cost-stressed) Sharpe, CAGR, maxDD, turnover, and an out-of-sample split.

No-lookahead: weights formed from data through day t are applied to day t+1 returns
(single .shift(1)); momentum signal also skips the most recent `skip` days.

Run: backend/.venv/Scripts/python.exe experiments/xsectional_rv_v0/scan_cross_sectional.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

R = pd.read_parquet(Path(__file__).resolve().parents[1] / "sync_regime_v0" / "out" / "daily_returns.parquet")
R.index = pd.to_datetime(R.index)
VOL = R.rolling(60, min_periods=20).std()
ANN = np.sqrt(252.0)
OOS_START = pd.Timestamp("2023-01-01", tz="UTC")


def strat(lookback: int, k: int = 5, skip: int = 1, cost_bps: float = 2.0):
    mom = R.rolling(lookback, min_periods=max(1, lookback // 2)).sum().shift(skip)
    score = mom / VOL
    iv = 1.0 / VOL
    W = pd.DataFrame(0.0, index=R.index, columns=R.columns)
    for t in score.index:
        s = score.loc[t].dropna()
        if len(s) < 2 * k:
            continue
        longs, shorts = s.nlargest(k).index, s.nsmallest(k).index
        lw = iv.loc[t, longs]; sw = iv.loc[t, shorts]
        W.loc[t, longs] = (lw / lw.sum()).to_numpy()
        W.loc[t, shorts] = -(sw / sw.sum()).to_numpy()
    pnl = (W.shift(1) * R).sum(axis=1)
    turn = W.diff().abs().sum(axis=1)
    net = pnl - turn * cost_bps / 1e4
    return pnl, net, turn


GROUPS = {
    "equity": ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"],
    "rates": ["ZT.c.0", "ZF.c.0", "ZN.c.0", "ZB.c.0"],
    "energy": ["CL.c.0", "BZ.c.0", "HO.c.0", "RB.c.0", "NG.c.0"],
    "fx": ["6E.c.0", "6B.c.0", "6J.c.0", "6A.c.0", "6C.c.0", "6S.c.0", "6N.c.0"],
    "metals": ["GC.c.0", "SI.c.0", "HG.c.0"],
    "grains": ["ZC.c.0", "ZS.c.0", "ZW.c.0"],
}


def strat_grouped(lookback: int, skip: int = 1, cost_bps: float = 2.0):
    """Within-group (sector-neutral) relative value: rank only inside each correlated
    complex, dollar-neutral per group, then combine groups equally."""
    score = (R.rolling(lookback, min_periods=max(1, lookback // 2)).sum().shift(skip)) / VOL
    W = pd.DataFrame(0.0, index=R.index, columns=R.columns)
    active = [g for g, m in GROUPS.items() if len([x for x in m if x in R.columns]) >= 2]
    for g in active:
        members = [x for x in GROUPS[g] if x in R.columns]
        z = score[members].sub(score[members].mean(axis=1), axis=0)
        gw = z.div(z.abs().sum(axis=1), axis=0).fillna(0.0)
        W[members] = W[members].add(gw / len(active), fill_value=0.0)
    pnl = (W.shift(1) * R).sum(axis=1)
    turn = W.diff().abs().sum(axis=1)
    net = pnl - turn * cost_bps / 1e4
    return pnl, net, turn


def stats(x: pd.Series) -> dict:
    x = x.dropna()
    if x.std() == 0 or len(x) < 50:
        return {"sharpe": np.nan, "cagr": np.nan, "maxdd": np.nan}
    eq = x.cumsum()
    dd = (eq - eq.cummax()).min()
    return {"sharpe": float(x.mean() / x.std() * ANN),
            "cagr": float(x.mean() * 252),
            "maxdd": float(dd)}


def main() -> int:
    print(f"panel: {R.shape[0]} days x {R.shape[1]} assets  {R.index.min().date()} -> {R.index.max().date()}")
    print(f"\n{'lookback':>8} {'gross_Sh':>9} {'net_Sh':>8} {'net_CAGR':>9} {'maxDD':>8} {'turn/day':>9} {'OOS_net_Sh':>11}")
    rows = []
    for lb in (1, 2, 3, 5, 10, 20, 60, 120, 250):
        pnl, net, turn = strat(lb)
        g, n = stats(pnl), stats(net)
        oos = stats(net[net.index >= OOS_START])
        rows.append((lb, n["sharpe"], oos["sharpe"]))
        print(f"{lb:>8} {g['sharpe']:>9.2f} {n['sharpe']:>8.2f} {n['cagr']:>8.1%} "
              f"{n['maxdd']:>8.3f} {turn.mean():>9.3f} {oos['sharpe']:>11.2f}")

    # cost stress on the best |net Sharpe| lookback
    best = max(rows, key=lambda r: abs(r[1]) if not np.isnan(r[1]) else -1)[0]
    print(f"\ncost stress on lookback={best} (long winners; negative Sharpe => reversal would flip sign):")
    for c in (0.0, 1.0, 2.0, 5.0, 10.0):
        _, net, _ = strat(best, cost_bps=c)
        print(f"   {c:>4.0f} bps: net Sharpe full={stats(net)['sharpe']:+.2f}  "
              f"OOS={stats(net[net.index>=OOS_START])['sharpe']:+.2f}")

    print(f"\n=== WITHIN-GROUP (sector-neutral) relative value ===")
    print(f"{'lookback':>8} {'gross_Sh':>9} {'net_Sh':>8} {'net_CAGR':>9} {'maxDD':>8} {'turn/day':>9} {'OOS_net_Sh':>11}")
    for lb in (1, 2, 3, 5, 10, 20, 60, 120, 250):
        pnl, net, turn = strat_grouped(lb)
        g, n = stats(pnl), stats(net)
        oos = stats(net[net.index >= OOS_START])
        print(f"{lb:>8} {g['sharpe']:>9.2f} {n['sharpe']:>8.2f} {n['cagr']:>8.1%} "
              f"{n['maxdd']:>8.3f} {turn.mean():>9.3f} {oos['sharpe']:>11.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
