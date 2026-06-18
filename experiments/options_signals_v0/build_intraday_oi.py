"""Daily OI companion for the intraday band (Ben's spec: pull OI separately, pair PRIOR-day value).
OI is daily -> the bulk endpoint is light (no intraday-style wedge). Per (root, exp <=DTE_MAX in span):
bulk open_interest over the exp's life, filter to +-BAND of spot, store out/intraday_oi/root=R/exp=E.parquet.
Run: THETA_PORT=25510 python build_intraday_oi.py NDXP 2025-05-01 2026-06-30 0 1
"""

from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theta_store as TS  # noqa: E402
from gex_pull import _ymd  # noqa: E402

ROOT = sys.argv[1]
START = sys.argv[2]
END = sys.argv[3]
SHARD = int(sys.argv[4]) if len(sys.argv) > 4 else 0
NSHARDS = int(sys.argv[5]) if len(sys.argv) > 5 else 1
BAND = float(os.environ.get("BAND", "0.07"))
DTE_MAX = int(os.environ.get("DTE_MAX", "45"))
OUT = Path(__file__).resolve().parent / "out" / "intraday_oi"
BARS = Path(r"D:\data\processed\bars\timeframe=1m")
FUT = {
    "NDXP": ("NQ.c.0", 1.0),
    "SPXW": ("ES.c.0", 1.0),
    "RUTW": ("RTY.c.0", 1.0),
    "DJX": ("YM.c.0", 0.01),
    "NDX": ("NQ.c.0", 1.0),
    "SPX": ("ES.c.0", 1.0),
    "RUT": ("RTY.c.0", 1.0),
}  # monthly/deep-history roots
KEEP = ["date", "strike", "right", "expiration", "open_interest"]


def spot_by_day() -> pd.Series:
    sym, scale = FUT[ROOT]
    d = (
        ds.dataset(BARS / f"symbol={sym}", format="parquet")
        .to_table(columns=["ts_event", "close"])
        .to_pandas()
    )
    d["date"] = pd.to_datetime(d["ts_event"]).dt.strftime("%Y%m%d").astype(int)
    return d.sort_values("ts_event").groupby("date")["close"].last() * scale


def main() -> int:
    s, e = _ymd(START), _ymd(END)
    spot = spot_by_day()
    exps = [
        E
        for E in sorted(int(x) for x in TS.expirations(ROOT))
        if _ymd(pd.Timestamp(str(E)) - pd.Timedelta(days=DTE_MAX)) <= e and E >= s
    ][SHARD::NSHARDS]
    print(f"[{ROOT} s{SHARD}] {len(exps)} expirations (OI)", flush=True)

    def do_exp(E):
        outf = OUT / f"root={ROOT}" / f"exp={E}.parquet"
        if outf.exists():
            return 0
        life_s = max(s, _ymd(pd.Timestamp(str(E)) - pd.Timedelta(days=DTE_MAX)))
        life_e = min(e, E)
        sl = spot[(spot.index >= life_s) & (spot.index <= life_e)]
        if sl.empty:
            return 0
        lo, hi = sl.min() * (1 - BAND), sl.max() * (1 + BAND)
        try:
            oi = TS.fetch(
                "bulk_hist/option/open_interest", root=ROOT, exp=E, start_date=life_s, end_date=life_e
            )
        except Exception:
            return 0
        if oi.empty:
            return 0
        band = oi[(oi["strike"] >= lo) & (oi["strike"] <= hi)]
        if not len(band):
            return 0
        outf.parent.mkdir(parents=True, exist_ok=True)
        tmp = outf.with_suffix(".tmp.parquet")
        band[[c for c in KEEP if c in band.columns]].to_parquet(tmp)
        tmp.replace(outf)
        return 1

    wrote = 0
    with ThreadPoolExecutor(max_workers=int(os.environ.get("WORKERS", "6"))) as pool:
        for i, r in enumerate(pool.map(do_exp, exps)):
            wrote += r
            if (i + 1) % 50 == 0:
                print(f"[{ROOT} s{SHARD}] {i+1}/{len(exps)} exps, {wrote} OI files", flush=True)
    print(f"[{ROOT} s{SHARD}] DONE: {wrote} OI files", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
