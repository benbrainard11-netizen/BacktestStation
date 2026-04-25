# Backtest Engine v1

> **Status: shipped** (bar-based, single-symbol, single-position, bracket orders).
>
> Lives at `backend/app/backtest/`. Tests at `backend/tests/test_backtest_*.py`.

## What it is

A pure event-driven backtest engine. Strategies plug in via a tiny callback interface; the engine owns the loop, fills, positions, equity, and metrics. One strategy doesn't fight against the engine for its own slippage model — there's only one model, in one place, used for every strategy.

The `CLAUDE.md` non-negotiables are all enforced:

- Engine is pure (no DB, no HTTP, no filesystem) — that's the runner's job.
- Strategies are dumb (events in, intents out).
- No lookahead — strategies can only see bars with `ts_event ≤ now`.
- Honest fills — when a bar contains both stop and target, the stop wins (`fill_confidence = "conservative"`).
- Reproducible — same inputs, byte-identical trades / equity / events / metrics.
- Named constants — tick size, contract value, commission, slippage all live in `BrokerConfig` / `RunConfig`. No inline magic numbers.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  RUNNER  (backend/app/backtest/runner.py)                       │
│  - load bars via app.data.read_bars                             │
│  - call engine.run                                              │
│  - write config.json / trades.parquet / equity.parquet /        │
│    events.parquet / metrics.json                                │
│  - insert BacktestRun row (source="engine")                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  ENGINE  (backend/app/backtest/engine.py)  — PURE               │
│                                                                 │
│  for each bar:                                                  │
│    1. resolve pending entries  -> Fills (entry)                 │
│    2. resolve active brackets  -> Fills (stop / target / amb.)  │
│    3. mark equity (realized + open MTM)                         │
│    4. push history                                              │
│    5. strategy.on_bar(bar, ctx)  -> OrderIntents                │
│    6. broker.submit each intent                                 │
│  finally: flatten on last bar (configurable)                    │
└──────────────┬──────────────────────────────────────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────┐     ┌─────────────────────────────────┐
│  BROKER                  │     │  STRATEGY  (subclass)           │
│  - pending entries       │     │  - on_start                     │
│  - active brackets       │     │  - on_bar -> intents            │
│  - fill resolution       │     │  - on_fill                      │
│  - slippage / commission │     │  - on_end                       │
└──────────────────────────┘     └─────────────────────────────────┘
```

## Strategy interface

```python
from app.backtest.strategy import Bar, Context, Strategy
from app.backtest.orders import BracketOrder, MarketEntry, Side

class MyStrategy(Strategy):
    name = "my_strategy"

    def on_start(self, context: Context) -> None:
        ...

    def on_bar(self, bar: Bar, context: Context) -> list[OrderIntent]:
        # return any orders you want to submit on this bar
        return [BracketOrder(side=Side.LONG, qty=1, stop_price=..., target_price=...)]

    def on_fill(self, fill: Fill, context: Context) -> None:
        ...

    def on_end(self, context: Context) -> None:
        ...
```

That's the entire contract. Four methods, three of which usually stay as no-ops.

### What strategies CAN see

- The current `bar` (OHLCV)
- `context.now` — current timestamp
- `context.bar_index` — zero-indexed bar number
- `context.history` — bars seen so far (capped at `history_max`)
- `context.position` — current open position, or `None`
- `context.equity` — running equity

### What strategies CANNOT do

- Look at any future bar (no API exists for it; structurally enforced)
- Read the database, filesystem, or network
- Use `datetime.now()` (use `context.now` for determinism)
- Mutate the bar or context

## Order intent types (v1)

| Intent | Description |
|---|---|
| `MarketEntry(side, qty)` | Open a position at next bar's open + slippage. No stop/target — the position runs until you submit another order or EOD flatten kicks in. |
| `BracketOrder(side, qty, stop_price, target_price)` | The standard. Entry + atomic OCO stop/target. The engine creates everything internally. |
| `CancelOrder(order_id)` | Cancel a pending order by id. |

## Fill rules

- **Market entry:** fills at *next* bar's `open` plus slippage (`slippage_ticks * tick_size`, in the trade's direction).
- **Bracket entry:** same as market — next bar's open + slippage. Stop and target legs become live for the bar after that.
- **Bracket exit:** each subsequent bar, the engine checks whether the bar's `[low, high]` range contains the stop or target price.
  - **Only stop touched** → fill at stop, `fill_confidence = "exact"`.
  - **Only target touched** → fill at target, `fill_confidence = "exact"`.
  - **Both touched** → ambiguous. Stop wins. `fill_confidence = "conservative"`. `metrics.ambiguous_fill_count` increments. This is the conservative default per `CLAUDE.md` §8.
  - **Neither touched** → bracket stays active.
- **EOD flatten:** if `flatten_on_last_bar=True`, any open position closes at the final bar's `close`. Records `exit_reason = "eod_flatten"`.

## Outputs

Every run produces five files plus a database row:

```
data/backtests/strategy={name}/run={timestamp}_{id}/
├── config.json       full RunConfig + engine_version + git_sha + timestamps
├── trades.parquet    one row per closed trade
├── equity.parquet    one row per bar (ts, equity, drawdown)
├── events.parquet    one row per event (order_submitted, fill, eod, etc.)
└── metrics.json      net_pnl, net_r, win_rate, profit_factor, max_dd, etc.
```

Plus, when `strategy_version_id` is supplied, a `BacktestRun` row in the SQLite metadata DB with `source = "engine"` (vs `"imported"` for runs ingested from external CSVs). The Strategy Workstation UI surfaces both kinds in the same dossier.

## Running a backtest

CLI:

```bash
python -m app.backtest.runner \
    --strategy moving_average_crossover \
    --symbol NQ.c.0 \
    --start 2026-04-20 --end 2026-04-25 \
    --strategy-version-id 5 \
    --params '{"fast_period": 5, "slow_period": 20, "stop_ticks": 8, "target_ticks": 16}'
```

Python:

```python
from app.backtest import RunConfig
from app.backtest.runner import run_backtest

config = RunConfig(
    strategy_name="moving_average_crossover",
    symbol="NQ.c.0",
    timeframe="1m",
    start="2026-04-20",
    end="2026-04-25",
    params={"fast_period": 5, "slow_period": 20},
)
result, out_dir, run_id = run_backtest(config, strategy_version_id=5)
print(result.metrics)
```

## Adding a new strategy

1. Create `backend/app/strategies/my_strategy.py`.
2. Subclass `Strategy`, set `name`, implement `on_bar`.
3. Add a branch in `runner._resolve_strategy(name)` so the CLI / API can find it. (When there are 3+ strategies we'll add a registry; not now.)
4. Run the engine + a simple unit test against synthetic bars to confirm the cross / signal logic.

That's the whole how-to. Strategies stay tiny because the engine handles everything else.

## What's NOT in v1 (deferred to Level 2 / 3)

- Tick-replay engine (TBBO). Engine architecture leaves room for it via a swappable bar-iterator and the same broker interface; not built yet.
- MBP-1 order book replay (Level 3).
- Multi-symbol / portfolio mode.
- Partial fills, limit-order queue modeling.
- Parameter sweeps / optimization.
- Walk-forward / Monte Carlo wrappers.
- ML-filtered strategies as a first-class concept (you can wire ML predictions into a regular Strategy's `on_bar` today).

## Tests

48 tests across:

- `test_backtest_orders.py` — dataclass invariants
- `test_backtest_broker.py` — fill resolution, ambiguous bars, force-close
- `test_backtest_engine.py` — determinism, lookahead, fill rules, EOD flatten, metrics
- `test_backtest_strategy_ma.py` — example strategy round-trip
- `test_backtest_runner.py` — file outputs + DB row insertion + bar loading

Determinism test: run the same backtest twice, compare trades + equity + metrics — must be identical.

Lookahead test: the structure of `Context` and `Bar` makes future access impossible. The `FuturePeekStrategy` test asserts no `next_bar` / `future_bars` / `all_bars` attributes exist on context.

## Reproducibility checklist

Every run records:

- Engine version (`ENGINE_VERSION` constant in `backend/app/backtest/__init__.py`)
- Git SHA (from `git rev-parse HEAD` at run time)
- Full RunConfig (strategy, symbol, dates, qty, slippage, commission, params)
- Started_at + completed_at timestamps

Two runs with identical config (and identical input bars) produce byte-identical `trades.parquet`, `equity.parquet`, `events.parquet`, and `metrics.json`. The `config.json` differs only in the timestamps and git SHA.

## Future work

Per `docs/ARCHITECTURE.md` §0 build order, the next pieces that build on the engine:

1. Port Fractal AMD as the first real strategy plugin (validates the interface against a non-toy strategy).
2. Forward Drift Monitor — once the engine produces a baseline run, the drift monitor can compare live signals to that baseline.
3. Tick-replay engine (Level 2) — when bar-based fill assumptions get noisy enough that you want intra-bar precision.
