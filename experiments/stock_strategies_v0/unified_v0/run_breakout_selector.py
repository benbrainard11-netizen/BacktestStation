"""Dedicated BREAKOUT selector, best-shot edition: existing 18 features + the NEW free 'squeeze'
features (short interest, days-to-cover, short-interest change, short-volume ratio). Walk-forward
LightGBM. The decisive test is NOT rank-IC -- it's whether the selector's TOP cohort beats the
RANDOM-DAY baseline (the bar that dominates every breakout). Also: does squeeze ADD over the base
model, and do the squeeze features actually carry it? Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy.stats import spearmanr

import run_intraday_entry as rie

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
RNG = np.random.default_rng(0)

BASE = ["is_gap", "big_gap", "gap", "vol_spike", "ret_3m", "ret_6m", "ret_12_1", "rs_6m",
        "high52_prox", "atr_pct", "vol_contract", "base_width", "dist_ma50", "regime_up",
        "spy_ret60", "log_price", "log_dvol"]
SQUEEZE = ["days_to_cover", "short_int", "si_chg", "short_vol_ratio", "news_5d"]
PARAMS = dict(n_estimators=300, learning_rate=0.03, num_leaves=31, min_child_samples=80,
              subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1)


def load_daily_dict():
    df = pd.read_parquet(OUT / "daily_slim.parquet").sort_values(["ticker", "date"])
    D = {}
    for t, g in df.groupby("ticker", sort=False):
        o, h, l, c = (g[x].to_numpy() for x in ("open", "high", "low", "close"))
        dts = g["date"].to_numpy(); pc = np.roll(c, 1)
        tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
        atr = pd.Series(tr).rolling(14).mean().to_numpy()
        D[t] = dict(o=o, h=h, l=l, c=c, atr=atr, idx={int(x): i for i, x in enumerate(dts)})
    return D


def daily_mech(D, t, i):
    d = D.get(t)
    if d is None or i < 0 or i + 1 >= len(d["c"]):
        return None
    atr = d["atr"][i]
    if np.isnan(atr) or atr <= 0:
        return None
    entry = d["o"][i + 1] * (1 + rie.FRICTION)
    stop = entry - rie.K_ATR * atr
    if entry - stop <= 0:
        return None
    R, *_ = rie.forward_daily(d, i, entry, stop, atr)
    return R - 2 * rie.FRICTION * entry / (entry - stop)


def walk_forward(df, feats, shuffle=False):
    df = df.copy(); df["dt"] = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d")
    df["y"] = df["R"].clip(-3, 10)
    out = []
    for Y in (2023, 2024, 2025, 2026):
        tr = df[df["dt"] < pd.Timestamp(Y, 1, 1) - pd.Timedelta(days=45)]
        te = df[df["dt"].dt.year == Y]
        if len(tr) < 3000 or len(te) < 300:
            continue
        y = tr["y"].sample(frac=1, random_state=0).to_numpy() if shuffle else tr["y"].to_numpy()
        m = lgb.LGBMRegressor(**PARAMS).fit(tr[feats], y)
        t = te.copy(); t["pred"] = m.predict(te[feats]); out.append(t)
    return pd.concat(out, ignore_index=True)


def eqw(df):
    return df.groupby("tkr")["R"].mean().mean()


def boot(x, n=2000):
    x = np.asarray(x); idx = RNG.integers(0, len(x), (n, len(x)))
    return np.percentile(x[idx].mean(1), [2.5, 97.5])


def main():
    res = pd.read_parquet(OUT / "intraday_entry_results.parquet")
    setups = pd.read_parquet(OUT / "setups.parquet").rename(columns={"ticker": "tkr"})
    sq = pd.read_parquet(OUT / "selector_feats.parquet")
    news = pd.read_parquet(OUT / "news_counts.parquet")
    df = res.merge(setups[["tkr", "date"] + BASE], on=["tkr", "date"], how="left")
    df = df.merge(sq, on=["tkr", "date"], how="left")
    df = df.merge(news, on=["tkr", "date"], how="left")
    for c in SQUEEZE:
        df[c] = df[c].astype(float)
    print(f"merged {len(df):,} trades | squeeze coverage: "
          + ", ".join(f"{c} {df[c].notna().mean()*100:.0f}%" for c in SQUEEZE) + "\n")

    oos_b = walk_forward(df, BASE)
    oos_s = walk_forward(df, BASE + SQUEEZE)
    ctrl = walk_forward(df, BASE + SQUEEZE, shuffle=True)
    print("=== OOS rank-IC (pred vs intraday R) ===")
    print(f"  base 18 feats          : {spearmanr(oos_b.pred, oos_b.R).correlation:+.3f}")
    print(f"  base + squeeze + news  : {spearmanr(oos_s.pred, oos_s.R).correlation:+.3f}")
    print(f"  shuffled control       : {spearmanr(ctrl.pred, ctrl.R).correlation:+.3f}")

    print("\n=== feature importance (base + squeeze, full-fit gain) ===")
    imp = pd.Series(lgb.LGBMRegressor(**PARAMS).fit(df[BASE + SQUEEZE].fillna(-1), df["R"].clip(-3, 10)).feature_importances_,
                    index=BASE + SQUEEZE).sort_values(ascending=False)
    print("  " + "  ".join(f"{k}:{int(v)}" for k, v in imp.head(12).items()))
    print("  SQUEEZE ranks: " + ", ".join(f"{c}=#{list(imp.index).index(c)+1}" for c in SQUEEZE))

    # decisive: top decile vs random-day baseline
    print("\n=== DECISIVE: model top decile (squeeze) — does it beat the random-day bar? ===")
    oos_s["dec"] = pd.qcut(oos_s["pred"].rank(method="first"), 10, labels=False)
    top = oos_s[oos_s["dec"] == 9]
    ci = boot(top["R"].to_numpy())
    print(f"  top-decile intraday R: mean {top.R.mean():+.3f} CI[{ci[0]:+.3f},{ci[1]:+.3f}]  "
          f"eqw-by-ticker {eqw(top):+.3f}  cap[-3,10] {top.R.clip(-3,10).mean():+.3f}  win {(top.R>0).mean()*100:.0f}%")
    print(f"  (base-only top decile intraday R: {oos_b[pd.qcut(oos_b['pred'].rank(method='first'),10,labels=False)==9].R.mean():+.3f})")

    D = load_daily_dict()
    cand = {(r.tkr, int(r.date)) for r in top.itertuples(index=False)}
    cand_by_t = {t: set() for t, _ in cand}
    for t, d in cand:
        cand_by_t[t].add(d)
    cR, rR = [], []
    for t, days in cand_by_t.items():
        d = D.get(t)
        if d is None:
            continue
        for dd in days:
            if dd in d["idx"]:
                v = daily_mech(D, t, d["idx"][dd])
                if v is not None:
                    cR.append(v)
        rev = {v: k for k, v in d["idx"].items()}
        avail = [j for j in range(60, len(d["c"]) - 41) if rev[j] not in days]
        if avail:
            for j in RNG.choice(avail, min(3 * len(days), len(avail)), replace=False):
                v = daily_mech(D, t, j)
                if v is not None:
                    rR.append(v)
    cR, rR = np.array(cR), np.array(rR)
    print(f"\n  NULL CONTROL (daily mechanic): top-decile breakout days {cR.mean():+.3f} (n{len(cR)})  "
          f"vs random days {rR.mean():+.3f} (n{len(rR)})  DELTA {cR.mean()-rR.mean():+.3f}")
    print("\nREAD: top-decile beats random-day (DELTA>0) AND squeeze ranks high AND adds rank-IC")
    print("=> a dedicated breakout selector works. Else: even the best free squeeze features can't rescue it.")


if __name__ == "__main__":
    main()
