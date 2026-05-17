"""TBBO-aware trade exit resolver.

Replays a v8a-shape trade against the actual trade tape (Databento TBBO) to
produce an honest exit. Compares to the 1m simulator output to surface
discount factor.

Public API:
  TbboCache  : lazy loader for D:/data/raw/databento/tbbo/symbol=X/date=Y/part.parquet
  resolve_trade(trade_row, tbbo, ...) -> dict
      Returns a record with tbbo-derived entry/exit/pnl_r alongside the
      original 1m values.

Notes:
  - TBBO data is trade prints (action='T') with full bid/ask state at each
    print. ~466K prints/day for ES.
  - Resolution: walk prints in ts_event order; first level reached wins.
  - Entry slippage: pay ask (long) or hit bid (short) at first print after
    confirmation bar end.
  - Stop slippage: market exit = next print after stop trigger (adverse).
  - Target: limit fill at target_price IF any print at-or-beyond target_price
    happened in the trade direction. Optimistic on queue position but
    realistic on whether the price was even touched.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

TBBO_ROOT = Path(r"D:/data/raw/databento/tbbo")


class TbboCache:
    """Lazy loader keyed by (symbol, date_str)."""

    def __init__(self):
        self._cache: dict[tuple[str, str], pd.DataFrame] = {}

    def _load(self, symbol: str, date_str: str) -> pd.DataFrame:
        key = (symbol, date_str)
        if key in self._cache:
            return self._cache[key]
        path = TBBO_ROOT / f"symbol={symbol}" / f"date={date_str}" / "part-000.parquet"
        if not path.exists():
            df = pd.DataFrame(columns=["ts_event", "price", "size", "side",
                                        "bid_px", "ask_px", "bid_sz", "ask_sz"])
        else:
            df = pd.read_parquet(path, columns=["ts_event", "action", "price", "size", "side",
                                                  "bid_px", "ask_px", "bid_sz", "ask_sz"])
            df = df[df["action"] == "T"].copy()
            df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
            df = df.sort_values("ts_event").reset_index(drop=True)
        self._cache[key] = df
        return df

    def get_window(self, symbol: str, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> pd.DataFrame:
        """Return all prints between start_ts and end_ts. Spans date boundary if needed."""
        start = pd.Timestamp(start_ts, tz="UTC") if start_ts.tzinfo is None else start_ts
        end = pd.Timestamp(end_ts, tz="UTC") if end_ts.tzinfo is None else end_ts
        dates_needed = []
        cur = start.date()
        while cur <= end.date():
            dates_needed.append(cur.isoformat())
            cur = (pd.Timestamp(cur) + pd.Timedelta(days=1)).date()
        frames = [self._load(symbol, d) for d in dates_needed]
        nonempty = [f for f in frames if not f.empty]
        if not nonempty:
            return pd.DataFrame()
        combined = pd.concat(nonempty, ignore_index=True)
        mask = (combined["ts_event"] >= start) & (combined["ts_event"] <= end)
        return combined[mask].reset_index(drop=True)


@dataclass
class ResolvedTrade:
    """TBBO-resolved trade record."""
    entry_ts_tbbo: pd.Timestamp | None
    entry_price_tbbo: float | None
    exit_ts_tbbo: pd.Timestamp | None
    exit_price_tbbo: float | None
    exit_reason_tbbo: str
    pnl_r_tbbo: float | None
    target_hit_ts: pd.Timestamp | None
    stop_hit_ts: pd.Timestamp | None
    note: str = ""


def resolve_trade(
    trade: dict,
    tbbo: TbboCache,
    *,
    confirm_window_min: int = 60,
    trade_window_min: int = 240,
) -> dict:
    """Replay one v8a trade against TBBO. Returns ResolvedTrade fields as a dict."""
    symbol = trade["symbol"]
    fire_ts = pd.to_datetime(trade["fire_ts"], utc=True)
    direction = trade["direction"]
    stop_price = float(trade["stop_price"]) if trade.get("stop_price") is not None else None
    target_price = float(trade["target_price"]) if trade.get("target_price") is not None else None
    entry_price_1m = float(trade["entry_price"]) if trade.get("entry_price") is not None else None

    if stop_price is None or target_price is None or entry_price_1m is None:
        return _empty_resolved("missing_fields")

    # Window: confirmation + trade
    window_start = fire_ts
    window_end = fire_ts + pd.Timedelta(minutes=confirm_window_min + trade_window_min)
    prints = tbbo.get_window(symbol, window_start, window_end)
    if prints.empty:
        return _empty_resolved("no_tbbo_data")

    # Entry: first print AFTER the trade's recorded entry_ts (confirmation bar already happened)
    entry_ts_1m = pd.to_datetime(trade["entry_ts"], utc=True) if trade.get("entry_ts") else fire_ts
    entry_prints = prints[prints["ts_event"] >= entry_ts_1m]
    if entry_prints.empty:
        return _empty_resolved("no_prints_after_entry")
    first_print = entry_prints.iloc[0]
    # Cross the spread on entry
    if direction == "long":
        entry_price_tbbo = float(first_print["ask_px"]) if pd.notna(first_print["ask_px"]) else float(first_print["price"])
    else:
        entry_price_tbbo = float(first_print["bid_px"]) if pd.notna(first_print["bid_px"]) else float(first_print["price"])
    entry_ts_tbbo = first_print["ts_event"]

    # Determine stop_distance for R-scaling (matches the 1m simulator's interpretation)
    stop_distance = abs(entry_price_tbbo - stop_price)
    if stop_distance == 0:
        return _empty_resolved("zero_stop_distance")

    # Walk post-entry prints looking for stop or target hit
    post_entry = entry_prints.iloc[1:]  # skip the entry print itself
    target_hit_ts = None
    stop_hit_ts = None

    if direction == "long":
        # Target = price >= target_price; stop = price <= stop_price
        target_hits = post_entry[post_entry["price"] >= target_price]
        stop_hits = post_entry[post_entry["price"] <= stop_price]
    else:
        target_hits = post_entry[post_entry["price"] <= target_price]
        stop_hits = post_entry[post_entry["price"] >= stop_price]

    if not target_hits.empty:
        target_hit_ts = target_hits.iloc[0]["ts_event"]
    if not stop_hits.empty:
        stop_hit_ts = stop_hits.iloc[0]["ts_event"]

    # Determine which came first
    if target_hit_ts is not None and (stop_hit_ts is None or target_hit_ts < stop_hit_ts):
        exit_reason_tbbo = "target"
        exit_price_tbbo = target_price  # limit fills at exact target price (optimistic on queue)
        exit_ts_tbbo = target_hit_ts
    elif stop_hit_ts is not None:
        exit_reason_tbbo = "stop"
        # Stop slippage: market exit = next print after stop trigger
        stop_idx = stop_hits.index[0]
        if stop_idx + 1 < len(post_entry):
            next_print = post_entry.loc[stop_idx + 1]
            exit_price_tbbo = float(next_print["price"])
        else:
            exit_price_tbbo = stop_price  # fallback if no next print
        exit_ts_tbbo = stop_hit_ts
    else:
        # Time exit at window end — use midpoint of last bid/ask
        last_print = post_entry.iloc[-1] if not post_entry.empty else first_print
        bid = last_print["bid_px"]; ask = last_print["ask_px"]
        if pd.notna(bid) and pd.notna(ask):
            exit_price_tbbo = float((bid + ask) / 2)
        else:
            exit_price_tbbo = float(last_print["price"])
        exit_ts_tbbo = last_print["ts_event"]
        exit_reason_tbbo = "time_exit"

    # PnL in R units
    if direction == "long":
        pnl_r_tbbo = (exit_price_tbbo - entry_price_tbbo) / stop_distance
    else:
        pnl_r_tbbo = (entry_price_tbbo - exit_price_tbbo) / stop_distance

    return {
        "entry_ts_tbbo": entry_ts_tbbo,
        "entry_price_tbbo": entry_price_tbbo,
        "exit_ts_tbbo": exit_ts_tbbo,
        "exit_price_tbbo": exit_price_tbbo,
        "exit_reason_tbbo": exit_reason_tbbo,
        "pnl_r_tbbo": pnl_r_tbbo,
        "target_hit_ts": target_hit_ts,
        "stop_hit_ts": stop_hit_ts,
        "note": "",
    }


def _empty_resolved(reason: str) -> dict:
    return {
        "entry_ts_tbbo": None, "entry_price_tbbo": None,
        "exit_ts_tbbo": None, "exit_price_tbbo": None,
        "exit_reason_tbbo": "skip",
        "pnl_r_tbbo": None, "target_hit_ts": None, "stop_hit_ts": None,
        "note": reason,
    }
