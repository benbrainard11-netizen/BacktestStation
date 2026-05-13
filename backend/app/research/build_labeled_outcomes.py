"""Build labeled trade-outcomes dataset from pre10 paper logs + FractalAMD live trades.

Output: D:\\data\\research\\labeled_outcomes\\trades_v1.parquet

Each row = one trade with:
  - features available at signal time (bar context, time-of-day, vol regime, etc.)
  - outcome label (realized R, exit reason, MFE/MAE, A/B/C/D quality bucket)
  - source/strategy provenance

This is the spine for future ML work (setup-quality classifier, outcome model,
regime classifier). Idempotent — re-running rebuilds cleanly.

Sources:
  - pre10_paper_log.jsonl  (paired entry/exit events, has p_up_router)
  - trades.jsonl           (FractalAMD live trades, has rof_score)

Bar context comes from `C:/Fractal-AMD/data/raw/NQ_ohlcv-1m_2026.parquet`.
Trades outside the bar parquet date range are emitted with bar-derived
features as NaN — flagged via `bars_available=False`.

CLI:
    python -m app.research.build_labeled_outcomes
    python -m app.research.build_labeled_outcomes --dry-run
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

ET = ZoneInfo("America/New_York")

REPO_ROOT = Path(r"C:\Users\benbr\BacktestStation")
PRE10_PAPER_LOG = Path(r"C:\Users\benbr\FractalAMD-\production\pre10_paper_log.jsonl")
FRACTALAMD_TRADES = Path(r"C:\Users\benbr\FractalAMD-\production\trades.jsonl")
NQ_BARS_PARQUET = Path(r"C:\Fractal-AMD\data\raw\NQ_ohlcv-1m_2026.parquet")

OUTPUT_ROOT = Path(r"D:\data\research\labeled_outcomes")
OUTPUT_PARQUET = OUTPUT_ROOT / "trades_v1.parquet"
OUTPUT_SUMMARY = OUTPUT_ROOT / "trades_v1_summary.json"

NQ_TICK_VALUE = 0.25
NQ_DOLLAR_PER_POINT = 20.0  # full NQ; MNQ is 2.0


# ---------- bar loading ---------------------------------------------------


def load_nq_1m_bars(parquet: Path = NQ_BARS_PARQUET) -> pd.DataFrame:
    """Load 1m NQ bars indexed by UTC ts. Adds an ET timestamp column."""
    if not parquet.exists():
        raise FileNotFoundError(f"missing bar parquet: {parquet}")
    df = pd.read_parquet(parquet)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df = df.sort_index()
    # ET timestamp for filtering / RTH math
    df["ts_et"] = df.index.tz_convert(ET)
    df["date_et"] = df["ts_et"].dt.date
    df["minute_of_day_et"] = df["ts_et"].dt.hour * 60 + df["ts_et"].dt.minute
    return df


# ---------- pre10 paper log → paired trades --------------------------------


def load_pre10_paper_pairs() -> list[dict[str, Any]]:
    """Walk pre10_paper_log.jsonl, pair entry/trail/exit events into trades."""
    if not PRE10_PAPER_LOG.exists():
        return []
    events: list[dict] = []
    for line in PRE10_PAPER_LOG.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))

    trades: list[dict] = []
    pending: dict | None = None
    for ev in events:
        kind = ev.get("kind")
        if kind == "entry":
            pending = {"entry": ev, "trails": [], "exit": None}
        elif kind == "trail" and pending is not None:
            pending["trails"].append(ev)
        elif kind == "exit" and pending is not None:
            pending["exit"] = ev
            trades.append(pending)
            pending = None
    return trades


# ---------- FractalAMD trades.jsonl ---------------------------------------


def load_fractalamd_trades() -> list[dict[str, Any]]:
    if not FRACTALAMD_TRADES.exists():
        return []
    out: list[dict] = []
    for line in FRACTALAMD_TRADES.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


# ---------- feature extraction --------------------------------------------


@dataclass(slots=True)
class BarContext:
    bar_available: bool
    bar_open: float | None = None
    bar_high: float | None = None
    bar_low: float | None = None
    bar_close: float | None = None
    bar_volume: float | None = None
    atr_5: float | None = None
    atr_15: float | None = None
    prior_5bar_return_pts: float | None = None
    prior_15bar_return_pts: float | None = None
    range_from_rth_open_pts: float | None = None
    session_high_at_signal: float | None = None
    session_low_at_signal: float | None = None
    distance_from_session_high_pts: float | None = None
    distance_from_session_low_pts: float | None = None
    rth_volume_to_signal: float | None = None


def compute_bar_context(bars: pd.DataFrame, signal_ts_utc: pd.Timestamp) -> BarContext:
    """Compute features at signal_ts_utc (UTC, tz-aware) using only bars at or
    before that timestamp — strict no-leakage."""
    if signal_ts_utc not in bars.index:
        # try the floor-to-minute fallback
        floored = signal_ts_utc.floor("1min")
        if floored not in bars.index:
            return BarContext(bar_available=False)
        signal_ts_utc = floored

    sig = bars.loc[signal_ts_utc]
    ctx = BarContext(
        bar_available=True,
        bar_open=float(sig["open"]),
        bar_high=float(sig["high"]),
        bar_low=float(sig["low"]),
        bar_close=float(sig["close"]),
        bar_volume=float(sig["volume"]),
    )

    # all bars strictly <= signal_ts_utc
    history = bars.loc[bars.index <= signal_ts_utc]

    # ATR (true range)
    def _atr(window: int) -> float | None:
        if len(history) < window + 1:
            return None
        h = history.iloc[-(window + 1):]
        prev_close = h["close"].shift(1)
        tr = pd.concat([
            h["high"] - h["low"],
            (h["high"] - prev_close).abs(),
            (h["low"] - prev_close).abs(),
        ], axis=1).max(axis=1)
        return float(tr.iloc[-window:].mean())

    ctx.atr_5 = _atr(5)
    ctx.atr_15 = _atr(15)

    if len(history) >= 6:
        ctx.prior_5bar_return_pts = float(history["close"].iloc[-1] - history["close"].iloc[-6])
    if len(history) >= 16:
        ctx.prior_15bar_return_pts = float(history["close"].iloc[-1] - history["close"].iloc[-16])

    # RTH session features (since 9:30 ET on the signal's date)
    sig_et = signal_ts_utc.tz_convert(ET)
    rth_open_et = sig_et.replace(hour=9, minute=30, second=0, microsecond=0)
    if sig_et.time() < time(9, 30):
        rth_open_et = rth_open_et - timedelta(days=1)  # overnight signal — not expected for pre10 but safe
    rth_open_utc = rth_open_et.tz_convert("UTC")

    rth = history.loc[history.index >= rth_open_utc]
    if len(rth) >= 1:
        rth_open = float(rth["open"].iloc[0])
        ctx.range_from_rth_open_pts = float(history["close"].iloc[-1] - rth_open)
        ctx.session_high_at_signal = float(rth["high"].max())
        ctx.session_low_at_signal = float(rth["low"].min())
        ctx.distance_from_session_high_pts = float(history["close"].iloc[-1] - ctx.session_high_at_signal)
        ctx.distance_from_session_low_pts = float(history["close"].iloc[-1] - ctx.session_low_at_signal)
        ctx.rth_volume_to_signal = float(rth["volume"].sum())

    return ctx


# ---------- outcome bucketing ---------------------------------------------


def quality_bucket(realized_r: float) -> str:
    if realized_r >= 1.5:
        return "A"
    if realized_r >= 0.5:
        return "B"
    if realized_r >= -0.5:
        return "C"
    return "D"


def normalize_pre10_exit_reason(reason: str) -> str:
    return {
        "stop": "SL",
        "target": "TP",
        "trail_stop": "TRAIL_STOP",
        "time_stop": "TIMEOUT",
    }.get(reason, reason.upper())


def normalize_fractalamd_exit_reason(reason: str) -> str:
    return reason.upper()  # already SL / TP / etc


# ---------- row builders --------------------------------------------------


def _parse_iso_ts(s: str) -> pd.Timestamp:
    """Parse an ISO timestamp (with offset) into UTC tz-aware pd.Timestamp."""
    return pd.Timestamp(datetime.fromisoformat(s)).tz_convert("UTC")


def build_pre10_row(trade: dict, bars: pd.DataFrame) -> dict | None:
    entry = trade["entry"]
    exit_ev = trade["exit"]
    if exit_ev is None:
        return None

    signal_ts_utc = _parse_iso_ts(entry["bar_end"])
    signal_ts_et = signal_ts_utc.tz_convert(ET)

    ref_price = float(entry["ref_price"])
    stop_price = float(entry["stop_price"])
    side = entry["side"]  # 'buy' or 'sell'
    side_norm = "long" if side == "buy" else "short"
    risk_pts = abs(ref_price - stop_price)

    realized_r = float(exit_ev["realized_r"])
    bar_ctx = compute_bar_context(bars, signal_ts_utc)

    signal_id = f"pre10_paper_{signal_ts_et.strftime('%Y%m%d_%H%M%S')}_{side_norm}"

    return {
        "signal_id": signal_id,
        "source": "paper",
        "strategy": "pre10_vp_continuation",
        "symbol": entry.get("instrument", "NQ"),
        "ts_signal_utc": signal_ts_utc,
        "ts_signal_et": signal_ts_et,
        "date_et": signal_ts_et.date(),
        "minute_of_day_et": signal_ts_et.hour * 60 + signal_ts_et.minute,
        "day_of_week": signal_ts_et.weekday(),
        "side": side_norm,
        "entry_price": ref_price,
        "stop_price": stop_price,
        "target_price": entry.get("target_price"),
        "risk_pts": risk_pts,
        "contracts": int(entry.get("contracts", 0)),
        # pre10-specific
        "p_up_router": float(entry.get("p_up_router", float("nan"))),
        "router_passed": bool(entry.get("router_passed", False)),
        "trigger": (entry.get("metadata") or {}).get("trigger"),
        "exit_side": (entry.get("metadata") or {}).get("exit_side"),
        "target_r_mode": (entry.get("metadata") or {}).get("target_r"),
        "rof_score": float("nan"),
        # outcome
        "exit_reason": normalize_pre10_exit_reason(exit_ev["reason"]),
        "exit_price": float(exit_ev["exit_price"]),
        "realized_r": realized_r,
        "pnl_gross": float(exit_ev.get("pnl_gross", float("nan"))),
        "pnl_net": float(exit_ev.get("pnl_net", float("nan"))),
        "held_minutes": int(exit_ev.get("held_minutes", 0)),
        "mfe_pts": float(exit_ev.get("mfe_pts", float("nan"))),
        "mae_pts": float(exit_ev.get("mae_pts", float("nan"))),
        "n_trail_moves": len(trade.get("trails", [])),
        # quality label
        "quality_bucket": quality_bucket(realized_r),
        # bar context
        "bars_available": bar_ctx.bar_available,
        "bar_open": bar_ctx.bar_open,
        "bar_high": bar_ctx.bar_high,
        "bar_low": bar_ctx.bar_low,
        "bar_close": bar_ctx.bar_close,
        "bar_volume": bar_ctx.bar_volume,
        "atr_5": bar_ctx.atr_5,
        "atr_15": bar_ctx.atr_15,
        "prior_5bar_return_pts": bar_ctx.prior_5bar_return_pts,
        "prior_15bar_return_pts": bar_ctx.prior_15bar_return_pts,
        "range_from_rth_open_pts": bar_ctx.range_from_rth_open_pts,
        "session_high_at_signal": bar_ctx.session_high_at_signal,
        "session_low_at_signal": bar_ctx.session_low_at_signal,
        "distance_from_session_high_pts": bar_ctx.distance_from_session_high_pts,
        "distance_from_session_low_pts": bar_ctx.distance_from_session_low_pts,
        "rth_volume_to_signal": bar_ctx.rth_volume_to_signal,
    }


def build_fractalamd_row(trade: dict, bars: pd.DataFrame) -> dict | None:
    """FractalAMD trades.jsonl has a different schema. The signal time is
    `date` + `entry_time` interpreted in ET."""
    date_str = trade["date"]
    entry_time_str = trade["entry_time"]
    signal_ts_et = pd.Timestamp(f"{date_str} {entry_time_str}").tz_localize(ET)
    signal_ts_utc = signal_ts_et.tz_convert("UTC")

    entry_price = float(trade["entry_price"])
    stop_price = float(trade["stop"])
    target_price = float(trade.get("target")) if trade.get("target") is not None else None
    direction = trade["direction"]  # BULLISH / BEARISH
    side_norm = "long" if direction == "BULLISH" else "short"
    risk_pts = float(trade.get("risk", abs(entry_price - stop_price)))

    pnl_r = float(trade["pnl_r"])
    bar_ctx = compute_bar_context(bars, signal_ts_utc)

    signal_id = f"fractalamd_{trade.get('order_id', signal_ts_et.strftime('%Y%m%d_%H%M%S'))}"

    return {
        "signal_id": signal_id,
        "source": "live",
        "strategy": "fractalamd",
        "symbol": trade.get("symbol", "NQ"),
        "ts_signal_utc": signal_ts_utc,
        "ts_signal_et": signal_ts_et,
        "date_et": signal_ts_et.date(),
        "minute_of_day_et": signal_ts_et.hour * 60 + signal_ts_et.minute,
        "day_of_week": signal_ts_et.weekday(),
        "side": side_norm,
        "entry_price": entry_price,
        "stop_price": stop_price,
        "target_price": target_price,
        "risk_pts": risk_pts,
        "contracts": int(trade.get("contracts", 1)),
        # FractalAMD-specific (pre10 fields = NaN)
        "p_up_router": float("nan"),
        "router_passed": False,
        "trigger": None,
        "exit_side": None,
        "target_r_mode": None,
        "rof_score": float(trade.get("rof_score", float("nan"))),
        # outcome
        "exit_reason": normalize_fractalamd_exit_reason(trade["exit_reason"]),
        "exit_price": float(trade["exit_price"]),
        "realized_r": pnl_r,
        "pnl_gross": float("nan"),
        "pnl_net": float(trade.get("pnl_dollars", float("nan"))),
        "held_minutes": 0,  # not logged in FractalAMD trades.jsonl
        "mfe_pts": float("nan"),
        "mae_pts": float("nan"),
        "n_trail_moves": 0,
        # quality label
        "quality_bucket": quality_bucket(pnl_r),
        # bar context
        "bars_available": bar_ctx.bar_available,
        "bar_open": bar_ctx.bar_open,
        "bar_high": bar_ctx.bar_high,
        "bar_low": bar_ctx.bar_low,
        "bar_close": bar_ctx.bar_close,
        "bar_volume": bar_ctx.bar_volume,
        "atr_5": bar_ctx.atr_5,
        "atr_15": bar_ctx.atr_15,
        "prior_5bar_return_pts": bar_ctx.prior_5bar_return_pts,
        "prior_15bar_return_pts": bar_ctx.prior_15bar_return_pts,
        "range_from_rth_open_pts": bar_ctx.range_from_rth_open_pts,
        "session_high_at_signal": bar_ctx.session_high_at_signal,
        "session_low_at_signal": bar_ctx.session_low_at_signal,
        "distance_from_session_high_pts": bar_ctx.distance_from_session_high_pts,
        "distance_from_session_low_pts": bar_ctx.distance_from_session_low_pts,
        "rth_volume_to_signal": bar_ctx.rth_volume_to_signal,
    }


# ---------- main ----------------------------------------------------------


def build(args: argparse.Namespace) -> int:
    print(f"loading bars from {NQ_BARS_PARQUET}")
    bars = load_nq_1m_bars(NQ_BARS_PARQUET)
    print(f"  {len(bars):,} bars, {bars.index.min()} to {bars.index.max()}")

    rows: list[dict] = []

    print(f"loading pre10 paper pairs from {PRE10_PAPER_LOG}")
    pre10_pairs = load_pre10_paper_pairs()
    print(f"  {len(pre10_pairs)} paired pre10 paper trades")
    seen_ids: set[str] = set()
    for trade in pre10_pairs:
        row = build_pre10_row(trade, bars)
        if row is None:
            continue
        # dedup by signal_id (the paper log has a duplicate replay)
        if row["signal_id"] in seen_ids:
            continue
        seen_ids.add(row["signal_id"])
        rows.append(row)

    print(f"loading FractalAMD trades from {FRACTALAMD_TRADES}")
    famd_trades = load_fractalamd_trades()
    print(f"  {len(famd_trades)} FractalAMD live trades")
    for trade in famd_trades:
        row = build_fractalamd_row(trade, bars)
        if row is None:
            continue
        if row["signal_id"] in seen_ids:
            continue
        seen_ids.add(row["signal_id"])
        rows.append(row)

    if not rows:
        print("no trades to write — aborting", file=sys.stderr)
        return 1

    df = pd.DataFrame(rows).sort_values("ts_signal_utc").reset_index(drop=True)
    print(f"\nbuilt {len(df)} rows")

    # ---- summary stats
    summary = {
        "n_trades": int(len(df)),
        "by_source": df["source"].value_counts().to_dict(),
        "by_strategy": df["strategy"].value_counts().to_dict(),
        "by_quality_bucket": df["quality_bucket"].value_counts().to_dict(),
        "by_exit_reason": df["exit_reason"].value_counts().to_dict(),
        "bars_available": int(df["bars_available"].sum()),
        "bars_missing": int((~df["bars_available"]).sum()),
        "expectancy_R_overall": float(df["realized_r"].mean()),
        "expectancy_R_by_source": {
            k: float(v) for k, v in df.groupby("source")["realized_r"].mean().items()
        },
        "win_rate_overall": float((df["realized_r"] > 0).mean()),
        "date_range_et": {
            "min": str(df["date_et"].min()),
            "max": str(df["date_et"].max()),
        },
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_path": str(OUTPUT_PARQUET),
    }
    print("\nsummary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    if args.dry_run:
        print("\n--dry-run: not writing parquet")
        return 0

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PARQUET, index=False)
    OUTPUT_SUMMARY.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nwrote {OUTPUT_PARQUET}")
    print(f"wrote {OUTPUT_SUMMARY}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true",
                   help="Don't write parquet, just print summary.")
    args = p.parse_args(argv)
    return build(args)


if __name__ == "__main__":
    raise SystemExit(main())
