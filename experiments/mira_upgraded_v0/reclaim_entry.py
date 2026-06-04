"""Reclaim-entry combo sweep (v2): the CORRECTED trade = enter ON the reclaim (confirmation), not the touch.

Universe = swept levels that RECLAIMED (the confirmation fired). Stop just past the 5m sweep extreme (tight),
target = R x risk. Resolved off the post-extreme path to bracket the truth:
  CONSERVATIVE (repo rule 8, stop wins ties): any re-break of the extreme => loss.   [headline]
  OPTIMISTIC: target reached counts (ignores rebreak sequencing).                     [upper bracket]
Per (family x horizon): baseline vs MBO-confirmation gate, day-block bootstrap CI. Reads events_upgraded.parquet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

EV = Path(__file__).resolve().parent / "out" / "events_upgraded.parquet"
OOS_START = pd.Timestamp("2026-04-01").date()
HORIZONS, TARGET_R = ["15m", "60m", "120m"], 2.0
BUFFER, COST_USD, PTV, MIN_RISK, N_BOOT = 1.0, 30.0, 50.0, 2.0, 1500


def _geom(df: pd.DataFrame, target_r: float):
    depth = np.maximum(df["sweep.5m.max_through_pts"].to_numpy(float), MIN_RISK)   # level -> extreme = sweep depth
    risk = depth + BUFFER                                                          # tight stop just past extreme
    return depth + target_r * risk, COST_USD / (risk * PTV)                        # target (from extreme), cost in R


def seq_r(df: pd.DataFrame, target_r: float) -> np.ndarray:
    """Honest sequenced R: enter on reclaim, stop past extreme. Walk 15/60/120m buckets -- WIN only if target
    bucket is strictly EARLIER than the rebreak bucket (same bucket => stop wins ties, rule 8)."""
    tgt, cost_r = _geom(df, target_r)
    n, INF = len(df), 9
    first_tgt, first_reb = np.full(n, INF), np.full(n, INF)
    for i, h in enumerate(HORIZONS):
        away = df[f"post_extreme.5m.{h}.max_away_from_extreme_pts"].to_numpy(float)
        reb = df[f"post_extreme.5m.{h}.rebreak_extreme"].to_numpy(float) > 0
        first_tgt = np.where((first_tgt == INF) & (away >= tgt), i, first_tgt)
        first_reb = np.where((first_reb == INF) & reb, i, first_reb)
    win = (first_tgt < INF) & (first_tgt < first_reb)
    return np.where(win, target_r, -1.0) - cost_r


def reclaim_r(df: pd.DataFrame, h: str, target_r: float, mode: str) -> np.ndarray:
    """Single-horizon bracket: cons (any rebreak=loss) | opt (target reached, ignore rebreak)."""
    tgt, cost_r = _geom(df, target_r)
    away = df[f"post_extreme.5m.{h}.max_away_from_extreme_pts"].to_numpy(float)
    rebreak = df[f"post_extreme.5m.{h}.rebreak_extreme"].to_numpy(float) > 0
    hit = away >= tgt
    win = hit & (~rebreak) if mode == "cons" else hit
    return np.where(win, target_r, -1.0) - cost_r


def boot(vals: np.ndarray, days: np.ndarray):
    u = np.unique(days)
    di = {d: np.where(days == d)[0] for d in u}
    rng = np.random.default_rng(0)
    b = [vals[np.concatenate([di[d] for d in rng.choice(u, len(u), True)])].mean() for _ in range(N_BOOT)]
    return vals.mean(), np.percentile(b, 5), np.percentile(b, 95)


def main() -> int:
    df = pd.read_parquet(EV)
    df["day"] = pd.to_datetime(df["session_date"]).dt.date
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].copy()          # confirmation universe
    mbo = [c for c in df.columns if c.startswith("mbo.")]
    fams = list(df["level_family"].unique())
    print(f"reclaimed events n={len(df)} (confirmation universe)  mbo feats={len(mbo)}  target {TARGET_R}R\n")

    print("(1) RECLAIM-ENTRY honest SEQUENCED R by family -- OOS mean [day-block CI], 2R and 3R, + opt-60m bracket:")
    for fam in fams:
        sc = df[(df["level_family"] == fam) & (df["day"] >= OOS_START)]
        if len(sc) < 15:
            print(f"   {fam:14} n<15 OOS")
            continue
        r2, r3 = seq_r(sc, 2.0), seq_r(sc, 3.0)
        m2, l2, h2 = boot(r2, sc["day"].to_numpy())
        m3, l3, h3 = boot(r3, sc["day"].to_numpy())
        opt = reclaim_r(sc, "60m", 2.0, "opt").mean()
        print(f"   {fam:14} 2R {m2:+.2f}[{l2:+.2f},{h2:+.2f}]  3R {m3:+.2f}[{l3:+.2f},{h3:+.2f}]  "
              f"(opt2R {opt:+.2f}) n{len(sc)}")

    print("\n(2) MBO gate on sequenced 2R: does confirmation-quality improve it OOS?")
    import lightgbm as lgb
    for fam in fams:
        sub = df[df["level_family"] == fam].copy()
        sub["r"] = seq_r(sub, 2.0)
        tr, te = sub[sub["day"] < OOS_START], sub[sub["day"] >= OOS_START]
        if len(te) < 20 or len(tr) < 30:
            print(f"   {fam:14} thin (tr={len(tr)} te={len(te)})")
            continue
        y = (tr["r"] > 0).astype(int)
        if y.nunique() < 2:
            print(f"   {fam:14} one-class train")
            continue
        g = lgb.LGBMClassifier(n_estimators=150, num_leaves=15, learning_rate=0.03, min_child_samples=15,
                               reg_lambda=1.0, random_state=0, verbose=-1)
        g.fit(tr[mbo].to_numpy(), y.to_numpy())
        p = g.predict_proba(te[mbo].to_numpy())[:, 1]
        take = p >= np.median(p)
        bm, bl, bh = boot(te["r"].to_numpy(), te["day"].to_numpy())
        gm, gl, gh = boot(te["r"].to_numpy()[take], te["day"].to_numpy()[take])
        print(f"   {fam:14} base {bm:+.2f}[{bl:+.2f},{bh:+.2f}] ->GATE {gm:+.2f}[{gl:+.2f},{gh:+.2f}] (n_take={take.sum()})")
    print("\n(3) POOLED gate (all families, family+MBO+geometry, sequenced 2R) -- the power check (~130 OOS):")
    d = df.copy()
    d["r"] = seq_r(d, 2.0)
    d["fam"] = d["level_family"].map({f: i for i, f in enumerate(fams)})
    feats = mbo + ["fam", "sweep.5m.max_through_pts"]
    tr, te = d[d["day"] < OOS_START], d[d["day"] >= OOS_START]
    g = lgb.LGBMClassifier(n_estimators=200, num_leaves=15, learning_rate=0.03, min_child_samples=25,
                           reg_lambda=1.0, random_state=0, verbose=-1)
    g.fit(tr[feats].to_numpy(), (tr["r"] > 0).astype(int).to_numpy())
    p = g.predict_proba(te[feats].to_numpy())[:, 1]
    bm, bl, bh = boot(te["r"].to_numpy(), te["day"].to_numpy())
    print(f"   baseline (all OOS reclaims): {bm:+.2f}[{bl:+.2f},{bh:+.2f}] n={len(te)}")
    for q, lab in [(0.50, "top50%"), (0.67, "top33%"), (0.80, "top20%")]:
        take = p >= np.quantile(p, q)
        gm, gl, gh = boot(te["r"].to_numpy()[take], te["day"].to_numpy()[take])
        print(f"   gated {lab}: {gm:+.2f}[{gl:+.2f},{gh:+.2f}] n_take={take.sum()}")
    print("\nREAD: sequenced R = honest (target-before-rebreak, stop wins ties); pooled gated CI>0 = a real tradeable subset.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
