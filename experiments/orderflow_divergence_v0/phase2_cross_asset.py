"""Phase 2 — does cross-asset OFI divergence add incremental forward-prediction over own-asset OFI?

Aligns the index complex (ES/NQ/YM/RTY) on a common 1s grid; per day, z-scores each asset's OFI,
builds the common-flow factor f (cross-sectional mean) and idiosyncratic OFI (z - f); then for each
target asset compares OOS IC of an own-asset-only model vs own + OTHER assets' idiosyncratic OFI.
Research expectation: cross-asset adds a small-but-real increment over own + common factor.

Run: backend/.venv/Scripts/python.exe experiments/orderflow_divergence_v0/phase2_cross_asset.py
"""
from __future__ import annotations

import datetime as dt
import glob
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out" / "event_ofi"
INDEX = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
SHORT = {s: s[:-4] for s in INDEX}
CUT = dt.date(2026, 2, 15)
H = 5  # forward horizon (s) — slightly past the 1s where own-OFI dominates, to give cross a chance


def load_sym(s: str) -> pd.DataFrame:
    fs = sorted(glob.glob(str(OUT / s / "*.parquet")))
    df = pd.concat([pd.read_parquet(f, columns=["ts", "ofi", "imb", "micro_mid", "mid"]) for f in fs],
                   ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df.sort_values("ts").drop_duplicates("ts")


def ridge_oos(Xtr, ytr, Xte, lam=10.0):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    Xtr, Xte = (Xtr - mu) / sd, (Xte - mu) / sd
    Xtr, Xte = np.c_[np.ones(len(Xtr)), Xtr], np.c_[np.ones(len(Xte)), Xte]
    reg = lam * np.eye(Xtr.shape[1]); reg[0, 0] = 0
    return Xte @ np.linalg.solve(Xtr.T @ Xtr + reg, Xtr.T @ ytr)


def main() -> int:
    merged = None
    for s in INDEX:
        d = load_sym(s).set_index("ts")[["ofi", "imb", "micro_mid", "mid"]]
        d.columns = [f"{c}_{SHORT[s]}" for c in d.columns]
        merged = d if merged is None else merged.join(d, how="inner")
    merged = merged.reset_index()
    merged["date"] = merged["ts"].dt.date
    print(f"aligned index panel: {len(merged):,} common 1s-bars  {merged['date'].min()}..{merged['date'].max()}")

    ofic = [f"ofi_{SHORT[s]}" for s in INDEX]
    parts = []
    for _, g in merged.groupby("date"):
        g = g.sort_values("ts").copy()
        z = (g[ofic] - g[ofic].mean()) / (g[ofic].std() + 1e-9)
        f = z.mean(axis=1)
        g["cf"] = f
        for s in INDEX:
            sh = SHORT[s]
            g[f"idio_{sh}"] = z[f"ofi_{sh}"] - f
            g[f"ofiewm_{sh}"] = g[f"ofi_{sh}"].ewm(span=30).mean()
            g[f"fwd_{sh}"] = g[f"mid_{sh}"].shift(-H) - g[f"mid_{sh}"]
        parts.append(g)
    df = pd.concat(parts, ignore_index=True)

    print(f"\n-- cross-asset increment (forward {H}s, OOS IC) --")
    print(f"   {'target':6} {'IC_own':>8} {'IC_own+cross':>13} {'delta':>8}")
    for s in INDEX:
        sh = SHORT[s]
        others = [SHORT[o] for o in INDEX if o != s]
        own = [f"ofi_{sh}", f"ofiewm_{sh}", f"imb_{sh}", f"micro_mid_{sh}"]
        cross = own + [f"idio_{o}" for o in others] + ["cf"]
        y = f"fwd_{sh}"
        d = df.dropna(subset=cross + [y])
        tr, te = d[d["date"] < CUT], d[d["date"] >= CUT]
        if len(tr) < 5000 or len(te) < 5000:
            print(f"   {sh:6} insufficient"); continue
        yte = te[y].to_numpy()
        ic_own = float(np.corrcoef(ridge_oos(tr[own].to_numpy(), tr[y].to_numpy(), te[own].to_numpy()), yte)[0, 1])
        ic_cr = float(np.corrcoef(ridge_oos(tr[cross].to_numpy(), tr[y].to_numpy(), te[cross].to_numpy()), yte)[0, 1])
        print(f"   {sh:6} {ic_own:+8.4f} {ic_cr:+13.4f} {ic_cr - ic_own:+8.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
