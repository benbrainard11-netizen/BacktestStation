"""ANGLE 1 (descriptive scan) — within CAUSAL regime buckets, is NQ direction biased,
and is the bias STABLE across the 7 dev months? Pure in-sample description to find
candidate regimes before the honest walk-forward. No model, no claim of edge yet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = Path(__file__).resolve().parent / "out"


def load():
    ds = pd.read_parquet(OUT / "dataset_ndx.parquet")
    rg = pd.read_parquet(OUT / "dirhunt_regime.parquet")
    df = ds.merge(rg, on=["date", "ms"], how="inner")
    df = df[df["y"].isin([0, 1])].copy()
    df["dir"] = df["y"] * 2 - 1
    df["mo"] = df["date"].str.slice(0, 7)
    return df


def bucket_report(df, name, series, edges):
    """Tertile/quantile bucket -> frac_up + per-month frac_up stability."""
    q = pd.qcut(series, edges, labels=False, duplicates="drop")
    print(f"\n### regime = {name}  (quantile buckets)")
    for b in sorted(q.dropna().unique()):
        sub = df[q == b]
        fu = sub["dir"].gt(0).mean()
        # per-month frac_up to check stability
        mm = sub.groupby("mo")["dir"].apply(lambda s: (s > 0).mean())
        consistent = ((mm - 0.5).abs() > 0.0)
        same_side = (np.sign(mm - 0.5)).sum()
        n_mo_up = int((mm > 0.5).sum())
        rng = f"[{series[q==b].min():+.3f},{series[q==b].max():+.3f}]"
        print(f"  bucket {int(b)} {rng:22s} n={len(sub):5d} frac_up={fu:.3f}  "
              f"months_up={n_mo_up}/{mm.size}  mo_fracup=[{mm.min():.2f}..{mm.max():.2f}]")


def main() -> int:
    df = load()
    print(f"resolved moves n={len(df)}  overall frac_up={df['dir'].gt(0).mean():.4f}")

    # candidate regime conditioners (causal)
    for name in ["rv_ratio", "rv_atr", "rv_accel", "trend_tr30", "trend_vwap_dev",
                 "chop_ac1", "chop_eff", "gap_z", "gam_zero", "gam_pin", "tod_mins"]:
        bucket_report(df, name, df[name], 4)

    # interaction worth a look: trend sign x chop (trend-continuation vs mean-revert)
    print("\n### interaction: trend_sign x chop_eff (trending up/down vs choppy)")
    df["_eff_hi"] = (df["chop_eff"] > df["chop_eff"].median()).astype(int)
    for ts in (-1, 1):
        for eh in (0, 1):
            sub = df[(df["trend_sign"] == ts) & (df["_eff_hi"] == eh)]
            if len(sub) < 50:
                continue
            mm = sub.groupby("mo")["dir"].apply(lambda s: (s > 0).mean())
            print(f"  trend_sign={ts:+d} eff_hi={eh} n={len(sub):5d} frac_up={sub['dir'].gt(0).mean():.3f}"
                  f"  months_up={int((mm>0.5).sum())}/{mm.size}  [{mm.min():.2f}..{mm.max():.2f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
