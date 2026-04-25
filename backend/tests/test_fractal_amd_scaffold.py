"""Fractal AMD scaffold smoke test.

Asserts the strategy plugin loads, runs against multi-instrument bars
without crashing, and produces zero trades (expected -- signal stubs
return None / [] / False). Once the port lands actual signal logic,
add real tests next to this one.
"""

from __future__ import annotations

import datetime as dt

import pytest

from app.backtest.engine import RunConfig, run as engine_run
from app.backtest.strategy import Bar
from app.strategies.fractal_amd import FractalAMD
from app.strategies.fractal_amd.config import FractalAMDConfig
from app.strategies.fractal_amd.signals import is_in_entry_window


def _make_bars(symbol: str, start: dt.datetime, minutes: int) -> list[Bar]:
    bars: list[Bar] = []
    base = 21000.0 if symbol == "NQ.c.0" else 5000.0 if symbol == "ES.c.0" else 41000.0
    for i in range(minutes):
        ts = start + dt.timedelta(minutes=i)
        price = base + i * 0.25
        bars.append(
            Bar(
                ts_event=ts,
                symbol=symbol,
                open=price,
                high=price + 0.5,
                low=price - 0.5,
                close=price + 0.25,
                volume=100,
                trade_count=10,
                vwap=price + 0.1,
            )
        )
    return bars


def test_scaffold_runs_without_crashing() -> None:
    """Bare-minimum sanity: NQ-only, no aux, defaults. No trades expected."""
    start = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    bars = _make_bars("NQ.c.0", start, minutes=60)

    strategy = FractalAMD(FractalAMDConfig())
    config = RunConfig(
        strategy_name="fractal_amd",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
    )

    result = engine_run(strategy, bars, config)

    assert result.trades == []
    # Equity curve still gets one point per bar even when no trades.
    assert len(result.equity_points) == 60


def test_scaffold_sees_aux_bars() -> None:
    """With aux symbols configured, context.aux is populated per bar."""
    start = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    nq = _make_bars("NQ.c.0", start, minutes=10)
    es = _make_bars("ES.c.0", start, minutes=10)
    ym = _make_bars("YM.c.0", start, minutes=10)

    strategy = FractalAMD(FractalAMDConfig())
    config = RunConfig(
        strategy_name="fractal_amd",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
        aux_symbols=["ES.c.0", "YM.c.0"],
    )

    aux_bars = {
        "ES.c.0": {b.ts_event: b for b in es},
        "YM.c.0": {b.ts_event: b for b in ym},
    }

    # Patch on_bar to capture the aux dict it sees so we can assert
    # the engine plumbed it through.
    seen_aux_keys: set[str] = set()
    seen_es_close: list[float] = []
    original_on_bar = strategy.on_bar

    def capturing_on_bar(bar, context):
        seen_aux_keys.update(context.aux.keys())
        es_bar = context.aux.get("ES.c.0")
        if es_bar is not None:
            seen_es_close.append(es_bar.close)
        return original_on_bar(bar, context)

    strategy.on_bar = capturing_on_bar  # type: ignore[method-assign]

    result = engine_run(strategy, nq, config, aux_bars=aux_bars)

    assert result.trades == []
    assert seen_aux_keys == {"ES.c.0", "YM.c.0"}
    assert len(seen_es_close) == 10
    # ES close at minute 0 is 5000.25 per _make_bars (price + 0.25).
    assert seen_es_close[0] == pytest.approx(5000.25)


def test_runner_resolves_fractal_amd_name() -> None:
    """runner._resolve_strategy('fractal_amd') returns a FractalAMD instance."""
    from app.backtest.runner import _resolve_strategy

    config = RunConfig(
        strategy_name="fractal_amd",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
    )
    strategy = _resolve_strategy("fractal_amd", {}, config)
    assert isinstance(strategy, FractalAMD)
    assert strategy.config.target_r == 3.0
    assert strategy.config.aux_symbols == ("ES.c.0", "YM.c.0")


def test_config_overrides_via_params_dict() -> None:
    """RunConfig.params lets a caller tweak FractalAMDConfig defaults."""
    cfg = FractalAMDConfig.from_params(
        {
            "target_r": 5.0,
            "max_trades_per_day": 4,
            "aux_symbols": ["ES.c.0"],  # list -> tuple normalization
            "unknown_key_ignored": True,
        }
    )
    assert cfg.target_r == 5.0
    assert cfg.max_trades_per_day == 4
    assert cfg.aux_symbols == ("ES.c.0",)
    # Defaults preserved for unset fields.
    assert cfg.min_risk_pts == 8.0


def test_entry_window_helper_is_pure() -> None:
    """is_in_entry_window matches the trusted-backtest gate semantics."""
    base = dt.datetime(2026, 4, 24, tzinfo=dt.timezone.utc)
    fields = {"open_hour": 9, "open_min": 30, "close_hour": 14}

    # 09:29 -> rejected (before open_min)
    assert not is_in_entry_window(base.replace(hour=9, minute=29), **fields)
    # 09:30 -> accepted (window opens here)
    assert is_in_entry_window(base.replace(hour=9, minute=30), **fields)
    # 13:59 -> accepted (last allowed entry minute)
    assert is_in_entry_window(base.replace(hour=13, minute=59), **fields)
    # 14:00 -> rejected (window closed)
    assert not is_in_entry_window(base.replace(hour=14, minute=0), **fields)
    # 03:00 -> rejected (well before open_hour)
    assert not is_in_entry_window(base.replace(hour=3, minute=0), **fields)
