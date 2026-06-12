"""Lever 1 — POOLED multi-symbol training: one model, 4x the examples.

Stack ES/NQ/RTY/YM matrices (champion raw feature set; features are scale-free) with
symbol one-hots, train ONE model in the same purged day-fold WF, score per-symbol.
Compare per-symbol era ICs vs the solo models. Control-first on the pooled set.

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/pooled_model.py
Artifact: report/pooled_model.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(REPO / "experiments" / "btc_model_v0"))
from features_index import build  # noqa: E402
from model_wf import PARAMS  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

SYMS = ["ES.c.0", "NQ.c.0", "RTY.c.0", "YM.c.0"]
ERA = pd.Timestamp("2024-07-01")
MIN_TRAIN_D, TEST_D, EMBARGO_D = 400, 90, 5
SOLO_ERA = {
    "ES.c.0": 0.108,
    "NQ.c.0": 0.083,
    "RTY.c.0": None,
    "YM.c.0": None,
}  # from prior runs


def load_stack() -> pd.DataFrame:
    """V2: DENSE consistent encoding — every row gets the SAME reference-asset block
    (v1's per-target peer names left the signal carriers NaN on 3/4 of rows)."""
    pan = pd.read_parquet(
        REPO / "experiments" / "sync_regime_v0" / "out" / "daily_returns.parquet"
    )
    pan.index = pd.DatetimeIndex(pan.index).tz_localize(None).normalize()
    ext_p = REPO / "experiments" / "btc_model_v0" / "data" / "panel_ext.parquet"
    if ext_p.exists():
        ext = pd.read_parquet(ext_p).reindex(columns=pan.columns)
        pan = pd.concat([pan, ext[ext.index > pan.index.max()]]).sort_index()
    refs = ["ES.c.0", "NQ.c.0", "GC.c.0", "6E.c.0", "ZN.c.0"]
    dense = pd.DataFrame(index=pan.index)
    for r_ in refs:
        tg = r_.split(".")[0].lower()
        dense[f"ref_{tg}_1"] = pan[r_]
        dense[f"ref_{tg}_5"] = pan[r_].rolling(5).sum()
        dense[f"ref_{tg}_20"] = pan[r_].rolling(20).sum()
    parts = []
    for s in SYMS:
        tag = s.split(".")[0].lower()
        fp = MODULE / "data" / f"features_{tag}.parquet"
        if not fp.exists():
            build(s)
        f = pd.read_parquet(fp)
        own = [
            c
            for c in f.columns
            if not c.startswith(("y_", "gx_", "ox_", "xs_", "x_"))
            and c not in ("rv20_bps", "c_px")
        ]
        d = f[own + ["y_tbR"]].copy()
        d = d.join(
            dense.reindex(f.index)
        )  # same names for every symbol -> truly pooled
        d["sym"] = s
        d["date"] = f.index
        parts.append(d)
    st = pd.concat(parts, ignore_index=True)
    for s in SYMS:
        st[f"is_{s.split('.')[0].lower()}"] = (st["sym"] == s).astype(float)
    return st


def pooled_wf(st: pd.DataFrame, shuffle: bool) -> pd.Series:
    feats = [c for c in st.columns if c not in ("y_tbR", "sym", "date")]
    dates = pd.DatetimeIndex(st["date"])
    udays = dates.unique().sort_values()
    preds = pd.Series(np.nan, index=st.index)
    rng = np.random.default_rng(7)
    start = MIN_TRAIN_D
    while start < len(udays):
        test_days = udays[start : start + TEST_D]
        tr_mask = dates < (test_days[0] - pd.Timedelta(days=EMBARGO_D))
        te_mask = dates.isin(test_days)
        ytr = st.loc[tr_mask, "y_tbR"].dropna()
        if len(ytr) < 800:
            start += TEST_D
            continue
        if shuffle:
            ytr = pd.Series(rng.permutation(ytr.to_numpy()), index=ytr.index)
        mdl = lgb.LGBMRegressor(**PARAMS)
        mdl.fit(st.loc[ytr.index, feats], ytr)
        preds[te_mask] = mdl.predict(st.loc[te_mask, feats])
        start += TEST_D
    return preds


def per_symbol_ic(st, preds, era_only: bool) -> dict:
    out = {}
    for s in SYMS:
        m = (st["sym"] == s) & preds.notna() & st["y_tbR"].notna()
        if era_only:
            m &= pd.DatetimeIndex(st["date"]) >= ERA
        out[s.split(".")[0]] = (
            round(float(spearmanr(preds[m], st.loc[m, "y_tbR"]).statistic), 3)
            if m.sum() > 60
            else np.nan
        )
    return out


def main() -> int:
    st = load_stack()
    print(f"pooled stack: {len(st)} rows across {len(SYMS)} symbols")
    pc = pooled_wf(st, shuffle=True)
    mc = pc.notna() & st["y_tbR"].notna()
    ic_c = float(spearmanr(pc[mc], st.loc[mc, "y_tbR"]).statistic)
    print(f"pooled control: {ic_c:+.3f}")
    if abs(ic_c) > 0.04:
        raise RuntimeError(f"CONTROL SCORED {ic_c:+.3f}")
    pr = pooled_wf(st, shuffle=False)
    full = per_symbol_ic(st, pr, era_only=False)
    era = per_symbol_ic(st, pr, era_only=True)
    lines = [
        "# Pooled multi-symbol model (champion features + symbol one-hots)",
        "",
        f"control {ic_c:+.3f}",
        f"per-symbol FULL IC:  {full}",
        f"per-symbol ERA IC:   {era}",
        "solo-model era reference: ES 0.108 / NQ 0.083 (RTY/YM solo era ~0.02/0.07 from replication)",
    ]
    (MODULE / "report" / "pooled_model.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
