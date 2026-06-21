"""A/B: money-label challenger PLAIN vs +CONTEXT features (Ben's narrative layer, 2026-06-10):
signed distance to weekly/daily open (+ above flags) and direction-aware HTF PSP cracks at the
sweep (4h + daily, +1 supportive / -1 contrary / 0 none). Same training recipe both sides;
the DIFFERENCE on jan_oos + oos_holdout realized R is the verdict on the feature family.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/challenger_context.py
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
os.environ["BACKTESTSTATION_BACKEND"] = str(ROOT / "live_engine" / "vendor")
os.environ.pop("BS_MIRA_ROOT", None)
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\experiments\smt_ltf_bench")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import smt_bench as SB  # noqa: E402
import harness as H  # noqa: E402
import gate as G  # noqa: E402

SYMS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
ET = "America/New_York"
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10}

bars1m = {s: SB.load_1m(s, "2025-12-20", "2026-06-06") for s in SYMS}
grids = {tf: pd.DataFrame({s: np.sign((b := SB.resample_tf(bars1m[s], tf))["close"] - b["open"])
                           for s in SYMS}).dropna() for tf in (240, 1440)}


def ctx_features(ds: pd.DataFrame) -> pd.DataFrame:
    ts = pd.to_datetime(ds["trigger_ts_utc"], utc=True)
    mins = pd.to_numeric(ds["combined.minutes_from_sweep_decision_to_trigger"], errors="coerce").fillna(0)
    sweep = ts - pd.to_timedelta(mins, unit="m")
    out = {k: [] for k in ("ctx.d_wopen_tk", "ctx.d_dopen_tk", "ctx.above_w", "ctx.above_d",
                           "ctx.psp4h", "ctx.psp1d")}
    for i in ds.index:
        sym = str(ds.at[i, "symbol"])
        t = ts.loc[i]
        px = float(ds.at[i, "trigger_price"])
        want = 1 if str(ds.at[i, "smt_anchor_side"]) == "low" else -1
        et = t.tz_convert(ET)
        d18 = (et - pd.Timedelta(hours=18)).normalize() + pd.Timedelta(hours=18)
        w18 = d18 - pd.Timedelta(days=(d18.weekday() + 1) % 7)
        b = bars1m[sym]
        vals = {}
        for key, anchor in (("w", w18.tz_convert("UTC")), ("d", d18.tz_convert("UTC"))):
            j = b.index.searchsorted(anchor, side="left")
            vals[key] = float(b["open"].iloc[j]) if j < len(b) else np.nan
        out["ctx.d_wopen_tk"].append((px - vals["w"]) / TICK[sym] if np.isfinite(vals["w"]) else np.nan)
        out["ctx.d_dopen_tk"].append((px - vals["d"]) / TICK[sym] if np.isfinite(vals["d"]) else np.nan)
        out["ctx.above_w"].append(float(px > vals["w"]) if np.isfinite(vals["w"]) else np.nan)
        out["ctx.above_d"].append(float(px > vals["d"]) if np.isfinite(vals["d"]) else np.nan)
        for tf, key in ((240, "ctx.psp4h"), (1440, "ctx.psp1d")):
            D = grids[tf]
            pos = D.index.searchsorted(sweep.loc[i] - pd.Timedelta(minutes=tf), side="right") - 1
            v = 0.0
            if pos >= 0:
                row = D.iloc[pos]
                mine = row[sym]
                if mine != 0 and any(row[s] != 0 and row[s] != mine for s in SYMS if s != sym):
                    v = 1.0 if mine == want else -1.0
            out[key].append(v)
    return pd.DataFrame(out, index=ds.index)


def train_eval(tag, extra):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    gate = G.Gate()
    tr = H.build_dataset("train", *H.WINDOWS["train"])
    tr["trigger_ts_utc"] = pd.to_datetime(tr["trigger_ts_utc"], utc=True)
    rr = pd.to_numeric(tr["realized_r"], errors="coerce")
    tr = tr[rr.notna()]
    y = (rr[rr.notna()] > 0).astype(int)
    X = gate._encode(tr)
    if extra:
        X = pd.concat([X, ctx_features(tr)], axis=1)
    pipe = Pipeline([("imp", SimpleImputer(strategy="median")),
                     ("rf", RandomForestClassifier(n_estimators=250, max_depth=5, min_samples_leaf=20,
                                                   class_weight="balanced_subsample", random_state=2605, n_jobs=4))])
    pipe.fit(X, y)
    thr = float(pd.Series(pipe.predict_proba(X)[:, 1]).quantile(0.75))
    print(f"\n### {tag} (thr={thr:.4f})")
    for name in ("jan_oos", "oos_holdout"):
        d = H.build_dataset(name, *H.WINDOWS[name])
        d["trigger_ts_utc"] = pd.to_datetime(d["trigger_ts_utc"], utc=True)
        Xd = gate._encode(d)
        if extra:
            Xd = pd.concat([Xd, ctx_features(d)], axis=1)
        sc = pipe.predict_proba(Xd)[:, 1]
        g = (d[sc >= thr].sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
             .groupby(H.OPP, sort=False).head(1))
        r = pd.to_numeric(g["realized_r"], errors="coerce").dropna()
        print(f"  {name:12s} n={len(r):4d} meanR={r.mean():+.3f} win={100*(r>0).mean():4.1f}% sumR={r.sum():+7.1f}")


train_eval("PLAIN money-label", extra=False)
train_eval("+CONTEXT features", extra=True)
print("\nchampion reference: jan +0.456/138, holdout +0.298/83")
