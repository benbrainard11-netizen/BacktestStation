# NQ Session Sweep Reaction V1 Backtest

## What Was Implemented

The V1 strategy candidate is now implemented as a real MBP-1 research/backtest harness.

Code:

- `backend/app/research/nq_session_sweep_reaction_v1.py`
- `backend/app/research/nq_session_sweep_reaction_v1_chunked.py`
- `backend/app/research/nq_session_sweep_reaction_v1_detection.py`
- `backend/app/research/nq_session_sweep_reaction_v1_execution.py`
- `backend/app/research/nq_session_sweep_reaction_v1_output.py`
- `backend/app/research/nq_session_sweep_reaction_v1_replay.py`
- `backend/app/research/nq_session_sweep_reaction_v1_session.py`
- `backend/app/research/nq_session_sweep_reaction_v1_types.py`
- `backend/app/research/nq_session_sweep_reaction_v1_utils.py`
- `backend/app/cli/nq_session_sweep_reaction_v1.py`
- `backend/app/cli/nq_session_sweep_reaction_v1_chunked.py`
- `backend/tests/test_nq_session_sweep_reaction_v1.py`

Spec:

- `docs/STRATEGY_CANDIDATE_NQ_SESSION_SWEEP_REACTION_V1.md`

## Beginner Explanation

The backtest does this one session at a time:

```text
1. Look at the completed Globex session.
2. Decide whether the session closed bullish, bearish, or neutral.
3. If bullish, arm a prior-high sweep short setup.
4. If bearish, arm a prior-low sweep long setup.
5. Watch next-session MBP-1 trades in timestamp order.
6. If the armed level sweeps first, wait 30 seconds.
7. Check one MBP-1 imbalance confirmation.
8. Wait for a completed 1m reclaim bar.
9. Enter on the next MBP-1 event.
10. Simulate stop, target, or forced flat using MBP-1 event order.
```

Nothing in the strategy can see future data. It only acts after the required event or confirmation window has completed.

## Implemented V1 Rules

### Context

Session close bias:

```text
session_close_position = (close - low) / (high - low)
```

Rules:

- `>= 0.60`: bullish context, arm high sweep short.
- `<= 0.40`: bearish context, arm low sweep long.
- between those: neutral, skip.

### First Sweep

High sweep:

```text
MBP-1 trade price >= anchor_high + 0.25
```

Low sweep:

```text
MBP-1 trade price <= anchor_low - 0.25
```

The first sweep is detected from next Globex session start through `10:30 ET`.

The strategy only continues if the context-armed side sweeps first.

### MBP-1 Confirmation

Confirmation feature:

```text
post_sweep_30s_mean_imbalance
```

Imbalance math:

```text
(bid_sz - ask_sz) / (bid_sz + ask_sz)
```

Rules:

- Short after high sweep requires mean imbalance `<= -0.20`.
- Long after low sweep requires mean imbalance `>= +0.20`.

### Entry

After confirmation:

- wait for a completed 1m bar to close back inside the prior range
- enter on the next MBP-1 event after that reclaim bar

Execution:

- Long entry fills at top ask plus slippage.
- Short entry fills at top bid minus slippage.

### Stop And Target

Stop:

- Short stop goes above the sweep extreme plus `0.50` points.
- Long stop goes below the sweep extreme minus `0.50` points.
- Minimum stop distance is `6.00` points.
- Maximum stop distance is `30.00` points.

Target:

```text
1.5R
```

Forced flat:

```text
12:00 ET
```

## How To Run

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m app.cli.nq_session_sweep_reaction_v1 `
  --start 2026-04-22 `
  --end 2026-04-23 `
  --warmup-days 0 `
  --load-padding-days 1 `
  --disable-range-sanity `
  --output-dir ..\data\backtests\nq_session_sweep_reaction_v1_smoke_2026-04-22
```

For a real study, use warmup and keep range sanity on:

```powershell
.\.venv\Scripts\python.exe -m app.cli.nq_session_sweep_reaction_v1 `
  --start 2026-04-01 `
  --end 2026-05-01 `
  --warmup-days 45 `
  --load-padding-days 4 `
  --output-dir ..\data\backtests\nq_session_sweep_reaction_v1_2026_04
```

`data/` is gitignored, so generated outputs stay local.

For larger MBP-1 windows, prefer the chunked runner so one giant MBP-1
DataFrame is not loaded all at once:

```powershell
.\.venv\Scripts\python.exe -m app.cli.nq_session_sweep_reaction_v1_chunked `
  --start 2026-04-01 `
  --end 2026-05-01 `
  --warmup-days 45 `
  --output-dir ..\data\backtests\nq_session_sweep_reaction_v1_april_2026
```

## Output Files

The CLI writes:

```text
config.json
summary.json
trades.csv
sessions.csv
replay_events.csv
equity.csv
```

### `trades.csv`

One row per completed trade.

Important columns:

- `entry_ts`
- `exit_ts`
- `side`
- `entry_price`
- `stop_price`
- `target_price`
- `exit_price`
- `pnl`
- `r_multiple`
- `exit_reason`
- `post_sweep_30s_mean_imbalance`

### `sessions.csv`

One row per anchor session.

This is important because skipped setups are part of the truth.

Important columns:

- `status`
- `skip_reason`
- `armed_side`
- `trade_side`
- `anchor_high`
- `anchor_low`
- `session_close_bias`
- `first_sweep_side`
- `post_sweep_30s_mean_imbalance`

### `replay_events.csv`

Replay-friendly event markers.

Important event types:

- `session_armed`
- `first_sweep`
- `confirmation_passed`
- `confirmation_failed`
- `reclaim`
- `entry`
- `exit`

These rows include anchor high, anchor low, trade side, event timestamp, and event price so a replay viewer can plot them.

### `summary.json`

Overall metrics:

- trade count
- net PnL
- net R
- win rate
- average R
- median R
- profit factor
- max drawdown
- long/short split
- exit counts
- skip reason counts

## Real Smoke Runs

Two small R2-backed smoke runs completed.

### Anchor `2026-04-23`

Output:

```text
data/backtests/nq_session_sweep_reaction_v1_smoke_2026-04-23/
```

Result:

```text
skipped: neutral_session_bias
```

### Anchor `2026-04-22`

Output:

```text
data/backtests/nq_session_sweep_reaction_v1_smoke_2026-04-22/
```

Result:

```text
skipped: no_sweep_before_cutoff
```

This is still a successful plumbing check. The backtest correctly refused to invent trades when the exact setup was not present.

## Tests

Synthetic tests cover:

- high sweep, short rejection, MBP confirmation, target hit
- low sweep, long rejection, MBP confirmation, stop hit
- opposite side first skip
- MBP confirmation failure skip
- no entry before confirmation and reclaim timing complete

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_nq_session_sweep_reaction_v1.py
```

## Leakage Safety

The implementation has two clocks:

Before the next session:

- may use completed anchor-session context only

During the next session:

- processes MBP-1 events in timestamp order
- waits until the 30-second confirmation window is complete
- waits until the reclaim bar is complete
- enters on a later MBP-1 event

It does not use:

- future next-session high/low/close
- future MBP-1 events before their timestamp
- same-bar hindsight for entry

## Current Status

This is now ready for a larger development-period run.

Do not treat results as validated until:

1. development period results are reviewed
2. code is frozen
3. holdout period is run once
4. slippage sensitivity is checked
5. skip reasons and replay events are inspected
