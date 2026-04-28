"""
Live-engine backtest — drives production/live_bot.py SignalEngine, TBBOBuffer,
and CandleBuilder against historical NQ/ES/YM 1m parquets and NQ TBBO parquets.

This BacktestStation copy points at the FactalAMD- repo's `feat/risk-profiles`
branch (the commit deployed on ben-247 as of 2026-04-28 PM). Output IS what
the live bot deployed on ben-247 would do on the same historical data —
modulo the risk_profiles sizing knobs which only change dollar PnL, not
R-multiples.

Provenance: copied from `C:/Fractal-AMD/scripts/backtest_live_engine.py`
on 2026-04-28 PM, with sys.path swapped to FactalAMD- and DATA_RAW
left at C:/Fractal-AMD/data/raw/ since both repos share the same
historical bars on disk.

Two configs in one run (legacy from the original harness):
  pre_update  : MIN_HOUR=9, MAX_HOUR=16, SKIP_HOUR=13   (the old window)
  post_update : MIN_HOUR=8, MAX_HOUR=17, SKIP_HOUR=13   (a now-stale label)

Note: live_bot.py at feat/risk-profiles uses the trusted-aligned 09:30–14:00
ET window via RTH_OPEN/RTH_CLOSE, not the legacy MIN_HOUR/MAX_HOUR knobs.
The configs below still set MIN_HOUR/MAX_HOUR for compatibility with the
harness's own gates, but the entry decision is driven by the bot's actual
RTH gates.

Usage:
  cd backend
  .venv\\Scripts\\python -m scripts.backtest_live_bot --start 2024-01-02 --end 2024-03-31
  .venv\\Scripts\\python -m scripts.backtest_live_bot --start 2024-01-02 --end 2026-03-31
"""
from __future__ import annotations
import sys, os, argparse, glob, json, logging, time
from collections import deque
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta

# Use FactalAMD- (the GitHub-deployed repo, on `feat/risk-profiles` branch
# matching ben-247) for live_bot + features. Override via env if needed.
_FA_ROOT = Path(os.environ.get("FA_REPO", r"C:\Users\benbr\FractalAMD-"))
sys.path.insert(0, str(_FA_ROOT / "production"))
sys.path.insert(0, str(_FA_ROOT / "src"))

import pandas as pd
import numpy as np

# Imports from live_bot — DO NOT re-implement strategy logic.
# MIN_ROF / MAX_ROF removed in the 2026-04-12 align-to-trusted commit; the
# live bot at feat/risk-profiles dropped the ROF gate entirely.
from live_bot import (
    CandleBuilder,
    TBBOBuffer,
    SignalEngine,
    Setup,
    Trade,
    BUFFER,
    MAX_TRADES_PER_DAY,
    TARGET_R,
    MIN_CO_SCORE,
)

log = logging.getLogger("FractalAMD.live_engine_bt")


# ─── Fast TBBO buffer ─────────────────────────────────────────────────────
# live_bot.TBBOBuffer.add_tick rebuilds self.ticks with a list comprehension
# every single tick (~230k/day * ~1000-entry buffer = ~230M ops/day, 94% of
# backtest runtime). Replace with a deque so prune is O(1) amortized.
# All other methods (to_dataframe, last_price, last_bid, last_ask) work
# unchanged because deque supports iteration and [-1] indexing.

class FastTBBOBuffer(TBBOBuffer):
    def __init__(self, max_seconds=600):
        self.ticks = deque()
        self.max_seconds = max_seconds

    def add_tick(self, timestamp, price, size, side, bid, ask, bid_sz, ask_sz):
        self.ticks.append({
            "ts": timestamp, "price": price, "size": size, "side": side,
            "bid_px_00": bid, "ask_px_00": ask,
            "bid_sz_00": bid_sz, "ask_sz_00": ask_sz,
        })
        cutoff = timestamp - pd.Timedelta(seconds=self.max_seconds)
        while self.ticks and self.ticks[0]["ts"] < cutoff:
            self.ticks.popleft()

DATA_RAW = Path("C:/Fractal-AMD/data/raw")
DATA_L2 = Path("C:/Fractal-AMD/data/l2")
OUTPUTS = Path("C:/Fractal-AMD/outputs")
OUTPUTS.mkdir(exist_ok=True)


# ─── Configs ──────────────────────────────────────────────────────────────

@dataclass
class BTConfig:
    name: str
    min_hour: int
    max_hour: int
    skip_hour: int                 # 99 = no skip
    rth_only_candles: bool = False  # True = drop bars outside 8:30-16 ET (old live bot)
    candle_buffer_size: int = 1500  # ring buffer trim length (old=500, new=1500)
    min_entry_minute: int = 0       # 0 = whole hour; 30 = block entries until :30 of min_hour


# 1. The ACTUAL old live bot behavior: RTH-only candles, 500 buffer, hours 9-16, skip 13.
#    HTF session/1H detection only sees RTH-aggregated bars; Asia/London never fire.
PRE_REAL = BTConfig(
    name="pre_real",
    min_hour=9, max_hour=16, skip_hour=13,
    rth_only_candles=True,
    candle_buffer_size=500,
    min_entry_minute=0,
)

# 2. The CURRENT live bot: full globex, 1500 buffer, hours 8-17, skip 13.
POST_NOW = BTConfig(
    name="post_now",
    min_hour=8, max_hour=17, skip_hour=13,
    rth_only_candles=False,
    candle_buffer_size=1500,
    min_entry_minute=0,
)

# 3. Locked to validated trusted-strategy window 9-14 (no 13 skip), full globex, 9:00 entries.
#    Matches Ben's "9-14 with overnight structure" preference.
VAL_900 = BTConfig(
    name="val_900",
    min_hour=9, max_hour=14, skip_hour=99,
    rth_only_candles=False,
    candle_buffer_size=1500,
    min_entry_minute=0,
)

# 4. Strict trusted-baseline match: 9:30-14, full globex, no skip.
#    This is what export_trades_tv.py implicitly enforces via rth_s = 9:30.
VAL_930 = BTConfig(
    name="val_930",
    min_hour=9, max_hour=14, skip_hour=99,
    rth_only_candles=False,
    candle_buffer_size=1500,
    min_entry_minute=30,
)

# 5. pre_real with entries restricted to hour 10 only.
#    Q1 v3 showed pre_real's profit (+28.9R) was concentrated in hour 10
#    (+24R at 44% WR / 32 trades). Hours 11-15 were near break-even.
#    This config tests "isolate the sweet hour and ship that."
PRE_REAL_H10 = BTConfig(
    name="pre_real_h10",
    min_hour=10, max_hour=11, skip_hour=99,
    rth_only_candles=True,
    candle_buffer_size=500,
    min_entry_minute=0,
)

ALL_CONFIGS = {c.name: c for c in [PRE_REAL, POST_NOW, VAL_900, VAL_930, PRE_REAL_H10]}


# ─── Data loading ─────────────────────────────────────────────────────────

def _to_et(df: pd.DataFrame) -> pd.DataFrame:
    """Force the index to America/New_York timezone."""
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert("America/New_York")
    elif str(df.index.tz) != "America/New_York":
        df.index = df.index.tz_convert("America/New_York")
    return df


def load_ohlcv(symbol: str) -> pd.DataFrame:
    """Load full 1m OHLCV history for a symbol from local parquets."""
    pieces = []
    p1 = DATA_RAW / f"{symbol}.c.0_ohlcv-1m_2022_2025.parquet"
    p2 = DATA_RAW / f"{symbol}_ohlcv-1m_2026.parquet"
    if not p1.exists() and not p2.exists():
        raise FileNotFoundError(f"No OHLCV parquet for {symbol}")
    for p in (p1, p2):
        if not p.exists():
            continue
        df = pd.read_parquet(p)
        df = df[["open", "high", "low", "close", "volume"]].copy()
        df = _to_et(df)
        pieces.append(df)
    df = pd.concat(pieces).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def _parse_tbbo_filename(path: Path):
    parts = path.stem.split("_")
    if len(parts) < 4:
        return None
    try:
        return (date.fromisoformat(parts[2]), date.fromisoformat(parts[3]))
    except Exception:
        return None


def find_tbbo_files_for_day(d: date) -> list[Path]:
    """Find NQ TBBO parquet file(s) covering one trading day's session.
    Includes the prior day's file too in case the 18:00 → 24:00 portion of
    the prior session is in a different file (handles weekly chunks).
    """
    out = []
    prev = d - timedelta(days=1)
    for f in DATA_L2.glob("NQ*_tbbo_*.parquet"):
        rng = _parse_tbbo_filename(f)
        if rng is None:
            continue
        fs, fe = rng
        if fs <= d < fe or fs <= prev < fe:
            out.append(f)
    return sorted(set(out))


def load_tbbo_for_day(d: date) -> pd.DataFrame:
    """Load NQ TBBO ticks for one trading day, trimmed to a tight window
    around trading hours (07:50 → 17:00 ET) so we don't pay for overnight
    ticks the strategy never looks at. The 10-min lead-in covers the
    TBBOBuffer's 600-second lookback for compute_real_of at the first scan.
    """
    files = find_tbbo_files_for_day(d)
    if not files:
        return pd.DataFrame()
    pieces = []
    for f in files:
        df = pd.read_parquet(f)
        if "action" in df.columns:
            df = df[df["action"] == "T"]
        df = _to_et(df)
        pieces.append(df)
    if not pieces:
        return pd.DataFrame()
    tbbo = pd.concat(pieces).sort_index()
    tbbo = tbbo[~tbbo.index.duplicated(keep="last")]
    day_ts = pd.Timestamp(d, tz="America/New_York")
    win_start = day_ts.replace(hour=7, minute=50)
    win_end = day_ts.replace(hour=17)
    return tbbo.loc[win_start:win_end]


# ─── Trade record for output ──────────────────────────────────────────────

@dataclass
class TradeRecord:
    date: str
    direction: str
    entry_time: str
    entry_price: float
    stop: float
    target: float
    risk: float
    rof_score: int
    exit_time: str
    exit_price: float
    exit_reason: str
    pnl_r: float
    htf_tf: str
    ltf_tf: str


def _trade_to_record(t: Trade, day_str: str, exit_time: pd.Timestamp = None) -> TradeRecord:
    return TradeRecord(
        date=day_str,
        direction=t.setup.direction,
        entry_time=t.entry_time.strftime("%H:%M") if t.entry_time is not None else "",
        entry_price=float(t.entry_price),
        stop=float(t.stop),
        target=float(t.target),
        risk=float(t.risk),
        rof_score=int(t.rof_score),
        exit_time=exit_time.strftime("%H:%M") if exit_time is not None else "",
        exit_price=float(t.exit_price),
        exit_reason=t.exit_reason,
        pnl_r=float(t.pnl_r),
        htf_tf=t.setup.htf_tf,
        ltf_tf=t.setup.ltf_tf,
    )


# ─── Per-day backtest ─────────────────────────────────────────────────────

def run_day(
    day: pd.Timestamp,
    nq: pd.DataFrame,
    es: pd.DataFrame,
    ym: pd.DataFrame,
    tbbo: pd.DataFrame,
    config: BTConfig,
) -> tuple[list[TradeRecord], int]:
    """Run a single trading day through the live SignalEngine.

    Returns (trade records, setups detected).
    """
    day_start = (day - pd.Timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
    day_end = day.replace(hour=17, minute=0, second=0, microsecond=0)

    nq_day = nq.loc[day_start:day_end]
    es_day = es.loc[day_start:day_end]
    ym_day = ym.loc[day_start:day_end]
    if len(nq_day) < 60 or len(es_day) < 60 or len(ym_day) < 60:
        return [], 0

    # Optionally drop bars outside RTH (8:30-16 ET) — matches old live bot's tick filter.
    if config.rth_only_candles:
        def _rth_mask(idx):
            h = idx.hour; m = idx.minute
            return ~((h < 8) | ((h == 8) & (m < 30)) | (h >= 16))
        nq_day = nq_day[_rth_mask(nq_day.index)]
        es_day = es_day[_rth_mask(es_day.index)]
        ym_day = ym_day[_rth_mask(ym_day.index)]
        if len(nq_day) < 60 or len(es_day) < 60 or len(ym_day) < 60:
            return [], 0

    # Build live-bot state from scratch each day. The deployed
    # SignalEngine doesn't take min_hour/max_hour/skip_hour kwargs anymore —
    # those gates are module-level constants (RTH_OPEN, RTH_CLOSE) baked
    # into the trusted-aligned bot. The BTConfig fields are kept for
    # candle_buffer_size + rth_only_candles + min_entry_minute, which the
    # harness uses outside of SignalEngine.
    candle_builder = CandleBuilder(buffer_size=config.candle_buffer_size)
    tbbo_buffer = FastTBBOBuffer(max_seconds=600)
    engine = SignalEngine()
    engine.persist_enabled = False  # don't clobber live state from backtest
    engine.reset_day()
    engine.today = day.date()  # FIX: live_bot.reset_day() sets today=system date, not bar date

    active: list[Trade] = []
    closed: list[tuple[Trade, pd.Timestamp]] = []  # (trade, exit_time)

    nq_idx = nq_day.index
    nq_high = nq_day["high"].values.astype(float)
    nq_low = nq_day["low"].values.astype(float)
    nq_close = nq_day["close"].values.astype(float)

    # Pre-extract TBBO arrays for speed
    if not tbbo.empty:
        tbbo_in = tbbo.loc[day_start:day_end]
    else:
        tbbo_in = pd.DataFrame()

    if not tbbo_in.empty:
        tbbo_idx = tbbo_in.index
        tbbo_price = tbbo_in["price"].values.astype(float)
        tbbo_size = tbbo_in["size"].values.astype(np.int64) if "size" in tbbo_in.columns else np.zeros(len(tbbo_in), dtype=np.int64)
        tbbo_side = tbbo_in["side"].astype(str).values if "side" in tbbo_in.columns else np.full(len(tbbo_in), "N", dtype=object)
        tbbo_bid = tbbo_in["bid_px_00"].values.astype(float) if "bid_px_00" in tbbo_in.columns else np.zeros(len(tbbo_in))
        tbbo_ask = tbbo_in["ask_px_00"].values.astype(float) if "ask_px_00" in tbbo_in.columns else np.zeros(len(tbbo_in))
        tbbo_bid_sz = tbbo_in["bid_sz_00"].values.astype(np.int64) if "bid_sz_00" in tbbo_in.columns else np.zeros(len(tbbo_in), dtype=np.int64)
        tbbo_ask_sz = tbbo_in["ask_sz_00"].values.astype(np.int64) if "ask_sz_00" in tbbo_in.columns else np.zeros(len(tbbo_in), dtype=np.int64)
    else:
        tbbo_idx = pd.DatetimeIndex([], tz="America/New_York")
        tbbo_price = np.zeros(0)
        tbbo_size = np.zeros(0, dtype=np.int64)
        tbbo_side = np.zeros(0, dtype=object)
        tbbo_bid = np.zeros(0)
        tbbo_ask = np.zeros(0)
        tbbo_bid_sz = np.zeros(0, dtype=np.int64)
        tbbo_ask_sz = np.zeros(0, dtype=np.int64)

    tbbo_ptr = 0
    nq_open_arr = nq_day["open"].values.astype(float)

    # PERFORMANCE: skip the overnight prologue. Find the first NQ bar at or after
    # MIN_HOUR (the earliest possible trade time) and pre-warm state up to there:
    #   - bulk-advance tbbo_ptr so the buffer has the last ~10 min of ticks
    #   - candle_builder.candles will be set inside the loop on its first iteration
    # Then start the per-minute loop from that bar instead of from prev 18:00.
    day_local = day.tz_convert("America/New_York") if day.tzinfo else day.tz_localize("America/New_York")
    trading_start = day_local.replace(hour=config.min_hour, minute=0, second=0, microsecond=0)
    start_i = int(nq_idx.searchsorted(trading_start))
    if start_i >= len(nq_idx):
        return [], 0  # no bars in trading window
    # Bulk-advance TBBO buffer to (trading_start - 1 minute), so when the loop
    # processes the trading_start bar it will fill the last minute of ticks.
    tbbo_warmup_until = trading_start - pd.Timedelta(minutes=1)
    while tbbo_ptr < len(tbbo_idx) and tbbo_idx[tbbo_ptr] <= tbbo_warmup_until:
        ts = tbbo_idx[tbbo_ptr]
        tbbo_buffer.add_tick(
            ts,
            float(tbbo_price[tbbo_ptr]),
            int(tbbo_size[tbbo_ptr]),
            str(tbbo_side[tbbo_ptr]),
            float(tbbo_bid[tbbo_ptr]),
            float(tbbo_ask[tbbo_ptr]),
            int(tbbo_bid_sz[tbbo_ptr]),
            int(tbbo_ask_sz[tbbo_ptr]),
        )
        tbbo_ptr += 1

    # Walk every NQ bar from trading_start onward
    for i in range(start_i, len(nq_idx)):
        t = nq_idx[i]

        # 1. Check fills on the just-closed bar (i-1)
        if i > 0 and active:
            prev_bar_t = nq_idx[i - 1]
            ph = nq_high[i - 1]
            pl = nq_low[i - 1]
            for trade in list(active):
                if trade.entry_time is not None and prev_bar_t < trade.entry_time:
                    continue  # bar before entry
                if trade.setup.direction == "BEARISH":
                    stop_hit = ph >= trade.stop
                    tp_hit = pl <= trade.target
                else:
                    stop_hit = pl <= trade.stop
                    tp_hit = ph >= trade.target
                if stop_hit and tp_hit:
                    tp_hit = False  # conservative SL-first when ambiguous
                if stop_hit:
                    trade.exit_price = float(trade.stop)
                    trade.exit_reason = "SL"
                    trade.pnl_r = -1.0
                    trade.status = "CLOSED"
                    closed.append((trade, prev_bar_t))
                    active.remove(trade)
                elif tp_hit:
                    trade.exit_price = float(trade.target)
                    trade.exit_reason = "TP"
                    trade.pnl_r = float(TARGET_R)
                    trade.status = "CLOSED"
                    closed.append((trade, prev_bar_t))
                    active.remove(trade)

        # 2. Advance TBBO buffer to time t
        ticks_added_this_min = 0
        while tbbo_ptr < len(tbbo_idx) and tbbo_idx[tbbo_ptr] <= t:
            ts = tbbo_idx[tbbo_ptr]
            tbbo_buffer.add_tick(
                ts,
                float(tbbo_price[tbbo_ptr]),
                int(tbbo_size[tbbo_ptr]),
                str(tbbo_side[tbbo_ptr]),
                float(tbbo_bid[tbbo_ptr]),
                float(tbbo_ask[tbbo_ptr]),
                int(tbbo_bid_sz[tbbo_ptr]),
                int(tbbo_ask_sz[tbbo_ptr]),
            )
            tbbo_ptr += 1
            ticks_added_this_min += 1

        # Synthetic TBBO fallback: if no real ticks for this minute (days outside
        # the NQ TBBO coverage window 2025-04 → 2026-03), inject one synthetic
        # tick at the current bar's open price. This lets the bot run on OHLCV-only
        # data. Only kicks in when ENABLE_ROF_GATE is False in live_bot (the gate
        # would reject trades without real TBBO anyway).
        if ticks_added_this_min == 0:
            bar_open = nq_open_arr[i]
            tbbo_buffer.add_tick(t, bar_open, 1, "N", bar_open, bar_open, 0, 0)

        # 3. Refresh candle_builder with closed bars (bars at index < t), trimmed to buffer size
        bsize = config.candle_buffer_size
        nq_closed_full = nq_day.iloc[:i]
        nq_closed = nq_closed_full.iloc[-bsize:] if len(nq_closed_full) > bsize else nq_closed_full
        candle_builder.candles["NQ"] = nq_closed

        es_pos = es_day.index.searchsorted(t)
        es_closed_full = es_day.iloc[:es_pos]
        es_closed = es_closed_full.iloc[-bsize:] if len(es_closed_full) > bsize else es_closed_full
        candle_builder.candles["ES"] = es_closed

        ym_pos = ym_day.index.searchsorted(t)
        ym_closed_full = ym_day.iloc[:ym_pos]
        ym_closed = ym_closed_full.iloc[-bsize:] if len(ym_closed_full) > bsize else ym_closed_full
        candle_builder.candles["YM"] = ym_closed

        # 4. Scan + entry check
        # Always run scan during trading hours (gated internally by SignalEngine).
        # Block check_entry until t >= (min_hour, min_entry_minute) — gives finer control
        # than SignalEngine's hour-resolution gate, used to test 9:00 vs 9:30 entries.
        entry_blocked = (t.hour == config.min_hour and t.minute < config.min_entry_minute)

        if len(nq_closed) > 20 and len(es_closed) > 20 and len(ym_closed) > 20:
            # 1. Scan for new setups. scan_for_setups now dedupes internally so calling
            #    every minute is cheap, but we still throttle to 5 min since LTF is 5m.
            if t.minute % 5 == 0 or len(engine.setups) == 0:
                engine.scan_for_setups(nq_closed, es_closed, ym_closed, t)

            # 2. Check whether the just-closed bar (nq_closed.iloc[-1]) touched the
            #    nearest WATCHING setup per direction. Mirrors live_bot's call site.
            engine.check_touch(nq_closed, t)

            # 3. Enter on TOUCHED setups. check_entry handles the rest of validation
            #    (ROF as timing filter, CO score, risk sanity, dedup) and resets to
            #    WATCHING on validation failure so the same FVG can re-touch later.
            if not entry_blocked:
                for setup in list(engine.setups):
                    if setup.status != "TOUCHED":
                        continue
                    trade = engine.check_entry(setup, nq_closed, tbbo_buffer, t)
                    if trade:
                        active.append(trade)

    # Force-close any remaining at last NQ close
    if active:
        last_close = float(nq_close[-1])
        last_t = nq_idx[-1]
        for trade in active:
            trade.exit_price = last_close
            trade.exit_reason = "EOT"
            if trade.risk > 0:
                if trade.setup.direction == "BEARISH":
                    trade.pnl_r = (trade.entry_price - last_close) / trade.risk
                else:
                    trade.pnl_r = (last_close - trade.entry_price) / trade.risk
            trade.status = "CLOSED"
            closed.append((trade, last_t))

    day_str = day.strftime("%Y-%m-%d")
    records = [_trade_to_record(t, day_str, et) for (t, et) in closed]
    return records, len(engine.setups)


# ─── Main run ─────────────────────────────────────────────────────────────

def trading_days_in_range(nq: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> list[pd.Timestamp]:
    """Get unique trading days from the NQ index in [start, end]."""
    if start.tz is None:
        start = start.tz_localize("America/New_York")
    if end.tz is None:
        end = end.tz_localize("America/New_York")
    sliced = nq.loc[start:end]
    if sliced.empty:
        return []
    days = sorted(set(sliced.index.normalize()))
    return [d for d in days if start <= d <= end]


def run_backtest(start: pd.Timestamp, end: pd.Timestamp, configs: list[BTConfig]) -> dict:
    log.info("Loading OHLCV...")
    nq = load_ohlcv("NQ")
    es = load_ohlcv("ES")
    ym = load_ohlcv("YM")
    log.info(f"  NQ: {len(nq):,} bars  {nq.index.min()} -> {nq.index.max()}")
    log.info(f"  ES: {len(es):,} bars")
    log.info(f"  YM: {len(ym):,} bars")

    days = trading_days_in_range(nq, start, end)
    log.info(f"Trading days in range: {len(days)} ({days[0].date() if days else '?'} -> {days[-1].date() if days else '?'})")

    results = {c.name: {"trades": [], "setups": 0, "days_run": 0, "days_no_tbbo": 0} for c in configs}

    t0 = time.time()
    for di, day in enumerate(days):
        tbbo = load_tbbo_for_day(day.date())
        if tbbo.empty:
            # Days outside TBBO coverage — run with synthetic bid/ask from bar opens.
            # Only valid if ENABLE_ROF_GATE is False in live_bot (otherwise check_entry
            # would reject due to insufficient tick history).
            for cfg in configs:
                results[cfg.name]["days_no_tbbo"] += 1

        per_day_summary = []
        for cfg in configs:
            try:
                trades, n_setups = run_day(day, nq, es, ym, tbbo, cfg)
                results[cfg.name]["trades"].extend(trades)
                results[cfg.name]["setups"] += n_setups
                results[cfg.name]["days_run"] += 1
                per_day_summary.append(f"{cfg.name}={len(trades)}t")
            except Exception as e:
                log.warning(f"  {day.date()} {cfg.name}: {e}")
                import traceback; traceback.print_exc()

        elapsed = time.time() - t0
        rate = (di + 1) / elapsed if elapsed > 0 else 0
        eta = (len(days) - di - 1) / rate if rate > 0 else 0
        log.info(f"  [{di+1:>3}/{len(days)}] {day.date()}  {' '.join(per_day_summary)}  "
                 f"({elapsed:.0f}s elapsed, ~{eta:.0f}s left)")

    return results


def summarize(records: list[TradeRecord]) -> dict:
    if not records:
        return {"trades": 0, "wins": 0, "losses": 0, "wr": 0.0, "total_r": 0.0,
                "avg_r": 0.0, "max_dd": 0.0}
    n = len(records)
    wins = sum(1 for r in records if r.pnl_r > 0)
    losses = sum(1 for r in records if r.pnl_r < 0)
    wr = wins / n
    total_r = sum(r.pnl_r for r in records)
    avg_r = total_r / n
    sorted_r = sorted(records, key=lambda r: (r.date, r.entry_time))
    eq, peak, worst = 0.0, 0.0, 0.0
    for r in sorted_r:
        eq += r.pnl_r
        peak = max(peak, eq)
        worst = min(worst, eq - peak)
    return {"trades": n, "wins": wins, "losses": losses, "wr": wr,
            "total_r": total_r, "avg_r": avg_r, "max_dd": abs(worst)}


def write_csv(records: list[TradeRecord], path: Path):
    df = pd.DataFrame([asdict(r) for r in records])
    df.to_csv(path, index=False)
    log.info(f"Wrote {len(records)} trades to {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--configs",
        default="pre_real,post_now,val_900,val_930",
        help="Comma-separated config names from: " + ", ".join(ALL_CONFIGS.keys()),
    )
    parser.add_argument("--out-prefix", default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)

    configs = []
    for name in args.configs.split(","):
        name = name.strip()
        if name not in ALL_CONFIGS:
            raise SystemExit(f"unknown config '{name}'. options: {list(ALL_CONFIGS.keys())}")
        configs.append(ALL_CONFIGS[name])

    log.info("=" * 72)
    log.info(f"LIVE-ENGINE BACKTEST  {args.start} -> {args.end}")
    for c in configs:
        skip_str = "none" if c.skip_hour >= 24 else str(c.skip_hour)
        cand_str = "rth-only" if c.rth_only_candles else "globex"
        log.info(f"  {c.name}: hr {c.min_hour}:{c.min_entry_minute:02d}-{c.max_hour} "
                 f"skip {skip_str}  candles={cand_str}  buf={c.candle_buffer_size}")
    log.info("=" * 72)

    results = run_backtest(start, end, configs)

    log.info("")
    log.info("=" * 72)
    log.info("RESULTS")
    log.info("=" * 72)

    summaries = {}
    for cfg in configs:
        recs = results[cfg.name]["trades"]
        s = summarize(recs)
        summaries[cfg.name] = s
        log.info(f"\n{cfg.name}:")
        log.info(f"  days run         : {results[cfg.name]['days_run']}")
        log.info(f"  days w/o TBBO    : {results[cfg.name]['days_no_tbbo']} (skipped, live bot can't trade w/o ROF)")
        log.info(f"  setups detected  : {results[cfg.name]['setups']}")
        log.info(f"  trades           : {s['trades']}")
        log.info(f"  wins / losses    : {s['wins']}W / {s['losses']}L")
        log.info(f"  win rate         : {s['wr']*100:.1f}%")
        log.info(f"  total R          : {s['total_r']:+.1f}")
        log.info(f"  avg R            : {s['avg_r']:+.2f}")
        log.info(f"  max drawdown R   : {s['max_dd']:.1f}")

    if len(configs) >= 2:
        log.info("")
        log.info("SIDE BY SIDE")
        header = f"  {'metric':<12}" + "".join(f"{c.name:>14}" for c in configs)
        log.info(header)
        log.info("  " + "-" * (12 + 14 * len(configs)))
        for k, label in [("trades", "trades"), ("wr", "WR %"), ("total_r", "total R"),
                         ("avg_r", "avg R"), ("max_dd", "max DD R")]:
            row = f"  {label:<12}"
            for cfg in configs:
                v = summaries[cfg.name][k]
                if k == "wr":
                    v = v * 100
                if k == "trades":
                    row += f"{int(v):>14d}"
                else:
                    row += f"{v:>14.2f}"
            log.info(row)

    prefix = args.out_prefix or f"live_engine_bt_{args.start}_{args.end}"
    for cfg in configs:
        path = OUTPUTS / f"{prefix}__{cfg.name}.csv"
        write_csv(results[cfg.name]["trades"], path)


if __name__ == "__main__":
    main()
