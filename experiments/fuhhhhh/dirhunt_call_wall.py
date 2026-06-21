"""ANGLE 4 step 2: dissect the opt_dist_call_atr -> up-direction signal (7/7 sign-stable).

opt_dist_call_atr = (call_wall - entry)/ATR, PRIOR-DAY NDX call wall (causal). Positive
corr with up-move: more room below the call wall -> more likely up next 15min.

Questions:
  (a) Is it monotone? bucket dist_call into quantiles, show up-rate + tradeR per bucket per month.
  (b) Is it just distance-from-put-wall or position-in-range in disguise? control for them.
  (c) Does a SIMPLE TRADEABLE RULE (long when dist_call>=thr) beat shuffled + survive
      drop-best-2 + be positive in >=5/7 months?  Net-cost R via r_long.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(20260613)


def block_boot(df, col, b=4000):
    days = df["date"].unique()
    by = {d: df[df["date"] == d][col].to_numpy() for d in days}
    means = np.array([np.concatenate([by[d] for d in RNG.choice(days, len(days), True)]).mean()
                      for _ in range(b)])
    return float(df[col].mean()), float((means <= 0).mean())


def main() -> int:
    base = pd.read_parquet(OUT / "dataset_ndx.parquet")
    new = pd.read_parquet(OUT / "dirhunt_feats_ndx.parquet")
    df = base.merge(new, on=["date", "ms"], how="left")
    df["mo"] = df["date"].str.slice(0, 7)
    mv = df[df["y"].isin([0, 1])].copy()
    mv["dir"] = mv["y"] * 2 - 1
    months = sorted(mv["mo"].unique())

    # (a) monotonicity: quintiles of dist_call
    print("### (a) up-rate + long-R by quintile of opt_dist_call_atr  (resolved moves)")
    mv["q"] = pd.qcut(mv["opt_dist_call_atr"], 5, labels=False, duplicates="drop")
    g = mv.groupby("q").agg(n=("dir", "size"), uprate=("y", "mean"),
                            meanR_long=("r_long", "mean"), dist=("opt_dist_call_atr", "mean"))
    print(g.round(3).to_string())

    # (b) controls: partial — regress dir on dist_call after removing pos_dayrng / dist_put
    print("\n### (b) corr(dist_call, dir) controlling for confounders (resid corr)")
    def resid_corr(target, x, ctrls):
        sub = mv[[target, x] + ctrls].dropna()
        if len(sub) < 100:
            return np.nan, 0
        import numpy.linalg as la
        def resid(yv):
            X = np.column_stack([np.ones(len(sub))] + [sub[c].to_numpy() for c in ctrls])
            beta, *_ = la.lstsq(X, yv, rcond=None)
            return yv - X @ beta
        rx = resid(sub[x].to_numpy(float))
        ry = resid(sub[target].to_numpy(float))
        if np.std(rx) < 1e-9:
            return np.nan, len(sub)
        return float(np.corrcoef(rx, ry)[0, 1]), len(sub)
    for ctrls in ([], ["trd_pos_dayrng"], ["opt_dist_put_atr"],
                  ["trd_pos_dayrng", "opt_dist_put_atr", "trd_dist_vwap_atr", "ov_gap_atr"]):
        c, n = resid_corr("dir", "opt_dist_call_atr", ctrls)
        print(f"   ctrl={ctrls}: resid corr={c:+.4f} (n={n})")

    # (c) tradeable rule: LONG when dist_call in top tercile (most room to call wall)
    #     evaluate on ALL decision rows where we'd go long (use r_long for the long).
    print("\n### (c) tradeable LONG rule: dist_call >= per-day-causal median? (simple, fixed thr)")
    # Use a FIXED in-distribution threshold so it's implementable: dist_call >= 0.35 ATR
    for thr in (0.0, 0.2, 0.35, 0.5):
        sig = df[df["opt_dist_call_atr"] >= thr].copy()   # ALL rows (incl chop) we'd trade long
        sig = sig[np.isfinite(sig["r_long"])]
        m, p = block_boot(sig, "r_long")
        bymo = sig.groupby("mo")["r_long"].mean()
        nmo_pos = int((bymo > 0).sum())
        worst2 = bymo.sort_values(ascending=False).index[:2]
        drop2 = sig[~sig.mo.isin(worst2)]["r_long"].mean()
        print(f"   thr={thr:>4.2f}: n={len(sig):5d}  meanR={m:+.4f} p(<=0)={p:.3f}  "
              f"mo+={nmo_pos}/{len(bymo)}  drop-best-2={drop2:+.4f}")

    # (c2) shuffled control for thr=0.35 long rule: shuffle r_long within day
    thr = 0.35
    sig = df[(df["opt_dist_call_atr"] >= thr) & np.isfinite(df["r_long"])].copy()
    shuf_means = []
    allr = df[np.isfinite(df["r_long"])].copy()
    for _ in range(2000):
        # null: random subset of same size from all long-R outcomes
        s = allr["r_long"].sample(len(sig), replace=False, random_state=RNG.integers(1e9))
        shuf_means.append(s.mean())
    shuf_means = np.array(shuf_means)
    real = sig["r_long"].mean()
    print(f"\n### (c2) shuffled/random-subset control (thr={thr}): real meanR={real:+.4f}  "
          f"null mean={shuf_means.mean():+.4f}  null 95pct={np.percentile(shuf_means,95):+.4f}  "
          f"p(null>=real)={(shuf_means>=real).mean():.3f}")

    # (c3) per-month detail for thr=0.35
    print("\n### (c3) per-month detail, LONG dist_call>=0.35:")
    print(sig.groupby("mo")["r_long"].agg(["size", "mean"]).round(3).to_string())

    # baseline: what does long-everything earn? (is the rule beating naive long?)
    base_long = df[np.isfinite(df["r_long"])]
    print(f"\n   baseline LONG-everything meanR={base_long['r_long'].mean():+.4f} (n={len(base_long)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
