"""Where do live's extra trades come from? Compare plug's setup pool vs
live's setup pool day-by-day for Jan 2026.

For each day, instrument both engines to log:
  - Number of HTF stages detected
  - Number of setups materialized (one per stage in plug's per-stage model;
    one per stage in live's new model after the 2026-04-29 AM rewrite)
  - Total FVG count across all setups
  - First 5 setup signatures (direction, htf_tf, ltf_tf, fvg_low, fvg_high)

If counts diverge, the bug is in scan_for_setups or detect_fvgs. If counts
match but trade lists diverge, the bug is in check_touch / check_entry.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import pandas as pd

# live_bot setup
_FA_ROOT = Path(os.environ.get("FA_REPO", r"C:\Users\benbr\FractalAMD-"))
sys.path.insert(0, str(_FA_ROOT / "production"))
sys.path.insert(0, str(_FA_ROOT / "src"))

from app.backtest.engine import RunConfig, run as engine_run
from app.backtest.strategy import Bar
from app.strategies.fractal_amd_trusted import (
    FractalAMDTrusted,
    FractalAMDTrustedConfig,
)

DATA_DIR = Path(r"C:\Fractal-AMD\data\raw")
TZ = "America/New_York"


def _bars(sym, t0, t1):
    s = sym.split(".")[0]
    files = [
        DATA_DIR / f"{s}.c.0_ohlcv-1m_2022_2025.parquet",
        DATA_DIR / f"{s}_ohlcv-1m_2026.parquet",
    ]
    pieces = []
    for f in files:
        if not f.exists():
            continue
        df = pd.read_parquet(f)[["open", "high", "low", "close", "volume"]].copy()
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(TZ)
        elif str(df.index.tz) != TZ:
            df.index = df.index.tz_convert(TZ)
        pieces.append(df)
    df = pd.concat(pieces).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df = df[(df.index >= t0) & (df.index <= t1)]
    return df


def plug_setups_for_day(day: pd.Timestamp):
    """Run plug for one day; return final setups (each with stage info + fvg list)."""
    t0 = (day - pd.Timedelta(days=1)).replace(hour=18)
    t1 = day.replace(hour=17)
    nq_df = _bars("NQ.c.0", t0, t1)
    es_df = _bars("ES.c.0", t0, t1)
    ym_df = _bars("YM.c.0", t0, t1)
    if len(nq_df) < 60 or len(es_df) < 60 or len(ym_df) < 60:
        return None

    nq_bars = []
    for row in nq_df.itertuples():
        ts = row.Index.to_pydatetime() if hasattr(row.Index, "to_pydatetime") else row.Index
        o, h, l, c = float(row.open), float(row.high), float(row.low), float(row.close)
        nq_bars.append(Bar(
            ts_event=ts, symbol="NQ.c.0", open=o, high=h, low=l, close=c,
            volume=int(row.volume), trade_count=0, vwap=(o + h + l + c) / 4,
        ))
    es_map = {}
    for row in es_df.itertuples():
        ts = row.Index.to_pydatetime() if hasattr(row.Index, "to_pydatetime") else row.Index
        o, h, l, c = float(row.open), float(row.high), float(row.low), float(row.close)
        es_map[ts] = Bar(
            ts_event=ts, symbol="ES.c.0", open=o, high=h, low=l, close=c,
            volume=int(row.volume), trade_count=0, vwap=(o + h + l + c) / 4,
        )
    ym_map = {}
    for row in ym_df.itertuples():
        ts = row.Index.to_pydatetime() if hasattr(row.Index, "to_pydatetime") else row.Index
        o, h, l, c = float(row.open), float(row.high), float(row.low), float(row.close)
        ym_map[ts] = Bar(
            ts_event=ts, symbol="YM.c.0", open=o, high=h, low=l, close=c,
            volume=int(row.volume), trade_count=0, vwap=(o + h + l + c) / 4,
        )

    cfg = FractalAMDTrustedConfig()
    strat = FractalAMDTrusted(cfg)
    rc = RunConfig(
        strategy_name="fractal_amd_trusted",
        symbol="NQ.c.0", timeframe="1m",
        start=str(day.date()), end=str(day.date()),
        history_max=2000, aux_symbols=["ES.c.0", "YM.c.0"],
        commission_per_contract=0.0, slippage_ticks=0,
        flatten_on_last_bar=False,
    )
    engine_run(strat, nq_bars, rc, aux_bars={"ES.c.0": es_map, "YM.c.0": ym_map})

    # After run: strat.day_state has final setups for the day.
    if strat.day_state is None:
        return {"stages": 0, "setups": 0, "fvgs": 0, "sigs": []}
    stages = len(strat.day_state.htf_stages)
    setups = strat.day_state.setups
    sigs = []
    total_fvgs = 0
    for s in setups:
        total_fvgs += len(s.fvgs)
        for f in s.fvgs[:3]:  # first 3 per setup
            sigs.append((s.stage.direction, s.stage.timeframe, s.ltf_tf, round(f.low, 2), round(f.high, 2)))
    return {
        "stages": stages,
        "setups": len(setups),
        "fvgs": total_fvgs,
        "sigs": sigs,
    }


def live_setups_for_day(day: pd.Timestamp):
    """Run live's SignalEngine via the harness for one day; return setups."""
    from live_bot import CandleBuilder, SignalEngine
    from scripts.backtest_live_bot import (
        load_ohlcv, find_tbbo_files_for_day, load_tbbo_for_day,
        run_day, VAL_930, FastTBBOBuffer,
    )

    nq = load_ohlcv("NQ")
    es = load_ohlcv("ES")
    ym = load_ohlcv("YM")
    tbbo = load_tbbo_for_day(day.date())

    # Replicate the harness's run_day setup logic but stop after building setups
    # Use SignalEngine directly with full day's bars to materialize setups.
    day_start = (day - pd.Timedelta(days=1)).replace(hour=18)
    day_end = day.replace(hour=17)
    nq_day = nq.loc[day_start:day_end]
    es_day = es.loc[day_start:day_end]
    ym_day = ym.loc[day_start:day_end]
    if len(nq_day) < 60:
        return None

    engine = SignalEngine()
    engine.persist_enabled = False
    engine.reset_day()
    engine.today = day.date()

    # Run scan every minute (matching harness post-fix)
    for i in range(20, len(nq_day)):
        t = nq_day.index[i]
        nq_closed = nq_day.iloc[:i]
        es_pos = es_day.index.searchsorted(t)
        es_closed = es_day.iloc[:es_pos]
        ym_pos = ym_day.index.searchsorted(t)
        ym_closed = ym_day.iloc[:ym_pos]
        if len(nq_closed) > 20 and len(es_closed) > 20 and len(ym_closed) > 20:
            engine.scan_for_setups(nq_closed, es_closed, ym_closed, t)

    setups = engine.setups
    sigs = []
    total_fvgs = 0
    for s in setups:
        total_fvgs += len(s.fvgs)
        for f in s.fvgs[:3]:
            sigs.append((s.direction, s.htf_tf, s.ltf_tf, round(f.low, 2), round(f.high, 2)))
    return {
        "stages": len(engine._htf_stages),
        "setups": len(setups),
        "fvgs": total_fvgs,
        "sigs": sigs,
    }


def main():
    days = [
        pd.Timestamp(d, tz=TZ) for d in [
            "2026-01-02", "2026-01-05", "2026-01-09", "2026-01-19",
            "2026-01-20", "2026-01-30",
        ]
    ]
    print("=" * 90)
    print(f"{'day':<12} {'stages':>14}  {'setups':>14}  {'fvgs':>14}")
    print(f"{'':12} {'plug | live':>14}  {'plug | live':>14}  {'plug | live':>14}")
    print("=" * 90)
    for day in days:
        plug = plug_setups_for_day(day)
        live = live_setups_for_day(day)
        if plug is None or live is None:
            print(f"{day.date()}  (skipped)")
            continue
        print(
            f"{day.date()}  "
            f"{plug['stages']:>5} | {live['stages']:>5}  "
            f"{plug['setups']:>5} | {live['setups']:>5}  "
            f"{plug['fvgs']:>5} | {live['fvgs']:>5}"
        )

    # Detail diff for one specific day where live trades but plug doesn't
    detail_day = pd.Timestamp("2026-01-19", tz=TZ)
    print()
    print("=" * 90)
    print(f"DETAIL: {detail_day.date()}  (plug=0 trades, live=2 trades)")
    print("=" * 90)
    plug = plug_setups_for_day(detail_day)
    live = live_setups_for_day(detail_day)
    print(f"\nplug setups ({plug['setups']}):")
    for sig in plug["sigs"][:20]:
        print(f"  {sig}")
    print(f"\nlive setups ({live['setups']}):")
    for sig in live["sigs"][:20]:
        print(f"  {sig}")


if __name__ == "__main__":
    main()
