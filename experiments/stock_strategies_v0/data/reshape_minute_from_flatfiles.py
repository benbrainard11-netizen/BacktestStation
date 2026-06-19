"""Reshape Polygon RAW flat-file minute aggs -> per-(ticker,date) parquet in the strategy's format
(cols t,o,h,l,c,v; t = ms epoch), SPLIT-ADJUSTED to match the existing adjusted basis.

WHY adjust: the flat files are UNADJUSTED (NVDA 2024-05-01 close = 830.41 raw vs 83.04 adjusted,
the 10:1 split). But daily_*.parquet and the 23k REST minute were pulled adjusted=true. Mixing
bases would corrupt split names' pre-split dates. So each (ticker,date)'s raw minute is scaled by
    fac = adj_daily_open / raw_first_RTH_open
the SAME causal open-reconciliation run_intraday_entry.py applies at load -- computed here once so
the output is uniformly adjusted and the consumer's reconciliation becomes a no-op (fac == 1).
Setups with no adjusted daily are passed raw (the consumer skips those anyway: no daily => no entry).

Reads each day's flat file ONCE (grouped by date). Writes
D:\\data\\processed\\stocks\\polygon\\minute\\<TICKER>__<YYYYMMDD>.parquet (skip-existing, so the
23k REST files are kept and only the ~159k missing setups are filled). Idempotent / resumable.
Run with backend\\.venv\\Scripts\\python.exe.   Optional arg: worker count (default 8).
"""

from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import time as T
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SETUPS = ROOT / "unified_v0" / "out" / "setups.parquet"
FF = Path(r"E:\data\polygon\flatfiles\us_stocks_sip\minute_aggs_v1")
POLY = Path(r"D:\data\processed\stocks\polygon")
OUT = POLY / "minute"
WORKERS = int(sys.argv[1]) if len(sys.argv) > 1 else 8
RTH0 = T(9, 30)
FAC_LO, FAC_HI = 0.02, 50.0  # accept up to 50:1 / 1:50 split factors; reject data-error ratios
SRC_COLS = ["ticker", "volume", "open", "close", "high", "low", "window_start"]


def flatpath(d: int) -> Path:
    s = str(int(d))
    return FF / s[:4] / s[4:6] / f"{s[:4]}-{s[4:6]}-{s[6:]}.csv.gz"


def do_date(args):
    d, tickers, adj_open = args  # adj_open: {ticker: adjusted daily open for this date}
    fp = flatpath(d)
    if not fp.exists():
        return (d, 0, "nofile")
    need = {t for t in tickers if not (OUT / f"{t}__{d}.parquet").exists()}
    if not need:
        return (d, 0, "alldone")
    try:
        df = pd.read_csv(fp, compression="gzip", usecols=SRC_COLS)
    except Exception:
        return (d, 0, "readerr")
    df = df[df["ticker"].isin(need)]
    if not len(df):
        return (d, 0, "noticks")
    ws = df["window_start"].to_numpy()
    et = pd.to_datetime(ws, utc=True).tz_convert("America/New_York")
    df = df.assign(_ms=(ws // 1_000_000).astype("int64"), _rth=(et.time >= RTH0))
    wrote = 0
    for t, g in df.groupby("ticker", sort=False):
        g = g.sort_values("_ms")
        rth = g[g["_rth"]]
        raw_ref = float(rth["open"].iloc[0]) if len(rth) else float(g["open"].iloc[0])
        ao = adj_open.get(t)
        fac = 1.0
        if ao and raw_ref:
            f = ao / raw_ref
            if FAC_LO < f < FAC_HI:
                fac = f
        out = pd.DataFrame(
            {
                "t": g["_ms"].to_numpy(),
                "o": g["open"].to_numpy() * fac,
                "h": g["high"].to_numpy() * fac,
                "l": g["low"].to_numpy() * fac,
                "c": g["close"].to_numpy() * fac,
                "v": g["volume"].to_numpy(),
            }
        )
        of = OUT / f"{t}__{d}.parquet"
        tmp = of.with_suffix(".tmp.parquet")
        out.to_parquet(tmp)
        tmp.replace(of)
        wrote += 1
    return (d, wrote, "ok")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    s = pd.read_parquet(SETUPS)
    b = s[s["is_breakout"] == 1][["ticker", "date"]].drop_duplicates()
    b["date"] = b["date"].astype(int)
    by_date = {int(d): list(g["ticker"]) for d, g in b.groupby("date")}
    dates = sorted(by_date)

    dd = pd.concat(
        [
            pd.read_parquet(f, columns=["ticker", "date", "open"])
            for f in sorted(POLY.glob("daily_*.parquet"))
        ],
        ignore_index=True,
    )
    dd = dd[dd["date"].isin(set(dates))]
    adj_by_date = {int(d): dict(zip(g["ticker"], g["open"])) for d, g in dd.groupby("date")}

    items = [(d, by_date[d], {t: adj_by_date.get(d, {}).get(t) for t in by_date[d]}) for d in dates]
    print(f"{len(b):,} setup (ticker,date) over {len(items)} dates; workers={WORKERS}", flush=True)
    wrote = nofile = 0
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        for i, (d, w, st) in enumerate(ex.map(do_date, items), 1):
            wrote += w
            nofile += st == "nofile"
            if i % 100 == 0 or i == len(items):
                print(f"  {i}/{len(items)} dates  wrote={wrote:,}  nofile={nofile}", flush=True)
    print(f"DONE: wrote={wrote:,} minute files, {nofile} dates missing flat file -> {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
