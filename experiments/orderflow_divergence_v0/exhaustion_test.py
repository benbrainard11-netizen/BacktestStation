"""Exhaustion + breakout-vs-fakeout — the unified test of the user's two live hypotheses, at scale.

At a LEVEL SWEEP (price freshly penetrates a prior swing low = liquidity grab / PO3 manipulation candidate),
does ORDER FLOW predict CONTINUATION (real breakout) vs REVERSAL (fakeout / distribution)?
  - continuation thesis : heavy CONFIRMING sell-flow INTO the sweep -> real breakout (flow WITH the grain)
  - exhaustion thesis   : flow that FLIPS at the low (sold into the sweep, then buyers step in) -> reversal
Built at 1-MINUTE scale so there are thousands of sweeps (the 1H swept-only test hinted flow matters but had
only ~150 test events -> GBDT overfit). Decision point = D minutes AFTER the sweep (so the post-sweep reaction
flow is known); the label horizon starts there -> no lookahead. Restricted to DECISIVE events (exactly one
barrier hit) so it's a clean breakout-vs-fakeout label. Reports univariate OOS AUC per feature, a grouped
ablation vs mean-reversion, and tradeability (precision + implied R/trade on high-confidence calls, after cost).

Run: backend/.venv/Scripts/python.exe experiments/orderflow_divergence_v0/exhaustion_test.py --symbol ZN.c.0
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path

import numpy as np
import pandas as pd

OFI = Path(__file__).resolve().parent / "out" / "event_ofi"
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10,
        "ZN.c.0": 1 / 64, "ZB.c.0": 1 / 32, "CL.c.0": 0.01}
CUT = pd.Timestamp("2026-02-15", tz="UTC")
LB, W, D, N, R = 60, 10, 3, 60, 1.0   # prior-low lookback, pre-flow win, decision win, label horizon (min), barrier xATR


def fwd_ext(s: pd.Series, n: int, how: str) -> pd.Series:
    r = s[::-1].rolling(n, min_periods=1)
    return ((r.max() if how == "max" else r.min())[::-1]).shift(-1)   # extreme over (i, i+n]


def minute_bars(sym: str) -> pd.DataFrame:
    fs = sorted(glob.glob(str(OFI / sym / "*.parquet")))
    df = pd.concat([pd.read_parquet(f, columns=["ts", "mid", "signed", "volume"]) for f in fs], ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.set_index("ts").sort_index().dropna(subset=["mid"])
    df = df[~df.index.duplicated(keep="first")]
    g = df.resample("1min", label="right", closed="right")
    b = pd.DataFrame({"o": g["mid"].first(), "h": g["mid"].max(), "l": g["mid"].min(), "c": g["mid"].last(),
                      "net": g["signed"].sum(), "vol": g["volume"].sum()}).dropna(subset=["c"])
    return b


def build(sym: str) -> pd.DataFrame:
    tick = TICK[sym]
    b = minute_bars(sym)
    b["rng"] = b["h"] - b["l"]
    b["atr"] = b["rng"].rolling(N, min_periods=20).mean()
    level = b["l"].rolling(LB, min_periods=LB // 2).min().shift(1)        # prior swing-low (liquidity pool)
    pen = b["l"] < level
    b["sweep"] = pen & ~pen.shift(1, fill_value=False)                    # fresh penetration only
    # flow features at the sweep -------------------------------------------------------------------
    b["pre_sgn"] = b["net"].rolling(W).sum()                             # confirming sell pressure into the sweep
    pre_vol = b["vol"].rolling(W).sum()
    pre_rng = (b["h"].rolling(W).max() - b["l"].rolling(W).min()) / tick + 1.0
    b["pre_absorp"] = pre_vol / pre_rng                                  # contracts per tick of range (absorption)
    b["post_sgn"] = b["net"][::-1].rolling(D, min_periods=1).sum()[::-1].shift(-1)  # net flow over (i, i+D] (the reaction)
    b["ret_pre"] = (b["c"] - b["c"].shift(W)) / b["c"].shift(W)          # move INTO the sweep (mean-reversion proxy)
    lowD = fwd_ext(b["l"], D, "min")
    b["ref"] = np.minimum(b["l"], lowD.fillna(b["l"]))                   # lowest price through decision window (FEATURE only)
    b["pen_depth"] = (level - b["ref"]) / b["atr"]                       # how far below the level (in ATR) -- a feature
    # HONEST label: ENTER at the decision-time price (i+D, a tradeable price), barriers in horizon-vol units.
    # No local-low artifact -> base rate should be ~0.5 and any lift is real.
    vol_h = b["c"].pct_change().rolling(240, min_periods=60).std() * np.sqrt(N) * b["c"]   # ~N-min 1-sigma move
    entry = b["c"].shift(-D)                                             # price D min AFTER the sweep (what you'd fill at)
    fhi = fwd_ext(b["h"], N, "max").shift(-D)
    flo = fwd_ext(b["l"], N, "min").shift(-D)
    up = fhi >= (entry + R * vol_h)
    dn = flo <= (entry - R * vol_h)
    b["reversal"] = (up & ~dn).astype(float)                            # 1 = price ROSE from a tradeable entry (fade worked)
    b["decisive"] = (up ^ dn)                                           # exactly one barrier -> clean label
    b["valid"] = (~fhi.isna()) & (~flo.isna()) & (vol_h > 0) & (~entry.isna())
    return b


FEATS = ["ret_pre", "pen_depth", "pre_sgn", "pre_absorp", "post_sgn"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    a = ap.parse_args(argv)
    b = build(a.symbol)
    ev = b[b["sweep"] & b["valid"] & b["decisive"]].copy()
    ev["delta_div"] = ev["pre_sgn"].diff()                              # exhaustion vs the PRIOR sweep
    feats = FEATS + ["delta_div"]
    ev = ev.replace([np.inf, -np.inf], np.nan).dropna(subset=feats + ["reversal"])
    tr, te = ev[ev.index < CUT], ev[ev.index >= CUT]
    print(f"{a.symbol}: sweeps train {len(tr):,} / test {len(te):,}  reversal(fakeout) base-rate {te['reversal'].mean():.3f}")
    if len(te) < 150:
        print("  too few test events"); return 0

    from lightgbm import LGBMClassifier
    from sklearn.metrics import roc_auc_score
    yte = te["reversal"].to_numpy()
    uni = {f: max(roc_auc_score(yte, te[f]), 1.0 - roc_auc_score(yte, te[f])) for f in feats}
    print("-- univariate OOS AUC per feature (0.50 = useless) --")
    for f in sorted(feats, key=lambda x: -uni[x]):
        print(f"  {f:12} {uni[f]:.4f}")

    def gbdt(fs):
        m = LGBMClassifier(n_estimators=200, learning_rate=0.03, num_leaves=7, min_child_samples=40,
                           subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1)
        m.fit(tr[fs], tr["reversal"])
        return m.predict_proba(te[fs])[:, 1]

    groups = {"mean_rev [ret_pre,pen_depth]": ["ret_pre", "pen_depth"],
              "flow_confirm [pre_sgn,absorp]": ["pre_sgn", "pre_absorp"],
              "flow_exhaust [post_sgn,delta_div]": ["post_sgn", "delta_div"],
              "ALL": feats}
    print("-- grouped ablation (does flow beat mean-reversion at predicting fakeout-reversal?) --")
    p_all = None
    for name, fs in groups.items():
        p = gbdt(fs)
        if name == "ALL":
            p_all = p
        print(f"  {name:36} AUC={roc_auc_score(yte, p):.4f}")

    # tradeability: high-confidence reversal calls -> go long the sweep low, +/-R*ATR barriers (decisive => +-R)
    cost_R = 0.10                                                       # ~cost as a fraction of the R barrier (stub)
    for q in (0.70, 0.85):
        hi = p_all >= np.quantile(p_all, q)
        prec = yte[hi].mean()                                          # P(reversal | high-confidence call)
        exp_R = (2 * prec - 1) * R - cost_R
        print(f"  top-{int((1-q)*100)}% conf: n={int(hi.sum())}  precision={prec:.3f}  "
              f"E[R/trade]={exp_R:+.3f}  (base {te['reversal'].mean():.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
