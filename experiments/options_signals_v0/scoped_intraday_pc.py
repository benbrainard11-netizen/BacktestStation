"""Per-CONTRACT intraday options puller — the method that does NOT wedge the terminal.

The bulk endpoint returns the whole strike chain in one giant response (~336k rows) and wedges the
Terminal. This pulls ONE contract at a time (hist/option/greeks?strike&right) -> tiny responses
(~thousands of rows, ~1.5s each) that never wedge. Concurrent thread pool (WORKERS per terminal,
within HTTP_CONCURRENCY) for throughput. Band strikes only (+-BAND of spot over each expiration's
<=DTE_MAX life). Resumable per contract. Sharded by expiration across terminals.

Store: out/intraday_pc/root=<ROOT>/exp=<E>/<strike1000>_<right>.parquet  (consolidate to (root,date) later)
Run: THETA_PORT=25510 WORKERS=8 python scoped_intraday_pc.py NDXP 2025-05-01 2026-06-30 0 3
"""

from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theta_store as TS  # noqa: E402
from gex_pull import _ymd  # noqa: E402

ROOT = sys.argv[1]
START = sys.argv[2]
END = sys.argv[3]
SHARD = int(sys.argv[4]) if len(sys.argv) > 4 else 0
NSHARDS = int(sys.argv[5]) if len(sys.argv) > 5 else 1
WORKERS = int(os.environ.get("WORKERS", "8"))
IVL = int(os.environ.get("IVL", "60000"))
BAND = float(os.environ.get("BAND", "0.07"))
DTE_MAX = int(os.environ.get("DTE_MAX", "45"))
PORT = os.environ.get("THETA_PORT", "25510")
BASE = f"http://127.0.0.1:{PORT}/v2"
OUT = Path(__file__).resolve().parent / "out" / "intraday_pc"
BARS = Path(r"D:\data\processed\bars\timeframe=1m")
# weekly/PM roots (recent intraday) + monthly/AM roots (deep history back to ~2016) -> same index future
FUT = {
    "NDXP": ("NQ.c.0", 1.0),
    "SPXW": ("ES.c.0", 1.0),
    "RUTW": ("RTY.c.0", 1.0),
    "DJX": ("YM.c.0", 0.01),
    "NDX": ("NQ.c.0", 1.0),
    "SPX": ("ES.c.0", 1.0),
    "RUT": ("RTY.c.0", 1.0),
}
# QUOTE feed has full 2025-05+ history (greeks feed is recent-only ~2026-05+). Pull bid/ask; pair
# underlying from the index future at build, BS-invert IV/gamma there (per spec: guard quotes+underlying).
ENDPOINT = os.environ.get("OPT_EP", "hist/option/quote")
KEEP = ["date", "ms_of_day", "strike", "right", "expiration", "bid", "ask", "bid_size", "ask_size"]


def spot_by_day() -> pd.Series:
    sym, scale = FUT[ROOT]
    d = (
        ds.dataset(BARS / f"symbol={sym}", format="parquet")
        .to_table(columns=["ts_event", "close"])
        .to_pandas()
    )
    d["date"] = pd.to_datetime(d["ts_event"]).dt.strftime("%Y%m%d").astype(int)
    return d.sort_values("ts_event").groupby("date")["close"].last() * scale


def fetch_contract(exp: int, strike: int, right: str, s: int, e: int):
    try:
        r = requests.get(
            f"{BASE}/{ENDPOINT}",
            params={
                "root": ROOT,
                "exp": exp,
                "strike": strike,
                "right": right,
                "start_date": s,
                "end_date": e,
                "ivl": IVL,
            },
            timeout=60,
        )
        if r.status_code != 200:
            return None
        j = r.json()
        rows = j.get("response", []) or []
        if not rows:
            return None
        df = pd.DataFrame(rows, columns=j["header"]["format"])
        df["strike"] = strike / 1000.0
        df["right"] = right
        df["expiration"] = exp
        return df[[c for c in KEEP if c in df.columns]]
    except Exception:
        return None


def main() -> int:
    s, e = _ymd(START), _ymd(END)
    spot = spot_by_day()
    allexps = sorted(int(x) for x in TS.expirations(ROOT))
    exps = [E for E in allexps if _ymd(pd.Timestamp(str(E)) - pd.Timedelta(days=DTE_MAX)) <= e and E >= s]
    exps = sorted(exps, reverse=True)[SHARD::NSHARDS]  # recent-first
    print(
        f"[{ROOT} s{SHARD}/{NSHARDS}] {len(exps)} expirations, WORKERS={WORKERS}, band=±{BAND:.0%}, DTE<={DTE_MAX}",
        flush=True,
    )
    wrote = 0
    for ei, E in enumerate(exps):
        life_s = max(s, _ymd(pd.Timestamp(str(E)) - pd.Timedelta(days=DTE_MAX)))
        life_e = min(e, E)
        if life_s > life_e:
            continue
        sl = spot[(spot.index >= life_s) & (spot.index <= life_e)]
        if sl.empty:
            continue
        lo, hi = sl.min() * (1 - BAND) * 1000, sl.max() * (1 + BAND) * 1000
        try:
            strikes = [
                int(x)
                for x in requests.get(
                    f"{BASE}/list/strikes", params={"root": ROOT, "exp": E}, timeout=30
                ).json()["response"]
            ]
        except Exception:
            continue
        edir = OUT / f"root={ROOT}" / f"exp={E}"
        work = [
            (E, k, rt, life_s, life_e)
            for k in strikes
            if lo <= k <= hi
            for rt in ("C", "P")
            if not (edir / f"{k}_{rt}.parquet").exists()
        ]
        if not work:
            continue
        edir.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futs = {pool.submit(fetch_contract, *w): w for w in work}
            for fut in as_completed(futs):
                _, k, rt, _, _ = futs[fut]
                df = fut.result()
                if df is not None and len(df):
                    outf = edir / f"{k}_{rt}.parquet"
                    tmp = outf.with_suffix(".tmp.parquet")
                    df.to_parquet(tmp)
                    tmp.replace(outf)
                    wrote += 1
        if (ei + 1) % 10 == 0 or work:
            print(
                f"[{ROOT} s{SHARD}] exp {E} ({ei+1}/{len(exps)}): {len(work)} contracts this exp, {wrote} total",
                flush=True,
            )
    print(f"[{ROOT} s{SHARD}] DONE: {wrote} contracts written", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
