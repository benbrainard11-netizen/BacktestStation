"""Test strategy variants on the full 2024-01 → 2026-01 window.

Goal: find a no-lookahead variant that preserves enough of the trusted
edge to be deployable. Tests four (entry_delay, co_lookahead)
combinations:

  | label                | delay | lookahead | what it represents        |
  |----------------------|-------|-----------|---------------------------|
  | trusted_lookahead    |   0   |   True    | trusted-faithful baseline |
  | enter_now_no_la      |   0   |   False   | live's no-lookahead reality |
  | wait1_no_la          |   1   |   False   | wait one bar, score T+1 (closed) |
  | wait1_lookahead      |   1   |   True    | wait one bar, score T+2 (lookahead) |

The hypothesis: `wait1_no_la` lets the strategy see the same bar as
`trusted_lookahead` (= T+1 of touch) but without lookahead, at the cost
of one bar of price drift between T+1.open and T+2.open. If that drift
is small relative to typical risk, most of the +356R lookahead-edge
should survive.
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
T0 = pd.Timestamp(os.environ.get("VARIANT_T0", "2024-01-02"), tz=TZ)
T1 = pd.Timestamp(os.environ.get("VARIANT_T1", "2026-01-31") + " 23:59", tz=TZ)


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
    out = []
    for row in df.itertuples():
        ts = row.Index.to_pydatetime() if hasattr(row.Index, "to_pydatetime") else row.Index
        o, h, l, c = float(row.open), float(row.high), float(row.low), float(row.close)
        out.append(Bar(
            ts_event=ts, symbol=sym, open=o, high=h, low=l, close=c,
            volume=int(row.volume), trade_count=0, vwap=(o + h + l + c) / 4,
        ))
    return out


def run_variant(label: str, *, entry_delay_bars: int, co_lookahead: bool):
    nq = _bars("NQ.c.0", T0, T1)
    es = {b.ts_event: b for b in _bars("ES.c.0", T0, T1)}
    ym = {b.ts_event: b for b in _bars("YM.c.0", T0, T1)}
    cfg = FractalAMDTrustedConfig(
        entry_delay_bars=entry_delay_bars,
        co_lookahead=co_lookahead,
    )
    strat = FractalAMDTrusted(cfg)
    rc = RunConfig(
        strategy_name="fractal_amd_trusted",
        symbol="NQ.c.0", timeframe="1m",
        start=str(T0.date()), end=str(T1.date()),
        history_max=2000, aux_symbols=["ES.c.0", "YM.c.0"],
        commission_per_contract=0.0, slippage_ticks=0,
        flatten_on_last_bar=False,
    )
    result = engine_run(strat, nq, rc, aux_bars={"ES.c.0": es, "YM.c.0": ym})
    rows = []
    for t in result.trades:
        rows.append({
            "entry_ts": pd.Timestamp(t.entry_ts),
            "direction": "BEARISH" if t.side.value == "short" else "BULLISH",
            "pnl_r": t.r_multiple,
        })
    df = pd.DataFrame(rows)
    n = len(df)
    if n == 0:
        return {"label": label, "n": 0, "wr": 0.0, "total_r": 0.0, "avg_r": 0.0, "max_dd": 0.0}
    wr = (df.pnl_r > 0).mean() * 100
    total_r = df.pnl_r.sum()
    cum = df.pnl_r.cumsum()
    peak = cum.cummax()
    dd = (cum - peak).min()
    return {
        "label": label, "n": n, "wr": wr, "total_r": total_r,
        "avg_r": total_r / n, "max_dd": -dd,
    }


def main():
    print(f"=== Strategy variants on {T0.date()} → {T1.date()} ===\n")
    configs = [
        ("trusted_lookahead", 0, True),
        ("enter_now_no_la",   0, False),
        ("wait1_no_la",       1, False),
        ("wait1_lookahead",   1, True),
    ]
    rows = []
    for label, delay, lookahead in configs:
        print(f">>> running {label} (delay={delay}, lookahead={lookahead})...")
        r = run_variant(label, entry_delay_bars=delay, co_lookahead=lookahead)
        rows.append(r)
        print(f"   n={r['n']}  WR={r['wr']:.1f}%  totalR={r['total_r']:+.1f}  "
              f"avgR={r['avg_r']:+.2f}  maxDD={r['max_dd']:.1f}R")

    print("\n" + "=" * 80)
    print(f"{'variant':<20} {'trades':>8} {'WR%':>8} {'totalR':>10} {'avgR':>8} {'maxDD':>8}")
    print("-" * 80)
    for r in rows:
        print(
            f"{r['label']:<20} {r['n']:>8} {r['wr']:>7.1f}% "
            f"{r['total_r']:>+9.1f} {r['avg_r']:>+7.2f} {r['max_dd']:>7.1f}"
        )


if __name__ == "__main__":
    main()
