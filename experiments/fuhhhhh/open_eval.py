"""Is the opening drive directionally predictable from overnight context? (bars-only, 8yr)

Walk-forward by year (expanding), simple LOGISTIC model (small sample -> small hypothesis),
per-year R + AUC + shuffled control + drop-best-year. Plus univariate feature->fwd corr by
era (does any overnight feature predict the rest-of-day move, and is the sign stable?).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(31)
df = pd.read_parquet(OUT / "open_dataset.parquet").dropna(subset=["r_long", "r_short"]).reset_index(drop=True)
FEATS = ["dow", "gap_atr", "or_drive_atr", "or_range_atr", "open_loc", "prev_ret_atr", "es_gap", "es_or_drive"]
df = df.dropna(subset=FEATS).reset_index(drop=True)
yrs = sorted(df["yr"].unique())


def walk(shuffle=False):
    oos = []
    for i, y in enumerate(yrs):
        if i < 2:
            continue
        tr, te = df[df.yr < y], df[df.yr == y]
        if len(tr) < 200 or len(te) < 20:
            continue
        sc = StandardScaler().fit(tr[FEATS])
        yt = tr["y_up"].to_numpy()
        if shuffle:
            yt = RNG.permutation(yt)
        m = LogisticRegression(C=0.3, max_iter=500).fit(sc.transform(tr[FEATS]), yt)
        p = m.predict_proba(sc.transform(te[FEATS]))[:, list(m.classes_).index(1)]
        t = te.copy(); t["p"] = p
        t["r"] = np.where(p >= 0.5, t["r_long"], t["r_short"])
        oos.append(t)
    return pd.concat(oos)


def summ(o, lab):
    auc = roc_auc_score(o["y_up"], o["p"]) if o["y_up"].nunique() == 2 else np.nan
    days = o["date"].to_numpy(); r = o["r"].to_numpy()
    by = {d: r[days == d] for d in np.unique(days)}
    bm = np.array([np.concatenate([by[d] for d in RNG.choice(list(by), len(by), True)]).mean() for _ in range(3000)])
    print(f"  {lab:16s} AUC={auc:.3f} meanR={r.mean():+.4f} p(<=0)={(bm<=0).mean():.3f} n={len(o)} win%={(r>0).mean()*100:.0f}")


o = walk(); os = walk(shuffle=True)
print(f"OOS years {sorted(o.yr.unique())} (expanding walk-forward, logistic)\n")
summ(o, "MODEL")
summ(os, "shuffled-y")
print("\n### per-year traded meanR (model)")
print(o.groupby("yr")["r"].agg(["size", "mean"]).round(4).to_string())
bymo = o.groupby("yr")["r"].mean()
print(f"  yrs+={int((bymo>0).sum())}/{len(bymo)}  drop-best-1={o[~o.yr.isin(bymo.sort_values(ascending=False).index[:1])]['r'].mean():+.4f}")

print("\n### univariate corr(feature, fwd_eod_atr): OLD (2018-2022) vs RECENT (2023-2026)")
old, rec = df[df.yr <= "2022"], df[df.yr >= "2023"]
print(f"  {'feature':14s} {'old':>8s} {'recent':>8s} {'flip?':>6s}")
for f in FEATS:
    co = np.corrcoef(old[f], old["fwd_eod_atr"])[0, 1]
    cr = np.corrcoef(rec[f], rec["fwd_eod_atr"])[0, 1]
    flip = "FLIP" if co * cr < 0 and abs(co) > 0.04 and abs(cr) > 0.04 else ""
    print(f"  {f:14s} {co:>+8.3f} {cr:>+8.3f} {flip:>6s}")
