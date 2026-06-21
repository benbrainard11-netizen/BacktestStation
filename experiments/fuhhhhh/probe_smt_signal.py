"""Deep-dive on the ONLY survivor from ANGLE 3: the cross-asset SMT sign rule.

Rule (registered a-priori by SMT theory, sign NOT fitted): xa_smt_sum = sum over
{ES,YM,RTY} of a proper swing-pivot SMT divergence for NQ. >0 => NQ oversold vs peers
=> go LONG; <0 => NQ overbought vs peers => go SHORT. Only fires when at least one peer
diverges (so it is a CONDITIONAL, trigger-like rule, not an always-on bet).

Scrutiny battery:
  1. Decompose long-only vs short-only legs (is it a real two-sided compass or a long bias?)
  2. Conditional set only (rows where smt_sum != 0) — the actual tradeable population.
  3. Shuffled control: permute the SMT sign within the tradeable set, 2000x.
  4. Per-month + drop-best-2 + NO-Feb/Mar on the CONDITIONAL set.
  5. OOS walk-forward sanity: the sign is fixed, so "OOS" = apply the same fixed rule to
     each expanding test block; report per-block to show it isn't one block.
  6. Magnitude version: |smt_sum| >= 2 (multi-peer agreement) — stronger conviction subset.
  7. Compare vs the dataset's OWN struct_smt (the old/buggy single-asset SMT) as a baseline.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(20260613)


def block_boot(df, col="r", b=4000):
    days = df["date"].unique()
    by = {d: df[df["date"] == d][col].to_numpy() for d in days}
    means = np.array([np.concatenate([by[d] for d in RNG.choice(days, len(days), True)]).mean()
                      for _ in range(b)])
    return float(df[col].mean()), float((means <= 0).mean())


def summarize(sub, tag):
    sub = sub.copy()
    sub["mo"] = sub["date"].str.slice(0, 7)
    m, p = block_boot(sub)
    bymo = sub.groupby("mo")["r"].mean().sort_values(ascending=False)
    d1 = sub[~sub.mo.isin(bymo.index[:1])]["r"].mean()
    d2 = sub[~sub.mo.isin(bymo.index[:2])]["r"].mean()
    norec = sub[~sub.mo.isin({"2026-02", "2026-03"})]["r"].mean()
    wr = (sub["r"] > 0).mean()
    print(f"  {tag:30s} R={m:+.4f} p(<=0)={p:.3f} win%={wr*100:.1f} "
          f"drop1={d1:+.4f} drop2={d2:+.4f} noFM={norec:+.4f} mo+={int((bymo>0).sum())}/{len(bymo)} n={len(sub)}")
    return m, p, bymo


def main() -> int:
    ds = pd.read_parquet(OUT / "dataset_ndx.parquet")
    assert ds["date"].max() < "2026-04-01"
    xa = pd.read_parquet(OUT / "dirhunt_xasset.parquet")
    df = ds.merge(xa, on=["date", "ms"], how="inner")
    df = df[df["y"].isin([0, 1])].copy()
    print(f"resolved n={len(df)} days={df.date.nunique()}")

    # tradeable conditional population: smt_sum != 0
    cond = df[df["xa_smt_sum"] != 0].copy()
    long_sig = cond["xa_smt_sum"] > 0
    cond["r"] = np.where(long_sig, cond["r_long"], cond["r_short"])
    print(f"\nCONDITIONAL set (xa_smt_sum != 0): n={len(cond)} "
          f"({(cond['xa_smt_sum']>0).sum()} long-sig, {(cond['xa_smt_sum']<0).sum()} short-sig) "
          f"over {cond.date.nunique()} days")

    print("\n### 1. two-sided decomposition (conditional set)")
    summarize(cond, "BOTH sides (smt rule)")
    lo = cond[long_sig].copy(); lo["r"] = lo["r_long"]
    sh = cond[~long_sig].copy(); sh["r"] = sh["r_short"]
    summarize(lo, "LONG leg (smt_sum>0)")
    summarize(sh, "SHORT leg (smt_sum<0)")
    # baseline: what if you just always went long / always short the same population?
    al = cond.copy(); al["r"] = al["r_long"]; summarize(al, "  [ctrl] always-long pop")
    ash = cond.copy(); ash["r"] = ash["r_short"]; summarize(ash, "  [ctrl] always-short pop")

    print("\n### 2. shuffled-sign control (permute smt sign within conditional set, 2000x)")
    obs = cond["r"].mean()
    signs = cond["xa_smt_sum"].to_numpy()
    rl, rs = cond["r_long"].to_numpy(), cond["r_short"].to_numpy()
    sh_means = []
    for _ in range(2000):
        ps = RNG.permutation(signs)
        rr = np.where(ps > 0, rl, rs)
        sh_means.append(rr.mean())
    sh_means = np.array(sh_means)
    pval = float((sh_means >= obs).mean())
    print(f"  observed R={obs:+.4f}  shuffled mean={sh_means.mean():+.4f} (std {sh_means.std():.4f})  "
          f"p(shuffled>=obs)={pval:.4f}")

    print("\n### 3. magnitude subset |smt_sum|>=2 (multi-peer agreement)")
    strong = df[df["xa_smt_sum"].abs() >= 2].copy()
    if len(strong) > 30:
        strong["r"] = np.where(strong["xa_smt_sum"] > 0, strong["r_long"], strong["r_short"])
        summarize(strong, "|smt_sum|>=2")

    print("\n### 4. expanding OOS blocks (fixed rule, per block = no fitting, no peeking)")
    days = sorted(cond["date"].unique())
    WARMUP, BLOCK = 20, 10
    blockrows = []
    for s in range(WARMUP, len(days), BLOCK):
        te_d = days[s:s + BLOCK]
        te = cond[cond.date.isin(te_d)]
        if len(te) < 10:
            continue
        blockrows.append((te_d[0], te_d[-1], len(te), te["r"].mean()))
    bdf = pd.DataFrame(blockrows, columns=["from", "to", "n", "R"])
    print(bdf.round(4).to_string(index=False))
    print(f"  blocks positive: {(bdf['R']>0).sum()}/{len(bdf)}  mean-of-blocks={bdf['R'].mean():+.4f}")

    print("\n### 5. per-peer SMT (which peer carries it?)")
    for s in ["es", "ym", "rty"]:
        col = f"xa_smt_{s}"
        c2 = df[df[col] != 0].copy()
        c2["r"] = np.where(c2[col] > 0, c2["r_long"], c2["r_short"])
        summarize(c2, f"smt vs {s} only")

    print("\n### 6. baseline: dataset's own struct_smt (old single-asset SMT)")
    osmt = df[df["struct_smt"] != 0].copy()
    osmt["r"] = np.where(osmt["struct_smt"] > 0, osmt["r_long"], osmt["r_short"])
    summarize(osmt, "struct_smt (existing)")

    print("\n### 7. by hour-of-day (is it concentrated in one part of the session?)")
    cond["hr"] = (cond["ms"] // 3600000).astype(int)
    print(cond.groupby("hr")["r"].agg(["size", "mean"]).round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
