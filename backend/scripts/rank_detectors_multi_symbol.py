"""Multi-asset validation: run Layer 1 R-multiple analysis across symbols.

For each symbol in TEST_SYMBOLS, load bars + ATRs, then simulate v8a-style
fills on every research event with thesis_direction + reference_close.
Aggregate per (symbol, feature, event_type, side).

Headline question: does swing_pivot's edge (~+0.3 R/trade on NQ) hold up
across other futures (ES, YM, RTY, CL, GC, 6E)?

If yes across most → universal pattern, port to streaming SM with high
confidence.
If only NQ → NQ-specific quirk, dig deeper before deploying.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
BARS_ROOT = Path(r"D:/data/processed/bars/timeframe=1m")
RESEARCH_PARQUET = Path(r"C:/Users/benbr/BacktestStation/data/research_events")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rank_detectors_by_edge import (  # noqa: E402
    SUPPORTED_DETECTORS, load_bars_for_dates, compute_atr, simulate_fill,
    ATR_TIMEFRAME_MIN, ATR_FLOOR_MIN, ATR_PERIOD,
)

TEST_SYMBOLS = [
    "ES.c.0",   # E-mini S&P 500 (equity index, most liquid)
    "YM.c.0",   # E-mini Dow (equity index)
    "RTY.c.0",  # E-mini Russell 2000 (small-cap, different character)
    "CL.c.0",   # Crude oil (different asset class)
    "GC.c.0",   # Gold (different asset class)
    "6E.c.0",   # Euro FX (different asset class)
]


def run_one_symbol(symbol: str) -> pd.DataFrame:
    print(f"=" * 70)
    print(f"=== {symbol} ===")
    print(f"=" * 70)
    print("Loading bars...")
    all_dates = sorted([
        dt.date.fromisoformat(p.name.replace("date=", ""))
        for p in (BARS_ROOT / f"symbol={symbol}").iterdir()
        if p.name.startswith("date=")
    ])
    bars_1m = load_bars_for_dates(symbol, set(all_dates))
    print(f"  {len(bars_1m):,} 1m bars  ({bars_1m.index.min()} to {bars_1m.index.max()})")
    print("Computing ATRs...")
    atr_5m = compute_atr(bars_1m, ATR_TIMEFRAME_MIN, ATR_PERIOD)
    atr_30m = compute_atr(bars_1m, ATR_FLOOR_MIN, ATR_PERIOD)

    con = duckdb.connect()
    results: dict[tuple, list[float]] = defaultdict(list)
    for feat in SUPPORTED_DETECTORS:
        sql = f"""
            SELECT bar_end_utc, event_type, side, outcomes
            FROM read_parquet('{RESEARCH_PARQUET.as_posix()}/feature_name={feat}/event_year=*/*.parquet')
            WHERE primary_symbol = '{symbol}'
            AND json_extract(outcomes, '$.thesis_direction') IS NOT NULL
            AND json_extract(outcomes, '$.reference_close') IS NOT NULL
        """
        events = con.execute(sql).fetchall()
        n_filled = 0
        for bar_end_utc, event_type, side, outcomes_json in events:
            try:
                out = json.loads(outcomes_json)
                thesis = out.get("thesis_direction")
                ref = out.get("reference_close")
                if thesis not in ("up", "down") or ref is None:
                    continue
                ts = pd.Timestamp(bar_end_utc, tz="UTC") if isinstance(bar_end_utc, str) \
                    else (pd.Timestamp(bar_end_utc).tz_localize("UTC") if bar_end_utc.tzinfo is None
                          else pd.Timestamp(bar_end_utc))
                fill = simulate_fill(ts, float(ref), thesis, bars_1m, atr_5m, atr_30m)
                if fill is None:
                    continue
                results[(feat, event_type, side)].append(fill["r_multiple"])
                n_filled += 1
            except Exception:
                continue
        print(f"  {feat:<22s} {n_filled:>7,} filled (of {len(events):>7,} events)")

    # Build DataFrame
    rows = []
    for (feat, etype, side), rs in results.items():
        if not rs:
            continue
        n = len(rs)
        rows.append({
            "symbol": symbol,
            "feature": feat, "event_type": etype, "side": side,
            "n_trades": n,
            "win_rate": sum(1 for r in rs if r > 0) / n,
            "avg_R": sum(rs) / n,
            "sum_R": sum(rs),
        })
    return pd.DataFrame(rows)


def main():
    all_results = []
    for sym in TEST_SYMBOLS:
        all_results.append(run_one_symbol(sym))

    combined = pd.concat(all_results, ignore_index=True)
    out_path = REPO_ROOT / "STRATEGY_DISCOVERY_multi_symbol.csv"
    combined.to_csv(out_path, index=False)
    print()
    print(f"Wrote {out_path}")
    print()

    # Focus on the top-edge NQ modes: do they hold elsewhere?
    swing_pivots = combined[
        (combined["feature"] == "swing_pivot")
        & (combined["event_type"].isin(["pivot_3_1h", "pivot_5_1h"]))
        & (combined["n_trades"] >= 500)
    ].copy()
    swing_pivots["mode"] = swing_pivots["event_type"] + "/" + swing_pivots["side"]

    # Pivot table: rows = mode, cols = symbol, values = avg_R
    pivot = swing_pivots.pivot_table(
        index="mode", columns="symbol", values="avg_R", aggfunc="first"
    )
    print("=" * 90)
    print("SWING PIVOT avg_R BY SYMBOL (n>=500 trades):")
    print("=" * 90)
    print(pivot.round(3).to_string())
    print()

    pivot_win = swing_pivots.pivot_table(
        index="mode", columns="symbol", values="win_rate", aggfunc="first"
    )
    print("=" * 90)
    print("SWING PIVOT win_rate BY SYMBOL (n>=500 trades):")
    print("=" * 90)
    print((pivot_win * 100).round(1).to_string())
    print()

    pivot_n = swing_pivots.pivot_table(
        index="mode", columns="symbol", values="n_trades", aggfunc="first"
    )
    print("=" * 90)
    print("SWING PIVOT n_trades BY SYMBOL:")
    print("=" * 90)
    print(pivot_n.astype(int).to_string())
    print()

    # Also show fvg_15m_bullish and the OB family for context
    other_top = combined[
        (
            ((combined["feature"] == "fvg_formation") & (combined["event_type"] == "15m_fvg"))
            | (combined["feature"] == "order_block")
        )
        & (combined["n_trades"] >= 100)
    ].copy()
    other_top["mode"] = (
        other_top["feature"] + "/" + other_top["event_type"]
        + "/" + other_top["side"]
    )
    pivot_other = other_top.pivot_table(
        index="mode", columns="symbol", values="avg_R", aggfunc="first"
    )
    print("=" * 90)
    print("OTHER detectors avg_R BY SYMBOL (n>=100):")
    print("=" * 90)
    print(pivot_other.round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
