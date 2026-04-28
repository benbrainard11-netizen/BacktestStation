"""Compare plugin output to trusted CSV — what's plugin missing?"""
from __future__ import annotations

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
T0 = pd.Timestamp("2024-01-02", tz=TZ)
T1 = pd.Timestamp("2024-01-31 23:59", tz=TZ)
TRUSTED_CSV = (
    Path(__file__).resolve().parent.parent.parent
    / "samples" / "fractal_trusted_multiyear" / "trades.csv"
)


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
        df = pd.read_parquet(f)[["open","high","low","close","volume"]].copy()
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert("America/New_York")
        elif str(df.index.tz) != "America/New_York":
            df.index = df.index.tz_convert("America/New_York")
        pieces.append(df)
    df = pd.concat(pieces).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df = df[(df.index >= t0) & (df.index <= t1)]
    out = []
    for row in df.itertuples():
        ts = row.Index.to_pydatetime() if hasattr(row.Index, "to_pydatetime") else row.Index
        o,h,l,c = float(row.open), float(row.high), float(row.low), float(row.close)
        out.append(Bar(ts_event=ts, symbol=sym, open=o, high=h, low=l, close=c,
                       volume=int(row.volume), trade_count=0, vwap=(o+h+l+c)/4))
    return out


def main():
    nq = _bars("NQ.c.0", T0, T1)
    es = {b.ts_event: b for b in _bars("ES.c.0", T0, T1)}
    ym = {b.ts_event: b for b in _bars("YM.c.0", T0, T1)}

    cfg = FractalAMDTrustedConfig()
    strat = FractalAMDTrusted(cfg)
    rc = RunConfig(
        strategy_name="fractal_amd_trusted",
        symbol="NQ.c.0", timeframe="1m",
        start=str(T0.date()), end=str(T1.date()),
        history_max=2000, aux_symbols=["ES.c.0","YM.c.0"],
        commission_per_contract=0.0, slippage_ticks=0,
        flatten_on_last_bar=False,
    )
    result = engine_run(strat, nq, rc, aux_bars={"ES.c.0":es,"YM.c.0":ym})

    print(f"Plugin trades: {len(result.trades)}")
    plugin_df = pd.DataFrame([
        {"entry_time": t.entry_ts, "direction": "BEARISH" if t.side.value == "short" else "BULLISH",
         "pnl_r": t.r_multiple, "exit_reason": t.exit_reason or ""}
        for t in result.trades
    ])
    if not plugin_df.empty:
        plugin_df["entry_time"] = pd.to_datetime(plugin_df["entry_time"])

    trusted = pd.read_csv(TRUSTED_CSV)
    trusted["entry_time"] = pd.to_datetime(trusted["entry_time"])
    trusted = trusted[(trusted.entry_time >= T0.tz_localize(None)) &
                      (trusted.entry_time <= T1.tz_localize(None))]

    print(f"Trusted trades in window: {len(trusted)}")

    # Compare day-by-day
    plugin_by_day = (
        plugin_df.groupby(plugin_df["entry_time"].dt.date).size()
        if not plugin_df.empty else pd.Series(dtype=int)
    )
    trusted_by_day = trusted.groupby(trusted["entry_time"].dt.date).size()

    print("\nDay-by-day:")
    print(f"{'date':<12} {'plug':>5} {'trust':>5}  diff  trust trades")
    all_days = sorted(set(plugin_by_day.index) | set(trusted_by_day.index))
    for day in all_days:
        p = plugin_by_day.get(day, 0)
        t = trusted_by_day.get(day, 0)
        # List trusted trades on this day
        tr_today = trusted[trusted["entry_time"].dt.date == day]
        tr_str = " ".join(
            f"{ts.strftime('%H:%M')}/{r}/{d[0]}"
            for ts, r, d in zip(tr_today["entry_time"], tr_today["pnl_r"], tr_today["direction"])
        )
        print(f"{str(day):<12} {p:>5} {t:>5}  {p-t:+3d}  {tr_str}")


if __name__ == "__main__":
    main()
