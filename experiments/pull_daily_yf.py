"""Pull deep daily EOD from Yahoo (yfinance) for the sector-leader universe.

Writes D:\\data\\processed\\stocks\\daily\\<TICKER>.parquet (split/div-adjusted, ~2010+). Free + deep,
and avoids the ThetaData terminals entirely (no backfill contention). NOTE: Yahoo is survivorship-biased
(active tickers only) — fine for prototyping a sector-leader model; use Norgate for the real
survivorship-free backtest. Cols: date(int YYYYMMDD), open, high, low, close, volume.
Run: python pull_daily_yf.py [start=2010-01-01]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

OUT = Path(r"D:\data\processed\stocks\daily")
UNI = Path(__file__).resolve().parent / "options_signals_v0" / "out" / "sector_leader_universe.parquet"
START = sys.argv[1] if len(sys.argv) > 1 else "2010-01-01"


def save(orig: str, df) -> int:
    if df is None or not len(df):
        return 0
    df = df.dropna(how="all")
    out = pd.DataFrame({
        "date": [int(d.strftime("%Y%m%d")) for d in df.index],
        "open": df["Open"].to_numpy(), "high": df["High"].to_numpy(), "low": df["Low"].to_numpy(),
        "close": df["Close"].to_numpy(), "volume": df["Volume"].to_numpy(),
    }).dropna(subset=["close"])
    if not len(out):
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT / f"{orig}.parquet")
    return len(out)


def main() -> int:
    uni = pd.read_parquet(UNI)
    tickers = sorted(uni["ticker"].unique())
    ymap = {t: t.replace(".", "-") for t in tickers}        # Yahoo uses BRK-B, not BRK.B
    ok = fail = 0
    failed: list[str] = []
    B = 80
    batches = [tickers[i:i + B] for i in range(0, len(tickers), B)]
    for bi, batch in enumerate(batches):
        ys = [ymap[t] for t in batch]
        data = yf.download(ys, start=START, auto_adjust=True, group_by="ticker", threads=True, progress=False)
        lvl0 = set(data.columns.get_level_values(0)) if hasattr(data.columns, "get_level_values") else set()
        for t in batch:
            y = ymap[t]
            try:
                df = data[y] if y in lvl0 else None
                n = save(t, df)
            except Exception:
                n = 0
            if n:
                ok += 1
            else:
                fail += 1
                failed.append(t)
        print(f"batch {bi+1}/{len(batches)}: ok={ok} fail={fail}", flush=True)
        time.sleep(2)
    print(f"DONE: {ok} pulled, {fail} failed -> {OUT}", flush=True)
    if failed:
        print("failed:", failed, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
