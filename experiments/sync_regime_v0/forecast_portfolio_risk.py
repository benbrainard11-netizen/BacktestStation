"""The absorption ratio's ACTUAL purpose (Kritzman): does it forecast
diversification breakdown / tail risk in a DIVERSIFIED multi-asset portfolio,
beyond that portfolio's own trailing vol?

Thesis: when correlations spike, an inverse-vol diversified portfolio's forward
risk jumps even though individual vols look normal — and trailing portfolio vol
can't see it. If absorption (or its change) adds OOS skill for forward portfolio
vol / worst-day here, the concept lives as a tail-risk/sizing overlay. If not,
it adds no incremental tradeable value on this data.

Run: backend/.venv/Scripts/python.exe experiments/sync_regime_v0/forecast_portfolio_risk.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
SYNC = ["ar_top1", "ar_topN5", "avg_corr", "dispersion"]


def ridge_oos(Xtr, ytr, Xte, lam=1.0):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    Xtr = (Xtr - mu) / sd; Xte = (Xte - mu) / sd
    Xtr = np.c_[np.ones(len(Xtr)), Xtr]; Xte = np.c_[np.ones(len(Xte)), Xte]
    reg = lam * np.eye(Xtr.shape[1]); reg[0, 0] = 0
    w = np.linalg.solve(Xtr.T @ Xtr + reg, Xtr.T @ ytr)
    return Xte @ w


def r2(y, yhat):
    return 1 - float(np.sum((y - yhat) ** 2)) / float(np.sum((y - y.mean()) ** 2))


def diversified_portfolio(R: pd.DataFrame) -> pd.Series:
    vol60 = R.rolling(60).std()
    w = 1.0 / vol60
    w = w.div(w.sum(axis=1), axis=0).shift(1)  # inverse-vol weights known at t-1
    return (w * R).sum(axis=1)


def run(port: pd.Series, S: pd.DataFrame, H: int):
    trail = port.rolling(H).std()
    ewma = port.ewm(span=H).std()
    fwd_vol = port.shift(-1).rolling(H).std()
    fwd_worst = -port.shift(-1).rolling(H).min()  # positive = magnitude of worst forward day

    df = pd.DataFrame({
        "y_vol": np.log(fwd_vol + 1e-6), "y_tail": np.log(fwd_worst + 1e-6),
        "f_trail": np.log(trail + 1e-6), "f_ewma": np.log(ewma + 1e-6),
    }).join(S[SYNC], how="inner")
    for c in SYNC:
        df[f"{c}_chg5"] = S[c].diff(5)
    df = df.dropna()

    n = len(df); cut = int(n * 0.6); emb = H
    tr, te = df.iloc[:cut], df.iloc[cut + emb:]
    vol_feats = ["f_trail", "f_ewma"]
    sync_feats = vol_feats + SYNC + [f"{c}_chg5" for c in SYNC]

    print(f"\n===== diversified-portfolio forward {H}-day risk (train {len(tr)}, test {len(te)}: "
          f"{te.index.min().date()}..{te.index.max().date()}) =====")
    for target in ("y_vol", "y_tail"):
        yte = te[target].to_numpy()
        base = ridge_oos(tr[vol_feats].to_numpy(), tr[target].to_numpy(), te[vol_feats].to_numpy())
        syn = ridge_oos(tr[sync_feats].to_numpy(), tr[target].to_numpy(), te[sync_feats].to_numpy())
        rb, rs = r2(yte, base), r2(yte, syn)
        label = "fwd VOL" if target == "y_vol" else "fwd TAIL (worst day)"
        print(f"  {label:22} ridge[vol]={rb:6.3f}  ridge[vol+sync]={rs:6.3f}  sync adds: {rs-rb:+.3f}")

    # partial signal: does ar_top1 explain forward vol after removing trailing vol?
    resid = te["y_vol"].to_numpy() - ridge_oos(tr[["f_trail"]].to_numpy(), tr["y_vol"].to_numpy(), te[["f_trail"]].to_numpy())
    for c in ("ar_top1", "ar_top1_chg5", "dispersion"):
        cc = np.corrcoef(te[c].to_numpy(), resid)[0, 1]
        print(f"     partial corr( {c:14}, fwd-vol residual ) = {cc:+.3f}")


def main() -> int:
    R = pd.read_parquet(OUT / "daily_returns.parquet"); R.index = pd.to_datetime(R.index)
    S = pd.read_parquet(OUT / "sync_state.parquet"); S.index = pd.to_datetime(S.index)
    port = diversified_portfolio(R)
    print(f"diversified portfolio: {port.notna().sum()} days, ann.vol~{port.std()*np.sqrt(252):.3f}")
    for H in (5, 20):
        run(port, S, H)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
