"""Rank ALL detectors in the warehouse by tradable edge.

For each (feature_name, event_type, side, symbol):
  - Pull all events from research_events parquet
  - For each event: simulate a v8a-style fill on subsequent 1m bars
    (entry = reference_close, stop = 2x ATR(5m) below/above, target = 5x ATR,
    time-stop = 240 min, conservative stop-wins-on-ambiguous)
  - Compute R-multiple per event
  - Aggregate: count, win_rate, avg_R, sum_R, median_R

Output: STRATEGY_DISCOVERY.md with sorted top-N table + per-detector breakdown.

Caveats logged:
  - Detectors without thesis_direction in outcomes skipped (need per-detector
    direction inference)
  - Sample-size threshold: only modes with >= 30 events shown in top list
  - Uses NQ.c.0 first; can extend to full universe after
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
BARS_ROOT = Path(r"D:/data/processed/bars/timeframe=1m")
RESEARCH_PARQUET = Path(r"C:/Users/benbr/BacktestStation/data/research_events")

SYMBOL = "NQ.c.0"
ATR_PERIOD = 14
ATR_TIMEFRAME_MIN = 5  # 5m primary ATR
ATR_FLOOR_MIN = 30     # 30m floor ATR
STOP_MULT = 2.0
FLOOR_STOP_MULT = 1.5
TARGET_MULT = 5.0
MAX_HOLD_MIN = 240
MIN_RISK_PTS = 1.0
MAX_RISK_PTS = 80.0

# Detectors that have BOTH thesis_direction + reference_close populated
SUPPORTED_DETECTORS = [
    "order_block",
    "fvg_formation",
    "displacement_candle",
    "swing_pivot",
    "time_profile",
]


def load_bars_for_dates(symbol: str, dates: set[dt.date]) -> pd.DataFrame:
    """Load 1m bars for the given dates. Returns indexed by ts_event UTC."""
    dfs = []
    for d in sorted(dates):
        p = BARS_ROOT / f"symbol={symbol}" / f"date={d.isoformat()}" / "part-000.parquet"
        if p.exists():
            dfs.append(pd.read_parquet(p))
    if not dfs:
        return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True)
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    df = df.sort_values("ts_event").set_index("ts_event")
    return df


def compute_atr(bars_1m: pd.DataFrame, tf_min: int, period: int) -> pd.Series:
    """Compute Wilder ATR on tf_min HTF bars built from the 1m frame."""
    # Resample 1m to tf_min
    htf = bars_1m.resample(f"{tf_min}min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()
    htf["prev_close"] = htf["close"].shift(1)
    htf["tr"] = pd.concat([
        htf["high"] - htf["low"],
        (htf["high"] - htf["prev_close"]).abs(),
        (htf["low"] - htf["prev_close"]).abs(),
    ], axis=1).max(axis=1)
    # Wilder ATR = EMA with alpha = 1/period
    atr = htf["tr"].ewm(alpha=1 / period, adjust=False).mean()
    return atr


def simulate_fill(
    event_ts: dt.datetime,
    reference_close: float,
    thesis_direction: str,  # "up" | "down"
    bars_1m: pd.DataFrame,
    atr_5m: pd.Series,
    atr_30m: pd.Series,
) -> dict | None:
    """Simulate a v8a-style trade from event_ts forward. Returns dict with
    r_multiple, exit_reason, bars_held, or None if not enough forward data."""
    # Find ATR at event time (most recent value at-or-before event_ts)
    atr_p = atr_5m.asof(event_ts)
    atr_f = atr_30m.asof(event_ts)
    if pd.isna(atr_p) or pd.isna(atr_f) or atr_p <= 0 or atr_f <= 0:
        return None
    stop_distance = max(STOP_MULT * atr_p, FLOOR_STOP_MULT * atr_f)
    target_distance = TARGET_MULT * atr_p
    if stop_distance < MIN_RISK_PTS or stop_distance > MAX_RISK_PTS:
        return None
    sign = 1.0 if thesis_direction == "up" else -1.0
    entry = float(reference_close)
    stop_px = entry - sign * stop_distance
    target_px = entry + sign * target_distance
    # Forward bars window: event_ts + 1 min through event_ts + MAX_HOLD_MIN
    end_ts = event_ts + dt.timedelta(minutes=MAX_HOLD_MIN)
    window = bars_1m.loc[
        (bars_1m.index > event_ts) & (bars_1m.index <= end_ts)
    ]
    if window.empty:
        return None
    for i, (ts, row) in enumerate(window.iterrows()):
        stop_hit = (row["low"] <= stop_px) if sign > 0 else (row["high"] >= stop_px)
        target_hit = (row["high"] >= target_px) if sign > 0 else (row["low"] <= target_px)
        if stop_hit and target_hit:
            exit_px = stop_px
            reason = "stop_ambiguous"
        elif stop_hit:
            exit_px, reason = stop_px, "stop"
        elif target_hit:
            exit_px, reason = target_px, "target"
        else:
            continue
        r = sign * (exit_px - entry) / stop_distance
        return {"r_multiple": r, "exit_reason": reason, "bars_held": i + 1}
    # Time-stopped: exit at last bar close
    last = window.iloc[-1]
    r = sign * (float(last["close"]) - entry) / stop_distance
    return {
        "r_multiple": r, "exit_reason": "time_stop",
        "bars_held": len(window),
    }


def main():
    print(f"=== rank_detectors_by_edge ===")
    print(f"Symbol: {SYMBOL}")
    print(f"v8a fill: stop=max({STOP_MULT}x5mATR, {FLOOR_STOP_MULT}x30mATR), "
          f"target={TARGET_MULT}x5mATR, time-stop={MAX_HOLD_MIN}m")
    print()

    # Load ALL 1m bars for NQ (needed for ATR + fill sim)
    print("Loading all NQ 1m bars (this is the heavy step)...")
    all_dates = sorted([
        dt.date.fromisoformat(p.name.replace("date=", ""))
        for p in (BARS_ROOT / f"symbol={SYMBOL}").iterdir()
        if p.name.startswith("date=")
    ])
    print(f"  {len(all_dates)} date partitions available")
    bars_1m = load_bars_for_dates(SYMBOL, set(all_dates))
    print(f"  loaded {len(bars_1m):,} 1m bars  ({bars_1m.index.min()} to {bars_1m.index.max()})")
    print()
    print("Precomputing ATR(14) on 5m and 30m...")
    atr_5m = compute_atr(bars_1m, ATR_TIMEFRAME_MIN, ATR_PERIOD)
    atr_30m = compute_atr(bars_1m, ATR_FLOOR_MIN, ATR_PERIOD)
    print(f"  atr_5m points: {len(atr_5m):,}, atr_30m points: {len(atr_30m):,}")
    print()

    con = duckdb.connect()

    # Aggregate results
    results: dict[tuple, list[float]] = defaultdict(list)
    exit_counts: dict[tuple, dict] = defaultdict(lambda: defaultdict(int))

    for feat in SUPPORTED_DETECTORS:
        print(f"--- {feat} ---")
        sql = f"""
            SELECT bar_end_utc, event_type, side, outcomes
            FROM read_parquet('{RESEARCH_PARQUET.as_posix()}/feature_name={feat}/event_year=*/*.parquet')
            WHERE primary_symbol = '{SYMBOL}'
            AND json_extract(outcomes, '$.thesis_direction') IS NOT NULL
            AND json_extract(outcomes, '$.reference_close') IS NOT NULL
        """
        rows = con.execute(sql).fetchall()
        print(f"  {len(rows):,} events with thesis_direction + reference_close")
        n_processed = 0
        n_no_atr = 0
        n_no_forward = 0
        for bar_end_utc, event_type, side, outcomes_json in rows:
            try:
                outcomes = json.loads(outcomes_json)
                thesis = outcomes.get("thesis_direction")
                ref_close = outcomes.get("reference_close")
                if thesis not in ("up", "down") or ref_close is None:
                    continue
                # Normalize event_ts to a pd.Timestamp UTC
                if isinstance(bar_end_utc, str):
                    event_ts = pd.Timestamp(bar_end_utc, tz="UTC")
                else:
                    event_ts = pd.Timestamp(bar_end_utc).tz_localize("UTC") \
                        if bar_end_utc.tzinfo is None else pd.Timestamp(bar_end_utc)
                fill = simulate_fill(
                    event_ts=event_ts,
                    reference_close=float(ref_close),
                    thesis_direction=thesis,
                    bars_1m=bars_1m,
                    atr_5m=atr_5m,
                    atr_30m=atr_30m,
                )
                if fill is None:
                    n_no_atr += 1
                    continue
                key = (feat, event_type, side)
                results[key].append(fill["r_multiple"])
                exit_counts[key][fill["exit_reason"]] += 1
                n_processed += 1
            except Exception:
                continue
        print(f"  filled: {n_processed:,}  rejected (atr/risk): {n_no_atr:,}")

    # Build summary table
    summary_rows = []
    for (feat, etype, side), rs in results.items():
        if not rs:
            continue
        n = len(rs)
        wins = sum(1 for r in rs if r > 0)
        avg_r = sum(rs) / n
        sum_r = sum(rs)
        win_rate = wins / n
        median_r = sorted(rs)[n // 2]
        exits = dict(exit_counts[(feat, etype, side)])
        summary_rows.append({
            "feature": feat,
            "event_type": etype,
            "side": side,
            "n_trades": n,
            "win_rate": win_rate,
            "avg_R": avg_r,
            "sum_R": sum_r,
            "median_R": median_r,
            "target_pct": exits.get("target", 0) / n,
            "stop_pct": (exits.get("stop", 0) + exits.get("stop_ambiguous", 0)) / n,
            "time_pct": exits.get("time_stop", 0) / n,
        })

    summary = pd.DataFrame(summary_rows)
    summary = summary.sort_values("sum_R", ascending=False)
    # Save
    out_csv = REPO_ROOT / "STRATEGY_DISCOVERY_layer1_raw.csv"
    summary.to_csv(out_csv, index=False)
    print()
    print(f"Wrote {out_csv}")
    print()

    # Print top + bottom
    print("=" * 110)
    print(f"TOP 25 by sum_R (n >= 30):")
    print(f"  {'feature':<20s} {'event_type':<22s} {'side':<8s} {'n':>6s} {'win%':>6s} {'avg_R':>8s} {'sum_R':>10s} {'tgt%':>6s}")
    big_enough = summary[summary["n_trades"] >= 30]
    for _, r in big_enough.head(25).iterrows():
        print(f"  {r['feature']:<20s} {r['event_type']:<22s} {r['side']:<8s} "
              f"{int(r['n_trades']):>6,} {r['win_rate']*100:>5.1f}% "
              f"{r['avg_R']:>+8.3f} {r['sum_R']:>+10.1f} "
              f"{r['target_pct']*100:>5.1f}%")
    print()
    print(f"BOTTOM 10 by sum_R (n >= 30) -- worst:")
    for _, r in big_enough.tail(10).iterrows():
        print(f"  {r['feature']:<20s} {r['event_type']:<22s} {r['side']:<8s} "
              f"{int(r['n_trades']):>6,} {r['win_rate']*100:>5.1f}% "
              f"{r['avg_R']:>+8.3f} {r['sum_R']:>+10.1f} "
              f"{r['target_pct']*100:>5.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
