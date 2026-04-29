"""Fractal AMD trusted-strategy engine plugin.

Faithful port of `C:/Fractal-AMD/scripts/trusted_multiyear_bt.py`. The
target is byte-equivalence at the trade-list level: same entry timestamp,
direction, entry/stop/target prices, exit timestamp, exit reason, pnl_r.
A regression test under `backend/tests/test_fractal_amd_trusted_regression.py`
asserts this against the bundled trusted CSV.

Architectural note — trusted is a per-day batch processor with the WHOLE
day's 1m bars in hand at scan time. The engine plugin is incremental: bars
arrive one at a time. We reproduce trusted's logic by detecting "newly-
closed HTF/LTF candles" each bar and running the same checks at that
moment. Result is the same set of stages and setups; just produced
event-driven rather than batch.

Helpers reused from `app.strategies.fractal_amd.signals` (already a list[Bar]
port of `C:/Fractal-AMD/src/features/...`):
  candle_bounds, get_ohlc, detect_smt_at_level, detect_rejection,
  detect_fvgs, find_nearest_unfilled_fvg, resample_bars

Continuation-OF gate uses the local list[Bar] port at
`app.strategies.fractal_amd_trusted.orderflow.compute_continuation_of`.
"""
from __future__ import annotations

import bisect
import datetime as dt
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from app.backtest.orders import BracketOrder, OrderIntent, Side
from app.backtest.strategy import Bar, Context, Strategy

from app.strategies.fractal_amd.signals import (
    ET,
    candle_bounds,
    detect_rejection,
    detect_smt_at_level,
    find_nearest_unfilled_fvg,
    get_ohlc,
    resample_bars,
)
from app.strategies.fractal_amd_trusted.config import FractalAMDTrustedConfig
from app.strategies.fractal_amd_trusted.fvg_port import detect_fvgs_trusted
from app.strategies.fractal_amd_trusted.orderflow import compute_continuation_of

if TYPE_CHECKING:
    from app.backtest.orders import Fill


Direction = Literal["BULLISH", "BEARISH"]


def _bars_in_range(
    bars: list[Bar], start: dt.datetime, end: dt.datetime
) -> list[Bar]:
    """Slice bars to half-open [start, end) using bisect on ts_event."""
    if not bars:
        return []
    lo = bisect.bisect_left(bars, start, key=lambda b: b.ts_event)
    hi = bisect.bisect_left(bars, end, key=lambda b: b.ts_event)
    return bars[lo:hi]


@dataclass
class _HTFStage:
    """One confirmed HTF stage (session or 1H, SMT or rejection)."""

    timeframe: str
    direction: Direction
    candle_start: dt.datetime
    candle_end: dt.datetime
    # Cached expansion window (computed once when the stage is added).
    exp_s: dt.datetime
    exp_e: dt.datetime
    # Once the LTF SMT is found, we hold the match here and wait for the
    # FVG window to fully populate before building the setup. Trusted is
    # batch-mode and has all bars at scan time; we're incremental so we
    # have to defer setup creation until bar.ts_event >= ltf_end + tf_min*5.
    pending_ltf_match: tuple | None = None  # (tf, tf_min, ref_start, ltf_end, fse)


@dataclass
class _Setup:
    """One LTF FVG setup waiting for a touch + entry.

    Mirrors trusted's per-stage `for ltf in ltf_sigs` inner state. Each
    stage produces at most one setup (find_ltf_smt early-returns on the
    first LTF SMT it finds across 15m/5m).
    """

    stage: _HTFStage
    ltf_tf: str
    ltf_min: int
    ref_start: dt.datetime  # fss in trusted; FVG window start
    ltf_candle_end: dt.datetime  # le in trusted
    fvgs: list  # list[FVG] from detect_fvgs
    waiting: bool = False
    pending_fvg: object | None = None  # FVG object — the touched zone
    filled: bool = False  # set after entry is emitted


@dataclass
class _DayState:
    """Per-trading-day state, rebuilt at each 18:00 ET rollover."""

    day: dt.date
    htf_bounds: dict[str, list[tuple[dt.datetime, dt.datetime]]] = field(
        default_factory=dict
    )
    htf_stages: list[_HTFStage] = field(default_factory=list)
    scanned_htf_pairs: set[tuple[str, dt.datetime]] = field(default_factory=set)
    setups: list[_Setup] = field(default_factory=list)
    # Stages whose LTF-SMT search is finished (either found one or window
    # passed without finding one).
    completed_ltf_search: set[int] = field(default_factory=set)
    trades_today: int = 0
    entries_today: set[tuple[str, dt.datetime]] = field(default_factory=set)


class FractalAMDTrusted(Strategy):
    """Engine plugin port of `trusted_multiyear_bt.py`.

    Processes bars incrementally but reproduces trusted's batch logic
    (HTF stages from full day's bars, LTF SMTs in expansion windows,
    FVG detection on resampled LTF bars, touch + next-bar-open entry).
    """

    name: str = "fractal_amd_trusted"

    def __init__(self, config: FractalAMDTrustedConfig):
        self.config = config
        self.aux_history: dict[str, list[Bar]] = {}
        self.day_state: _DayState | None = None
        self.debug: bool = False  # set True for verbose stage / setup logging

    def _debug_log(self, msg: str) -> None:
        if self.debug:
            print(msg)

    # ------------------------------------------------------------------
    # Engine lifecycle
    # ------------------------------------------------------------------

    def on_start(self, context: Context) -> None:
        self.aux_history = {sym: [] for sym in self.config.aux_symbols}
        self.day_state = None

    def on_bar(self, bar: Bar, context: Context) -> "list[OrderIntent]":
        # Accumulate aux history.
        for sym in self.config.aux_symbols:
            aux_bar = context.aux.get(sym)
            if aux_bar is not None:
                self.aux_history.setdefault(sym, []).append(aux_bar)

        # Day rollover at 18:00 ET (Globex open). Trusted's per-day loop
        # uses `day = pd.Timestamp(date)` and pulls bars in
        # [prev 18:00, current 17:00]. We treat "trading day" as the
        # calendar date of the 17:00 close, i.e. bars at 18:00+ on day
        # N belong to trading day N+1.
        bar_et = bar.ts_event.astimezone(ET)
        if bar_et.hour >= 18:
            trading_day = (bar_et + dt.timedelta(days=1)).date()
        else:
            trading_day = bar_et.date()

        if self.day_state is None or self.day_state.day != trading_day:
            self._roll_day(trading_day)

        # Already hit max trades for the day — short-circuit.
        if self.day_state.trades_today >= self.config.max_trades_per_day:
            return []

        # Engine guards: only one position at a time.
        if context.position is not None:
            return []

        # 1. Scan newly-closed HTF candle pairs for stages.
        self._scan_new_htf_pairs(bar, context)

        # 2. For each stage whose LTF SMT search isn't yet done, run it.
        self._search_ltf_smts(bar, context)

        # 3. Process touch-then-next-bar-open entries.
        return self._process_entries(bar, context)

    def on_fill(self, fill: "Fill", context: Context) -> None:
        # trades_today is bumped at intent emission (mirrors trusted's
        # `n_today += 1` at the entry point, not when fill happens).
        return None

    def on_end(self, context: Context) -> None:
        return None

    # ------------------------------------------------------------------
    # Day rollover
    # ------------------------------------------------------------------

    def _roll_day(self, trading_day: dt.date) -> None:
        """Reset day state and pre-compute HTF candle bounds for the day."""
        # day_dt is the day's 00:00 ET reference that signals.candle_bounds
        # uses internally — same convention as trusted's `day = pd.Timestamp(date)`.
        day_dt = dt.datetime(
            trading_day.year, trading_day.month, trading_day.day, tzinfo=ET
        )
        bounds = {
            tf: candle_bounds(day_dt, tf)
            for tf in self.config.htf_timeframes
        }
        self.day_state = _DayState(day=trading_day, htf_bounds=bounds)

    # ------------------------------------------------------------------
    # HTF stage scanning
    # ------------------------------------------------------------------

    def _bars_by_asset_for(
        self,
        context: Context,
        start: dt.datetime,
        end: dt.datetime,
    ) -> dict[str, list[Bar]]:
        """Build the per-asset window dict that signals helpers expect.

        Helpers iterate the lists we hand them; pre-slicing to the
        relevant time range keeps that iteration cheap.
        """
        primary_window = _bars_in_range(context.history, start, end)
        out: dict[str, list[Bar]] = {self.config.primary_symbol: primary_window}
        for sym in self.config.aux_symbols:
            out[sym] = _bars_in_range(self.aux_history.get(sym, []), start, end)
        return out

    def _scan_new_htf_pairs(self, bar: Bar, context: Context) -> None:
        """For each HTF timeframe, scan candle pairs that just closed.

        Mirrors trusted lines 109-132. SMT (high sweep → BEARISH) +
        SMT (low sweep → BULLISH) + rejection per-direction. Either
        signal type confirms the stage.
        """
        ds = self.day_state
        assert ds is not None

        for tf in self.config.htf_timeframes:
            bounds = ds.htf_bounds[tf]
            for i, (cur_start, cur_end) in enumerate(bounds):
                if i == 0:
                    continue
                if cur_end > bar.ts_event:
                    # Candle hasn't closed yet — skip (will retry on a
                    # later bar). All later candles in this TF are also
                    # unclosed (bounds is sorted).
                    break
                key = (tf, cur_start)
                if key in ds.scanned_htf_pairs:
                    continue
                ds.scanned_htf_pairs.add(key)

                ref_start, ref_end = bounds[i - 1]

                # Bars-by-asset window covers [ref_start, cur_end).
                bba = self._bars_by_asset_for(context, ref_start, cur_end)
                # Trusted requires every symbol have a non-None ref OHLC
                # AND a non-empty cur range to even consider this pair.
                ref_ohlc = {
                    sym: get_ohlc(bars, ref_start, ref_end)
                    for sym, bars in bba.items()
                }
                if any(v is None for v in ref_ohlc.values()):
                    # Rejection block in trusted is gated by `if all(v is
                    # not None ...)` — same gate here. Without ref OHLC
                    # we still try rejection if the cur ranges have bars.
                    pass

                # Rejection signals (trusted line 113).
                rejs = detect_rejection(
                    bba, cur_start, cur_end, ref_start, ref_end, tf
                )

                # SMT signals (trusted lines 116-128). Only run when ref
                # OHLC is computable AND every symbol has bars in the
                # cur range.
                smts: list[Direction] = []
                if all(v is not None for v in ref_ohlc.values()):
                    cur_bba = {
                        sym: _bars_in_range(bars, cur_start, cur_end)
                        for sym, bars in bba.items()
                    }
                    if all(len(b) > 0 for b in cur_bba.values()):
                        hi_levels = {sym: ref_ohlc[sym].high for sym in bba}
                        s_hi = detect_smt_at_level(
                            cur_bba, hi_levels, "high", cur_start, cur_end
                        )
                        if s_hi.has_smt and s_hi.direction == "BEARISH":
                            smts.append("BEARISH")
                        lo_levels = {sym: ref_ohlc[sym].low for sym in bba}
                        s_lo = detect_smt_at_level(
                            cur_bba, lo_levels, "low", cur_start, cur_end
                        )
                        if s_lo.has_smt and s_lo.direction == "BULLISH":
                            smts.append("BULLISH")

                # Per-direction stage commit (trusted lines 129-132).
                for d in ("BEARISH", "BULLISH"):
                    has_smt = d in smts
                    has_rej = any(r.direction == d for r in rejs)
                    if not (has_smt or has_rej):
                        continue
                    dur = cur_end - cur_start
                    exp_s = cur_end
                    exp_e = exp_s + dur * 2
                    ds.htf_stages.append(
                        _HTFStage(
                            timeframe=tf,
                            direction=d,  # type: ignore[arg-type]
                            candle_start=cur_start,
                            candle_end=cur_end,
                            exp_s=exp_s,
                            exp_e=exp_e,
                        )
                    )

    # ------------------------------------------------------------------
    # LTF SMT search inside expansion window
    # ------------------------------------------------------------------

    def _find_ltf_smt(
        self,
        stage: _HTFStage,
        bar: Bar,
        context: Context,
        *,
        only_tf: str | None = None,
    ) -> tuple[str, int, dt.datetime, dt.datetime] | None:
        """Replicate trusted's `find_ltf_smt`. Iterate `(15m, 5m)`; for
        each, walk candle pairs in the expansion window (where the
        later candle has CLOSED by `bar.ts_event`); return the first
        candle-pair with same-direction LTF SMT. Returns
        (tf, tf_min, ref_start, candle_end) or None.

        `only_tf`: when set, restricts the search to that single TF.
        Used by the caller to do a 15m-only eager pass first, then a
        5m-only fallback once all 15m candles in the expansion window
        have closed without a match.
        """
        ds = self.day_state
        assert ds is not None
        day_dt = dt.datetime(ds.day.year, ds.day.month, ds.day.day, tzinfo=ET)

        for tf, tf_min in self.config.ltf_timeframes:
            if only_tf is not None and tf != only_tf:
                continue
            ltf_bounds = candle_bounds(day_dt, tf)
            rel = [
                (s, e)
                for s, e in ltf_bounds
                if s >= stage.exp_s
                and e <= stage.exp_e + dt.timedelta(minutes=1)
            ]
            for i in range(1, len(rel)):
                cs, ce = rel[i]
                rs, re = rel[i - 1]
                if ce > bar.ts_event:
                    # Cur candle hasn't closed yet — stop (later are also
                    # unclosed; rel is sorted).
                    break
                bba = self._bars_by_asset_for(context, rs, ce)
                ref_ohlc = {
                    sym: get_ohlc(bars, rs, re)
                    for sym, bars in bba.items()
                }
                if any(v is None for v in ref_ohlc.values()):
                    continue
                cur_bba = {
                    sym: _bars_in_range(bars, cs, ce)
                    for sym, bars in bba.items()
                }
                if any(len(b) == 0 for b in cur_bba.values()):
                    continue
                if stage.direction == "BEARISH":
                    levels = {sym: ref_ohlc[sym].high for sym in bba}
                    s = detect_smt_at_level(cur_bba, levels, "high", cs, ce)
                    if s.has_smt and s.direction == "BEARISH":
                        return (tf, tf_min, rs, ce)
                else:
                    levels = {sym: ref_ohlc[sym].low for sym in bba}
                    s = detect_smt_at_level(cur_bba, levels, "low", cs, ce)
                    if s.has_smt and s.direction == "BULLISH":
                        return (tf, tf_min, rs, ce)
        return None

    def _search_ltf_smts(self, bar: Bar, context: Context) -> None:
        """For each stage whose LTF SMT search hasn't been done, try it.
        Mark the search done if (a) we found one and built a setup, or
        (b) the expansion window has fully passed without finding one.
        """
        ds = self.day_state
        assert ds is not None
        rth_open = self._rth_open_for(ds.day)
        rth_close = self._rth_close_for(ds.day)

        for idx, stage in enumerate(ds.htf_stages):
            if idx in ds.completed_ltf_search:
                continue
            # Trusted's `sc_s = max(exp_s, rth_s); sc_e = min(exp_e, rth_e);
            # if sc_s >= sc_e: continue` — no overlap with RTH means we
            # never get a chance to enter. Mark complete and move on.
            sc_s = max(stage.exp_s, rth_open)
            sc_e = min(stage.exp_e, rth_close)
            if sc_s >= sc_e:
                ds.completed_ltf_search.add(idx)
                self._debug_log(
                    f"  stage {stage.timeframe} {stage.direction} "
                    f"{stage.candle_start} REJECTED: no RTH overlap "
                    f"(sc_s={sc_s} sc_e={sc_e})"
                )
                continue

            # Step 1: find the LTF SMT match if we don't have one yet.
            # Trusted's batch `find_ltf_smt` iterates 15m fully then 5m,
            # returning first match. 15m has STRICT priority over 5m.
            #
            # Incremental compromise: eager on both TFs. When a 15m
            # match closes, we lock it in — overrides any 5m tentative.
            # If a 5m closes with SMT before any 15m, we tentatively
            # lock in the 5m. A later 15m (closing before exp_e) WILL
            # override the tentative 5m if found. Setup creation
            # remains at fse (the FVG window close), at which point the
            # current pending_ltf_match is final for this stage's
            # purposes — a 15m closing strictly AFTER fse won't override
            # an already-built setup. This matches trusted's batch
            # output for ~90% of stages; the residual mismatch is the
            # case where a 15m closes between the 5m's fse and exp_e.
            if stage.pending_ltf_match is None:
                if bar.ts_event < stage.exp_s:
                    continue
                # Prefer 15m if any has closed with SMT.
                ltf_match = self._find_ltf_smt(stage, bar, context, only_tf="15m")
                if ltf_match is None:
                    # Fall through to 5m if no 15m yet.
                    ltf_match = self._find_ltf_smt(
                        stage, bar, context, only_tf="5m"
                    )
                if ltf_match is None and bar.ts_event > stage.exp_e:
                    ds.completed_ltf_search.add(idx)
                    self._debug_log(
                        f"  stage {stage.timeframe} {stage.direction} "
                        f"{stage.candle_start} REJECTED: no LTF SMT"
                    )
                    continue
                if ltf_match is not None:
                    tf, tf_min, ref_start, ltf_end = ltf_match
                    fse = min(
                        ltf_end + dt.timedelta(minutes=tf_min * 5),
                        rth_close,
                    )
                    stage.pending_ltf_match = (
                        tf, tf_min, ref_start, ltf_end, fse
                    )
                    self._debug_log(
                        f"  stage {stage.timeframe} {stage.direction} "
                        f"{stage.candle_start} LTF MATCH {tf} ref={ref_start} "
                        f"ltf_end={ltf_end} fse={fse}"
                    )
                continue
            # Step 1b: while pending_ltf_match is a 5m and we haven't
            # built the setup yet, keep checking for 15m overrides on
            # each bar. Trusted's strict 15m-priority means a 15m match
            # found before the 5m's setup is built should replace it.
            tf_p, tf_min_p, _, _, fse_p = stage.pending_ltf_match
            if tf_p == "5m" and bar.ts_event < fse_p:
                upgrade = self._find_ltf_smt(stage, bar, context, only_tf="15m")
                if upgrade is not None:
                    tf, tf_min, ref_start, ltf_end = upgrade
                    fse = min(
                        ltf_end + dt.timedelta(minutes=tf_min * 5),
                        rth_close,
                    )
                    stage.pending_ltf_match = (
                        tf, tf_min, ref_start, ltf_end, fse
                    )
                    self._debug_log(
                        f"  stage {stage.timeframe} {stage.direction} "
                        f"{stage.candle_start} 15m UPGRADE: was 5m, now {tf} "
                        f"ref={ref_start} ltf_end={ltf_end}"
                    )

            # Step 2: have a pending match. Build the setup once the
            # FVG window has fully populated (incremental processing
            # vs trusted's batch — trusted has all day's bars at scan).
            tf, tf_min, ref_start, ltf_end, fse = stage.pending_ltf_match
            if bar.ts_event < fse:
                continue
            setup = self._build_setup_from_ltf(
                stage, tf, tf_min, ref_start, ltf_end, bar, context
            )
            if setup is not None:
                ds.setups.append(setup)
                self._debug_log(
                    f"  stage {stage.timeframe} {stage.direction} "
                    f"{stage.candle_start} SETUP {tf} fvgs={len(setup.fvgs)}"
                )
            else:
                self._debug_log(
                    f"  stage {stage.timeframe} {stage.direction} "
                    f"{stage.candle_start} LTF {tf} but no FVG (post-window)"
                )
            ds.completed_ltf_search.add(idx)

    def _build_setup_from_ltf(
        self,
        stage: _HTFStage,
        tf: str,
        tf_min: int,
        ref_start: dt.datetime,
        ltf_end: dt.datetime,
        bar: Bar,
        context: Context,
    ) -> _Setup | None:
        """Replicate trusted lines 146-154: detect FVGs on resampled LTF
        bars in the FVG window, return a setup with the FVG list. None
        if there aren't enough bars / no FVGs.
        """
        ds = self.day_state
        assert ds is not None
        rth_close = self._rth_close_for(ds.day)
        fss = ref_start
        fse = min(ltf_end + dt.timedelta(minutes=tf_min * 5), rth_close)
        primary_window = _bars_in_range(context.history, fss, fse)
        self._debug_log(
            f"    fvg_window {fss}->{fse} primary_bars={len(primary_window)}"
        )
        if len(primary_window) < tf_min * 3:
            self._debug_log(f"    REJECT: <{tf_min*3} primary bars")
            return None
        ltf_bars = resample_bars(primary_window, tf_min)
        self._debug_log(f"    resampled to {len(ltf_bars)} {tf_min}m candles")
        if len(ltf_bars) < 3:
            self._debug_log(f"    REJECT: <3 LTF bars")
            return None
        fvgs = detect_fvgs_trusted(
            ltf_bars,
            stage.direction,  # type: ignore[arg-type]
            min_gap_pct=self.config.fvg_min_gap_pct,
            expiry_bars=self.config.fvg_expiry_bars,
        )
        self._debug_log(f"    detect_fvgs returned {len(fvgs)} FVGs")
        if not fvgs:
            return None
        return _Setup(
            stage=stage,
            ltf_tf=tf,
            ltf_min=tf_min,
            ref_start=fss,
            ltf_candle_end=ltf_end,
            fvgs=list(fvgs),
        )

    # ------------------------------------------------------------------
    # Touch + entry
    # ------------------------------------------------------------------

    def _process_entries(
        self, bar: Bar, context: Context
    ) -> list[OrderIntent]:
        """For each setup, check this bar for a touch (and on the next
        bar after touch, try to emit an entry). Trusted's inner loop
        per setup, replicated incrementally.

        Why we DON'T just emit on the touch bar (which would fill at
        T+1's open via engine semantics, matching trusted's `ep =
        T+1.open` perfectly): trusted's validation gates fire AT T+1
        (entry-window check, dedup bucket, cont_of computed using T+1's
        history index). If we emit on T those gates fire 1 bar early,
        which can alter cont_of's score. We instead use the waiting
        pattern: detect touch on T, emit BracketOrder on T+1 (so gates
        validate with T+1 data and `bar.open` = T+1.open is the correct
        ep for stop/target math). The trade-off is that the engine then
        fills the entry at T+2.open (1 bar later than trusted's
        T+1.open). Net effect: 0-5pt entry-price drift per trade, no
        gate-timing skew.
        """
        ds = self.day_state
        assert ds is not None

        intents: list[OrderIntent] = []

        for setup in ds.setups:
            if setup.filled:
                continue
            if ds.trades_today >= self.config.max_trades_per_day:
                break

            # Step 1: if touched on prior bar, attempt entry on this bar.
            if setup.waiting and setup.pending_fvg is not None:
                intent = self._try_enter(setup, bar, context)
                setup.waiting = False
                setup.pending_fvg = None
                if intent is not None:
                    intents.append(intent)
                    setup.filled = True
                    bar_et = bar.ts_event.astimezone(ET)
                    bucket_min = (
                        bar_et.minute // self.config.entry_dedup_minutes
                    ) * self.config.entry_dedup_minutes
                    bucket = bar_et.replace(
                        minute=bucket_min, second=0, microsecond=0
                    )
                    ds.entries_today.add((setup.stage.direction, bucket))
                    ds.trades_today += 1
                    break
                # Trusted's per-setup `continue` after waiting handling
                # (skip touch detection on the same bar).
                continue

            # Step 2: touch detection on this bar (sets waiting for next).
            bcl = bar.close
            bhv = bar.high
            blv = bar.low
            bsi = int(
                (bar.ts_event - setup.ref_start).total_seconds()
                / 60
                / setup.ltf_min
            )
            nearest = find_nearest_unfilled_fvg(
                setup.fvgs,
                bcl,
                bsi,
                self.config.fvg_nearest_max_bar_age,
            )
            if nearest is None:
                continue
            if setup.stage.direction == "BULLISH":
                entered = blv <= nearest.high and bhv >= nearest.low
            else:
                entered = bhv >= nearest.low and blv <= nearest.high
            if entered:
                setup.waiting = True
                setup.pending_fvg = nearest

        return intents

    def _try_enter(
        self, setup: _Setup, bar: Bar, context: Context
    ) -> OrderIntent | None:
        """Validate the gates and emit a BracketOrder. Mirrors trusted
        lines 167-219.
        """
        ds = self.day_state
        assert ds is not None
        bar_et = bar.ts_event.astimezone(ET)

        # Entry-window gate: trusted is `et.hour < 9 or et.hour >= 14`,
        # combined with rth_s = 09:30. The 09:30 part is enforced via
        # `ess = max(le, rth_s)` upstream so we only need the
        # hour-based gate here. We do enforce 09:30 via `bar_et.hour ==
        # 9 and bar_et.minute < 30` for safety.
        if bar_et.hour < self.config.rth_open_hour:
            return None
        if (
            bar_et.hour == self.config.rth_open_hour
            and bar_et.minute < self.config.rth_open_min
        ):
            return None
        if bar_et.hour >= self.config.rth_close_hour:
            return None

        # 15-minute direction dedup.
        bucket_min = (
            bar_et.minute // self.config.entry_dedup_minutes
        ) * self.config.entry_dedup_minutes
        bucket = bar_et.replace(minute=bucket_min, second=0, microsecond=0)
        if (setup.stage.direction, bucket) in ds.entries_today:
            return None

        # Continuation-OF gate (trusted lines 178-181).
        history = context.history
        # Find the bar's index in context.history. Engine appends each
        # bar to history BEFORE on_bar is called, so the current bar is
        # at history[-1].
        if not history:
            return None
        co = compute_continuation_of(
            history,
            len(history) - 1,
            setup.stage.direction,
            lookback=self.config.co_lookback,
            atr=self.config.co_atr,
        )
        cos = co.get("co_continuation_score", 0) if co else 0
        if cos < self.config.min_co_score:
            return None

        # Entry / stop / target (trusted lines 183-188).
        ep = bar.open
        pending = setup.pending_fvg
        assert pending is not None
        if setup.stage.direction == "BEARISH":
            stop = pending.high + self.config.stop_buffer_pts
            risk = stop - ep
            target = ep - risk * self.config.target_r
            side = Side.SHORT
        else:
            stop = pending.low - self.config.stop_buffer_pts
            risk = ep - stop
            target = ep + risk * self.config.target_r
            side = Side.LONG

        if risk <= 0 or risk > self.config.max_risk_pts:
            return None
        # `min_risk_pts` defaults to 0 (faithful trusted reproduction);
        # live deployments set this to 8 to drop unfillable tight stops.
        if risk < self.config.min_risk_pts:
            return None

        return BracketOrder(
            side=side,
            qty=1,
            stop_price=stop,
            target_price=target,
            max_hold_bars=self.config.max_hold_bars,
            # Trusted's `ep = bar.open` of the bar AFTER the touch bar +
            # gates checked at the same bar's data. fill_immediately
            # makes the engine fill at THIS bar's open instead of next
            # bar's — entry-fill price, gate timing, and ep math all on
            # the same bar — exactly trusted.
            fill_immediately=True,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _rth_open_for(self, day: dt.date) -> dt.datetime:
        return dt.datetime(
            day.year,
            day.month,
            day.day,
            self.config.rth_open_hour,
            self.config.rth_open_min,
            tzinfo=ET,
        )

    def _rth_close_for(self, day: dt.date) -> dt.datetime:
        # Trusted's `rth_e = day.replace(hour=16)` — 16:00 ET. The
        # entry-window cap is rth_close_hour (14) which is enforced
        # separately; rth_close=16:00 is the FVG/scan-window cap.
        return dt.datetime(day.year, day.month, day.day, 16, tzinfo=ET)

    @classmethod
    def from_config(
        cls, params: dict, *, tick_size: float, qty: int
    ) -> "FractalAMDTrusted":
        del tick_size, qty
        return cls(FractalAMDTrustedConfig.from_params(params))
