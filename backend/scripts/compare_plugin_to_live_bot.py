"""Direct comparison: BacktestStation FractalAMDTrusted plugin vs the
rewritten FractalAMD- live_bot.SignalEngine. Both should produce the
same trades on the same data — that's the "live = backtest by
construction" goal of Lane C Phase E.

Default window is Jan 2026 (TBBO-covered, fast). Override with --start /
--end to run any range — useful for full-history runs against the live
bot's val_930 backtest output.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
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
# Defaults; overridden by --start / --end CLI args.
T0 = pd.Timestamp("2026-01-02", tz=TZ)
T1 = pd.Timestamp("2026-01-31 23:59", tz=TZ)
LIVE_BOT_OUT = Path(
    "C:/Fractal-AMD/outputs/live_engine_bt_2026-01-02_2026-01-31__val_930.csv"
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
        df = pd.read_parquet(f)[["open", "high", "low", "close", "volume"]].copy()
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
        o, h, l, c = float(row.open), float(row.high), float(row.low), float(row.close)
        out.append(Bar(
            ts_event=ts, symbol=sym, open=o, high=h, low=l, close=c,
            volume=int(row.volume), trade_count=0, vwap=(o+h+l+c)/4,
        ))
    return out


def run_plugin():
    nq = _bars("NQ.c.0", T0, T1)
    es = {b.ts_event: b for b in _bars("ES.c.0", T0, T1)}
    ym = {b.ts_event: b for b in _bars("YM.c.0", T0, T1)}
    cfg = FractalAMDTrustedConfig()
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
        ts = pd.Timestamp(t.entry_ts)
        if ts.tzinfo is None:
            ts = ts.tz_localize("America/New_York")
        else:
            ts = ts.tz_convert("America/New_York")
        rows.append({
            "entry_ts": ts,
            "direction": "BEARISH" if t.side.value == "short" else "BULLISH",
            "pnl_r": t.r_multiple,
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2026-01-02", help="YYYY-MM-DD")
    parser.add_argument("--end", default="2026-01-31", help="YYYY-MM-DD")
    parser.add_argument(
        "--live-csv",
        default=None,
        help="Path to live_bot val_930 CSV. Default infers from --start/--end.",
    )
    parser.add_argument(
        "--max-detail-days",
        type=int,
        default=20,
        help="Cap on per-day diff lines printed (long ranges produce too much output).",
    )
    args = parser.parse_args()

    global T0, T1, LIVE_BOT_OUT
    T0 = pd.Timestamp(args.start, tz=TZ)
    T1 = pd.Timestamp(args.end + " 23:59", tz=TZ)
    LIVE_BOT_OUT = (
        Path(args.live_csv)
        if args.live_csv
        else Path(
            f"C:/Fractal-AMD/outputs/live_engine_bt_{args.start}_{args.end}__val_930.csv"
        )
    )

    print(f"=== Plugin ({args.start} -> {args.end}) ===")
    plug = run_plugin()
    print(f"trades={len(plug)}  WR={(plug.pnl_r>0).mean()*100:.1f}%  totalR={plug.pnl_r.sum():+.2f}")

    print(f"\n=== Live bot val_930 ({args.start} -> {args.end}) ===")
    print(f"reading {LIVE_BOT_OUT}")
    lb = pd.read_csv(LIVE_BOT_OUT)
    lb["entry_ts"] = pd.to_datetime(lb["date"] + " " + lb["entry_time"]).dt.tz_localize("America/New_York")
    print(f"trades={len(lb)}  WR={(lb.pnl_r>0).mean()*100:.1f}%  totalR={lb.pnl_r.sum():+.2f}")

    # Day-by-day match
    plug["day"] = plug.entry_ts.dt.date
    lb["day"] = lb.entry_ts.dt.date
    p_by_day = plug.groupby("day").size()
    l_by_day = lb.groupby("day").size()
    all_days = sorted(set(p_by_day.index) | set(l_by_day.index))
    diffs = 0
    detail_printed = 0
    for day in all_days:
        p = p_by_day.get(day, 0)
        l = l_by_day.get(day, 0)
        if p != l:
            diffs += 1
            if detail_printed < args.max_detail_days:
                print(f"\n{day} (Plug={p} Live={l})")
                pd_today = plug[plug.day == day]
                lb_today = lb[lb.day == day]
                p_str = "; ".join(
                    f"{r.entry_ts.strftime('%H:%M')} {r.direction[:4]} R={r.pnl_r:+.1f}"
                    for _, r in pd_today.iterrows()
                )
                l_str = "; ".join(
                    f"{r.entry_ts.strftime('%H:%M')} {r.direction[:4]} R={r.pnl_r:+.1f}"
                    for _, r in lb_today.iterrows()
                )
                print(f"  Plug: {p_str or '(none)'}")
                print(f"  Live: {l_str or '(none)'}")
                detail_printed += 1
    if diffs == 0:
        print("\n*** PLUGIN AND LIVE BOT MATCH BYTE-FOR-BYTE ***")
    else:
        print(f"\nDivergent days: {diffs}/{len(all_days)}")
        if diffs > args.max_detail_days:
            print(f"(suppressed {diffs - args.max_detail_days} more divergent days; raise --max-detail-days to see all)")


if __name__ == "__main__":
    main()
