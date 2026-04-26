"""One-off diagnostic for the engine port producing zero trades.

Runs the strategy on the smoke week and prints:
  1. Aux timestamp alignment between NQ/ES/YM
  2. Stage signals detected (count + samples)
  3. Setups built (count + status breakdown)
  4. Trades emitted

Usage:
  cd backend
  .venv\\Scripts\\python.exe debug_fractal_zero_trades.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from app.backtest.engine import RunConfig, run as engine_run
from app.backtest.strategy import Bar
from app.strategies.fractal_amd import FractalAMD
from app.strategies.fractal_amd.config import FractalAMDConfig

DATA_DIR = Path(r"C:\Users\benbr\Documents\trading-bot-main\data\raw")
TZ = "America/New_York"
T0 = pd.Timestamp("2024-01-02", tz=TZ)
T1 = pd.Timestamp("2024-01-08 23:59", tz=TZ)


def _load_df(sym: str) -> pd.DataFrame:
    files = [
        DATA_DIR / f"{sym}.c.0_ohlcv-1m_2022_2025.parquet",
        DATA_DIR / f"{sym}_ohlcv-1m_2026.parquet",
    ]
    files = [f for f in files if f.exists()]
    df = pd.concat([pd.read_parquet(f) for f in files]).sort_index()
    return df[(df.index >= T0) & (df.index <= T1)]


def _to_bars(df: pd.DataFrame, sym_full: str) -> list[Bar]:
    out = []
    for row in df.itertuples():
        ts = row.Index.to_pydatetime() if hasattr(row.Index, "to_pydatetime") else row.Index
        o, h, l, c = float(row.open), float(row.high), float(row.low), float(row.close)
        out.append(
            Bar(
                ts_event=ts,
                symbol=sym_full,
                open=o, high=h, low=l, close=c,
                volume=int(row.volume),
                trade_count=0,
                vwap=(o + h + l + c) / 4,
            )
        )
    return out


def main() -> None:
    print("=" * 60)
    print("STEP 1: Load data")
    print("=" * 60)
    nq_df = _load_df("NQ")
    es_df = _load_df("ES")
    ym_df = _load_df("YM")
    print(f"NQ: {len(nq_df)} bars, {nq_df.index[0]} -> {nq_df.index[-1]}")
    print(f"ES: {len(es_df)} bars, {es_df.index[0]} -> {es_df.index[-1]}")
    print(f"YM: {len(ym_df)} bars, {ym_df.index[0]} -> {ym_df.index[-1]}")

    print()
    print("=" * 60)
    print("STEP 2: Aux timestamp alignment vs NQ")
    print("=" * 60)
    nq_ts = set(nq_df.index)
    es_ts = set(es_df.index)
    ym_ts = set(ym_df.index)
    print(f"NQ & ES: {len(nq_ts & es_ts)} of {len(nq_ts)} NQ bars  ({len(nq_ts & es_ts)/max(len(nq_ts),1):.1%})")
    print(f"NQ & YM: {len(nq_ts & ym_ts)} of {len(nq_ts)} NQ bars  ({len(nq_ts & ym_ts)/max(len(nq_ts),1):.1%})")
    nq_only = nq_ts - es_ts - ym_ts
    print(f"NQ only (no ES + no YM): {len(nq_only)}")
    if nq_only:
        sample = sorted(nq_only)[:5]
        print(f"  first 5 misaligned NQ ts: {sample}")

    print()
    print("=" * 60)
    print("STEP 3: Trusted entries we should be reproducing")
    print("=" * 60)
    trusted = pd.read_csv(
        Path(__file__).parent.parent / "samples" / "fractal_trusted_multiyear" / "trades.csv",
        parse_dates=["entry_time"],
    )
    trusted["entry_time"] = trusted["entry_time"].dt.tz_localize(TZ)
    trusted_window = trusted[
        (trusted["entry_time"] >= T0) & (trusted["entry_time"] <= T1)
    ]
    for _, row in trusted_window.iterrows():
        print(
            f"  {row['entry_time']} {row['direction']:7} entry={row['entry_price']:>10.2f} "
            f"stop={row['stop']:>10.2f} fvg=[{row['fvg_low']:>10.2f},{row['fvg_high']:>10.2f}] "
            f"pnl={row['pnl_r']:+.2f}R exit={row['exit_reason']}"
        )

    print()
    print("=" * 60)
    print("STEP 4: Run strategy and inspect internal state")
    print("=" * 60)
    nq_bars = _to_bars(nq_df, "NQ.c.0")
    es_bars = _to_bars(es_df, "ES.c.0")
    ym_bars = _to_bars(ym_df, "YM.c.0")
    es_aux = {b.ts_event: b for b in es_bars}
    ym_aux = {b.ts_event: b for b in ym_bars}

    cfg = FractalAMDConfig()
    strat = FractalAMD(cfg)
    rc = RunConfig(
        strategy_name="fractal_amd",
        symbol="NQ.c.0",
        timeframe="1m",
        start=str(T0.date()),
        end=str(T1.date()),
        history_max=2000,
        aux_symbols=["ES.c.0", "YM.c.0"],
        commission_per_contract=0.0,
        slippage_ticks=1,
        flatten_on_last_bar=False,
    )
    print(f"Running engine on {len(nq_bars)} NQ bars...")
    result = engine_run(strat, nq_bars, rc, aux_bars={"ES.c.0": es_aux, "YM.c.0": ym_aux})
    print(f"Trades emitted: {len(result.trades)}")

    print()
    print(f"Stage signals collected: {len(strat.stage_signals)}")
    for s in strat.stage_signals[:10]:
        print(f"  {s.timeframe:>7} {s.candle_start} -> {s.candle_end}  dir={s.direction}")

    print()
    print(f"Setups built: {len(strat.setups)}")
    if strat.setups:
        from collections import Counter
        status_counts = Counter(s.status for s in strat.setups)
        print(f"  by status: {dict(status_counts)}")
        for s in strat.setups[:10]:
            print(
                f"  {s.direction:7} {s.htf_tf}/{s.ltf_tf} fvg=[{s.fvg_low:>10.2f},{s.fvg_high:>10.2f}] "
                f"htf_close={s.htf_candle_end} status={s.status} touch_at={s.touch_bar_time}"
            )

    print()
    print(f"Aux history sizes (post-run):")
    for sym, hist in strat.aux_history.items():
        print(f"  {sym}: {len(hist)} bars")

    print()
    print(f"_fully_scanned cache: {len(strat._fully_scanned)} entries")


if __name__ == "__main__":
    main()
