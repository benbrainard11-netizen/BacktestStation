"""Walk-forward runner + evaluation layer for Iteration 1+.

Changes vs model_v0's inline version (locked there for the record):
- EV trade rule includes the TIMEOUT leg: + p_none * E[gross r | timeout], with the
  expectation estimated per fold from TRAIN rows only (no test leakage).
- Expanded metrics (median, gross, PF, maxDD, Brier, trade rate), EV-decile ranking
  table, calibration table, regime splits, per-fold feature-importance stability.
- run_wf carries decision-time price/objectives AND realized entry through to eval;
  the d1 (one-bar-delayed-entry) outcome columns ride along for robustness test I.
"""

from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd

import common as C

RNG = np.random.default_rng(7)
PARAMS = dict(objective="multiclass", num_class=3, learning_rate=0.05, num_leaves=31,
              n_estimators=400, min_child_samples=50, feature_fraction=0.8,
              bagging_fraction=0.8, bagging_freq=1, verbose=-1, seed=7, n_jobs=-1)
MIN_TRAIN_D, TEST_D, EMBARGO_D = 110, 21, 1
EV_MIN = 0.05
BOOT_N = 1000
CARRY = ["date", "ms", "y", "r_long_net", "r_short_net", "r_long_net_d1", "r_short_net_d1",
         "price", "entry", "obj_up", "obj_dn"]


def wf_folds(days: list[str]) -> list[tuple[list[str], list[str]]]:
    folds, i = [], MIN_TRAIN_D
    while i + TEST_D <= len(days):
        folds.append((days[: i - EMBARGO_D], days[i : i + TEST_D]))
        i += TEST_D
    if i < len(days) and len(days) - i >= 10:
        folds.append((days[: i - EMBARGO_D], days[i:]))
    return folds


def run_wf(df: pd.DataFrame, cols: list[str], y: np.ndarray, label: str):
    """Returns (oos_preds, fold_importances). Ambiguous rows never train, always score."""
    days = sorted(df["date"].unique())
    preds, imps = [], []
    for k, (tr_days, te_days) in enumerate(wf_folds(days)):
        tr = df["date"].isin(tr_days).to_numpy() & (y >= 0)
        te = df["date"].isin(te_days).to_numpy()
        m = lgb.LGBMClassifier(**PARAMS)
        m.fit(df.loc[tr, cols], y[tr])
        p = m.predict_proba(df.loc[te, cols])
        out = df.loc[te, CARRY].copy()
        out["p_dn"], out["p_up"], out["p_none"] = p[:, 0], p[:, 1], p[:, 2]
        out["fold"] = k
        # timeout-leg expectations from TRAIN rows only (gross R, per side)
        trn = df.loc[tr]
        to = trn[trn["y"] == 2]
        if len(to) >= 30:
            out["mu_to_long"] = float((to["r_long_net"] + C.COST_PTS / (to["entry"] - to["obj_dn"])).mean())
            out["mu_to_short"] = float((to["r_short_net"] + C.COST_PTS / (to["obj_up"] - to["entry"])).mean())
        else:
            out["mu_to_long"] = out["mu_to_short"] = 0.0
        preds.append(out)
        imps.append(pd.Series(m.booster_.feature_importance("gain"), index=cols, name=k))
    res = pd.concat(preds, ignore_index=True)
    res["ablation"] = label
    return res, pd.DataFrame(imps)


def ev_columns(res: pd.DataFrame) -> pd.DataFrame:
    """EV (R units, net of costs, WITH timeout leg) from decision-time geometry."""
    r = res.copy()
    du, dd = r["obj_up"] - r["price"], r["price"] - r["obj_dn"]
    r["ev_long"] = r["p_up"] * (du / dd) - r["p_dn"] + r["p_none"] * r["mu_to_long"] - C.COST_PTS / dd
    r["ev_short"] = r["p_dn"] * (dd / du) - r["p_up"] + r["p_none"] * r["mu_to_short"] - C.COST_PTS / du
    r["edge"] = np.maximum(r["ev_long"], r["ev_short"])
    r["side_long"] = r["ev_long"] >= r["ev_short"]
    return r


def _chosen_r(t: pd.DataFrame, suffix: str = "") -> pd.Series:
    return pd.Series(np.where(t["side_long"], t[f"r_long_net{suffix}"], t[f"r_short_net{suffix}"]),
                     index=t.index)


def trade_eval(res: pd.DataFrame, suffix: str = "") -> dict:
    """Full metric set for the EV rule (edge >= EV_MIN). suffix='_d1' = delayed entry."""
    r = ev_columns(res)
    t = r[r["edge"] >= EV_MIN].copy()
    t["r"] = _chosen_r(t, suffix)
    n_nan = int(t["r"].isna().sum())
    t = t.dropna(subset=["r"])
    if len(t) < 20:
        return {"n": len(t), "note": "too few trades"}
    du, dd = t["obj_up"] - t["entry"], t["entry"] - t["obj_dn"]
    cost_r = np.where(t["side_long"], C.COST_PTS / dd, C.COST_PTS / du)
    wins, losses = t.loc[t["r"] > 0, "r"], t.loc[t["r"] <= 0, "r"]
    daily = t.groupby("date")["r"].sum()
    cum = daily.cumsum()
    boots = [RNG.choice(daily.to_numpy() / np.maximum(t.groupby("date").size().to_numpy(), 1),
                        size=len(daily), replace=True).mean() for _ in range(BOOT_N)]
    monthly = t.groupby(t["date"].str.slice(0, 7))["r"].agg(["mean", "count"])
    resolved = res[res["y"] >= 0]
    p = resolved[["p_dn", "p_up", "p_none"]].to_numpy()
    onehot = np.eye(3)[resolved["y"].to_numpy()]
    return {
        "n": len(t), "n_dropped_nan": n_nan, "trade_rate": len(t) / len(res),
        "mean_r": float(t["r"].mean()), "median_r": float(t["r"].median()),
        "gross_mean_r": float((t["r"] + cost_r).mean()), "avg_cost_r": float(cost_r.mean()),
        "win": float((t["r"] > 0).mean()),
        "avg_win": float(wins.mean()) if len(wins) else np.nan,
        "avg_loss": float(losses.mean()) if len(losses) else np.nan,
        "pf": float(wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else np.nan,
        "max_dd": float((cum - cum.cummax()).min()),
        "ci": (float(np.percentile(boots, 5)), float(np.percentile(boots, 95))),
        "pos_months": int((monthly["mean"] > 0).sum()), "months": len(monthly), "monthly": monthly,
        "logloss": float(-np.mean(np.log(np.clip(np.take_along_axis(
            p, resolved["y"].to_numpy()[:, None], axis=1), 1e-9, 1)))),
        "brier": float(np.mean(((p - onehot) ** 2).sum(axis=1))),
        "fold_means": t.groupby("fold")["r"].agg(["mean", "count"]),
    }


def ranking_table(res: pd.DataFrame) -> pd.DataFrame:
    """Realized chosen-side net R by predicted-EV decile (deciles within fold)."""
    r = ev_columns(res)
    r["r"] = _chosen_r(r)
    r = r.dropna(subset=["r"])
    r["decile"] = r.groupby("fold")["edge"].transform(
        lambda s: pd.qcut(s.rank(method="first"), 10, labels=False))
    tab = r.groupby("decile")["r"].agg(["mean", "count"])
    tab["edge_mean"] = r.groupby("decile")["edge"].mean()
    return tab


def rank_spearman(tab: pd.DataFrame) -> float:
    from scipy.stats import spearmanr
    return float(spearmanr(tab.index.to_numpy(), tab["mean"].to_numpy()).statistic)


def calibration_table(res: pd.DataFrame) -> pd.DataFrame:
    """Predicted p_up vs realized up-first rate (resolved directional rows only)."""
    r = res[res["y"].isin([0, 1])].copy()
    r["bucket"] = pd.cut(r["p_up"], [0, 0.25, 0.35, 0.45, 0.55, 0.65, 1.0])
    g = r.groupby("bucket", observed=True)
    return pd.DataFrame({"pred_p_up": g["p_up"].mean(), "realized_up": g["y"].mean(), "n": g.size()})


def regime_table(res: pd.DataFrame, feats: pd.DataFrame) -> pd.DataFrame:
    """EV-rule trades' mean R by regime split (descriptive diagnostics, pooled medians)."""
    r = ev_columns(res)
    r["r"] = _chosen_r(r)
    r = r.merge(feats, on=["date", "ms"], how="left").dropna(subset=["r"])
    t = r[r["edge"] >= EV_MIN].copy()
    et_h = t["ms"] / 3600_000
    near = np.minimum(t["geo_dist_up"], t["geo_dist_dn"])
    splits = {
        "morning (<11:30)": et_h < 11.5, "midday (11:30-14)": (et_h >= 11.5) & (et_h < 14),
        "afternoon (>=14)": et_h >= 14,
        "near objective": near <= near.median(), "far objective": near > near.median(),
        "high rv30": t["fut_rv_30m"] > t["fut_rv_30m"].median(),
        "low rv30": t["fut_rv_30m"] <= t["fut_rv_30m"].median(),
        "mom up (ret15m>0)": t["fut_ret_15m"] > 0, "mom dn": t["fut_ret_15m"] <= 0,
        "high vol burst": t["fut_vol_burst"] > t["fut_vol_burst"].median(),
    }
    rows = [{"regime": k, "mean_r": float(t.loc[m, "r"].mean()), "n": int(m.sum())}
            for k, m in splits.items() if m.sum() >= 30]
    return pd.DataFrame(rows).set_index("regime")


def importance_stability(imps: pd.DataFrame) -> pd.DataFrame:
    """Per-feature: mean gain share, folds-in-top-20 count (1 = one-fold wonder)."""
    share = imps.div(imps.sum(axis=1), axis=0)
    top20 = share.rank(axis=1, ascending=False) <= 20
    return pd.DataFrame({"gain_share": share.mean(), "folds_top20": top20.sum(),
                         "n_folds": len(imps)}).sort_values("gain_share", ascending=False)
