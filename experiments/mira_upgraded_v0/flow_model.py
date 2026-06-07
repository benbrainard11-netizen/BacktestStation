"""Does intraday options FLOW predict the next move -- BEYOND price/time alone?

Walk-forward LightGBM on flow_panel, three models: price/time only, + options flow, options flow ONLY. For each:
OOS predictive corr (pred vs realized fwd return) with a day-block CI, and a sign-following trading sim (P&L in
ATR, held to the horizon, costed), day-block bootstrap. '+flow' clearly beating 'price-only' OOS = the options
data carries real, tradeable signal the sub paid for. Reads out/flow_panel.parquet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reclaim_entry import boot  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
FOLDS = [(20251001, 20251201), (20251201, 20260201), (20260201, 20260401), (20260401, 20260601)]
TARGET = "fwd_60"
COST = 0.02                                   # ATR units (ES round-turn proxy)
BASE = ["tod", "min_to_close", "ret_15", "ret_30", "ret_60", "ret_open"]
BASE_VOL = BASE + ["rv_15", "rv_30", "rv_60"]                  # + recent realized vol (vol clusters -> the bar to beat)
FLOW = ["d_zg", "d_pin0", "d_pinN", "d_cw", "d_pw", "ng0_sign", "ngN_sign", "ng0_n", "nv_n", "nc_n", "ngN_n",
        "dng0_15", "dng0_30", "dng0_60", "dnv_15", "dnv_30", "dnv_60", "dnc_15", "dnc_30", "dnc_60",
        "dngN_15", "dngN_30", "dngN_60"]
IV = ["atm_iv", "skew", "datm_iv_15", "datm_iv_30", "datm_iv_60", "dskew_15", "dskew_30", "dskew_60", "iv_open"]


def wf(df: pd.DataFrame, feats: list[str], target: str) -> np.ndarray:
    import lightgbm as lgb
    p = np.full(len(df), np.nan)
    dt = df["date"].to_numpy()
    for ts, te in FOLDS:
        tr = (dt < ts) & df[target].notna().to_numpy()
        tem = (dt >= ts) & (dt < te)
        if tr.sum() < 800 or tem.sum() < 200:
            continue
        m = lgb.LGBMRegressor(n_estimators=400, num_leaves=31, learning_rate=0.02, min_child_samples=80,
                              reg_lambda=3.0, subsample=0.8, colsample_bytree=0.6, random_state=0, verbose=-1)
        m.fit(df.loc[tr, feats], df.loc[tr, target])
        p[tem] = m.predict(df.loc[tem, feats])
    return p


def boot_corr(ph: np.ndarray, y: np.ndarray, days: np.ndarray, n: int = 2000):
    u = np.unique(days)
    di = {d: np.where(days == d)[0] for d in u}
    rng = np.random.default_rng(0)
    cs = []
    for _ in range(n):
        idx = np.concatenate([di[d] for d in rng.choice(u, len(u), True)])
        if len(idx) > 10:
            cs.append(np.corrcoef(ph[idx], y[idx])[0, 1])
    return np.corrcoef(ph, y)[0, 1], np.percentile(cs, 5), np.percentile(cs, 95)


def evalp(name: str, df: pd.DataFrame, pred: np.ndarray, target: str) -> None:
    m = (~np.isnan(pred)) & df[target].notna().to_numpy()
    ph, y, dy = pred[m], df[target].to_numpy()[m], df["date"].to_numpy()[m]
    c, cl, ch = boot_corr(ph, y, dy)
    take = np.abs(ph) >= np.quantile(np.abs(ph), 0.5)            # trade the more-confident half
    r = np.sign(ph[take]) * y[take] - COST
    rm, rl, rh = boot(r, dy[take])
    flag = "  <== predicts (sim CI>0)" if rl > 0 else ""
    print(f"  {name:20} corr {c:+.3f}[{cl:+.3f},{ch:+.3f}]   sim R {rm:+.3f}[{rl:+.3f},{rh:+.3f}] ATR  n{int(take.sum())}{flag}")


def vol_eval(name: str, df: pd.DataFrame, pred: np.ndarray, target: str) -> None:
    m = (~np.isnan(pred)) & df[target].notna().to_numpy()
    ph, y, dy = pred[m], df[target].to_numpy()[m], df["date"].to_numpy()[m]
    c, cl, ch = boot_corr(ph, y, dy)
    lo_t, hi_t = np.quantile(ph, [0.33, 0.67])
    hi, lo = y[ph >= hi_t].mean(), y[ph <= lo_t].mean()                  # realized range, predicted hi vs lo third
    flag = "  <== predicts vol (corr CI>0)" if cl > 0 else ""
    print(f"  {name:22} corr {c:+.3f}[{cl:+.3f},{ch:+.3f}]  realized range: hi3rd {hi:.2f} vs lo3rd {lo:.2f} ATR{flag}")


def main() -> int:
    df = pd.read_parquet(OUT / "flow_panel.parquet")
    df["date"] = df["date"].astype(int)
    print(f"flow model -- {len(df)} rows / {df['date'].nunique()} days.\n")
    print(f"=== DIRECTION (target {TARGET}) -- OOS corr + sign-following sim (ATR, costed) ===")
    evalp("price/time only", df, wf(df, BASE, TARGET), TARGET)
    evalp("+ options flow", df, wf(df, BASE + FLOW, TARGET), TARGET)
    evalp("+ flow + IV surface", df, wf(df, BASE + FLOW + IV, TARGET), TARGET)

    vt = "fwdrange_60"
    print(f"\n=== VOLATILITY (target {vt}) -- OOS corr + hi/lo-3rd realized range ===")
    vol_eval("price/recentvol", df, wf(df, BASE_VOL, vt), vt)
    vol_eval("+ options flow", df, wf(df, BASE_VOL + FLOW, vt), vt)
    vol_eval("+ IV surface (no flow)", df, wf(df, BASE_VOL + IV, vt), vt)
    vol_eval("+ flow + IV surface", df, wf(df, BASE_VOL + FLOW + IV, vt), vt)
    vol_eval("IV surface ONLY", df, wf(df, IV, vt), vt)
    print("\nREAD: vol -- '+flow' corr clearly > 'price/recentvol' (and hi/lo-3rd range spread widens) = the gamma flow "
          "predicts forward range beyond vol-clustering. That's the regime signal (expansion vs contraction) for setup "
          "selection -- the usable form of the options data, even though direction is null.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
