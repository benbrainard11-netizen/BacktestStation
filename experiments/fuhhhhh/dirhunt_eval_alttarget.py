"""ANGLE 2 — train a direction model on each ALTERNATIVE target, walk-forward, with all
three mandatory controls (shuffled-y, per-month, drop-best-2-months).

For each target column built by dirhunt_build_alttarget.py we:
  - merge the geo_/struct_/opt_ features (from dataset_ndx) + mbp_ (from mbp_features_ndx)
  - run an EXPANDING walk-forward (warmup 20 days, test blocks of 10) producing OOS p_up
  - report OOS AUC, and the tradeable net-cost mean R of the rule
        "go long if p_up>=0.5 else short" using that target's r_long/r_short
  - CONTROL 1: shuffled-y -> same pipeline with permuted train labels (AUC->~0.5)
  - CONTROL 2: per-month OOS mean R breakdown
  - CONTROL 3: drop-best-2-months mean R
  - block-bootstrap p(meanR<=0) by day

Robust bar (all required): OOS AUC > shuffled by a clear margin; positive tradeR;
drop-best-2-months still positive; not carried only by recent Feb-Mar 2026.

HOLDOUT: only reads dirhunt_alttarget (dates <= DEV_END) + dataset_ndx + mbp. Never
touches dates >= 2026-04-01.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\dirhunt_eval_alttarget.py [target ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(20260613)
PARAMS = dict(objective="binary", n_estimators=250, learning_rate=0.03, num_leaves=24,
              min_child_samples=50, subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
              n_jobs=-1, verbose=-1)
WARMUP, BLOCK = 20, 10

ALL_TARGETS = [f"fret_{h}" for h in (5, 30, 60, 120)] + \
              [f"exthold_{h}" for h in (5, 30, 60, 120)] + \
              [f"cont_{h}" for h in (5, 30, 60, 120)]


def load() -> pd.DataFrame:
    alt = pd.read_parquet(OUT / "dirhunt_alttarget.parquet")
    base = pd.read_parquet(OUT / "dataset_ndx.parquet")
    feat_cols = [c for c in base.columns if c.split("_")[0] in ("geo", "struct", "opt") and c != "geo_ms"]
    df = alt.merge(base[["date", "ms"] + feat_cols], on=["date", "ms"], how="left")
    mbp = pd.read_parquet(OUT / "mbp_features_ndx.parquet")
    df = df.merge(mbp, on=["date", "ms"], how="left")
    assert df["date"].max() <= C.DEV_END, "holdout leak"
    df["mo"] = df["date"].str.slice(0, 7)
    return df


def feature_list(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.split("_")[0] in ("geo", "struct", "opt", "mbp") and c != "geo_ms"]


def block_boot(d: pd.DataFrame, col="r", b=3000) -> tuple[float, float]:
    days = d["date"].unique()
    by = {dd: d[d["date"] == dd][col].to_numpy() for dd in days}
    means = np.array([np.concatenate([by[dd] for dd in RNG.choice(days, len(days), True)]).mean()
                      for _ in range(b)])
    return float(d[col].mean()), float((means <= 0).mean())


def walk(df: pd.DataFrame, ycol: str, feats: list[str], shuffle=False) -> pd.DataFrame:
    d = df.dropna(subset=[ycol]).copy()
    days = sorted(d["date"].unique())
    oos = []
    for s in range(WARMUP, len(days), BLOCK):
        tr_d, te_d = days[:s], days[s:s + BLOCK]
        tr, te = d[d.date.isin(tr_d)], d[d.date.isin(te_d)]
        if len(tr) < 200 or len(te) < 20 or tr[ycol].nunique() < 2:
            continue
        y = tr[ycol].to_numpy().astype(int)
        if shuffle:
            y = RNG.permutation(y)
        m = lgb.LGBMClassifier(**PARAMS)
        m.fit(tr[feats], y)
        t = te.copy()
        t["p_up"] = m.predict_proba(te[feats])[:, list(m.classes_).index(1)]
        oos.append(t)
    return pd.concat(oos) if oos else pd.DataFrame()


def evaluate(df: pd.DataFrame, ycol: str, feats: list[str]) -> dict:
    rl, rs = f"{ycol}_rl", f"{ycol}_rs"
    has_r = rl in df.columns and rs in df.columns
    preds = walk(df, ycol, feats)
    if preds.empty or preds[ycol].nunique() < 2:
        return {"target": ycol, "skip": True}
    auc = roc_auc_score(preds[ycol].astype(int), preds["p_up"])
    sh = walk(df, ycol, feats, shuffle=True)
    auc_sh = roc_auc_score(sh[ycol].astype(int), sh["p_up"]) if (not sh.empty and sh[ycol].nunique() == 2) else np.nan

    res = {"target": ycol, "n": int(len(preds)), "days": int(preds["date"].nunique()),
           "up_rate": round(float(preds[ycol].mean()), 3),
           "oos_auc": round(float(auc), 4), "shuffled_auc": round(float(auc_sh), 4),
           "auc_minus_shuf": round(float(auc - auc_sh), 4)}

    if has_r:
        preds = preds.copy()
        preds["r"] = np.where(preds["p_up"] >= 0.5, preds[rl], preds[rs])
        meanR, pboot = block_boot(preds)
        res["tradeR"] = round(meanR, 4)
        res["tradeR_p_le0"] = round(pboot, 3)
        res["win_pct"] = round(float((preds["r"] > 0).mean()) * 100, 1)
        # shuffled tradeR control
        sh2 = sh.copy()
        sh2["r"] = np.where(sh2["p_up"] >= 0.5, sh2[rl], sh2[rs])
        res["shuffled_tradeR"] = round(float(sh2["r"].mean()), 4)
        # per-month + drop-best-2
        bymo = preds.groupby("mo")["r"].agg(["size", "mean"])
        res["per_month"] = {m: (int(r["size"]), round(float(r["mean"]), 4)) for m, r in bymo.iterrows()}
        ordr = bymo["mean"].sort_values(ascending=False)
        res["mo_positive"] = f"{int((bymo['mean'] > 0).sum())}/{len(bymo)}"
        drop2 = preds[~preds.mo.isin(ordr.index[:2])]
        res["drop_best2_R"] = round(float(drop2["r"].mean()), 4) if len(drop2) else np.nan
        # recent-regime check: exclude Feb-Mar 2026
        non_recent = preds[~preds.mo.isin(["2026-02", "2026-03"])]
        res["ex_FebMar26_R"] = round(float(non_recent["r"].mean()), 4) if len(non_recent) else np.nan
    return res


def main() -> int:
    targets = [a for a in sys.argv[1:] if not a.startswith("-")] or ALL_TARGETS
    df = load()
    feats = feature_list(df)
    print(f"loaded n={len(df)} days={df.date.nunique()} feats={len(feats)} "
          f"({df.date.min()}..{df.date.max()})\n")
    print(f"{'target':12s} {'n':>5s} {'AUC':>6s} {'shuf':>6s} {'dAUC':>6s} "
          f"{'tradeR':>7s} {'shufR':>7s} {'p<=0':>5s} {'drop2':>7s} {'exFM':>7s} {'mo+':>5s}")
    rows = []
    for tcol in targets:
        if tcol not in df.columns:
            print(f"{tcol:12s}  (missing)")
            continue
        r = evaluate(df, tcol, feats)
        rows.append(r)
        if r.get("skip"):
            print(f"{tcol:12s}  (skip)")
            continue
        print(f"{r['target']:12s} {r['n']:>5d} {r['oos_auc']:>6.3f} {r['shuffled_auc']:>6.3f} "
              f"{r['auc_minus_shuf']:>+6.3f} {r.get('tradeR', float('nan')):>+7.4f} "
              f"{r.get('shuffled_tradeR', float('nan')):>+7.4f} {r.get('tradeR_p_le0', float('nan')):>5.2f} "
              f"{r.get('drop_best2_R', float('nan')):>+7.4f} {r.get('ex_FebMar26_R', float('nan')):>+7.4f} "
              f"{r.get('mo_positive', ''):>5s}")
    # detailed per-month for the best AUC-edge targets
    print("\n### per-month tradeR for top targets by AUC edge")
    rows_ok = [r for r in rows if not r.get("skip")]
    for r in sorted(rows_ok, key=lambda x: -x.get("auc_minus_shuf", -9))[:5]:
        if "per_month" in r:
            print(f"\n{r['target']}  (AUC {r['oos_auc']} vs shuf {r['shuffled_auc']}, tradeR {r.get('tradeR')})")
            for m, (n, mr) in r["per_month"].items():
                print(f"    {m}  n={n:>4d}  R={mr:+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
