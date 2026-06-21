"""Candle-event model — do orderflow EVENTS at candles help predict the NEXT candle? (gates the TSFM)

Aggregates the 1s event-OFI features into 5-min candles with: bar features (return, range, realized
vol, momentum) + orderflow-event features (net signed flow, signed ratio, absorption = |flow|/|move|
as the hidden-liquidity/iceberg proxy, book imbalance, OFI, price-flow divergence flag). Then a GBDT
predicts the NEXT candle's return, comparing bars-only vs bars+orderflow, OOS (non-overlapping candles
so no overlapping-sample trap). Also reports the divergence-conditioned slice (the user's event idea).

If bars+orderflow beats bars-only OOS, the event features carry signal -> the TSFM (sequence model on
these features) is worth building. If not, candle prediction doesn't clear the bar even with events.

Run: backend/.venv/Scripts/python.exe experiments/orderflow_divergence_v0/candle_event_model.py --symbol ZN.c.0
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out" / "event_ofi"
EPS = 1e-9
BAR_FEATS = ["ret", "range_n", "rvol", "mom3"]
OF_FEATS = ["net_signed", "signed_ratio", "absorption", "imb_mean", "imb_close",
            "ofi_sum", "micro_close", "pf_diverge"]


def candles(sym: str, tf: str = "5min") -> pd.DataFrame:
    fs = sorted(glob.glob(str(OUT / sym / "*.parquet")))
    df = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.sort_values("ts").set_index("ts")
    df["r1s"] = np.log(df["mid"]).diff()
    g = df.resample(tf, label="right", closed="right")
    c = pd.DataFrame({
        "o": g["mid"].first(), "h": g["mid"].max(), "l": g["mid"].min(), "cl": g["mid"].last(),
        "net_signed": g["signed"].sum(), "volume": g["volume"].sum(), "ofi_sum": g["ofi"].sum(),
        "imb_mean": g["imb"].mean(), "imb_close": g["imb"].last(), "micro_close": g["micro_mid"].last(),
        "rvol": g["r1s"].std(), "events": g["events"].sum(),
    }).dropna(subset=["cl"])
    c = c[c["volume"] > 0].copy()
    c["ret"] = np.log(c["cl"] / c["o"])
    c["range_n"] = (c["h"] - c["l"]) / c["cl"]
    c["signed_ratio"] = c["net_signed"] / c["volume"].where(c["volume"] > 0, np.nan)
    c["absorption"] = c["net_signed"].abs() / ((c["cl"] - c["o"]).abs() + EPS)   # iceberg/hidden-liq proxy
    c["pf_diverge"] = (np.sign(c["ret"]) != np.sign(c["net_signed"])).astype(float)
    c["mom3"] = c["ret"].rolling(3).sum()
    c["date"] = c.index.date
    c["next_ret"] = c["ret"].shift(-1)
    return c.dropna(subset=BAR_FEATS + OF_FEATS + ["next_ret"])


def gbdt_oos(Xtr, ytr, Xte):
    from lightgbm import LGBMRegressor
    m = LGBMRegressor(n_estimators=300, learning_rate=0.03, num_leaves=31, subsample=0.8,
                      colsample_bytree=0.8, min_child_samples=50, verbose=-1)
    m.fit(Xtr, ytr)
    return m.predict(Xte)


def report(name, pred, yte, cost_ret):
    ic = float(np.corrcoef(pred, yte)[0, 1])
    nz = yte != 0
    dacc = float(np.mean(np.sign(pred[nz]) == np.sign(yte[nz]))) if nz.sum() else float("nan")
    thr = np.quantile(np.abs(pred), 0.70)
    hi = np.abs(pred) >= thr
    gross = float((np.sign(pred[hi]) * yte[hi]).mean())          # mean next-candle return captured
    net = gross - cost_ret
    print(f"    {name:16} IC={ic:+.4f} dir={dacc:.3f} | top30%conv gross={gross*1e4:+.2f}bp "
          f"net(-{cost_ret*1e4:.1f}bp)={net*1e4:+.2f}bp (n={int(hi.sum())})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--tf", default="5min")
    ap.add_argument("--cut", default="2026-02-15")
    ap.add_argument("--cost-bp", type=float, default=1.0)   # ~1bp round-trip (cross spread+comm), tunable
    a = ap.parse_args(argv)
    c = candles(a.symbol, a.tf)
    cut = dt.date.fromisoformat(a.cut)
    tr, te = c[c["date"] < cut], c[c["date"] >= cut]
    yte = te["next_ret"].to_numpy()
    cost = a.cost_bp / 1e4
    print(f"{a.symbol} {a.tf} candles: train {len(tr):,} / test {len(te):,}  "
          f"({c.index.min().date()}..{c.index.max().date()})")
    p_bar = gbdt_oos(tr[BAR_FEATS], tr["next_ret"], te[BAR_FEATS])
    p_all = gbdt_oos(tr[BAR_FEATS + OF_FEATS], tr["next_ret"], te[BAR_FEATS + OF_FEATS])
    print("  -- predict NEXT candle return --")
    report("bars-only", p_bar, yte, cost)
    report("bars+orderflow", p_all, yte, cost)
    # event-conditioned slice: candles WITH price-flow divergence + high absorption
    cond = (te["pf_diverge"].to_numpy() == 1) & (te["absorption"].to_numpy() >= np.quantile(tr["absorption"], 0.7))
    if cond.sum() > 200:
        print(f"  -- divergence + high-absorption slice ({int(cond.sum())} candles) --")
        report("bars+of @ event", p_all[cond], yte[cond], cost)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
