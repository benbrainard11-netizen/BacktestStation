"""Unit tests for entry validation + BracketOrder emission.

Phase 3 of the Fractal AMD port. Drives `_try_emit_entry` and
`_validate_and_build_intent` directly with hand-built TOUCHED setups
to assert each gate (window, risk, dedup, touch-age) fires correctly.
"""

from __future__ import annotations

import datetime as dt

from app.backtest.orders import BracketOrder, Side
from app.backtest.strategy import Bar
from app.strategies.fractal_amd import FractalAMD
from app.strategies.fractal_amd.config import FractalAMDConfig
from app.strategies.fractal_amd.signals import ET, Setup


# --- Fixtures ----------------------------------------------------------


def _bar(*, ts, o=21000.0, h=21001.0, l=20999.0, c=21000.5):
    return Bar(
        ts_event=ts,
        symbol="NQ.c.0",
        open=o,
        high=h,
        low=l,
        close=c,
        volume=10,
        trade_count=1,
        vwap=(h + l) / 2,
    )


def _touched_bearish_setup(
    *,
    fvg_low=21010.0,
    fvg_high=21020.0,
    touch_bar_time: dt.datetime | None = None,
) -> Setup:
    s = Setup(
        direction="BEARISH",
        htf_tf="1H",
        htf_candle_start=dt.datetime(2026, 4, 24, 14, tzinfo=dt.timezone.utc),
        htf_candle_end=dt.datetime(2026, 4, 24, 15, tzinfo=dt.timezone.utc),
        ltf_tf="5m",
        ltf_candle_end=dt.datetime(2026, 4, 24, 15, tzinfo=dt.timezone.utc),
        fvg_low=fvg_low,
        fvg_high=fvg_high,
        fvg_mid=(fvg_low + fvg_high) / 2,
        status="TOUCHED",
        touch_bar_time=touch_bar_time,
    )
    return s


# --- Happy path --------------------------------------------------------


def test_entry_emits_bearish_bracket_order_with_correct_stop_target():
    """Within window, valid risk, fresh touch -> emits BracketOrder.

    Strategy uses bar.open as entry-price proxy (the engine fills at
    NEXT bar's open + slippage; bar.open is the live-bot reference
    point). bar.close is consulted only by the wrong-side-stop guard.
    """
    cfg = FractalAMDConfig(min_co_score=None)
    s = FractalAMD(cfg)
    # Touch on the prior bar (UTC). Entry window 9:30 ET.
    # 13:30 ET on 2026-04-24 in EDT = 17:30 UTC.
    touch_ts = dt.datetime(2026, 4, 24, 17, 30, tzinfo=dt.timezone.utc)
    s.setups.append(
        _touched_bearish_setup(touch_bar_time=touch_ts, fvg_low=21010, fvg_high=21020)
    )
    s.today = touch_ts.astimezone(ET).date()  # day already rolled

    # bar.open=21008 (entry proxy). bar.close=21015 < stop=21021 — guard ok.
    cur = _bar(
        ts=touch_ts + dt.timedelta(minutes=1), o=21008.0, h=21016.0, l=21006.0,
        c=21015.0,
    )
    intent = s._try_emit_entry(cur)
    assert isinstance(intent, BracketOrder)
    assert intent.side == Side.SHORT
    assert intent.qty == 1
    # stop = fvg_high + buffer = 21020 + 1.0 = 21021
    assert intent.stop_price == 21021.0
    # risk = stop - entry = 21021 - 21008 = 13. target = entry - 3R = 21008 - 39 = 20969.
    assert intent.target_price == 21008.0 - 13 * 3
    # Counters bumped + status flipped.
    assert s.trades_today == 1
    assert s.setups[0].status == "FILLED"


def test_entry_emits_bullish_bracket_order():
    cfg = FractalAMDConfig(min_co_score=None)
    s = FractalAMD(cfg)
    touch_ts = dt.datetime(2026, 4, 24, 17, 30, tzinfo=dt.timezone.utc)
    bull = _touched_bearish_setup(touch_bar_time=touch_ts, fvg_low=21000, fvg_high=21010)
    bull.direction = "BULLISH"
    s.setups.append(bull)
    s.today = touch_ts.astimezone(ET).date()

    # bar.open=21015. bar.close=21010 > stop=20999 — guard ok.
    cur = _bar(
        ts=touch_ts + dt.timedelta(minutes=1), o=21015.0, h=21018.0, l=21008.0,
        c=21010.0,
    )
    intent = s._try_emit_entry(cur)
    assert isinstance(intent, BracketOrder)
    assert intent.side == Side.LONG
    # stop = fvg_low - buffer = 21000 - 1 = 20999
    assert intent.stop_price == 20999.0
    # risk = entry - stop = 21015 - 20999 = 16. target = 21015 + 16*3 = 21063
    assert intent.target_price == 21015.0 + 16 * 3


# --- Gates that should reject ------------------------------------------


def test_entry_rejected_outside_entry_window():
    """Bar at 14:30 ET is past max_entry_hour=14 -> no order, but the
    setup is NOT consumed because we never even called _try_emit_entry
    (the bigger on_bar gate filters it out). Test calls on_bar end-to-end.
    """
    from app.backtest.engine import RunConfig, run as engine_run

    cfg = FractalAMDConfig(min_co_score=None)
    s = FractalAMD(cfg)
    touch_ts = dt.datetime(2026, 4, 24, 18, 30, tzinfo=dt.timezone.utc)  # 14:30 ET
    s.setups.append(_touched_bearish_setup(touch_bar_time=touch_ts))

    # One NQ bar at 14:31 ET, no aux.
    bar = _bar(ts=touch_ts + dt.timedelta(minutes=1))
    config = RunConfig(
        strategy_name="fractal_amd",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
    )
    result = engine_run(s, [bar], config)
    assert result.trades == []  # no trades emitted


def test_entry_rejected_when_risk_exceeds_max():
    cfg = FractalAMDConfig(min_co_score=None, max_risk_pts=50.0)
    s = FractalAMD(cfg)
    touch_ts = dt.datetime(2026, 4, 24, 17, 30, tzinfo=dt.timezone.utc)
    # Entry at 21000, fvg_high=21100 -> stop=21101, risk=101pt > 50
    s.setups.append(
        _touched_bearish_setup(touch_bar_time=touch_ts, fvg_low=21090, fvg_high=21100)
    )
    s.today = touch_ts.astimezone(ET).date()
    cur = _bar(ts=touch_ts + dt.timedelta(minutes=1), o=21000.0)
    intent = s._try_emit_entry(cur)
    assert intent is None
    # Setup reset to WATCHING for re-arm.
    assert s.setups[0].status == "WATCHING"


def test_entry_rejected_when_risk_below_min():
    cfg = FractalAMDConfig(min_co_score=None, min_risk_pts=10.0)
    s = FractalAMD(cfg)
    touch_ts = dt.datetime(2026, 4, 24, 17, 30, tzinfo=dt.timezone.utc)
    # bar.open=21015, fvg_high=21020 -> stop=21021, risk=6pt < 10
    s.setups.append(
        _touched_bearish_setup(touch_bar_time=touch_ts, fvg_low=21010, fvg_high=21020)
    )
    s.today = touch_ts.astimezone(ET).date()
    cur = _bar(
        ts=touch_ts + dt.timedelta(minutes=1), o=21015.0, h=21016.0, l=21014.0,
        c=21015.0,
    )
    intent = s._try_emit_entry(cur)
    assert intent is None
    assert s.setups[0].status == "WATCHING"


def test_entry_rejected_on_dedup_within_15min_bucket():
    """Two touched BEARISH setups in same 15-min bucket -> only one fires."""
    cfg = FractalAMDConfig(min_co_score=None, entry_dedup_minutes=15)
    s = FractalAMD(cfg)
    touch_ts = dt.datetime(2026, 4, 24, 17, 30, tzinfo=dt.timezone.utc)
    # Pre-load entries_today as if we'd already fired.
    bar_et = touch_ts.astimezone(ET) + dt.timedelta(minutes=1)
    bucket = bar_et.replace(minute=(bar_et.minute // 15) * 15, second=0, microsecond=0)
    s.entries_today.add(("BEARISH", bucket))
    s.setups.append(
        _touched_bearish_setup(touch_bar_time=touch_ts, fvg_low=21010, fvg_high=21020)
    )
    s.today = touch_ts.astimezone(ET).date()
    cur = _bar(ts=touch_ts + dt.timedelta(minutes=1), o=21008.0)
    intent = s._try_emit_entry(cur)
    assert intent is None
    assert s.setups[0].status == "WATCHING"


def test_entry_downshifts_to_mnq_when_nq_risk_exceeds_cap():
    """Wide-stop setup that would risk > $500 on 1 NQ contract gets
    auto-downshifted to MNQ (1/10 the contract value) instead of
    being rejected — mirrors the live bot's NQ→MNQ swap.

    Defaults: contract_value=$20/pt, micro_contract_value=$2/pt,
    max_risk_dollars=$500. 31-pt stop risks $620 on NQ (over cap)
    but only $62 on MNQ (well under cap) — downshift expected.
    """
    cfg = FractalAMDConfig(min_co_score=None)
    s = FractalAMD(cfg)
    touch_ts = dt.datetime(2026, 4, 24, 17, 30, tzinfo=dt.timezone.utc)
    s.setups.append(
        _touched_bearish_setup(touch_bar_time=touch_ts, fvg_low=21010, fvg_high=21030)
    )
    s.today = touch_ts.astimezone(ET).date()
    cur = _bar(
        ts=touch_ts + dt.timedelta(minutes=1), o=21000.0, h=21001.0, l=20999.0,
        c=21000.0,
    )

    intent = s._try_emit_entry(cur)
    assert isinstance(intent, BracketOrder)
    # Order carries the MNQ contract value override.
    assert intent.contract_value == 2.0
    assert intent.side == Side.SHORT
    assert s.setups[0].status == "FILLED"


def test_entry_rejected_when_even_mnq_risk_exceeds_cap():
    """Stop too wide for MNQ as well — reject. Catches the case
    where downshifting wouldn't bring dollar risk under the cap.

    300-pt stop on MNQ ($2/pt) = $600, over $500 cap. Should reject.
    NB: max_risk_pts=400 so the points-cap doesn't fire first.
    """
    cfg = FractalAMDConfig(min_co_score=None, max_risk_pts=400.0)
    s = FractalAMD(cfg)
    touch_ts = dt.datetime(2026, 4, 24, 17, 30, tzinfo=dt.timezone.utc)
    s.setups.append(
        _touched_bearish_setup(touch_bar_time=touch_ts, fvg_low=20710, fvg_high=21300)
    )
    s.today = touch_ts.astimezone(ET).date()
    cur = _bar(
        ts=touch_ts + dt.timedelta(minutes=1), o=21000.0, h=21001.0, l=20999.0,
        c=21000.0,
    )

    intent = s._try_emit_entry(cur)
    assert intent is None
    assert s.setups[0].status == "WATCHING"


def test_entry_keeps_nq_when_risk_fits_cap():
    """Tight-stop setup stays on NQ — no downshift needed."""
    cfg = FractalAMDConfig(min_co_score=None)
    s = FractalAMD(cfg)
    touch_ts = dt.datetime(2026, 4, 24, 17, 30, tzinfo=dt.timezone.utc)
    # 12-pt stop = $260 on NQ. Well under cap.
    s.setups.append(
        _touched_bearish_setup(touch_bar_time=touch_ts, fvg_low=21000, fvg_high=21012)
    )
    s.today = touch_ts.astimezone(ET).date()
    cur = _bar(
        ts=touch_ts + dt.timedelta(minutes=1), o=21000.0, h=21002.0, l=20999.0,
        c=21000.0,
    )

    intent = s._try_emit_entry(cur)
    assert isinstance(intent, BracketOrder)
    # No override — engine will use RunConfig.contract_value (=NQ).
    assert intent.contract_value is None


def test_entry_rejected_when_fill_proxy_lands_on_wrong_side_of_stop_short():
    """Bearish setup where bar.close has rallied THROUGH fvg_high+buffer
    by the time the validation bar closes — i.e., the bracket's stop
    would land BELOW the actual fill, acting as a near-target instead
    of a loss cap.

    Pre-fix this trade fired with risk computed against bar.open and
    silently produced a wrong-side stop. Post-fix the risk gate uses
    bar.close as the entry-price proxy, so risk goes non-positive and
    the trade is rejected.

    Concrete numbers: fvg_high=21020 -> stop=21021. bar.close=21030
    (price has rallied past the stop level). risk = 21021 - 21030 = -9.
    """
    cfg = FractalAMDConfig(min_co_score=None)
    s = FractalAMD(cfg)
    touch_ts = dt.datetime(2026, 4, 24, 17, 30, tzinfo=dt.timezone.utc)
    s.setups.append(
        _touched_bearish_setup(touch_bar_time=touch_ts, fvg_low=21010, fvg_high=21020)
    )
    s.today = touch_ts.astimezone(ET).date()
    cur = _bar(
        ts=touch_ts + dt.timedelta(minutes=1),
        o=21010.0, h=21035.0, l=21010.0, c=21030.0,
    )

    intent = s._try_emit_entry(cur)
    assert intent is None
    # Terminal — setup reset to WATCHING (geometry won't change).
    assert s.setups[0].status == "WATCHING"


def test_entry_rejected_when_fill_proxy_lands_on_wrong_side_of_stop_long():
    """Bullish-mirror of the wrong-side guard. fvg_low=21010 ->
    stop=21009. bar.close=21000 (price has fallen below the stop level).
    risk = 21000 - 21009 = -9. Trade must reject.
    """
    cfg = FractalAMDConfig(min_co_score=None)
    s = FractalAMD(cfg)
    touch_ts = dt.datetime(2026, 4, 24, 17, 30, tzinfo=dt.timezone.utc)
    bull = _touched_bearish_setup(touch_bar_time=touch_ts, fvg_low=21010, fvg_high=21020)
    bull.direction = "BULLISH"
    s.setups.append(bull)
    s.today = touch_ts.astimezone(ET).date()
    cur = _bar(
        ts=touch_ts + dt.timedelta(minutes=1),
        o=21015.0, h=21015.0, l=20995.0, c=21000.0,
    )

    intent = s._try_emit_entry(cur)
    assert intent is None
    assert s.setups[0].status == "WATCHING"


def test_entry_rejected_on_stale_touch():
    """Touch too long ago -> setup resets, no order."""
    cfg = FractalAMDConfig(min_co_score=None, entry_max_bars_after_touch=3)
    s = FractalAMD(cfg)
    touch_ts = dt.datetime(2026, 4, 24, 17, 30, tzinfo=dt.timezone.utc)
    s.setups.append(
        _touched_bearish_setup(touch_bar_time=touch_ts, fvg_low=21010, fvg_high=21020)
    )
    s.today = touch_ts.astimezone(ET).date()
    # 10 bars later.
    cur = _bar(ts=touch_ts + dt.timedelta(minutes=10), o=21008.0)
    intent = s._try_emit_entry(cur)
    assert intent is None
    assert s.setups[0].status == "WATCHING"


def test_entry_waits_on_touch_bar_keeps_setup_touched():
    """Entry must be on the bar AFTER the touch, not the touch bar itself
    (prevents lookahead within the touch bar). This is a TRANSIENT
    blocker — the setup stays TOUCHED so the next bar can fire it.
    Resetting to WATCHING here was the original "0 trades" bug.
    """
    cfg = FractalAMDConfig(min_co_score=None)
    s = FractalAMD(cfg)
    touch_ts = dt.datetime(2026, 4, 24, 17, 30, tzinfo=dt.timezone.utc)
    s.setups.append(
        _touched_bearish_setup(touch_bar_time=touch_ts, fvg_low=21010, fvg_high=21020)
    )
    s.today = touch_ts.astimezone(ET).date()
    # SAME bar as touch.
    cur = _bar(ts=touch_ts, o=21008.0)
    intent = s._try_emit_entry(cur)
    assert intent is None
    # Stays TOUCHED so the next bar can fire it.
    assert s.setups[0].status == "TOUCHED"
    assert s.setups[0].touch_bar_time == touch_ts


def test_entry_fires_on_bar_after_touch_after_initial_wait():
    """End-to-end transient sequence: bar T flips a setup to TOUCHED;
    _try_emit_entry on bar T returns None (wait, status stays TOUCHED);
    _try_emit_entry on bar T+1 fires the BracketOrder.

    This is the canonical "touched setup fires on the next bar"
    scenario the strategy port was silently dropping before the
    transient/terminal validation split landed.
    """
    cfg = FractalAMDConfig(min_co_score=None)
    s = FractalAMD(cfg)
    touch_ts = dt.datetime(2026, 4, 24, 17, 30, tzinfo=dt.timezone.utc)
    s.setups.append(
        _touched_bearish_setup(
            touch_bar_time=touch_ts, fvg_low=21010, fvg_high=21020
        )
    )
    s.today = touch_ts.astimezone(ET).date()

    # Bar T (same minute as the recorded touch).
    bar_t = _bar(ts=touch_ts, o=21008.0)
    intent_t = s._try_emit_entry(bar_t)
    assert intent_t is None
    assert s.setups[0].status == "TOUCHED"  # transient — keep waiting

    # Bar T+1 — should now fire.
    bar_t1 = _bar(ts=touch_ts + dt.timedelta(minutes=1), o=21008.0)
    intent_t1 = s._try_emit_entry(bar_t1)
    assert isinstance(intent_t1, BracketOrder)
    assert intent_t1.side == Side.SHORT
    assert s.setups[0].status == "FILLED"
    assert s.trades_today == 1


def test_entry_max_trades_per_day_cap_blocks_further_entries():
    """Once trades_today >= max_trades_per_day, on_bar bails before
    even running entry logic."""
    cfg = FractalAMDConfig(min_co_score=None, max_trades_per_day=1)
    s = FractalAMD(cfg)
    touch_ts = dt.datetime(2026, 4, 24, 17, 30, tzinfo=dt.timezone.utc)
    s.setups.append(
        _touched_bearish_setup(touch_bar_time=touch_ts, fvg_low=21010, fvg_high=21020)
    )
    s.today = touch_ts.astimezone(ET).date()
    s.trades_today = 1  # already at cap

    # End-to-end via on_bar (which checks the cap).
    from app.backtest.strategy import Context
    ctx = Context(
        now=touch_ts + dt.timedelta(minutes=1),
        bar_index=1,
        equity=25000.0,
        initial_equity=25000.0,
        position=None,
    )
    cur = _bar(ts=touch_ts + dt.timedelta(minutes=1), o=21008.0)
    intents = s.on_bar(cur, ctx)
    assert intents == []
    # Setup left as TOUCHED (we bailed before the entry path).
    assert s.setups[0].status == "TOUCHED"
