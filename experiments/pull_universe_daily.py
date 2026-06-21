"""Batched, resumable daily pull for a large ticker list (the small/mid-cap universe extension).

Same source + format as stock_strategies_v0/data/pull_daily_yf.py (yfinance, split+div adjusted,
cols date/open/high/low/close/volume) but batched + skip-existing so a ~5k-name pull is reliable and
restartable. Reads the ticker list, skips names already in the daily store, batch-downloads the rest.
Run: python pull_universe_daily.py
"""
from __future__ import annotations

import glob
import os
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

LIST = Path(__file__).resolve().parent / "stock_strategies_v0" / "data" / "universe_to_pull.txt"
OUT = Path(r"D:\data\processed\stocks\daily")
START = "2010-01-01"
BATCH = 100


def save(orig: str, df) -> int:
    if df is None or not len(df):
        return 0
    df = df.dropna(how="all")
    try:
        out = pd.DataFrame({
            "date": [int(d.strftime("%Y%m%d")) for d in df.index],
            "open": df["Open"].to_numpy().ravel(), "high": df["High"].to_numpy().ravel(),
            "low": df["Low"].to_numpy().ravel(), "close": df["Close"].to_numpy().ravel(),
            "volume": df["Volume"].to_numpy().ravel(),
        }).dropna(subset=["close"])
    except Exception:
        return 0
    if not len(out):
        return 0
    out.to_parquet(OUT / f"{orig}.parquet")
    return len(out)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    want = [t.strip() for t in LIST.read_text().splitlines() if t.strip()]
    have = {os.path.basename(f)[:-8] for f in glob.glob(str(OUT / "*.parquet"))}
    todo = [t for t in want if t not in have]
    print(f"universe {len(want)} | already have {len(have)} | to pull {len(todo)}", flush=True)
    ok = fail = 0
    failed: list[str] = []
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    for bi, batch in enumerate(batches):
        ymap = {t: t.replace(".", "-") for t in batch}
        try:
            data = yf.download(list(ymap.values()), start=START, auto_adjust=True,
                               group_by="ticker", threads=True, progress=False)
            lvl0 = set(data.columns.get_level_values(0)) if hasattr(data.columns, "get_level_values") else set()
        except Exception:
            data, lvl0 = None, set()
        for t in batch:
            y = ymap[t]
            n = 0
            if data is not None and y in lvl0:
                try:
                    n = save(t, data[y])
                except Exception:
                    n = 0
            if n:
                ok += 1
            else:
                fail += 1
                failed.append(t)
        if (bi + 1) % 5 == 0 or bi == len(batches) - 1:
            print(f"  batch {bi+1}/{len(batches)}: ok={ok} fail={fail}", flush=True)
        time.sleep(1.5)
    print(f"DONE: pulled {ok}, failed {fail} (delisted/illiquid/no-data) -> {OUT}", flush=True)
    if failed:
        Path(LIST.parent / "daily_pull_failed.txt").write_text("\n".join(failed))
        print(f"failed list -> {LIST.parent / 'daily_pull_failed.txt'} (first 30: {failed[:30]})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
