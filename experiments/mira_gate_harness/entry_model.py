"""Entry-selection MODEL (#15) vs the simple drift-threshold RULE, on zone-formed liquid-3.
Question: do the OTHER legal orderflow features add incremental ranking power beyond drift, or is
drift x zone already most of the signal? Discipline: regularized logistic on DESIGN with 5-fold CV,
ONE validation look, compared to the rule's frequency/edge curve. Small n -> overfit risk is real;
if the model appears to beat the rule OOS, it gets adversarial verification before we believe it.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
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
df = df[df["symbol"].isin(LIQ) & (df["zone_5m_has"] == 1)].copy()  # the regime where the edge lives
df["mo"] = pd.to_datetime(df["decision_ts_utc"], utc=True).dt.month
df["hour"] = pd.to_datetime(df["entry_ts_utc"], utc=True).dt.hour
df["R"] = pd.to_numeric(df["trail_2R"], errors="coerce")
df["win"] = (df["R"] > 0).astype(int)
for s in LIQ:
    df[f"is_{s[:2]}"] = (df["symbol"] == s).astype(int)
FEATS = NUM + ["hour", "is_ES", "is_NQ"]

des = df[df["mo"].isin([1, 2, 3])].copy()
val = df[df["mo"].isin([4, 5, 6])].copy()
med = des[FEATS].median()
Xd = des[FEATS].fillna(med)
Xv = val[FEATS].fillna(med)
scaler = StandardScaler().fit(Xd)
Xds, Xvs = scaler.transform(Xd), scaler.transform(Xv)

# 5-fold CV on design to confirm signal + pick C (light reg)
print(f"zone-formed liquid-3: design n={len(des)}  validation n={len(val)}")
for C in (0.05, 0.1, 0.3, 1.0):
    auc = cross_val_score(LogisticRegression(C=C, max_iter=500), Xds, des["win"],
                          cv=StratifiedKFold(5, shuffle=True, random_state=0), scoring="roc_auc")
    print(f"  C={C:<4}: design 5-fold CV AUC {auc.mean():.3f} +/- {auc.std():.3f}")

C = 0.1
clf = LogisticRegression(C=C, max_iter=500).fit(Xds, des["win"])
val = val.assign(score=clf.predict_proba(Xvs)[:, 1])
des2 = des.assign(score=clf.predict_proba(Xds)[:, 1])
coef = pd.Series(clf.coef_[0], index=FEATS).sort_values(key=abs, ascending=False)
print(f"\n  top model weights (C={C}): " + ", ".join(f"{k}{v:+.2f}" for k, v in coef.head(6).items()))


def curve(d, label):
    d = d.sort_values("score", ascending=False)
    print(f"  {label}: top-k by model score -> cumulative meanR")
    for k in (20, 30, 40, 50, 70, 100):
        if k <= len(d):
            sub = d.head(k)["R"]
            print(f"     top {k:3d}: R={sub.mean():+.3f} win={100*(sub>0).mean():4.1f}%")


print("\n=== MODEL frequency/edge curve ===")
curve(des2, "[DESIGN]")
print()
curve(val, "[VALIDATION]")

print("\n=== RULE baseline (drift threshold) for comparison, same zone-formed liquid-3 ===")
for thr in (10, 15, 20, 29.33):
    v = val[pd.to_numeric(val["w90_drift_dir_ticks"], errors="coerce") >= thr]["R"]
    print(f"  RULE drift>={thr:<6}: VAL n={len(v):3d} R={v.mean():+.3f}")
print("\nVERDICT: does the MODEL's top-k OOS meanR beat the RULE at matched n? If not, keep the rule.")
