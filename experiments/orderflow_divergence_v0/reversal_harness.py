"""Reversal harness v0 — what predicts that a candle extreme REVERSES (manipulation -> distribution)?

Index complex (ES/NQ/YM/RTY). Events = each 1H candle's LOW (bullish-reversal candidate; highs added next).
Decision point = candle close (the low has printed, flow into it is known); label = forward N hours.

Features available AT the extreme:
  - down_ret      : the candle's own close-open return (MEAN-REVERSION baseline — the dumb feature to beat)
  - flow_ratio    : whole-hour net signed / volume
  - absorp_low    : *localized* absorption INTO the low — contracts traded per tick of range over the 300s
                    leading into the low (high = a flood of orders with little price progress = iceberg/absorption)
  - sgn_into_low  : net signed flow over those 300s (very negative = heavy aggressive SELLING into the low;
                    if price then holds, that selling was absorbed -> the user's "reverses off no level" case)
  - smt_div       : ES made a new 1H low but the complex (NQ/YM/RTY) did NOT confirm = SMT divergence
  - cvd_div       : price made a new low but cumulative signed flow did not
  - swept         : the low took out a prior-day low (visible liquidity sweep); 0 = "no visible level"
  - pos_in_4h     : is this the low of its 4H window (HTF manipulation position)
  - hod           : hour of day
Label = did the low HOLD and price REVERSE up (triple-barrier: reach +R*ATR before breaking -R*ATR), next N hours.
Conservative: if BOTH barriers hit in-window, not counted a reversal (we lack intra-bar path order at 1H).

Decisive output = grouped ablation: does localized absorption / divergence / structure beat plain mean-reversion?

Run: backend/.venv/Scripts/python.exe experiments/orderflow_divergence_v0/reversal_harness.py
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path

import numpy as np
import pandas as pd

OFI = Path(__file__).resolve().parent / "out" / "event_ofi"
INDEX = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
RATES = ["ZN.c.0", "ZB.c.0"]
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10,
        "ZN.c.0": 1 / 64, "ZB.c.0": 1 / 32, "CL.c.0": 0.01}
TGT = "ES.c.0"
CUT = pd.Timestamp("2026-02-15", tz="UTC")
N_FWD, R, WIN = 8, 1.0, 300   # reversal horizon (hours), barrier (xATR), absorption window (s into the low)


def hourly(sym: str) -> pd.DataFrame:
    tick = TICK[sym]
    fs = sorted(glob.glob(str(OFI / sym / "*.parquet")))
    df = pd.concat([pd.read_parquet(f, columns=["ts", "mid", "signed", "volume"]) for f in fs], ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.set_index("ts").sort_index().dropna(subset=["mid"])
    df = df[~df.index.duplicated(keep="first")]                    # drop dup secs from file-boundary overlaps
    # rolling (trailing WIN seconds) order-flow features on the 1s series, sampled later AT each hour's low.
    rv = df["volume"].rolling(WIN, min_periods=60).sum()
    rng = (df["mid"].rolling(WIN, min_periods=60).max() - df["mid"].rolling(WIN, min_periods=60).min()) / tick + 1.0
    df["roll_absorp"] = rv / rng                                   # contracts per tick of range (iceberg proxy)
    df["roll_sgn"] = df["signed"].rolling(WIN, min_periods=60).sum()
    g = df.resample("1h", label="left", closed="left")
    h = pd.DataFrame({"o": g["mid"].first(), "high": g["mid"].max(), "low": g["mid"].min(),
                      "c": g["mid"].last(), "net": g["signed"].sum(), "vol": g["volume"].sum()}).dropna(subset=["c"])
    low_ts = df.groupby(df.index.floor("1h"))["mid"].idxmin()      # only non-empty hours -> no all-NA idxmin
    h["low_ts"] = low_ts.reindex(h.index)
    h["absorp_low"] = df["roll_absorp"].reindex(h["low_ts"]).to_numpy()
    h["sgn_into_low"] = df["roll_sgn"].reindex(h["low_ts"]).to_numpy()
    h["rng"] = h["high"] - h["low"]
    return h


def fwd_extreme(s: pd.Series, n: int, how: str) -> np.ndarray:
    r = s[::-1].rolling(n, min_periods=1)
    return ((r.max() if how == "max" else r.min())[::-1].shift(-1)).to_numpy()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=TGT)
    ap.add_argument("--complex", nargs="+", default=INDEX)
    ap.add_argument("--mode", choices=["reversal", "continuation"], default="reversal")
    ap.add_argument("--swept-only", action="store_true")
    a = ap.parse_args(argv)
    tgt, comp = a.target, a.complex
    print(f"target={tgt}  complex={comp}  mode={a.mode}  swept_only={a.swept_only}  "
          f"horizon={N_FWD}h  barrier={R}xATR")
    H = {s: hourly(s) for s in comp}
    idx = H[tgt].index
    for s in comp:
        idx = idx.intersection(H[s].index)
    for s in comp:
        H[s] = H[s].loc[idx]
    es = H[tgt].copy()

    new_low = {s: (H[s]["low"] < H[s]["low"].shift(1)).astype(float) for s in comp}
    others = [s for s in comp if s != tgt]
    es["es_new_low"] = new_low[tgt]
    es["smt_div"] = (1.0 - np.mean([new_low[o].to_numpy() for o in others], axis=0)) if others else 0.0
    es["flow_ratio"] = es["net"] / es["vol"].where(es["vol"] > 0, np.nan)
    es["cvd"] = es["net"].cumsum()
    es["cvd_div"] = ((es["low"] < es["low"].shift(1)) &
                     (es["cvd"] > es["cvd"].rolling(6, min_periods=3).min())).astype(float)
    es["swept"] = (es["low"] < es["low"].rolling(24, min_periods=6).min().shift(1)).astype(float)
    es["hod"] = es.index.hour
    es["pos_in_4h"] = (es["low"] <= es["low"].rolling(4, min_periods=2).min() + 1e-9).astype(float)
    es["down_ret"] = (es["c"] - es["o"]) / es["o"]

    atr = es["rng"].rolling(24, min_periods=6).mean().to_numpy()
    lowv = es["low"].to_numpy()
    fhi = fwd_extreme(es["high"], N_FWD, "max")
    flo = fwd_extreme(es["low"], N_FWD, "min")
    reach_up = fhi >= (lowv + R * atr)
    break_dn = flo <= (lowv - R * atr)
    if a.mode == "continuation":
        es["y"] = np.where(break_dn & ~reach_up, 1.0, 0.0)   # low BREAKS, price continues down
    else:
        es["y"] = np.where(reach_up & ~break_dn, 1.0, 0.0)   # low HOLDS, price reverses up
    es["valid"] = (~np.isnan(fhi)) & (~np.isnan(flo)) & (~np.isnan(atr)) & (atr > 0)

    FEATS = ["down_ret", "flow_ratio", "absorp_low", "sgn_into_low",
             "smt_div", "cvd_div", "es_new_low", "swept", "pos_in_4h", "hod"]
    d = es.dropna(subset=FEATS + ["y"]).copy()
    d = d[d["valid"]]
    if a.swept_only:
        d = d[d["swept"] == 1]
    tr, te = d[d.index < CUT], d[d.index >= CUT]
    print(f"events: train {len(tr):,} / test {len(te):,}  target base-rate {te['y'].mean():.3f}")

    from lightgbm import LGBMClassifier
    from sklearn.metrics import roc_auc_score
    yte = te["y"].to_numpy()

    def gbdt_auc(feats):
        m = LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=30,
                           subsample=0.8, colsample_bytree=0.8, verbose=-1)
        m.fit(tr[feats], tr["y"])
        return roc_auc_score(yte, m.predict_proba(te[feats])[:, 1]), m

    uni = {f: max(roc_auc_score(yte, te[f]), 1.0 - roc_auc_score(yte, te[f])) for f in FEATS}
    print("\n-- univariate OOS AUC per feature (0.50 = useless) --")
    for f in sorted(FEATS, key=lambda x: -uni[x]):
        print(f"  {f:13} {uni[f]:.4f}")

    groups = {
        "mean_rev [down_ret]":              ["down_ret"],
        "absorption-ONLY":                  ["absorp_low", "sgn_into_low"],
        "divergence-ONLY":                  ["smt_div", "cvd_div", "es_new_low"],
        "structure-ONLY":                   ["swept", "pos_in_4h"],
        "mean_rev + absorption":            ["down_ret", "absorp_low", "sgn_into_low"],
        "mean_rev + divergence":            ["down_ret", "smt_div", "cvd_div", "es_new_low"],
        "ALL":                              FEATS,
    }
    print("\n-- grouped ablation (does ANYTHING beat plain mean-reversion?) --")
    for name, fs in groups.items():
        a, _ = gbdt_auc(fs)
        print(f"  {name:26} AUC={a:.4f}")

    _, m_all = gbdt_auc(FEATS)
    print("\nfeature importance (gain), ALL model:")
    for f, v in sorted(zip(FEATS, m_all.feature_importances_), key=lambda x: -x[1]):
        print(f"  {f:13} {int(v)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
