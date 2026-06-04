"""Combo sweep: which LEVELS reverse, at which HORIZON, and does MBO order-flow confirmation pay?

The trade = FADE the sweep (bet reversal): enter at the level, TIGHT stop just past the 5m sweep extreme,
target = R x risk. Honest, conservative (stop wins ties), real costs. Scored per (level family x horizon),
two ways: BASELINE (fade every touch) and GATED (MBO-confirmation model selects). Day-block bootstrap CI.
Features = mbo.* only (order flow known at entry; no outcome leakage). Reads events_upgraded.parquet.

Run: backend/.venv/Scripts/python.exe experiments/mira_upgraded_v0/combo_sweep.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

EV = Path(__file__).resolve().parent / "out" / "events_upgraded.parquet"
OOS_START = pd.Timestamp("2026-04-01").date()
HORIZONS, TARGET_R = ["15m", "60m", "120m"], 2.0
BUFFER, COST_USD, PTV, MIN_RISK = 1.0, 30.0, 50.0, 2.0
N_BOOT = 1500


def trade_net_r(df: pd.DataFrame, h: str, target_r: float) -> np.ndarray:
    """Fade-the-sweep net R per event: tight stop = 5m sweep depth + buffer; +target_r on hit, -1 on stop."""
    risk = np.maximum(df["sweep.5m.max_through_pts"].to_numpy(float), MIN_RISK) + BUFFER
    target = target_r * risk
    stopped = df[f"y.{h}.max_through_pts"].to_numpy(float) > risk            # swept further than the stop
    hit = df[f"y.{h}.max_away_pts"].to_numpy(float) >= target               # reversal reached target
    win = hit & ~stopped                                                    # stop wins ties (conservative)
    cost_r = COST_USD / (risk * PTV)
    return np.where(win, target_r, -1.0) - cost_r


def boot_mean(vals: np.ndarray, days: np.ndarray):
    uniq = np.unique(days)
    di = {d: np.where(days == d)[0] for d in uniq}
    rng = np.random.default_rng(0)
    b = [vals[np.concatenate([di[d] for d in rng.choice(uniq, len(uniq), replace=True)])].mean()
         for _ in range(N_BOOT)]
    return vals.mean(), np.percentile(b, 5), np.percentile(b, 95)


def main() -> int:
    df = pd.read_parquet(EV)
    df["day"] = pd.to_datetime(df["session_date"]).dt.date
    mbo = [c for c in df.columns if c.startswith("mbo.")]
    print(f"events n={len(df)}  mbo features={len(mbo)}  fade target={TARGET_R}R, cost ${COST_USD}/RT\n")

    print("(1) BASELINE fade-2R by (family x horizon) -- OOS mean R [day-block 5,95] (which level reverses when):")
    fams = list(df["level_family"].unique())
    for fam in fams:
        sub = df[df["level_family"] == fam]
        cells = []
        for h in HORIZONS:
            r = trade_net_r(sub, h, TARGET_R)
            ok = np.isfinite(r)
            oos = sub.index.isin(sub[sub["day"] >= OOS_START].index)
            ro = r[ok & oos]
            if len(ro) < 20:
                cells.append(f"{h}: n<20")
                continue
            m, lo, hi = boot_mean(ro, sub["day"].to_numpy()[ok & oos])
            cells.append(f"{h}: {m:+.2f}R[{lo:+.2f},{hi:+.2f}]n{len(ro)}")
        print(f"   {fam:14} " + "  ".join(cells))

    print("\n(2) MBO-CONFIRMATION GATE per family (best horizon 60m): does order flow improve fade R, OOS?")
    import lightgbm as lgb
    for fam in fams:
        sub = df[df["level_family"] == fam].copy()
        sub["r"] = trade_net_r(sub, "60m", TARGET_R)
        sub = sub[np.isfinite(sub["r"])]
        tr, te = sub[sub["day"] < OOS_START], sub[sub["day"] >= OOS_START]
        if len(te) < 25 or len(tr) < 40:
            print(f"   {fam:14} thin (tr={len(tr)} te={len(te)})")
            continue
        y = (tr["r"] > 0).astype(int)
        if y.nunique() < 2:
            print(f"   {fam:14} one-class train")
            continue
        gate = lgb.LGBMClassifier(n_estimators=150, num_leaves=15, learning_rate=0.03, min_child_samples=20,
                                  reg_lambda=1.0, random_state=0, verbose=-1)
        gate.fit(tr[mbo].to_numpy(), y.to_numpy())
        p = gate.predict_proba(te[mbo].to_numpy())[:, 1]
        take = p >= np.median(p)                                    # gate selects the better half
        base_m, base_lo, base_hi = boot_mean(te["r"].to_numpy(), te["day"].to_numpy())
        g_m, g_lo, g_hi = boot_mean(te["r"].to_numpy()[take], te["day"].to_numpy()[take])
        print(f"   {fam:14} baseline {base_m:+.2f}R[{base_lo:+.2f},{base_hi:+.2f}]  "
              f"->GATED {g_m:+.2f}R[{g_lo:+.2f},{g_hi:+.2f}] (n_take={take.sum()})")
    print("\nREAD: a (family,horizon) with OOS R CI clearly > 0 = a level that reverses tradeably; "
          "GATED > baseline (CI>0) = MBO confirmation earns its place.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
