"""Capture a baseline of composable engine trade output for a fixed
fixture. Used to verify the chunk-3 engine state-machine rewrite
produces byte-identical trades for old-shape (entry_long/entry_short)
specs that auto-migrate to trigger_long/trigger_short.

Run BEFORE chunk 3:    python -m scripts.capture_engine_baseline > .baseline.txt
Run AFTER  chunk 3:    python -m scripts.capture_engine_baseline > .after.txt
                       diff .baseline.txt .after.txt
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json

from app.backtest.engine import RunConfig, run as engine_run
from app.backtest.strategy import Bar
from app.strategies.composable import ComposableStrategy
from app.strategies.composable.config import ComposableSpec


UTC = dt.timezone.utc


def _bar(
    ts: dt.datetime,
    open_: float = 21000.0,
    *,
    high: float | None = None,
    low: float | None = None,
    close: float | None = None,
    symbol: str = "NQ.c.0",
) -> Bar:
    return Bar(
        ts_event=ts,
        symbol=symbol,
        open=open_,
        high=open_ + 5 if high is None else high,
        low=open_ - 5 if low is None else low,
        close=open_ + 1 if close is None else close,
        volume=100,
        trade_count=10,
        vwap=open_,
    )


def _utc(year, month, day, hour, minute) -> dt.datetime:
    return dt.datetime(year, month, day, hour, minute, tzinfo=UTC)


def _build_pdh_fixture() -> tuple[list[Bar], dict]:
    """Same fixture as test_composable_fires_on_pdh_sweep_inside_session."""
    base = _utc(2026, 4, 24, 14, 30)
    bars: list[Bar] = []
    for i in range(5):
        bars.append(
            _bar(base + dt.timedelta(minutes=i),
                 open_=21000, high=21010 if i == 2 else 21008,
                 low=20995, close=21005)
        )
    base2 = _utc(2026, 4, 25, 14, 30)
    for i in range(5):
        if i == 4:
            bars.append(_bar(base2 + dt.timedelta(minutes=i),
                             open_=21015, high=21020, low=21013, close=21018))
        else:
            bars.append(_bar(base2 + dt.timedelta(minutes=i),
                             open_=21010, high=21013, low=21008, close=21012))
    spec_raw = {
        "entry_long": [],
        "entry_short": [
            {"feature": "prior_level_sweep", "params": {"level": "PDH", "direction": "above"}},
            {"feature": "time_window", "params": {"start_hour": 9.5, "end_hour": 14.0}},
        ],
        "stop": {"type": "fixed_pts", "stop_pts": 10.0},
        "target": {"type": "r_multiple", "r": 3.0},
        "qty": 1,
        "max_trades_per_day": 2,
    }
    return bars, spec_raw


def _trades_signature(trades: list) -> dict:
    """Stable, comparable representation of trades. Captures the keys
    that determinism cares about: count, entry/exit prices and times,
    R-multiple."""
    out = {
        "count": len(trades),
        "trades": [
            {
                "entry_ts": t.entry_ts.isoformat(),
                "exit_ts": t.exit_ts.isoformat() if t.exit_ts else None,
                "entry_price": float(t.entry_price),
                "exit_price": float(t.exit_price) if t.exit_price else None,
                "side": str(t.side),
                "r_multiple": float(t.r_multiple) if t.r_multiple is not None else None,
            }
            for t in trades
        ],
    }
    out["sha256"] = hashlib.sha256(
        json.dumps(out["trades"], sort_keys=True).encode()
    ).hexdigest()
    return out


def main() -> None:
    bars, spec_raw = _build_pdh_fixture()
    spec = ComposableSpec.from_dict(spec_raw)
    strat = ComposableStrategy(spec)
    config = RunConfig(
        strategy_name="composable",
        symbol="NQ.c.0",
        timeframe="1m",
        start="2026-04-24",
        end="2026-04-25",
        flatten_on_last_bar=True,
        params={},
    )
    result = engine_run(strat, bars, config)
    print(json.dumps(_trades_signature(result.trades), indent=2))


if __name__ == "__main__":
    main()
