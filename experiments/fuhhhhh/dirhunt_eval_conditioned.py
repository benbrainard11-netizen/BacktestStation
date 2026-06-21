"""ANGLE 2 (deepening) — conditioned direction skill on alternative targets.

The naked grid result is noise (AUC ~ shuffled; positive tradeR is just a static
short-lean drift, not OOS discrimination). The real question: does ANY alternative
target reveal direction SKILL inside a meaningful decision STATE that the naked grid
washes out? We train ONE walk-forward model per target on ALL rows (so training set is
large) but EVALUATE OOS AUC + tradeR within conditioning slices:
    @TRIG   : a sweep or SMT fired at t  (struct_sweep!=0 | struct_smt!=0)
    @OPEN   : first hour (geo_hour in {9,10})
    @MIDDAY : 11-13
    @PM     : 14-15
    @GAMMA+ : prior-day positive gamma (opt_gamma_sign>0, pinning/mean-revert regime)
    @GAMMA- : negative gamma (trending regime)
    @NEARWALL: close to a wall (min(|dist_call|,|dist_put|) < 0.5 ATR)

Controls per slice: shuffled-y AUC, per-month tradeR, drop-best-2-months, ex-FebMar26.
A slice is a real edge only if OOS AUC clearly beats its own shuffled control AND tradeR
survives drop-best-2 AND is not recent-regime-only.

HOLDOUT sealed (dates <= DEV_END only).

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\dirhunt_eval_conditioned.py [target ...]
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
DEFAULT_TARGETS = ["fret_30", "fret_60", "fret_120", "exthold_30", "exthold_60", "cont_60", "cont_120"]


def load() -> pd.DataFrame:
    alt = pd.read_parquet(OUT / "dirhunt_alttarget.parquet")
    base = pd.read_parquet(OUT / "dataset_ndx.parquet")
    feat_cols = [c for c in base.columns if c.split("_")[0] in ("geo", "struct", "opt") and c != "geo_ms"]
    df = alt.merge(base[["date", "ms"] + feat_cols], on=["date", "ms"], how="left")
    mbp = pd.read_parquet(OUT / "mbp_features_ndx.parquet")
    df = df.merge(mbp, on=["date", "ms"], how="left")
    assert df["date"].max() <= C.DEV_END, "holdout leak"
    df["mo"] = df["date"].str.slice(0, 7)
    # cont targets: build a tradeable bracket R from the fret bracket of the same H,
    # mapped to the pre-move direction. r for cont = "trade in pre-move dir if model
    # says continue, else opposite". We just attach the H-matched fret r so the eval
    # can construct a directional R from p_up.
    return df


def slices(df: pd.DataFrame) -> dict[str, np.ndarray]:
    h = df.get("geo_hour")
    sweep = df.get("struct_sweep")
    smt = df.get("struct_smt")
    gs = df.get("opt_gamma_sign")
    dc = df.get("opt_dist_call_atr").abs() if "opt_dist_call_atr" in df else None
    dp = df.get("opt_dist_put_atr").abs() if "opt_dist_put_atr" in df else None
    sl = {
        "ALL": np.ones(len(df), bool),
        "@TRIG": ((sweep != 0) | (smt != 0)).to_numpy(),
        "@OPEN": h.isin([9, 10]).to_numpy(),
        "@MIDDAY": h.isin([11, 12, 13]).to_numpy(),
        "@PM": h.isin([14, 15]).to_numpy(),
        "@GAMMA+": (gs > 0).to_numpy(),
        "@GAMMA-": (gs < 0).to_numpy(),
    }
    if dc is not None and dp is not None:
        sl["@NEARWALL"] = (np.minimum(dc, dp) < 0.5).to_numpy()
    return sl


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


def r_for_target(d: pd.DataFrame, ycol: str) -> pd.DataFrame:
    """Attach r_long/r_short for the directional rule on this target."""
    d = d.copy()
    if ycol.startswith("cont"):
        H = ycol.split("_")[1]
        rl, rs = f"fret_{H}_rl", f"fret_{H}_rs"
        # cont=1 means "continue pre-move dir". Map p_up (=p continue) to a directional
        # trade: if pre_d>0, continue=long; if pre_d<0, continue=short. So:
        #   predicted-continue & pre_d>0 -> long ; predicted-continue & pre_d<0 -> short
        #   predicted-reverse & pre_d>0 -> short; etc.
        d["_rl"] = d[rl]
        d["_rs"] = d[rs]
        return d
    rl, rs = f"{ycol}_rl", f"{ycol}_rs"
    d["_rl"] = d[rl]
    d["_rs"] = d[rs]
    return d


def trade_r(preds: pd.DataFrame, ycol: str) -> np.ndarray:
    if ycol.startswith("cont"):
        pre = preds["pre_d"].to_numpy()
        cont = preds["p_up"].to_numpy() >= 0.5     # predicted "continue"
        go_long = np.where(cont, pre > 0, pre < 0)  # continue&up OR reverse&down -> long
        return np.where(go_long, preds["_rl"], preds["_rs"])
    return np.where(preds["p_up"] >= 0.5, preds["_rl"], preds["_rs"])


def main() -> int:
    targets = [a for a in sys.argv[1:] if not a.startswith("-")] or DEFAULT_TARGETS
    df = load()
    feats = [c for c in df.columns if c.split("_")[0] in ("geo", "struct", "opt", "mbp") and c != "geo_ms"]
    print(f"loaded n={len(df)} days={df.date.nunique()} feats={len(feats)}\n")

    for tcol in targets:
        if tcol not in df.columns:
            continue
        preds = walk(df, tcol, feats)
        sh = walk(df, tcol, feats, shuffle=True)
        if preds.empty:
            continue
        preds = r_for_target(preds, tcol)
        sh = r_for_target(sh, tcol)
        preds["r"] = trade_r(preds, tcol)
        sh["r"] = trade_r(sh, tcol)
        sl = slices(preds.assign())
        sl_sh = slices(sh.assign())
        print(f"=== {tcol} ===  (OOS rows {len(preds)})")
        print(f"  {'slice':10s} {'n':>5s} {'AUC':>6s} {'shuf':>6s} {'dAUC':>6s} "
              f"{'tradeR':>7s} {'shufR':>7s} {'p<=0':>5s} {'drop2':>7s} {'exFM':>7s} {'mo+':>5s}")
        for name, mask in sl.items():
            seg = preds[mask]
            if len(seg) < 100 or seg[tcol].nunique() < 2:
                continue
            auc = roc_auc_score(seg[tcol].astype(int), seg["p_up"])
            seg_sh = sh[sl_sh[name]] if name in sl_sh else sh.iloc[0:0]
            auc_sh = roc_auc_score(seg_sh[tcol].astype(int), seg_sh["p_up"]) if (len(seg_sh) > 50 and seg_sh[tcol].nunique() == 2) else np.nan
            meanR, p = block_boot(seg)
            shufR = float(seg_sh["r"].mean()) if len(seg_sh) else np.nan
            bymo = seg.groupby("mo")["r"].mean()
            mo_pos = f"{int((bymo > 0).sum())}/{len(bymo)}"
            ordr = bymo.sort_values(ascending=False)
            drop2 = seg[~seg.mo.isin(ordr.index[:2])]["r"].mean()
            exfm = seg[~seg.mo.isin(["2026-02", "2026-03"])]["r"].mean()
            print(f"  {name:10s} {len(seg):>5d} {auc:>6.3f} {auc_sh:>6.3f} {auc-auc_sh:>+6.3f} "
                  f"{meanR:>+7.4f} {shufR:>+7.4f} {p:>5.2f} {drop2:>+7.4f} {exfm:>+7.4f} {mo_pos:>5s}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
