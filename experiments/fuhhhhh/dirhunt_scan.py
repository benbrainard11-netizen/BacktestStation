"""ANGLE 4 step 1: univariate causal-feature -> NQ direction scan + per-month stability.

For each new feature we report:
  - overall corr(feat, dir) on resolved moves (dir = +1 up / -1 down)
  - per-month corr (is the sign STABLE across all 7 months?)
  - a sign-consistent in-sample hit-bias (descriptive only)
This is a HUNT, not a model — it tells us which features carry a stable direction signal
to feed the walk-forward + the slice search. No OOS claim is made here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = Path(__file__).resolve().parent / "out"


def corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 30 or np.std(a[m]) < 1e-12:
        return np.nan, int(m.sum())
    return float(np.corrcoef(a[m], b[m])[0, 1]), int(m.sum())


def main() -> int:
    base = pd.read_parquet(OUT / "dataset_ndx.parquet")
    new = pd.read_parquet(OUT / "dirhunt_feats_ndx.parquet")
    mbp = pd.read_parquet(OUT / "mbp_features_ndx.parquet")
    df = base.merge(new, on=["date", "ms"], how="left").merge(mbp, on=["date", "ms"], how="left")
    df["mo"] = df["date"].str.slice(0, 7)
    mv = df[df["y"].isin([0, 1])].copy()
    mv["dir"] = mv["y"] * 2 - 1
    months = sorted(mv["mo"].unique())

    newf = [c for c in new.columns if c not in ("date", "ms")]
    mbpf = [c for c in mbp.columns if c not in ("date", "ms")]
    strf = ["struct_sweep", "struct_smt", "opt_gamma_sign", "opt_dist_zero_atr",
            "opt_above_zero_gamma", "opt_dist_call_atr", "opt_dist_put_atr"]
    feats = newf + mbpf + strf

    print(f"resolved moves n={len(mv)}  up={int((mv.dir>0).sum())} down={int((mv.dir<0).sum())}  "
          f"base up-rate={float((mv.dir>0).mean()):.3f}\n")
    print("### corr(feature, dir): overall + per-month sign-stability  (|monthly corr| signs)")
    print(f"{'feature':22s} {'overall':>8s} {'n+':>4s} {'#mo+':>5s} {'#mo-':>5s} {'minmo':>7s} {'maxmo':>7s}")
    results = []
    for f in feats:
        co, n = corr(mv[f], mv["dir"])
        if not np.isfinite(co):
            continue
        mcs = []
        for m in months:
            cm, nm = corr(mv[mv.mo == m][f], mv[mv.mo == m]["dir"])
            mcs.append(cm if np.isfinite(cm) else np.nan)
        mcs = np.array(mcs)
        npos = int(np.nansum(mcs > 0))
        nneg = int(np.nansum(mcs < 0))
        # sign agreement with overall sign
        agree = int(np.nansum(np.sign(mcs) == np.sign(co)))
        results.append((f, co, n, npos, nneg, agree, np.nanmin(mcs), np.nanmax(mcs)))
    # sort by absolute overall corr
    results.sort(key=lambda x: -abs(x[1]))
    for f, co, n, npos, nneg, agree, mn, mx in results:
        print(f"{f:22s} {co:>8.3f} {n:>4d} {npos:>5d} {nneg:>5d} {mn:>7.3f} {mx:>7.3f}  agree={agree}/{len(months)}")

    # highlight the most sign-stable (agree >=6/7 and |overall|>=0.03)
    print("\n### MOST SIGN-STABLE candidates (agree>=6/7, |corr|>=0.03):")
    for f, co, n, npos, nneg, agree, mn, mx in results:
        if agree >= 6 and abs(co) >= 0.03:
            print(f"  {f}: corr={co:+.3f} agree={agree}/7 range[{mn:+.3f},{mx:+.3f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
