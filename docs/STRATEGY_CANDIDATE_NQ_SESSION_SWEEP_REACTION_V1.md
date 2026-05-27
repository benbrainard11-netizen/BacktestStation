# Strategy Candidate: NQ Session Sweep Reaction V1

## Beginner Summary

This is the first fully-defined strategy candidate from the session-sweep research.

The setup is intentionally simple:

```text
1. Use the completed Globex session to decide which liquidity level matters.
2. Wait for next RTH morning to sweep that level first.
3. Only enter if price rejects back inside the prior range.
4. Use one MBP-1 top-of-book imbalance feature to confirm the rejection.
5. Use fixed, pre-declared stop and target rules.
```

This is not a proven live strategy yet. It is a clean candidate that can be backtested honestly.

## 1. Strategy Name

Working name:

```text
NQ Session Sweep Reaction V1
```

Short key:

```text
nq_session_sweep_reaction_v1
```

Market:

```text
NQ.c.0
```

Primary data:

- 1-minute bars for session context and simple replay views.
- MBP-1 events for sweep sequencing, confirmation, and realistic stop/target ordering.

Timezone:

```text
America/New_York
```

## 2. Strategy Hypothesis

Plain English:

```text
When a completed session closes strongly near one side of its range,
the next session often raids that same side first.

If that first sweep fails and price returns back inside the prior range,
we can take one rejection trade as it moves back inside the prior range.
```

More concrete:

- Bullish session close context means we watch the prior session high.
- Bearish session close context means we watch the prior session low.
- We do not chase the breakout.
- We fade the sweep only after rejection is visible.

Beginner translation:

```text
We are not trying to predict the whole next day.
We are waiting for a specific trap-like event, then trading only if it rejects.
```

## 3. Exact Event Definitions

### Anchor session

The anchor session is the completed Globex session:

```text
18:00 ET previous calendar day -> 17:00 ET current calendar day
```

At 17:00 ET, the anchor session is complete and safe to use.

Anchor values:

```text
anchor_open
anchor_high
anchor_low
anchor_close
anchor_range = anchor_high - anchor_low
anchor_mid = (anchor_high + anchor_low) / 2
```

### Session close position

```text
session_close_position = (anchor_close - anchor_low) / (anchor_high - anchor_low)
```

Buckets:

| Value | Label |
|---:|---|
| `<= 0.40` | `bearish` |
| `> 0.40 and < 0.60` | `neutral` |
| `>= 0.60` | `bullish` |

If the range is zero or invalid, skip the session.

### Armed sweep side

The session context chooses one side to watch.

| Session close bias | Armed side | Strategy intent |
|---|---|---|
| `bullish` | prior session high | wait for high sweep, then look for short rejection |
| `bearish` | prior session low | wait for low sweep, then look for long rejection |
| `neutral` | none | no trade |

Beginner translation:

```text
If yesterday closed near the high, we expect the high to be the obvious level.
If yesterday closed near the low, we expect the low to be the obvious level.
If yesterday closed in the middle, we do nothing.
```

### Liquidity sweep

Default tick size:

```text
0.25 NQ points
```

Sweep buffer:

```text
sweep_buffer_pts = 0.25
```

High sweep:

```text
MBP-1 trade event price >= anchor_high + sweep_buffer_pts
```

Low sweep:

```text
MBP-1 trade event price <= anchor_low - sweep_buffer_pts
```

Use MBP-1 `action == "T"` rows when available. The trade `price` column decides the sweep.

If a bar-based fallback is ever used for research, it must be marked as lower confidence. The actual strategy backtest should use MBP-1 because first-sweep sequence matters.

### First sweep

The first sweep is the earliest sweep of either anchor level during the next session.

Labels:

| Label | Meaning |
|---|---|
| `armed_side_first` | the side selected by context swept first |
| `opposite_side_first` | the wrong side swept first |
| `none` | no side swept inside the allowed window |
| `ambiguous` | sequence cannot be trusted |

The strategy only trades `armed_side_first`.

## 4. Time Restrictions

This first version trades only the RTH morning.

Reference next-session RTH:

```text
09:30 ET -> 16:00 ET
```

Entry setup window:

```text
09:35 ET -> 10:30 ET
```

Entry deadline:

```text
10:45 ET
```

Forced flat time:

```text
12:00 ET
```

Rules:

- No entries before 09:35 ET.
- No new sweeps accepted after 10:30 ET.
- No entries after 10:45 ET.
- Any open trade is closed at 12:00 ET if stop or target has not hit.
- Maximum one trade per anchor session.

Beginner translation:

```text
We are studying the morning reaction, not the whole day.
We also avoid the first five minutes because the open can be chaotic.
```

## 5. MBP-1 Confirmation Feature

Use exactly one MBP-1 confirmation feature in V1:

```text
post_sweep_30s_mean_imbalance
```

### Imbalance math

For each MBP-1 event:

```text
imbalance = (bid_sz - ask_sz) / (bid_sz + ask_sz)
```

Interpretation:

| Value | Beginner meaning |
|---:|---|
| positive | best bid size is heavier |
| zero | bid and ask sizes are balanced |
| negative | best ask size is heavier |

### Confirmation window

After the armed sweep event:

```text
confirmation_start = sweep_ts
confirmation_end = sweep_ts + 30 seconds
```

Calculate:

```text
post_sweep_30s_mean_imbalance =
average imbalance from confirmation_start through confirmation_end
```

The strategy is not allowed to enter until after `confirmation_end`.

### Confirmation thresholds

For high sweep rejection short:

```text
post_sweep_30s_mean_imbalance <= -0.20
```

For low sweep rejection long:

```text
post_sweep_30s_mean_imbalance >= +0.20
```

Beginner translation:

```text
After a high sweep, we want the ask side to look heavier before shorting.
After a low sweep, we want the bid side to look heavier before going long.
```

Why only one MBP-1 feature:

```text
The first candidate should prove whether one simple order-book confirmation helps.
If we add five MBP filters now, we will not know which one mattered.
```

## 6. Exact Entry Logic

### Short setup after high sweep

Required conditions:

1. Anchor session close bias is `bullish`.
2. Anchor range sanity filter passes.
3. No prior sweep of the anchor low occurred earlier in the next session.
4. The first valid sweep during `09:35 ET -> 10:30 ET` is a high sweep.
5. Price returns back inside the prior range.
6. MBP-1 confirmation passes:

```text
post_sweep_30s_mean_imbalance <= -0.20
```

Reclaim condition:

```text
first completed 1m bar after confirmation_end closes <= anchor_high
```

Entry:

```text
Enter short on the next MBP-1 event after the reclaim bar closes.
```

Backtest fill:

```text
short entry fill = bid_px on that next MBP-1 event
```

### Long setup after low sweep

Required conditions:

1. Anchor session close bias is `bearish`.
2. Anchor range sanity filter passes.
3. No prior sweep of the anchor high occurred earlier in the next session.
4. The first valid sweep during `09:35 ET -> 10:30 ET` is a low sweep.
5. Price returns back inside the prior range.
6. MBP-1 confirmation passes:

```text
post_sweep_30s_mean_imbalance >= +0.20
```

Reclaim condition:

```text
first completed 1m bar after confirmation_end closes >= anchor_low
```

Entry:

```text
Enter long on the next MBP-1 event after the reclaim bar closes.
```

Backtest fill:

```text
long entry fill = ask_px on that next MBP-1 event
```

### Reclaim deadline

The reclaim bar must close inside the range within:

```text
10 minutes after sweep_ts
```

If reclaim takes longer than 10 minutes, skip the setup.

Beginner translation:

```text
We want a fairly quick rejection.
If price hangs outside the level too long, that may be acceptance instead of rejection.
```

## 7. Exact Stop Logic

Use the sweep extreme plus a small safety buffer.

Stop buffer:

```text
stop_buffer_pts = 0.50
```

Minimum stop distance:

```text
min_stop_pts = 6.00
```

Maximum stop distance:

```text
max_stop_pts = 30.00
```

### Short stop

Find the highest trade price from sweep timestamp through entry timestamp:

```text
sweep_extreme = max_trade_price_between(sweep_ts, entry_ts)
```

Initial stop:

```text
stop_price = sweep_extreme + stop_buffer_pts
```

If that stop is closer than `min_stop_pts`, widen it:

```text
stop_price = entry_price + min_stop_pts
```

If final stop distance is greater than `max_stop_pts`, skip the trade.

### Long stop

Find the lowest trade price from sweep timestamp through entry timestamp:

```text
sweep_extreme = min_trade_price_between(sweep_ts, entry_ts)
```

Initial stop:

```text
stop_price = sweep_extreme - stop_buffer_pts
```

If that stop is closer than `min_stop_pts`, widen it:

```text
stop_price = entry_price - min_stop_pts
```

If final stop distance is greater than `max_stop_pts`, skip the trade.

Beginner translation:

```text
The stop goes beyond the sweep.
If price returns beyond the sweep extreme, the rejection idea is probably wrong.
```

## 8. Exact Target Logic

Target uses fixed R-multiple.

Default:

```text
target_r = 1.50
```

Risk per trade in points:

```text
risk_pts = abs(entry_price - stop_price)
```

Short target:

```text
target_price = entry_price - (target_r * risk_pts)
```

Long target:

```text
target_price = entry_price + (target_r * risk_pts)
```

No partial exits in V1.

No trailing stop in V1.

Beginner translation:

```text
If we risk 10 points, the first version tries to make 15 points.
Simple targets are easier to backtest honestly than fancy trade management.
```

## 9. Invalidations

Skip the trade if any of these happen:

| Invalidation | Reason |
|---|---|
| Anchor session close bias is neutral | no clear context |
| Anchor range is invalid | bad or unusable session |
| Anchor range sanity filter fails | session was unusually tiny or huge |
| The opposite level sweeps first | context thesis failed |
| Armed side swept before 09:35 ET | stale overnight/open event |
| Armed side sweeps after 10:30 ET | outside study window |
| Reclaim does not happen within 10 minutes | rejection too slow |
| MBP-1 confirmation is missing | no order-book confirmation |
| MBP-1 confirmation fails | no rejection confirmation |
| Stop distance is greater than 30 points | risk too wide |
| Already traded this anchor session | one trade per session |
| Data gap around sweep or entry | cannot trust sequence |
| Stop and target sequence cannot be resolved | mark ambiguous, do not count as clean proof |

Range sanity filter:

```text
prior20_median_range must exist
anchor_range >= 0.50 * prior20_median_range
anchor_range <= 1.75 * prior20_median_range
```

Beginner translation:

```text
We avoid weird sessions because they can make a strategy look better or worse for the wrong reason.
```

## 10. Realistic Backtest Design

### Data requirements

Required:

- NQ 1-minute bars.
- NQ MBP-1 events.
- Exchange timestamps in UTC.
- Session calendar using ET boundaries.

### Backtest level

Use MBP-1 event replay for:

- sweep sequence
- entry fill
- stop fill
- target fill
- stop-vs-target ordering

If a bar-based prototype is used first, label it:

```text
research prototype only
```

Do not treat bar-only results as final strategy evidence.

### Fill assumptions

Entry:

- Long fills at top ask on the next MBP-1 event after signal.
- Short fills at top bid on the next MBP-1 event after signal.

Stop and target:

- Long stop triggers when trade price is at or below stop.
- Long target triggers when trade price is at or above target.
- Short stop triggers when trade price is at or above stop.
- Short target triggers when trade price is at or below target.

If stop and target could both trigger, MBP-1 event order decides which happened first.

### Costs

Every backtest must include:

- commission
- exchange fees
- slippage sensitivity

Run at least these slippage settings:

```text
0 ticks
1 tick
2 ticks
```

Use 1 tick as the main report unless live broker data proves a better assumption.

### Time split

Do not optimize on the full year.

Recommended first split:

```text
Development set: first 70% of sessions
Holdout set: last 30% of sessions
```

The rule values in this document are fixed before looking at holdout results.

### Required output metrics

Report:

- number of candidate sessions
- number of armed sessions
- number of first armed-side sweeps
- number of confirmed entries
- skipped setup counts by reason
- win rate
- average R
- median R
- profit factor
- max drawdown
- average hold time
- R distribution
- long vs short split
- day-of-week split
- stop/target ambiguous count
- slippage sensitivity

Beginner translation:

```text
We care as much about what got skipped as what got traded.
Skip reasons tell us whether the idea is rare, fragile, or actually usable.
```

## 11. Leakage-Safe Implementation Rules

### Before next session starts

Safe:

- anchor session OHLC
- anchor session close position
- prior 20-session range median
- prior session context

Unsafe:

- next session open/high/low/close
- first sweep side
- RTH opening range
- any next-session MBP-1 event

### During the next session

The backtest must process events in time order.

At each moment, the strategy may only know:

- past MBP-1 events
- completed 1m bars
- current open position
- already submitted orders

### Confirmation timing

The strategy may not enter during the 30-second MBP confirmation window.

Correct sequence:

```text
sweep happens
wait 30 seconds
calculate mean imbalance from that completed window
wait for completed reclaim bar
enter on the next event
```

Wrong sequence:

```text
sweep happens
peek at the next 30 seconds
pretend entry happened at the sweep
```

That would be leakage.

## 12. Parameters Locked For V1

| Parameter | Value |
|---|---:|
| `sweep_buffer_pts` | `0.25` |
| `entry_start_et` | `09:35` |
| `sweep_cutoff_et` | `10:30` |
| `entry_deadline_et` | `10:45` |
| `forced_flat_et` | `12:00` |
| `mbp_confirmation_seconds` | `30` |
| `short_imbalance_threshold` | `-0.20` |
| `long_imbalance_threshold` | `+0.20` |
| `reclaim_deadline_minutes` | `10` |
| `stop_buffer_pts` | `0.50` |
| `min_stop_pts` | `6.00` |
| `max_stop_pts` | `30.00` |
| `target_r` | `1.50` |
| `max_trades_per_session` | `1` |

These should not be changed after seeing holdout results.

## 13. Sensitivity Checks Later

Only after V1 is tested, run small sensitivity checks:

| Parameter | Values |
|---|---|
| sweep buffer | `0.25`, `0.50`, `1.00` |
| imbalance threshold | `0.15`, `0.20`, `0.25` |
| target R | `1.00`, `1.50`, `2.00` |
| forced flat time | `11:30`, `12:00`, `15:45` |

Do not choose the best-looking combination from all of these and call it proven. Use sensitivity checks to see whether the idea is stable.

## 14. What This Strategy Is Not

This is not:

- a full-day trend strategy
- a breakout chase strategy
- a machine-learning strategy
- a multi-filter optimized system
- a live-ready strategy

It is:

```text
a first clean sweep-reaction candidate that can be falsified
```

## 15. First Implementation Plan

Recommended build order:

1. Build a research/backtest harness that creates one candidate row per anchor session.
2. Detect first sweep using MBP-1 trade events.
3. Add session context and range sanity filter.
4. Add post-sweep 30-second imbalance confirmation.
5. Simulate entry, stop, target, and forced flat using MBP-1 event order.
6. Export trades, skipped setups, and metrics.
7. Run development set.
8. Freeze the code.
9. Run holdout set.
10. Decide whether this candidate deserves a V2.

Suggested files:

- `backend/app/research/nq_session_sweep_reaction_v1.py`
- `backend/app/cli/nq_session_sweep_reaction_v1.py`
- `backend/tests/test_nq_session_sweep_reaction_v1.py`

## 16. Beginner Mental Model

Think of each day like this:

```text
Yesterday closed strong near one side.
That side becomes the obvious liquidity level.
Today, if the market raids that level first and then quickly rejects,
we take one measured trade back inside the prior range.
```

The MBP-1 imbalance check is there to avoid blindly fading every sweep.

The stop says:

```text
If the sweep keeps going, we are wrong.
```

The target says:

```text
If the rejection works, take a simple fixed reward.
```

The backtest says:

```text
Do not trust the idea until it survives realistic sequencing, costs, slippage, and holdout data.
```
