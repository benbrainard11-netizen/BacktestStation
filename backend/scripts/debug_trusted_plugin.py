"""Debug: run FractalAMDTrusted on a 1-day window with verbose state logging.

Use to find why the plugin produces 0 trades when the canonical trusted
script produces 7 trades on the same week.
"""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import pandas as pd

from app.backtest.engine import RunConfig, run as engine_run
from app.backtest.strategy import Bar
from app.strategies.fractal_amd_trusted import (
    FractalAMDTrusted,
    FractalAMDTrustedConfig,
)


DATA_DIR = Path(os.environ.get("FRACTAL_DATA_DIR", r"C:\Fractal-AMD\data\raw"))
TZ = "America/New_York"
# Pre-load a few extra days so the day-N HTF scan has prev-day bars.
PRELOAD = pd.Timedelta(days=3)
T0 = pd.Timestamp("2024-01-02", tz=TZ)
T1 = pd.Timestamp("2024-01-03 23:59", tz=TZ)


def _bars_for_symbol(sym_full, t0, t1):
    sym = sym_full.split(".")[0]
    files = [
        DATA_DIR / f"{sym}.c.0_ohlcv-1m_2022_2025.parquet",
        DATA_DIR / f"{sym}_ohlcv-1m_2026.parquet",
    ]
    files = [f for f in files if f.exists()]
    pieces = []
    for f in files:
        df = pd.read_parquet(f)[["open", "high", "low", "close", "volume"]].copy()
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert("America/New_York")
        elif str(df.index.tz) != "America/New_York":
            df.index = df.index.tz_convert("America/New_York")
        pieces.append(df)
    df = pd.concat(pieces).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df = df[(df.index >= t0) & (df.index <= t1)]
    bars = []
    for row in df.itertuples():
        ts = row.Index.to_pydatetime() if hasattr(row.Index, "to_pydatetime") else row.Index
        o, h, l, c = float(row.open), float(row.high), float(row.low), float(row.close)
        bars.append(
            Bar(
                ts_event=ts, symbol=sym_full, open=o, high=h, low=l, close=c,
                volume=int(row.volume), trade_count=0,
                vwap=(o+h+l+c)/4,
            )
        )
    return bars


def main():
    nq = _bars_for_symbol("NQ.c.0", T0 - PRELOAD, T1)
    es = {b.ts_event: b for b in _bars_for_symbol("ES.c.0", T0 - PRELOAD, T1)}
    ym = {b.ts_event: b for b in _bars_for_symbol("YM.c.0", T0 - PRELOAD, T1)}
    print(f"NQ bars loaded: {len(nq)}  ({nq[0].ts_event} -> {nq[-1].ts_event})")

    cfg = FractalAMDTrustedConfig()
    strat = FractalAMDTrusted(cfg)
    strat.debug = True

    rc = RunConfig(
        strategy_name="fractal_amd_trusted",
        symbol="NQ.c.0",
        timeframe="1m",
        start=str((T0 - PRELOAD).date()),
        end=str(T1.date()),
        history_max=2000,
        aux_symbols=["ES.c.0", "YM.c.0"],
        commission_per_contract=0.0,
        slippage_ticks=0,
        flatten_on_last_bar=False,
    )

    result = engine_run(strat, nq, rc, aux_bars={"ES.c.0": es, "YM.c.0": ym})

    print(f"\n=== POST-RUN STATE ===")
    print(f"Trades: {len(result.trades)}")
    if strat.day_state is not None:
        ds = strat.day_state
        print(f"Last day_state: {ds.day}")
        print(f"  HTF stages found:        {len(ds.htf_stages)}")
        print(f"  HTF pairs scanned:       {len(ds.scanned_htf_pairs)}")
        print(f"  Setups built:            {len(ds.setups)}")
        print(f"  LTF searches completed:  {len(ds.completed_ltf_search)}")
        print(f"  Trades today:            {ds.trades_today}")
        for stage in ds.htf_stages[:10]:
            print(f"    stage: {stage.timeframe} {stage.direction} "
                  f"{stage.candle_start} -> {stage.candle_end}")
        for s in ds.setups:
            print(f"    setup: {s.stage.direction} {s.ltf_tf} fvgs={len(s.fvgs)} "
                  f"waiting={s.waiting} filled={s.filled}")
    else:
        print("day_state is None — day rollover never fired")


if __name__ == "__main__":
    main()
