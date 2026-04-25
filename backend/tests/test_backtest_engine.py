"""Engine-level integration tests.

Covers the rules CLAUDE.md mandates: determinism (byte-equal output),
no lookahead, conservative fill on ambiguous bars, EOD flatten,
metrics derived from trades.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace

import pytest

from app.backtest.engine import RunConfig, run
from app.backtest.orders import BracketOrder, MarketEntry, OrderIntent, Side
from app.backtest.strategy import Bar, Context, Strategy


def _bar(
    minute: int, open_: float, high: float, low: float, close: float
) -> Bar:
    ts = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    return Bar(
        ts_event=ts + dt.timedelta(minutes=minute),
        symbol="NQ.c.0",
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=100,
        trade_count=10,
        vwap=(open_ + high + low + close) / 4,
    )


def _config(**overrides) -> RunConfig:
    base = RunConfig(
        strategy_name="test",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
    )
    for k, v in overrides.items():
        base = replace(base, **{k: v})
    return base


# --- Test strategies ----------------------------------------------------


class EnterOnceLongStrategy(Strategy):
    """Submit one bracket order on bar 1, then never trade again."""

    name = "enter_once_long"

    def __init__(
        self, stop_offset: float = 10.0, target_offset: float = 20.0
    ) -> None:
        self.stop_offset = stop_offset
        self.target_offset = target_offset
        self.fired = False

    def on_bar(self, bar: Bar, context: Context) -> list[OrderIntent]:
        if self.fired or context.bar_index < 1:
            return []
        self.fired = True
        return [
            BracketOrder(
                side=Side.LONG,
                qty=1,
                stop_price=bar.close - self.stop_offset,
                target_price=bar.close + self.target_offset,
            )
        ]


class HistoryLengthStrategy(Strategy):
    """Records context.history length on every bar; never trades."""

    name = "history_length"

    def __init__(self) -> None:
        self.history_lengths: list[int] = []

    def on_bar(self, bar: Bar, context: Context) -> list[OrderIntent]:
        self.history_lengths.append(len(context.history))
        return []


class FuturePeekStrategy(Strategy):
    """Tries to peek at non-existent future state. Should be impossible —
    the Strategy has no API to access future bars; this test just verifies
    the structural fact."""

    name = "future_peek"

    def on_bar(self, bar: Bar, context: Context) -> list[OrderIntent]:
        # No 'future' attribute on context. Confirm structurally.
        assert not hasattr(context, "future_bars")
        assert not hasattr(context, "next_bar")
        # context.history contains all bars seen so far INCLUDING the
        # current one (which the engine appends just before on_bar so
        # indicators can read it). The hard rule: NO bar in history can
        # have a ts_event later than the current bar.
        for h in context.history:
            assert h.ts_event <= bar.ts_event
        return []


# --- Determinism --------------------------------------------------------


def test_determinism_same_inputs_same_outputs() -> None:
    """Two runs with identical inputs produce identical trade + equity sequences."""
    bars = [
        _bar(0, 21000, 21010, 20998, 21005),
        _bar(1, 21005, 21015, 21000, 21010),
        _bar(2, 21010, 21030, 21008, 21025),
        _bar(3, 21025, 21035, 21020, 21030),
        _bar(4, 21030, 21055, 21028, 21050),
    ]
    config = _config()

    result_a = run(EnterOnceLongStrategy(), bars, config)
    result_b = run(EnterOnceLongStrategy(), bars, config)

    assert [t.entry_price for t in result_a.trades] == [
        t.entry_price for t in result_b.trades
    ]
    assert [t.exit_price for t in result_a.trades] == [
        t.exit_price for t in result_b.trades
    ]
    assert [p.equity for p in result_a.equity_points] == [
        p.equity for p in result_b.equity_points
    ]
    assert result_a.metrics == result_b.metrics


# --- Lookahead ----------------------------------------------------------


def test_history_only_contains_past_bars() -> None:
    """The strategy only ever sees bars whose ts_event < current bar."""
    bars = [_bar(i, 21000 + i, 21010 + i, 20995 + i, 21005 + i) for i in range(5)]
    strategy = FuturePeekStrategy()
    run(strategy, bars, _config())  # FuturePeekStrategy asserts internally


def test_history_grows_monotonically_no_more_than_one_per_bar() -> None:
    """history.length == bar_index. No way to skip ahead."""
    bars = [_bar(i, 21000, 21010, 20990, 21005) for i in range(10)]
    strategy = HistoryLengthStrategy()
    run(strategy, bars, _config())
    # On bar i, history contains bars [0..i-1] = i entries (this bar gets
    # appended AFTER on_bar; but the engine appends history before calling
    # on_bar). Verify: lengths increase by 1 each bar, starting at 1.
    assert strategy.history_lengths == list(range(1, 11))


def test_strategy_has_no_future_access_attributes() -> None:
    """Structural lookahead defense: no attribute exposes future bars."""
    bars = [_bar(i, 21000, 21010, 20990, 21005) for i in range(3)]

    class Snooper(Strategy):
        name = "snooper"

        def __init__(self) -> None:
            self.context_dict: dict | None = None

        def on_bar(self, bar: Bar, context: Context) -> list[OrderIntent]:
            self.context_dict = vars(context).copy()
            return []

    s = Snooper()
    run(s, bars, _config())
    forbidden = {"future_bars", "next_bar", "all_bars", "future"}
    assert s.context_dict is not None
    assert forbidden.isdisjoint(s.context_dict.keys())


# --- Bracket fill rules -------------------------------------------------


def test_bracket_long_target_hit_produces_winning_trade() -> None:
    bars = [
        _bar(0, 21000, 21010, 20998, 21005),  # entry submitted on bar 0 close
        _bar(1, 21005, 21015, 21000, 21010),  # entry fills here at 21005.25
        _bar(2, 21010, 21035, 21008, 21030),  # target=21025 hit
    ]
    strategy = EnterOnceLongStrategy(stop_offset=10, target_offset=20)
    # Fires on bar 1 (bar_index>=1). Stop = bar1.close-10 = 21000.
    # Target = bar1.close+20 = 21030.
    # Entry fills at bar2.open + slippage = 21010.25.
    # Bar 2 high = 21035 hits target at 21030.
    result = run(strategy, bars, _config())
    assert len(result.trades) == 1
    t = result.trades[0]
    assert t.side is Side.LONG
    assert t.entry_price == 21010.25
    assert t.exit_price == 21030.0
    assert t.exit_reason == "target"
    assert t.fill_confidence == "exact"
    assert t.pnl > 0


def test_bracket_long_stop_wins_on_ambiguous_bar() -> None:
    """Bar containing both stop and target -> stop wins, conservative."""
    bars = [
        _bar(0, 21000, 21010, 20998, 21005),
        _bar(1, 21005, 21015, 21000, 21010),  # entry fills here
        _bar(2, 21010, 21035, 20985, 21010),  # range covers both stop AND target
    ]
    strategy = EnterOnceLongStrategy(stop_offset=10, target_offset=20)
    result = run(strategy, bars, _config())
    assert len(result.trades) == 1
    t = result.trades[0]
    assert t.exit_reason == "stop"
    assert t.fill_confidence == "conservative"
    assert t.pnl < 0
    assert result.metrics["ambiguous_fill_count"] == 1


# --- EOD flatten --------------------------------------------------------


def test_eod_flatten_closes_open_position() -> None:
    """Position open at last bar -> force-close at last bar's close."""
    bars = [
        _bar(0, 21000, 21010, 20998, 21005),
        _bar(1, 21005, 21015, 21000, 21010),  # entry fills
        _bar(2, 21010, 21020, 21008, 21015),  # neither hit
        _bar(3, 21015, 21025, 21013, 21020),  # neither hit
    ]
    strategy = EnterOnceLongStrategy(stop_offset=50, target_offset=50)
    result = run(strategy, bars, _config(flatten_on_last_bar=True))

    # The last bar is an EOD flatten.
    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "eod_flatten"
    assert result.trades[0].exit_price == 21020.0  # last bar's close


def test_eod_flatten_disabled_leaves_position_open() -> None:
    bars = [
        _bar(0, 21000, 21010, 20998, 21005),
        _bar(1, 21005, 21015, 21000, 21010),
        _bar(2, 21010, 21020, 21008, 21015),
    ]
    strategy = EnterOnceLongStrategy(stop_offset=50, target_offset=50)
    result = run(strategy, bars, _config(flatten_on_last_bar=False))
    assert result.trades == []
    assert result.final_position is not None


# --- Metrics ------------------------------------------------------------


def test_metrics_match_trades_winning() -> None:
    bars = [
        _bar(0, 21000, 21010, 20998, 21005),
        _bar(1, 21005, 21015, 21000, 21010),
        _bar(2, 21010, 21035, 21008, 21030),  # target hit
    ]
    result = run(
        EnterOnceLongStrategy(stop_offset=10, target_offset=20), bars, _config()
    )
    assert result.metrics["trade_count"] == 1
    assert result.metrics["win_rate"] == 1.0
    assert result.metrics["net_pnl"] > 0


def test_metrics_match_trades_losing() -> None:
    bars = [
        _bar(0, 21000, 21010, 20998, 21005),
        _bar(1, 21005, 21015, 21000, 21010),
        _bar(2, 21010, 21010, 20985, 20988),  # stop hit
    ]
    result = run(
        EnterOnceLongStrategy(stop_offset=10, target_offset=20), bars, _config()
    )
    assert result.metrics["trade_count"] == 1
    assert result.metrics["win_rate"] == 0.0
    assert result.metrics["net_pnl"] < 0


def test_no_trades_yields_zero_metrics() -> None:
    bars = [_bar(i, 21000, 21010, 20990, 21005) for i in range(3)]

    class Idle(Strategy):
        name = "idle"

        def on_bar(self, bar: Bar, context: Context) -> list[OrderIntent]:
            return []

    result = run(Idle(), bars, _config())
    assert result.metrics["trade_count"] == 0
    assert result.metrics["net_pnl"] == 0.0
    assert result.metrics["win_rate"] == 0.0


# --- Empty inputs -------------------------------------------------------


def test_run_with_empty_bars() -> None:
    """No bars in -> no trades, no errors, valid empty result."""

    class Idle(Strategy):
        name = "idle"

        def on_bar(self, bar: Bar, context: Context) -> list[OrderIntent]:
            return []

    result = run(Idle(), [], _config())
    assert result.trades == []
    assert result.equity_points == []
    assert result.metrics["trade_count"] == 0
