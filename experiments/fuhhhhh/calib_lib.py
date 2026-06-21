"""Iteration 2A library: nested calibration, payoff caps, nested EV_MIN, metrics.

Fold anatomy (test blocks identical to v1 for comparability):
  fit days = train[: -CAL_D-1]   (1-day embargo before calibration segment)
  cal days = train[-CAL_D :]     (calibrator + EV_MIN threshold are chosen HERE)
  test     = same 21-day blocks as v1 (1-day embargo after train)
Nothing is ever fitted or selected on the fold's test segment.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import common as C
import eval_lib as E

CAL_D = 21
EV_GRID = (0.0, 0.02, 0.05, 0.08, 0.12, 0.20)
CAPS = (None, 1.5, 2.0, 3.0, 4.0)
MIN_CAL_TRADES = 40
DEFAULT_EV_MIN = 0.05
RNG = np.random.default_rng(7)


def fold_predictions(df: pd.DataFrame, cols: list[str], y: np.ndarray):
    """One model fit per fold; raw probabilities on cal + test segments.

    Returns list of dicts: {fold, cal (DataFrame), te (DataFrame)} where each frame
    carries eval columns + p_dn/p_up/p_none (raw) + mu_to_long/short (train-only).
    """
    import lightgbm as lgb

    days = sorted(df["date"].unique())
    out = []
    for k, (tr_days, te_days) in enumerate(E.wf_folds(days)):
        fit_days, cal_days = tr_days[: -CAL_D - 1], tr_days[-CAL_D:]
        fit = df["date"].isin(fit_days).to_numpy() & (y >= 0)
        m = lgb.LGBMClassifier(**E.PARAMS)
        m.fit(df.loc[fit, cols], y[fit])
        trn = df.loc[df["date"].isin(tr_days).to_numpy()]
        to = trn[trn["y"] == 2]
        mu_l = float((to["r_long_net"] + C.COST_PTS / (to["entry"] - to["obj_dn"])).mean()) if len(to) >= 30 else 0.0
        mu_s = float((to["r_short_net"] + C.COST_PTS / (to["obj_up"] - to["entry"])).mean()) if len(to) >= 30 else 0.0
        segs = {}
        for seg, seg_days in (("cal", cal_days), ("te", te_days)):
            mask = df["date"].isin(seg_days).to_numpy()
            p = m.predict_proba(df.loc[mask, cols])
            fr = df.loc[mask, E.CARRY].copy()
            fr["p_dn"], fr["p_up"], fr["p_none"] = p[:, 0], p[:, 1], p[:, 2]
            fr["mu_to_long"], fr["mu_to_short"], fr["fold"] = mu_l, mu_s, k
            segs[seg] = fr
        out.append(segs)
    return out


def make_calibrator(p_cal: np.ndarray, y_cal: np.ndarray, method: str):
    """Per-class one-vs-rest calibrator fitted on the calibration segment only."""
    if method == "none":
        return lambda p: p, False
    fns, unstable = [], False
    for k in range(3):
        tgt = (y_cal == k).astype(float)
        if tgt.sum() < 50:
            unstable = True
        x = p_cal[:, k]
        if method == "isotonic":
            from sklearn.isotonic import IsotonicRegression
            f = IsotonicRegression(out_of_bounds="clip", y_min=1e-4, y_max=1 - 1e-4).fit(x, tgt)
            fns.append(f.predict)
        else:  # sigmoid / Platt
            from sklearn.linear_model import LogisticRegression
            lx = np.log(np.clip(x, 1e-6, 1 - 1e-6) / np.clip(1 - x, 1e-6, 1 - 1e-6))
            f = LogisticRegression(C=1e6).fit(lx.reshape(-1, 1), tgt > 0.5)
            fns.append(lambda p, f=f: f.predict_proba(
                np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1 - 1e-6)).reshape(-1, 1))[:, 1])

    def apply(p: np.ndarray) -> np.ndarray:
        q = np.column_stack([fns[k](p[:, k]) for k in range(3)])
        q = np.clip(q, 1e-6, None)
        return q / q.sum(axis=1, keepdims=True)

    return apply, unstable


def ev_frame(fr: pd.DataFrame, cap: float | None) -> pd.DataFrame:
    """EV columns with optional payoff-ratio cap (cap affects SELECTION only; realized
    R is untouched). Cost terms always use the true uncapped denominators."""
    r = fr.copy()
    du, dd = r["obj_up"] - r["price"], r["price"] - r["obj_dn"]
    rl, rs = du / dd, dd / du
    if cap is not None:
        rl, rs = np.minimum(rl, cap), np.minimum(rs, cap)
    r["ev_long"] = r["p_up"] * rl - r["p_dn"] + r["p_none"] * r["mu_to_long"] - C.COST_PTS / dd
    r["ev_short"] = r["p_dn"] * rs - r["p_up"] + r["p_none"] * r["mu_to_short"] - C.COST_PTS / du
    r["edge"] = np.maximum(r["ev_long"], r["ev_short"])
    r["side_long"] = r["ev_long"] >= r["ev_short"]
    return r


def chosen_r(t: pd.DataFrame, suffix: str = "") -> pd.Series:
    return pd.Series(np.where(t["side_long"], t[f"r_long_net{suffix}"], t[f"r_short_net{suffix}"]),
                     index=t.index)


def pick_threshold(cal_fr: pd.DataFrame, cap: float | None) -> float:
    """Nested EV_MIN: maximize calibration-segment realized mean R (min-n guarded)."""
    r = ev_frame(cal_fr, cap)
    r["r"] = chosen_r(r)
    r = r.dropna(subset=["r"])
    best_thr, best = DEFAULT_EV_MIN, -np.inf
    for thr in EV_GRID:
        t = r[r["edge"] >= thr]
        if len(t) < MIN_CAL_TRADES:
            continue
        mu = t["r"].mean()
        if mu > best:
            best, best_thr = mu, thr
    return best_thr


def pooled_metrics(trades: pd.DataFrame, n_universe: int, te_all: pd.DataFrame) -> dict:
    """Required 2A metric set over pooled OOS trades."""
    t = trades.dropna(subset=["r"])
    if len(t) < 20:
        return {"n": len(t), "note": "too few trades"}
    du, dd = t["obj_up"] - t["entry"], t["entry"] - t["obj_dn"]
    cost_r = np.where(t["side_long"], C.COST_PTS / dd, C.COST_PTS / du)
    wins, losses = t.loc[t["r"] > 0, "r"], t.loc[t["r"] <= 0, "r"]
    daily = t.groupby("date")["r"].sum()
    cum = daily.cumsum()
    per_day_mean = t.groupby("date")["r"].mean()
    boots = [RNG.choice(per_day_mean.to_numpy(), size=len(per_day_mean), replace=True).mean()
             for _ in range(500)]
    monthly = t.groupby(t["date"].str.slice(0, 7))["r"].agg(["mean", "count"])
    res = te_all[te_all["y"] >= 0]
    p = res[["p_dn", "p_up", "p_none"]].to_numpy()
    onehot = np.eye(3)[res["y"].to_numpy()]
    return {
        "n": len(t), "trade_rate": len(t) / n_universe,
        "trades_per_fold": t.groupby("fold").size().to_dict(),
        "pct_days_traded": t["date"].nunique() / te_all["date"].nunique(),
        "mean_r": float(t["r"].mean()), "median_r": float(t["r"].median()),
        "gross_mean_r": float((t["r"] + cost_r).mean()),
        "win": float((t["r"] > 0).mean()),
        "avg_win": float(wins.mean()) if len(wins) else np.nan,
        "avg_loss": float(losses.mean()) if len(losses) else np.nan,
        "pf": float(wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else np.nan,
        "max_dd": float((cum - cum.cummax()).min()),
        "ci": (float(np.percentile(boots, 5)), float(np.percentile(boots, 95))),
        "pos_months": int((monthly["mean"] > 0).sum()), "months": len(monthly),
        "pos_folds": int((t.groupby("fold")["r"].mean() > 0).sum()),
        "n_folds": t["fold"].nunique(), "monthly": monthly,
        "logloss": float(-np.mean(np.log(np.clip(
            np.take_along_axis(p, res["y"].to_numpy()[:, None], axis=1), 1e-9, 1)))),
        "brier": float(np.mean(((p - onehot) ** 2).sum(axis=1))),
    }


def drop_days(trades: pd.DataFrame, n_best: int = 5, n_worst: int = 5) -> dict:
    """Day-removal robustness: mean R after dropping best/worst daily-sum days."""
    t = trades.dropna(subset=["r"])
    daily = t.groupby("date")["r"].sum().sort_values()
    worst, best = list(daily.index[:n_worst]), list(daily.index[-n_best:])
    keep_nb = t[~t["date"].isin(best)]
    keep_both = t[~t["date"].isin(best + worst)]
    return {"base": float(t["r"].mean()),
            "drop_best5": float(keep_nb["r"].mean()) if len(keep_nb) else np.nan,
            "drop_both5": float(keep_both["r"].mean()) if len(keep_both) else np.nan}


def residual_edge_table(te_all: pd.DataFrame) -> pd.DataFrame:
    """Residual edge over geometry: logit(p_dir) − logit(prior), |delta| deciles,
    side = sign(delta). Reports gross and net realized R per decile + fold stability."""
    r = te_all.copy()
    du, dd = r["obj_up"] - r["price"], r["price"] - r["obj_dn"]
    prior = (dd / (du + dd)).clip(1e-6, 1 - 1e-6)
    p_dir = (r["p_up"] / (r["p_up"] + r["p_dn"])).clip(1e-6, 1 - 1e-6)
    r["delta"] = np.log(p_dir / (1 - p_dir)) - np.log(prior / (1 - prior))
    r["side_long"] = r["delta"] > 0
    r["r"] = chosen_r(r)
    r = r.dropna(subset=["r"])
    edd, edu = r["entry"] - r["obj_dn"], r["obj_up"] - r["entry"]
    r["cost_r"] = np.where(r["side_long"], C.COST_PTS / edd, C.COST_PTS / edu)
    r["decile"] = r.groupby("fold")["delta"].transform(
        lambda s: pd.qcut(s.abs().rank(method="first"), 10, labels=False))
    g = r.groupby("decile")
    tab = pd.DataFrame({"net_r": g["r"].mean(), "gross_r": (g["r"].mean() + g["cost_r"].mean()),
                        "n": g.size(), "abs_delta": g["delta"].apply(lambda s: s.abs().mean())})
    top = r[r["decile"] >= 8]
    tab.attrs["top2_by_fold"] = top.groupby("fold")["r"].agg(["mean", "count"])
    tab.attrs["top2_d1"] = float(pd.Series(
        np.where(top["side_long"], top["r_long_net_d1"], top["r_short_net_d1"]),
        index=top.index).dropna().mean())
    return tab
