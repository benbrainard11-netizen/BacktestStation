"""Time-series momentum (TSMOM, Moskowitz-Ooi-Pedersen) on the 26-asset daily futures panel.

The high-CAPACITY edge class -- the scaling sleeve for a systematic bot portfolio (low Sharpe, big capacity,
uncorrelated to RV/Mira). Sign of trailing-N return per asset, inverse-vol sized to a target vol, no-lookahead
(signal through t applied to t+1), OOS split + cost-stress. Honest gate: must beat 0 net after costs OOS, and
the combo should be reasonably consistent. Uses daily CLOSES (not wick-contaminated like the 5m bars).

Run: backend/.venv/Scripts/python.exe experiments/edge_hunt_v0/ts_momentum.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

R = pd.read_parquet(Path(__file__).resolve().parents[1] / "sync_regime_v0" / "out" / "daily_returns.parquet")
R.index = pd.to_datetime(R.index)
ANN = np.sqrt(252.0)
OOS = pd.Timestamp("2023-01-01", tz="UTC")
VOL = R.rolling(60, min_periods=20).std()
TARGET = 0.10 / np.sqrt(252.0)   # per-asset ~10% annualized target vol


def tsmom(lookback: int, skip: int = 1, cost_bps: float = 1.0):
    mom = R.rolling(lookback, min_periods=lookback // 2).sum().shift(skip)
    w = np.sign(mom) * (TARGET / VOL)
    w = w.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    pnl = (w.shift(1) * R).sum(axis=1)              # t-1 weights on t returns -> no lookahead
    turn = w.diff().abs().sum(axis=1)
    return pnl, pnl - turn * cost_bps / 1e4, turn


def stats(x: pd.Series) -> dict:
    x = x.dropna()
    if len(x) < 100 or x.std() == 0:
        return {"sharpe": np.nan, "cagr": np.nan, "maxdd": np.nan}
    eq = x.cumsum()
    return {"sharpe": float(x.mean() / x.std() * ANN), "cagr": float(x.mean() * 252),
            "maxdd": float((eq - eq.cummax()).min())}


def main() -> int:
    print(f"panel {R.shape[0]} days x {R.shape[1]} assets  {R.index.min().date()}..{R.index.max().date()}")
    print(f"\n{'lookback':>9} {'grossSh':>8} {'netSh':>7} {'OOSnetSh':>9} {'netCAGR':>8} {'maxDD':>7} {'turn/d':>7}")
    nets = {}
    for lb in (21, 63, 126, 252):
        pnl, net, turn = tsmom(lb)
        g, n, oos = stats(pnl), stats(net), stats(net[net.index >= OOS])
        nets[lb] = net
        print(f"{lb:>4}d({lb//21:>2}m) {g['sharpe']:>8.2f} {n['sharpe']:>7.2f} {oos['sharpe']:>9.2f} "
              f"{n['cagr']:>7.1%} {n['maxdd']:>7.3f} {turn.mean():>7.2f}")
    combo = sum(nets.values()) / len(nets)
    print(f"\nCOMBO (avg of 4 lookbacks): full netSh={stats(combo)['sharpe']:+.2f}  "
          f"OOS netSh={stats(combo[combo.index >= OOS])['sharpe']:+.2f}  "
          f"netCAGR={stats(combo)['cagr']:+.1%}  maxDD={stats(combo)['maxdd']:.3f}")
    print("\ncost-stress on 12-month lookback (the canonical TSMOM horizon):")
    for cb in (0, 1, 2, 5, 10):
        _, net, _ = tsmom(252, cost_bps=cb)
        print(f"  {cb:>2}bp: netSh full={stats(net)['sharpe']:+.2f}  OOS={stats(net[net.index >= OOS])['sharpe']:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
