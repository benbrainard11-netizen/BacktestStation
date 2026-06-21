"""ANGLE 4 step 3: turn the call-wall tilt into a DIRECTIONAL rule (long top / short bottom).

The signal is RELATIVE (up-rate 0.41 near call wall -> 0.54 far below it). The dataset
has a structural short tilt so naive long loses. Test the directional version:
  - long when dist_call HIGH (room to rally), short when dist_call LOW (capped at wall)
  - pick r_long for the long leg, r_short for the short leg (net cost already in)
  - controls: shuffled-y, per-month, drop-best-2; require >=5/7 months positive.

Also a combined causal score (dist_call + a second 7/7-ish stable feature) to see if the
edge strengthens, and a per-decision-row rule (not just resolved moves) for tradeability.
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


def eval_rule(df, name):
    """df has column 'side' in {+1 long, -1 short, 0 flat} and r_long/r_short. Eval traded rows."""
    t = df[df["side"] != 0].copy()
    t["r"] = np.where(t["side"] > 0, t["r_long"], t["r_short"])
    t = t[np.isfinite(t["r"])]
    m, p = block_boot(t, "r")
    bymo = t.groupby("mo")["r"].mean()
    worst2 = bymo.sort_values(ascending=False).index[:2]
    drop2 = t[~t.mo.isin(worst2)]["r"].mean()
    drop1 = t[~t.mo.isin(bymo.sort_values(ascending=False).index[:1])]["r"].mean()
    wr = (t["r"] > 0).mean()
    print(f"  {name:32s} n={len(t):5d} meanR={m:+.4f} p(<=0)={p:.3f} win%={wr*100:.1f} "
          f"mo+={int((bymo>0).sum())}/{len(bymo)} d1={drop1:+.4f} d2={drop2:+.4f}")
    return t, bymo


def main() -> int:
    base = pd.read_parquet(OUT / "dataset_ndx.parquet")
    new = pd.read_parquet(OUT / "dirhunt_feats_ndx.parquet")
    mbp = pd.read_parquet(OUT / "mbp_features_ndx.parquet")
    df = base.merge(new, on=["date", "ms"], how="left").merge(mbp, on=["date", "ms"], how="left")
    df["mo"] = df["date"].str.slice(0, 7)
    df = df[np.isfinite(df["opt_dist_call_atr"])].copy()

    # FIXED, implementable thresholds (in ATR units, sensible & not fished day-by-day).
    # long when lots of room below call wall; short when near/above it.
    print("### directional rule on ALL decision rows (incl chop), net-cost R")
    for hi, lo in [(1.0, 0.2), (1.2, 0.3), (0.8, 0.1), (1.5, 0.4)]:
        d = df.copy()
        d["side"] = 0
        d.loc[d["opt_dist_call_atr"] >= hi, "side"] = 1
        d.loc[d["opt_dist_call_atr"] <= lo, "side"] = -1
        eval_rule(d, f"long>={hi} / short<={lo}")

    # shuffled control: shuffle the r_long/r_short pair within day for chosen rule
    print("\n### shuffled control (long>=1.0 / short<=0.2): permute outcomes across rows")
    d = df.copy()
    d["side"] = 0
    d.loc[d["opt_dist_call_atr"] >= 1.0, "side"] = 1
    d.loc[d["opt_dist_call_atr"] <= 0.2, "side"] = -1
    real_t, _ = eval_rule(d, "REAL")
    null = []
    traded = d[d["side"] != 0].copy()
    for _ in range(2000):
        s = RNG.permutation(traded["side"].to_numpy())
        r = np.where(s > 0, traded["r_long"], traded["r_short"])
        r = r[np.isfinite(r)]
        null.append(r.mean())
    null = np.array(null)
    print(f"  null meanR mean={null.mean():+.4f} 95pct={np.percentile(null,95):+.4f} "
          f"p(null>=real)={(null>=real_t['r'].mean()).mean():.3f}")

    # per-month detail for the chosen rule
    print("\n### per-month detail, long>=1.0 / short<=0.2:")
    print(real_t.groupby("mo")["r"].agg(["size", "mean"]).round(3).to_string())

    # combine with a second feature: directional only when dist_call AND activity agree?
    # near call wall + high quote rate -> more reliable short? test interaction.
    print("\n### add a confirming feature (mbp_quote_rate_1m z within day)")
    df["qr_z"] = df.groupby("date")["mbp_quote_rate_1m"].transform(
        lambda s: (s - s.mean()) / (s.std() + 1e-9))
    d2 = df.copy()
    d2["side"] = 0
    # long when far from wall AND active; short when near wall AND active
    d2.loc[(d2["opt_dist_call_atr"] >= 1.0) & (d2["qr_z"] > 0), "side"] = 1
    d2.loc[(d2["opt_dist_call_atr"] <= 0.2) & (d2["qr_z"] > 0), "side"] = -1
    eval_rule(d2, "wall-dir AND quote_rate>0")
    d3 = df.copy()
    d3["side"] = 0
    d3.loc[(d3["opt_dist_call_atr"] >= 1.0) & (d3["qr_z"] <= 0), "side"] = 1
    d3.loc[(d3["opt_dist_call_atr"] <= 0.2) & (d3["qr_z"] <= 0), "side"] = -1
    eval_rule(d3, "wall-dir AND quote_rate<=0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
