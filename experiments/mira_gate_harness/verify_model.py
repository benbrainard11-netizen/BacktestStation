"""Adversarial verification of the entry model's apparent OOS dominance over the drift rule.
Three controls: (1) DROP symbol dummies -> is it just 'trade YM'? (2) SHUFFLE target -> leakage/snoop
control (should collapse to ~0). (3) does model score just re-encode drift? Plus per-symbol/month of
the OOS top-k. If the edge dies without symbol dummies or survives a shuffle, REJECT the model."""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
R = HERE / "runs"
KEY = ["symbol", "session_date", "level_family", "side", "level_price", "decision_ts_utc"]
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]
NUM = ["w90_drift_dir_ticks", "w90_aggr_imb_dir", "w90_near_add_imb_dir", "w90_c2a_defend_near",
       "5m_zone_add_refill_dir", "5m_zone_absorption", "5m_zone_delta_dir", "5m_zone_aggr_imb_dir",
       "depth_tk", "wait_s", "trade_rate_ratio", "vol_rate_ratio"]
ZCOLS = ["zone_5m_has", "5m_zone_add_refill_dir", "5m_zone_absorption", "5m_zone_delta_dir",
         "5m_zone_aggr_imb_dir"]

sc = pd.read_parquet(R / "flow_at_scale_features.parquet")
zn = pd.read_parquet(R / "flow_at_zone_features.parquet")
df = sc.merge(zn[KEY + ZCOLS], on=KEY, how="inner")
df = df[pd.to_numeric(df["trail_2R"], errors="coerce").abs() <= 5].copy()
df = df[df["symbol"].isin(LIQ) & (df["zone_5m_has"] == 1)].copy()
df["mo"] = pd.to_datetime(df["decision_ts_utc"], utc=True).dt.month
df["hour"] = pd.to_datetime(df["entry_ts_utc"], utc=True).dt.hour
df["R"] = pd.to_numeric(df["trail_2R"], errors="coerce")
df["win"] = (df["R"] > 0).astype(int)
df["is_ES"] = (df["symbol"] == "ES.c.0").astype(int)
df["is_NQ"] = (df["symbol"] == "NQ.c.0").astype(int)
des, val = df[df["mo"].isin([1, 2, 3])].copy(), df[df["mo"].isin([4, 5, 6])].copy()


def fit_score(feats, shuffle=False, seed=0):
    med = des[feats].median()
    Xd, Xv = des[feats].fillna(med), val[feats].fillna(med)
    sca = StandardScaler().fit(Xd)
    y = des["win"].sample(frac=1, random_state=seed).to_numpy() if shuffle else des["win"]
    clf = LogisticRegression(C=0.1, max_iter=500).fit(sca.transform(Xd), y)
    return clf.predict_proba(sca.transform(Xv))[:, 1], clf


def topk(scores, d, ks=(30, 40, 50, 70)):
    o = d.assign(s=scores).sort_values("s", ascending=False)
    return "  ".join(f"top{k}:R={o.head(k)['R'].mean():+.3f}" for k in ks if k <= len(o))


NO_SYM = NUM + ["hour"]
WITH_SYM = NUM + ["hour", "is_ES", "is_NQ"]
print(f"zone-formed liquid-3: design n={len(des)} val n={len(val)}")
print("\n(1) WITH symbol dummies   VAL:", topk(fit_score(WITH_SYM)[0], val))
print("(2) WITHOUT symbol dummies VAL:", topk(fit_score(NO_SYM)[0], val))
print("    -> if (2) collapses toward the rule, the 'model edge' was mostly the YM tilt.")

print("\n(3) SHUFFLE control (target permuted on design; should be ~0 OOS):")
sh = [fit_score(WITH_SYM, shuffle=True, seed=s)[0] for s in range(5)]
for i, s in enumerate(sh):
    o = val.assign(s=s).sort_values("s", ascending=False)
    print(f"    shuffle {i}: top40 R={o.head(40)['R'].mean():+.3f}")

sc_real, clf = fit_score(NO_SYM)
print("\n(4) does score just re-encode drift? corr(score, drift) on VAL:",
      f"{np.corrcoef(sc_real, pd.to_numeric(val['w90_drift_dir_ticks'], errors='coerce').fillna(0))[0,1]:+.3f}")

print("\n(5) OOS top-40 (no-sym model) composition by symbol/month:")
o = val.assign(s=sc_real).sort_values("s", ascending=False).head(40)
print("    symbol:", o["symbol"].value_counts().to_dict())
print("    month :", o["mo"].value_counts().to_dict())
print(f"    this top-40 R={o['R'].mean():+.3f} vs rule drift>=29.33 (n37) +0.397")
