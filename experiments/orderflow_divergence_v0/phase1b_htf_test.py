"""Phase 1b — does AGGREGATED (HTF) own-asset OFI predict HIGHER-horizon moves, tradeably?

Closes the user's "higher horizons" question: trailing-window OFI sums (1/5/15 min) + imbalance ->
forward 1/5/15-min mid return, OOS, with the tradeability check (moves are bigger at higher horizons,
so crossing the spread could pay off IF OFI still predicts there). Honest prior: weak (OFI predictive
power decays by ~5-10 min per both research passes + the user's dead 15-60min direction work), but the
large-tick rates (ZN/ZB) held strong to 30s so they earn the check.

Run: backend/.venv/Scripts/python.exe experiments/orderflow_divergence_v0/phase1b_htf_test.py --symbol ZN.c.0
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out" / "event_ofi"
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10,
        "ZN.c.0": 1 / 64, "ZB.c.0": 1 / 32, "CL.c.0": 0.01}
FEATS = ["ofi_sum60", "ofi_sum300", "ofi_sum900", "sig_sum300", "imb", "imb_ewm120",
         "micro_mid", "signed_ratio"]


def load(sym: str) -> pd.DataFrame:
    fs = sorted(glob.glob(str(OUT / sym / "*.parquet")))
    df = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["date"] = df["ts"].dt.date
    return df.sort_values("ts").reset_index(drop=True)


def build_xy(df: pd.DataFrame, horizons) -> pd.DataFrame:
    parts = []
    for _, g in df.groupby("date"):
        g = g.sort_values("ts").copy()
        for w in (60, 300, 900):
            g[f"ofi_sum{w}"] = g["ofi"].rolling(w, min_periods=w // 4).sum()
            g[f"sig_sum{w}"] = g["signed"].rolling(w, min_periods=w // 4).sum()
        g["imb_ewm120"] = g["imb"].ewm(span=120).mean()
        for h in horizons:
            g[f"fwd{h}"] = g["mid"].shift(-h) - g["mid"]
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def ridge_oos(Xtr, ytr, Xte, lam=10.0):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    Xtr, Xte = (Xtr - mu) / sd, (Xte - mu) / sd
    Xtr, Xte = np.c_[np.ones(len(Xtr)), Xtr], np.c_[np.ones(len(Xte)), Xte]
    reg = lam * np.eye(Xtr.shape[1]); reg[0, 0] = 0
    return Xte @ np.linalg.solve(Xtr.T @ Xtr + reg, Xtr.T @ ytr)


def evaluate(sym, df, h, cut, cost_ticks):
    tick = TICK.get(sym, 0.25)
    d = df.dropna(subset=FEATS + [f"fwd{h}"])
    tr, te = d[d["date"] < cut], d[d["date"] >= cut]
    if len(tr) < 5000 or len(te) < 5000:
        print(f"  h{h:>4}s: insufficient ({len(tr)}/{len(te)})"); return
    yte = te[f"fwd{h}"].to_numpy()
    pred = ridge_oos(tr[FEATS].to_numpy(), tr[f"fwd{h}"].to_numpy(), te[FEATS].to_numpy())
    yt = yte / tick
    ic = float(np.corrcoef(pred, yte)[0, 1])
    nz = yt != 0
    diracc = float(np.mean(np.sign(pred[nz]) == np.sign(yt[nz]))) if nz.sum() else float("nan")
    thr = np.quantile(np.abs(pred), 0.90)
    hi = np.abs(pred) >= thr
    gross = float((np.sign(pred[hi]) * yt[hi]).mean()) if hi.sum() else float("nan")
    print(f"  h{h:>4}s ({h//60}m): IC={ic:+.4f} dir={diracc:.3f} | top10%conv gross={gross:+.2f}tk "
          f"net@{cost_ticks:.0f}tk={gross - cost_ticks:+.2f}tk")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--horizons", nargs="+", type=int, default=[60, 300, 900])
    ap.add_argument("--cut", default="2026-02-15")
    ap.add_argument("--cost-ticks", type=float, default=1.0)
    a = ap.parse_args(argv)
    df = load(a.symbol)
    cut = dt.date.fromisoformat(a.cut)
    print(f"{a.symbol}: {len(df):,} 1s-bars  {df['date'].min()}..{df['date'].max()}")
    df = build_xy(df, a.horizons)
    for h in a.horizons:
        evaluate(a.symbol, df, h, cut, a.cost_ticks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
