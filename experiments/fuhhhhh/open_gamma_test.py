"""Does SPX gamma regime CONDITION the NQ opening drive? (the options thesis, clean)

Merge PRIOR-DAY SPX gamma (walls_v2 gex_proxy, causal) onto the opening-drive dataset.
Test A (descriptive): corr(or_drive, fwd_eod) split by gamma regime — does the opening drive
  CONTINUE in one regime and FADE in the other? (sign-agnostic: we ask if the regimes DIFFER.)
Test B (ablation): walk-forward logistic, bars-only vs bars+gamma — does gamma add OOS lift?
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(37)
od = pd.read_parquet(OUT / "open_dataset.parquet").dropna(subset=["r_long", "r_short"]).copy()
od["d"] = pd.to_datetime(od["date"])
w = pd.read_parquet(OUT / "walls_v2.parquet")
w["d"] = pd.to_datetime(w["date"].astype(int).astype(str), format="%Y%m%d")
w = w.sort_values("d")
# prior-day SPX gamma (strictly before the open day -> causal)
m = pd.merge_asof(od.sort_values("d"), w[["d", "gex_proxy", "zero_gamma", "spot"]],
                  on="d", direction="backward", allow_exact_matches=False)
m = m.dropna(subset=["gex_proxy", "or_drive_atr", "fwd_eod_atr"]).reset_index(drop=True)
m["gpos"] = m["gex_proxy"] > 0
print(f"merged {len(m)} open-days with prior SPX gamma ({m.date.min()}..{m.date.max()})")
print(f"  gamma>0 (long-gamma): {int(m.gpos.sum())}   gamma<0 (short-gamma): {int((~m.gpos).sum())}")


def corr(a, b):
    return np.corrcoef(a, b)[0, 1] if len(a) > 30 else np.nan


print("\n### A. corr(or_drive, fwd_eod) by gamma regime  (continuation if >0, reversion if <0)")
for lab, sub in [("ALL", m), ("gamma>0 (should DAMPEN/fade)", m[m.gpos]), ("gamma<0 (should AMPLIFY/trend)", m[~m.gpos])]:
    c = corr(sub["or_drive_atr"], sub["fwd_eod_atr"])
    co = corr(sub[sub.yr <= "2022"]["or_drive_atr"], sub[sub.yr <= "2022"]["fwd_eod_atr"])
    cr = corr(sub[sub.yr >= "2023"]["or_drive_atr"], sub[sub.yr >= "2023"]["fwd_eod_atr"])
    print(f"  {lab:30s} all={c:+.3f}  old={co:+.3f}  recent={cr:+.3f}  n={len(sub)}")

# conditioned trade: follow the opening drive in short-gamma, fade it in long-gamma (a-priori)
print("\n### B. a-priori conditioned trade R (follow drive if gamma<0, fade if gamma>0)")
def cell(sub, follow):
    d = np.sign(sub["or_drive_atr"]) * (1 if follow else -1)
    r = np.where(d > 0, sub["r_long"], sub["r_short"])
    return r
rows = []
for lab, sub, follow in [("gamma<0 FOLLOW drive", m[~m.gpos], True), ("gamma>0 FADE drive", m[m.gpos], False),
                         ("gamma<0 FADE (ctrl)", m[~m.gpos], False), ("gamma>0 FOLLOW (ctrl)", m[m.gpos], True)]:
    r = cell(sub, follow)
    bymo = pd.Series(r).groupby(sub["yr"].values).mean()
    print(f"  {lab:24s} meanR={r.mean():+.4f} n={len(r)} win%={(r>0).mean()*100:.0f} yrs+={int((bymo>0).sum())}/{len(bymo)}")

# combined a-priori rule equity
combo = np.concatenate([cell(m[~m.gpos], True), cell(m[m.gpos], False)])
combo_yr = np.concatenate([m[~m.gpos]["yr"].values, m[m.gpos]["yr"].values])
byyr = pd.Series(combo).groupby(combo_yr).mean()
print(f"\n  COMBINED (follow in short-gamma, fade in long-gamma): meanR={combo.mean():+.4f} n={len(combo)} "
      f"yrs+={int((byyr>0).sum())}/{len(byyr)}")
print("  per-year:", {k: round(v, 3) for k, v in byyr.items()})

# Test C: ablation — does gamma add OOS lift over bars-only?
print("\n### C. ablation: walk-forward logistic bars vs bars+gamma (OOS meanR)")
BARS = ["dow", "gap_atr", "or_drive_atr", "or_range_atr", "open_loc", "prev_ret_atr"]
m["gam_sign"] = np.sign(m["gex_proxy"]); m["gam_mag"] = np.sign(m["gex_proxy"]) * np.log1p(np.abs(m["gex_proxy"]))
m["drive_x_gam"] = m["or_drive_atr"] * np.sign(m["gex_proxy"])     # the interaction (continuation x regime)
GAM = BARS + ["gam_sign", "gam_mag", "drive_x_gam"]
yrs = sorted(m["yr"].unique())
def walk(feats):
    oos = []
    for i, y in enumerate(yrs):
        if i < 2: continue
        tr, te = m[m.yr < y], m[m.yr == y]
        if len(tr) < 200 or len(te) < 20: continue
        sc = StandardScaler().fit(tr[feats])
        mod = LogisticRegression(C=0.3, max_iter=500).fit(sc.transform(tr[feats]), tr["y_up"])
        p = mod.predict_proba(sc.transform(te[feats]))[:, list(mod.classes_).index(1)]
        t = te.copy(); t["r"] = np.where(p >= 0.5, t["r_long"], t["r_short"]); t["p"] = p
        oos.append(t)
    return pd.concat(oos)
for lab, ff in [("bars-only", BARS), ("bars+gamma", GAM)]:
    o = walk(ff)
    auc = roc_auc_score(o["y_up"], o["p"])
    print(f"  {lab:12s} AUC={auc:.3f} meanR={o['r'].mean():+.4f} n={len(o)} yrs+={int((o.groupby('yr').r.mean()>0).sum())}/{o.yr.nunique()}")
