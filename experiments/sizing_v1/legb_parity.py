"""Leg-B parity: do the gate-input BOOKPROXY features computed from live RITHMIC MBO match those
from the DATABENTO MBO the gate trained on? (The definitive test of the parity hypothesis.)

Parity is a FEATURE-DRIFT question, so it only needs Rithmic n Databento TEMPORAL overlap (NOT armed
setups in the overlap, which is why the earlier 'blocked' call was wrong). Overlap available:
  ES.c.0  2026-06-01 03:47-05:50 UTC  and  2026-06-05 01:34-07:56 UTC  (both feeds present).

Method:
  * On a 60s grid through the overlap, compute features.book_proxy_features() from BOTH feeds over the
    SAME [t-30s, t+60s) window at the SAME trigger_price (Databento last-trade) -> isolates A/C counting drift.
  * Per-feature drift (Rithmic/Databento ratio + sign): does Rithmic run systematically BELOW Databento?
  * Gate impact: scale the Jan armed setups' cluster.bookproxy features by the measured drift, re-score
    through the FROZEN gate, count how many cross below 0.5818 -> implied arm loss.

No gate retuning, no live connection (reads recorded JSONL only).
Run: backend/.venv/Scripts/python.exe experiments/sizing_v1/legb_parity.py [--day 0601|0605|both]
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import features as F  # noqa: E402

RITHMIC = Path(r"C:\Users\benbr\Downloads\mira_live_transfer_20260605_110402\rithmic_mbo")
DBN = Path(r"D:\data\clean\databento\mbo_trading_day")
SYMBOL = "ES.c.0"
WINDOWS = {  # day -> (rithmic_file, trading_day, lo_utc, hi_utc)
    "0601": (RITHMIC / "RITHMIC-mbo-2026-06-01.jsonl", "2026-06-01", "2026-06-01 03:47", "2026-06-01 05:50"),
    "0605": (RITHMIC / "RITHMIC-mbo-2026-06-05.jsonl", "2026-06-05", "2026-06-05 01:34", "2026-06-05 07:55"),
}
GRID_SEC = 60
RAW4 = ["ask_add_size_above", "bid_add_size_below", "ask_cancel_size_above", "bid_cancel_size_below"]


def load_rithmic(path: Path, symbol: str, lo: pd.Timestamp, hi: pd.Timestamp) -> pd.DataFrame:
    key = f'"{symbol}"'
    lo_ns, hi_ns = lo.value, hi.value
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if key not in line:
                continue
            d = json.loads(line)
            if d.get("symbol") != symbol:
                continue
            ts = int(d["ts_event"])
            if ts < lo_ns or ts >= hi_ns:
                continue
            rows.append((ts, d["action"], d["side"], d["price"], d["size"]))
    df = pd.DataFrame(rows, columns=["ts_event", "action", "side", "price", "size"])
    if not df.empty:
        df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    return df


def load_databento(symbol: str, trading_day: str, lo: pd.Timestamp, hi: pd.Timestamp) -> pd.DataFrame:
    p = DBN / f"symbol={symbol}" / f"trading_day={trading_day}" / "part-000.parquet"
    df = pd.read_parquet(p, columns=["ts_event", "action", "side", "price", "size"])
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    return df[(df["ts_event"] >= lo) & (df["ts_event"] < hi)].reset_index(drop=True)


def drift_for_window(day: str) -> pd.DataFrame:
    rfile, tday, lo_s, hi_s = WINDOWS[day]
    lo = pd.Timestamp(lo_s, tz="UTC"); hi = pd.Timestamp(hi_s, tz="UTC")
    pad = pd.Timedelta(seconds=65)
    print(f"[{day}] loading Rithmic {SYMBOL} {lo}..{hi} ...", flush=True)
    R = load_rithmic(rfile, SYMBOL, lo - pad, hi + pad)
    print(f"[{day}] Rithmic rows={len(R)}  actions={R.action.value_counts().to_dict() if len(R) else {}}", flush=True)
    Dn = load_databento(SYMBOL, tday, lo - pad, hi + pad)
    print(f"[{day}] Databento rows={len(Dn)}  actions={Dn.action.astype(str).value_counts().to_dict()}", flush=True)

    # trigger_price = last Databento TRADE price at/just before each grid t
    trades = Dn[Dn.action.astype(str) == "T"][["ts_event", "price"]].sort_values("ts_event")
    grid = pd.date_range(lo, hi, freq=f"{GRID_SEC}s")
    tp = pd.merge_asof(pd.DataFrame({"ts_event": grid}), trades, on="ts_event", direction="backward")

    recs = []
    for t, trig_price in zip(grid, tp["price"]):
        if not np.isfinite(trig_price):
            continue
        rb = F.book_proxy_features(F.slice_window(R, t), symbol=SYMBOL, anchor_side="low", trigger_price=float(trig_price))
        db = F.book_proxy_features(F.slice_window(Dn, t), symbol=SYMBOL, anchor_side="low", trigger_price=float(trig_price))
        row = {"t": t, "trigger_price": float(trig_price)}
        for k in RAW4:
            row[f"r_{k}"] = rb[f"{F.BOOKPROXY_PREFIX}.{k}"]
            row[f"d_{k}"] = db[f"{F.BOOKPROXY_PREFIX}.{k}"]
        recs.append(row)
    return pd.DataFrame(recs)


def summarize_drift(df: pd.DataFrame, tag: str) -> dict:
    print(f"\n=== {tag}: per-feature Rithmic-vs-Databento drift (n={len(df)} grid pts) ===")
    print(f"  {'feature':24s} {'R_mean':>10s} {'D_mean':>10s} {'R/D':>7s} {'%pts R<D':>9s} {'medR/D':>7s}")
    ratios = {}
    for k in RAW4:
        r, d = df[f"r_{k}"], df[f"d_{k}"]
        both = (r > 0) | (d > 0)
        rd = (r[both].sum() / d[both].sum()) if d[both].sum() > 0 else np.nan
        perpt = (r / d.replace(0, np.nan))
        medrd = float(perpt[np.isfinite(perpt)].median()) if np.isfinite(perpt).any() else np.nan
        pct_lt = float((r < d).mean() * 100)
        print(f"  {k:24s} {r.mean():>10.1f} {d.mean():>10.1f} {rd:>7.3f} {pct_lt:>8.0f}% {medrd:>7.3f}")
        ratios[k] = rd
    add_ratio = (df[[f"r_{k}" for k in RAW4[:2]]].values.sum() /
                 df[[f"d_{k}" for k in RAW4[:2]]].values.sum())
    can_ratio = (df[[f"r_{k}" for k in RAW4[2:]]].values.sum() /
                 df[[f"d_{k}" for k in RAW4[2:]]].values.sum())
    print(f"  --> aggregate ADD ratio R/D = {add_ratio:.3f}   CANCEL ratio R/D = {can_ratio:.3f}")
    return {"per_feature": ratios, "add_ratio": float(add_ratio), "cancel_ratio": float(can_ratio)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default="both", choices=["0601", "0605", "both"])
    ap.add_argument("--symbol", default="ES.c.0")
    args = ap.parse_args()
    global SYMBOL
    SYMBOL = args.symbol
    days = ["0601", "0605"] if args.day == "both" else [args.day]
    out = Path(r"C:\Users\benbr\BacktestStation\experiments\sizing_v1\out\mira_short_revalidation")
    out.mkdir(parents=True, exist_ok=True)
    alld = []
    res = {}
    for day in days:
        df = drift_for_window(day)
        df.to_csv(out / f"legb_drift_{day}_{SYMBOL}.csv", index=False)
        res[day] = summarize_drift(df, f"{SYMBOL} {day}")
        df["day"] = day
        alld.append(df)
    if len(alld) > 1:
        summarize_drift(pd.concat(alld, ignore_index=True), f"{SYMBOL} COMBINED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
