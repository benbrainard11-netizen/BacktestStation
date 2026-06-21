"""ANGLE 1 — honest walk-forward of the strongest causal-regime direction cell found:
'fade the intraday uptrend' (SHORT when trend_tr30 > 0). The descriptive scan showed it
positive on full-universe (+0.0185R) and surviving drop-best-2, BUT per-month it is
negative for the first 3 dev months and positive only from Dec-2025 on.

This WF learns the side (long vs short) PER FOLD from train data only (no in-sample sign
leak), inside the causal regime, then reports OOS tradeR per month + drop-best-2 +
shuffled control + recent-vs-older. Definitive robustness call for ANGLE 1.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(20260613)
WARMUP, BLOCK = 25, 10


def load():
    ds = pd.read_parquet(OUT / "dataset_ndx.parquet")
    rg = pd.read_parquet(OUT / "dirhunt_regime.parquet")
    df = ds.merge(rg, on=["date", "ms"], how="inner")
    df["mo"] = df["date"].str.slice(0, 7)
    return df.sort_values(["date", "ms"]).reset_index(drop=True)


def block_boot(r, day, b=3000):
    days = day.unique()
    by = {d: r[day == d].to_numpy() for d in days}
    means = np.array([np.concatenate([by[d] for d in RNG.choice(days, len(days), True)]).mean()
                      for _ in range(b)])
    return float(r.mean()), float((means <= 0).mean())


def walk_side(df, cell_mask, shuffle=False):
    """Per fold: inside the regime cell, learn which side (long/short) was better in TRAIN,
    apply it to TEST. Returns OOS rows with chosen 'r'."""
    days = sorted(df["date"].unique())
    rows = []
    for s in range(WARMUP, len(days), BLOCK):
        tr_d, te_d = days[:s], days[s:s + BLOCK]
        tr = df[df.date.isin(tr_d) & cell_mask]
        te = df[df.date.isin(te_d) & cell_mask].copy()
        if len(tr) < 100 or len(te) < 10:
            continue
        if shuffle:
            side = RNG.choice([1, -1])  # random side per fold
        else:
            side = 1 if tr["r_long"].mean() >= tr["r_short"].mean() else -1  # better side in train
        te["r"] = te["r_long"] if side == 1 else te["r_short"]
        te["side"] = side
        rows.append(te)
    return pd.concat(rows) if rows else pd.DataFrame()


def report(p, label):
    if len(p) == 0:
        print(f"  {label}: empty"); return
    mean, pv = block_boot(p["r"], p["date"])
    bymo = p.groupby("mo")["r"].mean()
    d2 = p[~p.mo.isin(bymo.sort_values(ascending=False).index[:2])]["r"].mean()
    older = p[~p.mo.isin(["2026-02", "2026-03"])]["r"].mean()
    recent = p[p.mo.isin(["2026-02", "2026-03"])]["r"].mean()
    print(f"  {label:20s} n={len(p):5d} tradeR={mean:+.4f} p(<=0)={pv:.3f} "
          f"mo+={int((bymo>0).sum())}/{bymo.size} drop-best-2={d2:+.4f} older5={older:+.4f} FebMar={recent:+.4f}")
    print("     per-month:", {m: round(v, 4) for m, v in bymo.items()})


def main() -> int:
    df = load()
    cells = {
        "fade-uptrend(tr30>0)": df["trend_tr30"] > 0,
        "fade-downtrend(tr30<0)": df["trend_tr30"] < 0,
        "all (side-learned)": pd.Series(True, index=df.index),
    }
    print("### WF side-learned per fold (no in-sample sign leak), full universe")
    for name, mask in cells.items():
        report(walk_side(df, mask), name)
    print("\n### CONTROL shuffled (random side per fold), avg 5 seeds — fade-uptrend cell")
    rs = []
    for _ in range(5):
        p = walk_side(df, df["trend_tr30"] > 0, shuffle=True)
        rs.append(p["r"].mean() if len(p) else np.nan)
    print(f"  shuffled-side fade-uptrend tradeR = {np.nanmean(rs):+.4f} +- {np.nanstd(rs):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
