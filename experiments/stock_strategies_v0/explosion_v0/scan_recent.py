"""Scan the most RECENT breakouts in the data and score them with the explosion classifier (AUC 0.88).
Breakout = close > prior-20d-high (liquid). The model's P(explosion) flags which are explosion-prone /
high-variance -- a watchlist/risk signal, NOT a buy signal (breakouts have no tradeable directional edge).
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb

POLY = Path(r"D:\data\processed\stocks\polygon")
HERE = Path(__file__).resolve().parent
FEATS = ["gap", "is_brk", "vol_spike", "ret_1m", "ret_3m", "ret_6m", "ret_12_1", "rs_6m",
         "high52_prox", "atr_pct", "vol_contract", "base_width", "dist_ma50", "regime_up",
         "spy_ret60", "log_price", "log_dvol"]
PARAMS = dict(n_estimators=350, learning_rate=0.03, num_leaves=48, min_child_samples=120,
              subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1)
MIN_PRICE, MIN_DVOL = 3.0, 2e6

# train the explosion model on the historical labeled setups
S = pd.read_parquet(HERE / "out" / "explosion_setups.parquet")
mdl = lgb.LGBMClassifier(**PARAMS).fit(S[FEATS], S["expl40"])
base = S["expl40"].mean()

# build features for the LATEST breakouts
df = pd.concat([pd.read_parquet(f) for f in [POLY / "daily_2025.parquet", POLY / "daily_2026.parquet"]], ignore_index=True)
meta = pd.read_parquet(POLY / "meta.parquet")
cs = set(meta["ticker"]); active = dict(zip(meta["ticker"], meta["active"]))
spy = df[df["ticker"] == "SPY"].sort_values("date")
spy_ret60 = (spy.set_index("date")["close"] / spy.set_index("date")["close"].shift(60) - 1).to_dict()
spy_ma = (spy.set_index("date")["close"] > spy.set_index("date")["close"].rolling(50).mean()).to_dict()
last_date = int(df["date"].max())
print(f"latest data date: {last_date}  (breakouts on the last 2 trading days)\n")

dates_sorted = sorted(df["date"].unique())
recent = set(dates_sorted[-2:])
rows = []
for t, d in df[df["ticker"].isin(cs)].sort_values(["ticker", "date"]).groupby("ticker", sort=False):
    if len(d) < 260:
        continue
    o = d["open"].to_numpy(); h = d["high"].to_numpy(); l = d["low"].to_numpy()
    c = d["close"].to_numpy(); v = d["volume"].to_numpy(); dts = d["date"].to_numpy().astype(int)
    n = len(c); pc = np.roll(c, 1)
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = pd.Series(tr).rolling(14).mean().to_numpy(); atr50 = pd.Series(tr).rolling(50).mean().to_numpy()
    ma50 = pd.Series(c).rolling(50).mean().to_numpy()
    hi20 = pd.Series(h).rolling(20).max().shift(1).to_numpy(); lo20 = pd.Series(l).rolling(20).min().shift(1).to_numpy()
    hi252 = pd.Series(h).rolling(252).max().to_numpy()
    avgv = pd.Series(v).rolling(20).mean().shift(1).to_numpy(); dvol = pd.Series(c * v).rolling(20).mean().shift(1).to_numpy()
    for i in range(252, n):
        if dts[i] not in recent:
            continue
        gap = o[i] / c[i - 1] - 1
        is_brk = c[i] > hi20[i] if not np.isnan(hi20[i]) else False
        if not (is_brk or gap >= 0.05):
            continue
        if c[i] < MIN_PRICE or np.isnan(dvol[i]) or dvol[i] < MIN_DVOL or np.isnan(atr[i - 1]) or atr[i - 1] <= 0:
            continue
        di = int(dts[i])
        rows.append({"ticker": t, "date": di, "active": bool(active.get(t, False)), "price": c[i],
                     "gap": gap, "is_brk": int(is_brk), "vol_spike": v[i] / avgv[i] if avgv[i] else np.nan,
                     "ret_1m": c[i] / c[i - 21] - 1, "ret_3m": c[i] / c[i - 63] - 1,
                     "ret_6m": c[i] / c[i - 126] - 1, "ret_12_1": c[i - 21] / c[i - 252] - 1,
                     "rs_6m": (c[i] / c[i - 126] - 1) - (spy_ret60.get(di) or 0),
                     "high52_prox": c[i] / hi252[i] if hi252[i] else np.nan,
                     "atr_pct": atr[i - 1] / c[i], "vol_contract": atr[i - 1] / atr50[i - 1] if atr50[i - 1] else np.nan,
                     "base_width": (hi20[i] - lo20[i]) / c[i] if not np.isnan(hi20[i]) else np.nan,
                     "dist_ma50": c[i] / ma50[i] - 1 if ma50[i] else np.nan,
                     "regime_up": int(bool(spy_ma.get(di))), "spy_ret60": spy_ret60.get(di) or 0,
                     "log_price": np.log(c[i]), "log_dvol": np.log(dvol[i] + 1)})
B = pd.DataFrame(rows)
if not len(B):
    print("no recent breakouts found in the window."); raise SystemExit
B["P_explode"] = mdl.predict_proba(B[FEATS])[:, 1]
B = B.sort_values("P_explode", ascending=False)
print(f"recent breakouts: {len(B)}  (base explosion rate {base*100:.1f}%)\n")
print("=== TOP 20 by model P(>=40% move in ~60d) — explosion-prone watchlist ===")
print(f"  {'tkr':6s} {'date':9s} {'$price':>7s} {'gap%':>6s} {'6mo%':>6s} {'P_expl':>7s} {'lift':>5s}")
for r in B.head(20).itertuples(index=False):
    print(f"  {r.ticker:6s} {r.date}  {r.price:7.2f} {r.gap*100:+6.1f} {r.ret_6m*100:+6.0f} "
          f"{r.P_explode*100:6.0f}% {r.P_explode/base:4.1f}x")
print(f"\nNOTE: P_explode = predicted prob of a big (>=40%) move within ~60d (the model finds these at AUC 0.88).")
print("It flags HIGH-VARIANCE/explosion-prone names -> a watchlist + risk/sizing signal, NOT a buy signal.")
