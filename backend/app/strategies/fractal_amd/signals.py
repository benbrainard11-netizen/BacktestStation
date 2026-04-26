"""Fractal AMD signal-detection primitives.

Pure functions over `list[Bar]`. No pandas in the hot path -- the
strategy may build a DataFrame from history when convenient, but
these primitives accept lists so they're cheap to test and easy to
reason about.

Ported from `C:/Users/benbr/FractalAMD-/src/features/` (smt_detector,
candle_patterns, stage_detector). Adapted from pd.DataFrame +
DatetimeIndex inputs to `list[Bar]` + datetime ranges. ROF /
order-flow logic intentionally omitted -- the trusted strategy
(per `project_live_bot.md` memory) dropped the ROF gate, so we
ship without it. Cascade detection deferred to a later chunk; not
critical for stage-1 setup confirmation.

Upstream reference: ported from FractalAMD- at SHA
3d08e2b5108c276f268d7e0b8dce85eacf231f1a (2026-04-12). See
`docs/FRACTAL_AMD_PORT_REFERENCE.md`.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Literal
from zoneinfo import ZoneInfo

from app.backtest.strategy import Bar


ET = ZoneInfo("America/New_York")
Direction = Literal["BULLISH", "BEARISH"]


# --- Aggregated candle / setup dataclasses ----------------------------


@dataclass(frozen=True)
class HTFCandle:
    """One higher-timeframe candle (session, 1H, 15m, 5m).

    Built by aggregating the underlying 1m bars for a given
    [start, end) range.
    """

    timeframe: str
    start: dt.datetime
    end: dt.datetime
    open: float
    high: float
    low: float
    close: float


@dataclass
class SMTResult:
    """Result of an SMT divergence check across NQ + ES + YM."""

    has_smt: bool
    direction: Direction | None = None
    sweepers: list[str] = field(default_factory=list)
    holders: list[str] = field(default_factory=list)
    n_swept: int = 0
    n_held: int = 0
    strength: float = 0.0  # 0-1 score (more holders = stronger)
    leader: str | None = None  # best asset to trade (the one that held)


@dataclass
class RejectionSignal:
    """Rejection candle: assets swept prior level then closed back within."""

    direction: Direction
    timeframe: str
    candle_start: dt.datetime
    candle_end: dt.datetime
    reference_start: dt.datetime
    reference_end: dt.datetime
    n_swept: int = 0
    n_rejected: int = 0
    all_swept: bool = False
    all_rejected: bool = False


@dataclass
class StageSignal:
    """A confirmed stage in the fractal chain.

    Mirrors `live_bot.SignalEngine`'s stage-confirmation output.
    Multiple confirmation types (SMT / rejection) can stack on a
    single stage -- more = stronger.
    """

    timeframe: str
    direction: Direction
    candle_start: dt.datetime
    candle_end: dt.datetime
    ref_start: dt.datetime
    ref_end: dt.datetime
    has_smt: bool = False
    smt_result: SMTResult | None = None
    smt_level_swept: float = 0.0
    has_rejection: bool = False
    rejection: RejectionSignal | None = None

    @property
    def confirmation_count(self) -> int:
        """More confirmation types = stronger stage."""
        return int(self.has_smt) + int(self.has_rejection)


@dataclass
class Setup:
    """A detected trading setup waiting for entry.

    Mirrors `live_bot.Setup`. Mutable on purpose -- check_touch flips
    status WATCHING -> TOUCHED in place; chunk 3's entry validation
    flips TOUCHED -> FILLED.
    """

    direction: Direction
    htf_tf: str
    htf_candle_start: dt.datetime
    htf_candle_end: dt.datetime
    ltf_tf: str
    ltf_candle_end: dt.datetime
    fvg_high: float
    fvg_low: float
    fvg_mid: float
    status: Literal["WATCHING", "TOUCHED", "FILLED"] = "WATCHING"
    touch_bar_time: dt.datetime | None = None


@dataclass
class FVG:
    """A detected Fair Value Gap.

    Mirrors `fvg_detector.FVG`. `filled` / `expired` are set by the
    forward-walk inside `detect_fvgs`.
    """

    direction: Direction
    high: float
    low: float
    creation_time: dt.datetime
    creation_bar_idx: int  # index in the source bars list
    filled: bool = False
    fill_time: dt.datetime | None = None
    fill_bar_idx: int | None = None
    expired: bool = False

    @property
    def width(self) -> float:
        return self.high - self.low

    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2.0


# --- Time / candle bounds ---------------------------------------------


def _session_bounds(day_et: dt.datetime) -> list[tuple[str, dt.datetime, dt.datetime]]:
    """Return the four ET futures sessions for a trading day.

    `day_et` must be timezone-aware ET (America/New_York). Returns a list
    of (label, start, end) tuples covering the 23-hour Globex day from
    18:00 ET prior day -> 17:00 ET current day.
    """
    if day_et.tzinfo is None:
        raise ValueError("day_et must be tz-aware (ET)")
    prev = day_et - dt.timedelta(days=1)
    return [
        ("Asia", prev.replace(hour=18, minute=0, second=0, microsecond=0),
         day_et.replace(hour=0, minute=0, second=0, microsecond=0)),
        ("London", day_et.replace(hour=0, minute=0, second=0, microsecond=0),
         day_et.replace(hour=6, minute=0, second=0, microsecond=0)),
        ("NY_AM", day_et.replace(hour=6, minute=0, second=0, microsecond=0),
         day_et.replace(hour=12, minute=0, second=0, microsecond=0)),
        ("NY_PM", day_et.replace(hour=12, minute=0, second=0, microsecond=0),
         day_et.replace(hour=17, minute=0, second=0, microsecond=0)),
    ]


_TF_MINUTES = {"4H": 240, "1H": 60, "30m": 30, "15m": 15, "10m": 10, "5m": 5}


def candle_bounds(
    day_et: dt.datetime, timeframe: str
) -> list[tuple[dt.datetime, dt.datetime]]:
    """Return [(start, end), ...] for HTF candles in a Globex day.

    Trading day boundary is 18:00 ET prior day -> 17:00 ET current day.
    For "session" timeframe, returns the four session bounds. For
    other timeframes, slices the day into fixed-minute candles.
    """
    if day_et.tzinfo is None:
        raise ValueError("day_et must be tz-aware (ET)")
    prev = day_et - dt.timedelta(days=1)
    start = prev.replace(hour=18, minute=0, second=0, microsecond=0)
    end = day_et.replace(hour=17, minute=0, second=0, microsecond=0)

    if timeframe == "session":
        return [(s, e) for _, s, e in _session_bounds(day_et)]

    minutes = _TF_MINUTES.get(timeframe, 60)
    candles: list[tuple[dt.datetime, dt.datetime]] = []
    cur = start
    delta = dt.timedelta(minutes=minutes)
    while cur < end:
        nxt = cur + delta
        candles.append((cur, min(nxt, end)))
        cur = nxt
    return candles


def get_ohlc(
    bars: list[Bar], start: dt.datetime, end: dt.datetime
) -> HTFCandle | None:
    """Aggregate a contiguous range of 1m bars into a single OHLC.

    Half-open interval [start, end). Returns None if no bars in range.
    The bars list is assumed sorted by ts_event ascending (the engine
    guarantees this).
    """
    sub = [b for b in bars if start <= b.ts_event < end]
    if not sub:
        return None
    return HTFCandle(
        timeframe="",  # caller annotates
        start=start,
        end=end,
        open=sub[0].open,
        high=max(b.high for b in sub),
        low=min(b.low for b in sub),
        close=sub[-1].close,
    )


# --- SMT divergence ---------------------------------------------------


def detect_smt_at_level(
    bars_by_asset: dict[str, list[Bar]],
    level_prices: dict[str, float],
    direction: Literal["high", "low"],
    window_start: dt.datetime,
    window_end: dt.datetime,
) -> SMTResult:
    """Check if SMT divergence exists at a level across triad members.

    For a HIGH sweep (BEARISH SMT):
      - Each asset's high in [window_start, window_end) is compared to its level
      - SMT = at least one swept (high > level), at least one held

    For a LOW sweep (BULLISH SMT):
      - Each asset's low in [window_start, window_end) is compared to its level
      - SMT = at least one swept (low < level), at least one held

    Returns SMTResult; check `.has_smt` before consuming.
    """
    sweepers: list[str] = []
    holders: list[str] = []

    for symbol, bars in bars_by_asset.items():
        if symbol not in level_prices:
            continue
        level = level_prices[symbol]
        in_window = [b for b in bars if window_start <= b.ts_event < window_end]
        if not in_window:
            continue
        if direction == "high":
            swept = max(b.high for b in in_window) > level
        else:
            swept = min(b.low for b in in_window) < level
        (sweepers if swept else holders).append(symbol)

    n_total = len(sweepers) + len(holders)
    has_smt = len(sweepers) >= 1 and len(holders) >= 1
    strength = (len(holders) / n_total) if n_total > 0 else 0.0
    leader = holders[0] if holders else None

    trade_direction: Direction | None = None
    if has_smt:
        trade_direction = "BEARISH" if direction == "high" else "BULLISH"

    return SMTResult(
        has_smt=has_smt,
        direction=trade_direction,
        sweepers=sweepers,
        holders=holders,
        n_swept=len(sweepers),
        n_held=len(holders),
        strength=strength,
        leader=leader,
    )


# --- Rejection candle -------------------------------------------------


def detect_rejection(
    bars_by_asset: dict[str, list[Bar]],
    candle_start: dt.datetime,
    candle_end: dt.datetime,
    ref_start: dt.datetime,
    ref_end: dt.datetime,
    timeframe: str = "",
) -> list[RejectionSignal]:
    """Detect rejection-candle patterns across the triad.

    Bearish rejection: at least 2 of {NQ, ES, YM} sweep above the prior
    candle's high AND at least 2 close back at-or-below it.
    Bullish rejection: symmetric for the low.

    Returns 0, 1, or 2 RejectionSignals (could fire both directions
    on a single doji-like candle, though rare).
    """
    ref_ohlc: dict[str, HTFCandle | None] = {}
    cur_ohlc: dict[str, HTFCandle | None] = {}
    for sym, bars in bars_by_asset.items():
        ref_ohlc[sym] = get_ohlc(bars, ref_start, ref_end)
        cur_ohlc[sym] = get_ohlc(bars, candle_start, candle_end)

    if any(v is None for v in ref_ohlc.values()) or any(
        v is None for v in cur_ohlc.values()
    ):
        return []

    signals: list[RejectionSignal] = []

    # Bearish: sweep high then reject
    swept_hi = sum(
        1 for sym in bars_by_asset if cur_ohlc[sym].high > ref_ohlc[sym].high
    )
    rejected_hi = sum(
        1 for sym in bars_by_asset if cur_ohlc[sym].close <= ref_ohlc[sym].high
    )
    if swept_hi >= 2 and rejected_hi >= 2:
        n_total = len(bars_by_asset)
        signals.append(
            RejectionSignal(
                direction="BEARISH",
                timeframe=timeframe,
                candle_start=candle_start,
                candle_end=candle_end,
                reference_start=ref_start,
                reference_end=ref_end,
                n_swept=swept_hi,
                n_rejected=rejected_hi,
                all_swept=swept_hi == n_total,
                all_rejected=rejected_hi == n_total,
            )
        )

    # Bullish: sweep low then reject
    swept_lo = sum(
        1 for sym in bars_by_asset if cur_ohlc[sym].low < ref_ohlc[sym].low
    )
    rejected_lo = sum(
        1 for sym in bars_by_asset if cur_ohlc[sym].close >= ref_ohlc[sym].low
    )
    if swept_lo >= 2 and rejected_lo >= 2:
        n_total = len(bars_by_asset)
        signals.append(
            RejectionSignal(
                direction="BULLISH",
                timeframe=timeframe,
                candle_start=candle_start,
                candle_end=candle_end,
                reference_start=ref_start,
                reference_end=ref_end,
                n_swept=swept_lo,
                n_rejected=rejected_lo,
                all_swept=swept_lo == n_total,
                all_rejected=rejected_lo == n_total,
            )
        )

    return signals


# --- Combined stage check ---------------------------------------------


def check_candle_pair(
    bars_by_asset: dict[str, list[Bar]],
    cur_start: dt.datetime,
    cur_end: dt.datetime,
    ref_start: dt.datetime,
    ref_end: dt.datetime,
    timeframe: str,
    direction_filter: Direction | None = None,
) -> StageSignal | None:
    """Check a candle pair for any stage-confirmation pattern.

    Combines the SMT + rejection detectors. Returns the first
    StageSignal that fires (matching `direction_filter` if set), or
    None.

    SMT alone or rejection alone is sufficient to confirm a stage --
    PSP would be confluence-only and is omitted from this chunk.
    Cascade detection (look-back to prior pair's SMT) is also
    omitted; it's an enhancement, not foundational.
    """
    # SMT — high sweep
    ref_ohlc: dict[str, HTFCandle | None] = {
        sym: get_ohlc(bars, ref_start, ref_end)
        for sym, bars in bars_by_asset.items()
    }
    if any(v is None for v in ref_ohlc.values()):
        return None

    smt_bearish: tuple[SMTResult, float] | None = None
    smt_bullish: tuple[SMTResult, float] | None = None

    hi_levels = {sym: ref_ohlc[sym].high for sym in bars_by_asset}
    smt_hi = detect_smt_at_level(
        bars_by_asset, hi_levels, "high", cur_start, cur_end
    )
    if smt_hi.has_smt and smt_hi.direction == "BEARISH":
        # Use NQ's level as the canonical "swept level" reference.
        smt_bearish = (smt_hi, ref_ohlc["NQ.c.0"].high if "NQ.c.0" in ref_ohlc else 0.0)

    lo_levels = {sym: ref_ohlc[sym].low for sym in bars_by_asset}
    smt_lo = detect_smt_at_level(
        bars_by_asset, lo_levels, "low", cur_start, cur_end
    )
    if smt_lo.has_smt and smt_lo.direction == "BULLISH":
        smt_bullish = (smt_lo, ref_ohlc["NQ.c.0"].low if "NQ.c.0" in ref_ohlc else 0.0)

    # Rejection
    rejections = detect_rejection(
        bars_by_asset, cur_start, cur_end, ref_start, ref_end, timeframe
    )

    # Build a signal for each direction, return first match.
    for direction in ("BEARISH", "BULLISH"):
        if direction_filter and direction != direction_filter:
            continue
        if direction == "BEARISH":
            has_smt = smt_bearish is not None
            smt_data = smt_bearish
        else:
            has_smt = smt_bullish is not None
            smt_data = smt_bullish

        matching_rejections = [r for r in rejections if r.direction == direction]
        has_rej = len(matching_rejections) > 0

        if not has_smt and not has_rej:
            continue

        signal = StageSignal(
            timeframe=timeframe,
            direction=direction,  # type: ignore[arg-type]
            candle_start=cur_start,
            candle_end=cur_end,
            ref_start=ref_start,
            ref_end=ref_end,
        )
        if has_smt and smt_data is not None:
            signal.has_smt = True
            signal.smt_result = smt_data[0]
            signal.smt_level_swept = smt_data[1]
        if has_rej:
            signal.has_rejection = True
            signal.rejection = matching_rejections[0]
        return signal

    return None


# --- Entry-window helper (already wired in scaffold) ------------------


def is_in_entry_window(
    now_et: dt.datetime, *, open_hour: int, open_min: int, close_hour: int
) -> bool:
    """Is the timestamp inside the strategy's entry window?

    Trusted backtest gate: `et.hour < open_hour or et.hour >= close_hour`,
    combined with `rth_s = (open_hour, open_min)`. Pure function -- safe
    to call from any context.
    """
    if now_et.hour < open_hour:
        return False
    if now_et.hour == open_hour and now_et.minute < open_min:
        return False
    if now_et.hour >= close_hour:
        return False
    return True


# --- FVG detection ----------------------------------------------------


def resample_bars(bars: list[Bar], tf_minutes: int) -> list[HTFCandle]:
    """Resample 1m bars into N-minute HTFCandles.

    Mirrors `fvg_detector.resample_bars` (left-closed / left-labeled).
    Bars are bucketed by their `ts_event` floored to the nearest
    `tf_minutes` boundary in UTC. Output ordered by start ascending.
    """
    if not bars:
        return []
    delta = dt.timedelta(minutes=tf_minutes)
    buckets: dict[dt.datetime, list[Bar]] = {}
    for b in bars:
        # Floor to nearest tf_minutes boundary (UTC).
        ts = b.ts_event
        epoch = dt.datetime(1970, 1, 1, tzinfo=ts.tzinfo)
        offset_min = int((ts - epoch).total_seconds() // 60)
        bucket_min = (offset_min // tf_minutes) * tf_minutes
        bucket_start = epoch + dt.timedelta(minutes=bucket_min)
        buckets.setdefault(bucket_start, []).append(b)

    out: list[HTFCandle] = []
    for start in sorted(buckets):
        group = buckets[start]
        out.append(
            HTFCandle(
                timeframe=f"{tf_minutes}m",
                start=start,
                end=start + delta,
                open=group[0].open,
                high=max(b.high for b in group),
                low=min(b.low for b in group),
                close=group[-1].close,
            )
        )
    return out


def detect_fvgs(
    candles: list[HTFCandle],
    direction: Direction,
    *,
    min_gap_pct: float = 0.3,
    expiry_bars: int = 60,
) -> list[FVG]:
    """Detect Fair Value Gaps in a sequence of candles.

    A bullish FVG forms when candle 2 displaces UP enough that
    candle_1.high < candle_3.low (price skipped upward). The gap zone
    is (candle_1.high, candle_3.low).

    A bearish FVG forms symmetrically: candle_3.high < candle_1.low.

    `min_gap_pct` filters noise: gap width must be >= min_gap_pct *
    20-bar avg range. After detection, walks forward to mark fills
    (price traded fully through the zone) and expiries.

    Mirrors `fvg_detector.detect_fvgs`. Trusted-bot uses
    min_gap_pct=0.3, expiry_bars=60 on resampled 5m/15m candles.
    """
    if len(candles) < 3:
        return []

    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    ranges = [h - l for h, l in zip(highs, lows)]

    # Rolling 20-candle avg range. Reuse first valid for early bars.
    avg_range: list[float] = [0.0] * len(candles)
    for i in range(len(candles)):
        if i >= 20:
            avg_range[i] = sum(ranges[i - 20 : i]) / 20
        else:
            # Use whatever's available so early-day FVGs don't get
            # zero-floored. Fall back to 1.0 if no range data at all.
            avail = ranges[:i] or ranges
            avg_range[i] = sum(avail) / len(avail) if avail else 1.0

    fvgs: list[FVG] = []
    for i in range(2, len(candles)):
        c1_h = highs[i - 2]
        c1_l = lows[i - 2]
        c3_h = highs[i]
        c3_l = lows[i]
        ar = avg_range[i] if avg_range[i] > 0 else 1.0

        if direction == "BULLISH":
            gap_low = c1_h
            gap_high = c3_l
            gap_width = gap_high - gap_low
            if gap_width > 0 and gap_width >= ar * min_gap_pct:
                fvgs.append(
                    FVG(
                        direction="BULLISH",
                        high=gap_high,
                        low=gap_low,
                        creation_time=candles[i].start,
                        creation_bar_idx=i,
                    )
                )
        else:
            gap_high = c1_l
            gap_low = c3_h
            gap_width = gap_high - gap_low
            if gap_width > 0 and gap_width >= ar * min_gap_pct:
                fvgs.append(
                    FVG(
                        direction="BEARISH",
                        high=gap_high,
                        low=gap_low,
                        creation_time=candles[i].start,
                        creation_bar_idx=i,
                    )
                )

    # Forward walk to track fills + expiries.
    for fvg in fvgs:
        start = fvg.creation_bar_idx + 1
        end = min(start + expiry_bars, len(candles))
        for j in range(start, end):
            if fvg.direction == "BULLISH":
                # Filled when price drops fully through (bar low <= fvg.low)
                if lows[j] <= fvg.low:
                    fvg.filled = True
                    fvg.fill_time = candles[j].start
                    fvg.fill_bar_idx = j
                    break
            else:
                if highs[j] >= fvg.high:
                    fvg.filled = True
                    fvg.fill_time = candles[j].start
                    fvg.fill_bar_idx = j
                    break
        if not fvg.filled and (end - start) >= expiry_bars:
            fvg.expired = True

    return fvgs


def find_nearest_unfilled_fvg(
    fvgs: list[FVG], current_price: float, current_bar_idx: int, expiry_bars: int = 60
) -> FVG | None:
    """Return the unfilled, non-expired FVG nearest to current_price.

    "Nearest" = smallest |current_price - fvg.mid|. Mirrors
    `fvg_detector.find_nearest_unfilled_fvg`.
    """
    candidates: list[FVG] = []
    for fvg in fvgs:
        if fvg.creation_bar_idx >= current_bar_idx:
            continue
        if (current_bar_idx - fvg.creation_bar_idx) > expiry_bars:
            continue
        if fvg.filled and fvg.fill_bar_idx is not None and fvg.fill_bar_idx < current_bar_idx:
            continue
        candidates.append(fvg)
    if not candidates:
        return None
    candidates.sort(key=lambda f: abs(current_price - f.mid))
    return candidates[0]


# --- Touch detection --------------------------------------------------


def check_touch(setups: list[Setup], bar: Bar) -> list[Setup]:
    """Mark the nearest WATCHING setup per direction as TOUCHED if the
    bar's [low, high] intersects its FVG range.

    Mirrors `live_bot.SignalEngine.check_touch`. The "nearest" rule
    (sort by `abs(setup.fvg_mid - bar.close)`) was the bug fix in the
    trusted bot -- without it, the engine fires on the first random
    FVG-zone match instead of waiting for a real touch on the
    relevant zone.

    Mutates the matched setup's status / touch_bar_time and returns
    the list of newly touched setups.
    """
    bh = bar.high
    bl = bar.low
    bc = bar.close
    touched: list[Setup] = []

    for direction in ("BEARISH", "BULLISH"):
        candidates = [
            s for s in setups
            if s.status == "WATCHING" and s.direction == direction
        ]
        if not candidates:
            continue
        candidates.sort(key=lambda s: abs(s.fvg_mid - bc))
        nearest = candidates[0]
        in_zone = bh >= nearest.fvg_low and bl <= nearest.fvg_high
        if in_zone:
            nearest.status = "TOUCHED"
            nearest.touch_bar_time = bar.ts_event
            touched.append(nearest)

    return touched
