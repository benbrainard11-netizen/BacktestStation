"""Phase 0 — event-based OFI + microprice + queue imbalance from MBP-1, at 1-second resolution.

Reuses the MBP-1 parsing / sign convention from tsfm_milk_v0/orderflow_features.py, but computes
the Cont-Kukanov-Stoikov top-of-book Order Flow Imbalance per event and aggregates to 1s (NOT the
15-min buckets — the research says the signal lives in seconds). Each 1s bar at timestamp t covers
events in (t-1s, t] and is known AT t (label='right'); forward returns are computed later from
future bars, so features are no-lookahead.

Source : D:/data/raw/databento/mbp-1/symbol=<SYM>/date=<YYYY-MM-DD>/part-000.parquet
Output : out/event_ofi/<SYM>/<YYYY-MM-DD>.parquet   (resumable: skips existing)

CKS OFI (top of book), per consecutive book update:
  dW = bid_sz            if bid_px > prev_bid_px      (bid improved -> all new size is demand)
       bid_sz - prev     if bid_px == prev_bid_px     (same level -> size delta)
      -prev_bid_sz       if bid_px < prev_bid_px      (bid worsened -> prior demand pulled)
  dV = symmetric on the ask;  OFI_event = dW - dV.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

MBP1_ROOT = Path("D:/data/raw/databento/mbp-1")
OUT_ROOT = Path(__file__).resolve().parent / "out" / "event_ofi"
READ_COLS = ["ts_event", "action", "side", "size", "bid_px", "ask_px", "bid_sz", "ask_sz"]
BUCKET = "1s"


def compute_day(path: Path, symbol: str) -> pd.DataFrame | None:
    df = pd.read_parquet(path, columns=READ_COLS)
    if df.empty:
        return None
    df = df.sort_values("ts_event", kind="stable")
    bpx = df["bid_px"].to_numpy("f8"); apx = df["ask_px"].to_numpy("f8")
    bsz = df["bid_sz"].to_numpy("f8"); asz = df["ask_sz"].to_numpy("f8")
    pbpx, pbsz = np.roll(bpx, 1), np.roll(bsz, 1)
    papx, pasz = np.roll(apx, 1), np.roll(asz, 1)
    pbpx[0], pbsz[0], papx[0], pasz[0] = bpx[0], bsz[0], apx[0], asz[0]

    dW = np.where(bpx > pbpx, bsz, np.where(bpx == pbpx, bsz - pbsz, -pbsz))
    dV = np.where(apx < papx, asz, np.where(apx == papx, asz - pasz, -pasz))
    ofi = dW - dV
    ofi[0] = 0.0

    tot = bsz + asz
    tot_safe = np.where(tot == 0, np.nan, tot)
    mid = (bpx + apx) / 2.0
    micro_mid = (bpx * asz + apx * bsz) / tot_safe - mid   # microprice - mid
    imb = (bsz - asz) / tot_safe
    spread = apx - bpx

    is_tr = df["action"].to_numpy() == "T"
    sd = df["side"].to_numpy()
    sgn = np.where(sd == "B", 1.0, np.where(sd == "A", -1.0, 0.0))
    sz = df["size"].to_numpy("f8")
    signed = np.where(is_tr, sgn * sz, 0.0)
    tsz = np.where(is_tr, sz, 0.0)

    work = pd.DataFrame(
        {"ofi": ofi, "mid": mid, "micro_mid": micro_mid, "imb": imb, "spread": spread,
         "signed": signed, "tsz": tsz, "ev": 1.0},
        index=pd.DatetimeIndex(df["ts_event"]),
    )
    g = work.resample(BUCKET, label="right", closed="right")
    out = pd.DataFrame({
        "ofi": g["ofi"].sum(),
        "micro_mid": g["micro_mid"].mean(),
        "imb": g["imb"].mean(),
        "spread": g["spread"].mean(),
        "signed": g["signed"].sum(),
        "volume": g["tsz"].sum(),
        "events": g["ev"].sum(),
        "mid": g["mid"].last(),
    }).dropna(subset=["mid"])
    out["signed_ratio"] = out["signed"] / out["volume"].where(out["volume"] > 0, np.nan)
    out = out.reset_index(names="ts")
    out["symbol"] = symbol
    return out


def date_parts(symbol: str, start: str | None, end: str | None) -> list[Path]:
    sym_dir = MBP1_ROOT / f"symbol={symbol}"
    out = []
    for p in sorted(sym_dir.glob("date=*")):
        d = p.name.removeprefix("date=")
        if (start and d < start) or (end and d > end):
            continue
        f = p / "part-000.parquet"
        if f.exists():
            out.append(f)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+", required=True)
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    args = ap.parse_args(argv)
    import time
    for sym in args.symbols:
        files = date_parts(sym, args.start, args.end)
        odir = OUT_ROOT / sym
        odir.mkdir(parents=True, exist_ok=True)
        print(f"{sym}: {len(files)} symbol-days", flush=True)
        for f in files:
            date = f.parent.name.removeprefix("date=")
            op = odir / f"{date}.parquet"
            if op.exists():
                continue
            t = time.time()
            try:
                res = compute_day(f, sym)
            except Exception as e:
                print(f"  {date}: FAIL {type(e).__name__}: {e}", flush=True)
                continue
            if res is None or res.empty:
                print(f"  {date}: empty", flush=True)
                continue
            res.to_parquet(op, index=False)
            print(f"  {date}: {len(res):,} 1s-bars in {time.time()-t:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
