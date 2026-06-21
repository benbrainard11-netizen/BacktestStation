"""Phase 1 — does OWN-asset OFI predict short-horizon futures moves OOS, after costs? (decisive gate)

Reads 1s event_ofi features, builds EWMA / depth-normalized OFI features + forward mid-return targets
(per-day, no cross-day lookahead), temporal train/test split, ridge regression, and reports OOS IC,
directional accuracy, and net-ticks-after-cost vs a volume-only baseline. The cost-aware mean-per-trade
is the real bar (literature: high IC != tradeable).

Run: backend/.venv/Scripts/python.exe experiments/orderflow_divergence_v0/phase1_transfer_test.py --symbol ES.c.0
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
FEATURES_FULL = ["ofi", "ofi_ewm5", "ofi_ewm30", "ofi_ewm120", "imb", "imb_ewm30",
                 "micro_mid", "ofi_dn", "signed_ratio", "spread"]
FEATURES_VOL = ["signed_ratio", "signed", "volume"]


def load(sym: str) -> pd.DataFrame:
    fs = sorted(glob.glob(str(OUT / sym / "*.parquet")))
    if not fs:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["date"] = df["ts"].dt.date
    return df.sort_values("ts").reset_index(drop=True)


def build_xy(df: pd.DataFrame, horizons) -> pd.DataFrame:
    parts = []
    for _, g in df.groupby("date"):
        g = g.sort_values("ts").copy()
        for span in (5, 30, 120):
            g[f"ofi_ewm{span}"] = g["ofi"].ewm(span=span).mean()
        g["imb_ewm30"] = g["imb"].ewm(span=30).mean()
        depth = g["volume"].rolling(60, min_periods=10).mean() + 1.0
        g["ofi_dn"] = g["ofi"] / depth
        for h in horizons:
            g[f"fwd{h}"] = g["mid"].shift(-h) - g["mid"]
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def ridge_oos(Xtr, ytr, Xte, lam=10.0):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    Xtr, Xte = (Xtr - mu) / sd, (Xte - mu) / sd
    Xtr, Xte = np.c_[np.ones(len(Xtr)), Xtr], np.c_[np.ones(len(Xte)), Xte]
    reg = lam * np.eye(Xtr.shape[1]); reg[0, 0] = 0
    w = np.linalg.solve(Xtr.T @ Xtr + reg, Xtr.T @ ytr)
    return Xte @ w


def evaluate(sym, df, h, cut, cost_ticks, feats, name):
    tick = TICK.get(sym, 0.25)
    d = df.dropna(subset=feats + [f"fwd{h}"])
    tr, te = d[d["date"] < cut], d[d["date"] >= cut]
    if len(tr) < 5000 or len(te) < 5000:
        print(f"  {name:10} h{h:>2}s: insufficient ({len(tr)}/{len(te)})"); return
    yte = te[f"fwd{h}"].to_numpy()
    pred = ridge_oos(tr[feats].to_numpy(), tr[f"fwd{h}"].to_numpy(), te[feats].to_numpy())
    yt = yte / tick                              # realized forward move, in ticks
    ic = float(np.corrcoef(pred, yte)[0, 1])
    nz = yt != 0                                 # dir-acc only where price actually moved
    diracc = float(np.mean(np.sign(pred[nz]) == np.sign(yt[nz]))) if nz.sum() else float("nan")
    # high-conviction tradeable test: top-decile |pred| -> ticks captured per trade, net of cost
    thr = np.quantile(np.abs(pred), 0.90)
    hi = np.abs(pred) >= thr
    gross = float((np.sign(pred[hi]) * yt[hi]).mean()) if hi.sum() else float("nan")
    net = gross - cost_ticks
    print(f"  {name:10} h{h:>2}s: IC={ic:+.4f} dir={diracc:.3f} | top10%conv gross={gross:+.3f}tk "
          f"net@{cost_ticks:.0f}tk={net:+.3f}tk (n={int(hi.sum()):,})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--horizons", nargs="+", type=int, default=[1, 5, 30])
    ap.add_argument("--cut", default="2026-02-15")
    ap.add_argument("--cost-ticks", type=float, default=1.0)
    a = ap.parse_args(argv)
    df = load(a.symbol)
    if df.empty:
        print(f"{a.symbol}: no event_ofi data yet"); return 1
    cut = dt.date.fromisoformat(a.cut)
    print(f"{a.symbol}: {len(df):,} 1s-bars  {df['date'].min()}..{df['date'].max()}  cut={a.cut}")
    df = build_xy(df, a.horizons)
    for h in a.horizons:
        print(f"-- horizon {h}s (cost {a.cost_ticks} tick, optimistic) --")
        evaluate(a.symbol, df, h, cut, a.cost_ticks, FEATURES_FULL, "OFI-full")
        evaluate(a.symbol, df, h, cut, a.cost_ticks, FEATURES_VOL, "vol-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
