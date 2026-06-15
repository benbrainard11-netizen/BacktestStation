# NQ Liquidity Sweep Outcome Holdout Results

## Status

Holdout evaluation completed.

The exact same sweep detection, outcome labels, feature definitions, and study config were used. No thresholds were optimized or changed.

## Data Split

| Split | Window | Purpose |
|---|---|---|
| In-sample discovery | `2025-05-01` through `2026-02-01` half-open | Selected/ranked features |
| Holdout validation | `2026-02-01` through `2026-05-23` half-open | Tested whether the selected effects survived |

Holdout export folder:

```text
data/backtests/nq_liquidity_sweep_outcomes_holdout_oos_2026-02-01_2026-05-23/
```

Comparison export:

```text
data/backtests/nq_liquidity_sweep_outcomes_holdout_oos_2026-02-01_2026-05-23/insample_vs_holdout_top5_comparison.csv
```

## Sample Size

| Split | Events | Usable labels | Continuations | Reversals | Ambiguous | Months |
|---|---:|---:|---:|---:|---:|---:|
| In-sample | 400 | 383 | 225 | 158 | 17 | 9 |
| Holdout | 168 | 162 | 95 | 67 | 6 | 4 |

The holdout sample is large enough for a first validation check, but still smaller than the in-sample set.

## Level Type Check

| Level type | In-sample continuation rate | Holdout continuation rate | Read |
|---|---:|---:|---|
| `prior_day_high` | 66.7% | 68.2% | Survived |
| `prior_day_low` | 67.1% | 66.7% | Survived |
| `overnight_high` | 48.6% | 54.8% | Mixed / weak |
| `overnight_low` | 55.1% | 45.0% | Did not hold |

The prior-day level context held up well. This is the strongest structural result so far.

## Exact Frozen Top Feature Comparison

These were the exact top 5 exported by the in-sample discovery ranking.

| Feature | In-sample direction | Holdout direction | In-sample AUC | Holdout AUC | In-sample Cliff's delta | Holdout Cliff's delta | In-sample n | Holdout n | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| `post_5_30s_mbp_event_count` | Continuation higher | Continuation higher | 0.616 | 0.534 | 0.233 | 0.067 | 383 | 162 | Weakened hard |
| `post_5_30s_mbp_events_per_second` | Continuation higher | Continuation higher | 0.616 | 0.534 | 0.233 | 0.067 | 383 | 162 | Weakened hard |
| `sweep_0_5s_directional_size_change` | Reversal higher | Reversal higher | 0.410 raw / 0.590 separation | 0.397 raw / 0.603 separation | -0.181 | -0.205 | 383 | 162 | Direction survived, still weak evidence |
| `post_5_30s_trade_count` | Continuation higher | Reversal higher | 0.620 | 0.461 raw / 0.539 separation | 0.240 | -0.079 | 383 | 162 | Failed / flipped |
| `post_5_30s_trade_events_per_second` | Continuation higher | Reversal higher | 0.620 | 0.461 raw / 0.539 separation | 0.240 | -0.079 | 383 | 162 | Failed / flipped |

Beginner translation:

- The best in-sample post-sweep activity idea did not clearly survive.
- MBP event count still pointed the same way, but the effect became tiny.
- Trade count actually flipped direction in the holdout.
- The size-change feature kept the same direction, but it had weak permutation evidence in both samples, so it is not a strong strategy feature.

## Feature By Feature

### `post_5_30s_mbp_event_count`

Definition:

```text
count all MBP-1 rows from sweep_ts + 5s through sweep_ts + 30s
```

In-sample:

```text
continuation median = 14190.0
reversal median     = 11783.5
AUC                 = 0.616
Cliff's delta       = 0.233
```

Holdout:

```text
continuation median = 17966.0
reversal median     = 16168.0
AUC                 = 0.534
Cliff's delta       = 0.067
```

The direction stayed the same, but the edge nearly disappeared. AUC moved close to 0.50, which means near-random separation.

### `post_5_30s_mbp_events_per_second`

Definition:

```text
post_5_30s_mbp_event_count / 25 seconds
```

This is the same signal as event count because the window length is fixed.

In-sample:

```text
continuation median = 567.60
reversal median     = 471.34
AUC                 = 0.616
Cliff's delta       = 0.233
```

Holdout:

```text
continuation median = 718.64
reversal median     = 646.72
AUC                 = 0.534
Cliff's delta       = 0.067
```

Same conclusion: direction survived, effect weakened hard.

### `sweep_0_5s_directional_size_change`

Definition:

```text
direction = +1 for high sweeps
direction = -1 for low sweeps

bid_size_change = last_bid_size - first_bid_size
ask_size_change = last_ask_size - first_ask_size

directional_size_change = direction * (bid_size_change - ask_size_change)
```

Window:

```text
sweep_ts through sweep_ts + 5 seconds
```

In-sample:

```text
continuation median = 0.0
reversal median     = 1.0
raw AUC             = 0.410
separation AUC      = 0.590
Cliff's delta       = -0.181
```

Holdout:

```text
continuation median = 0.0
reversal median     = 1.0
raw AUC             = 0.397
separation AUC      = 0.603
Cliff's delta       = -0.205
```

This one held direction and got slightly stronger by separation AUC. But both in-sample and holdout permutation p-values were poor, so it is not strong enough to trust as a strategy feature yet.

### `post_5_30s_trade_count`

Definition:

```text
count MBP-1 rows where action == "T"
from sweep_ts + 5s through sweep_ts + 30s
```

In-sample:

```text
continuation median = 754.0
reversal median     = 580.5
AUC                 = 0.620
Cliff's delta       = 0.240
```

Holdout:

```text
continuation median = 704.0
reversal median     = 764.0
raw AUC             = 0.461
separation AUC      = 0.539
Cliff's delta       = -0.079
```

This failed the holdout. In-sample said more trades after the sweep favored continuation; holdout said reversals had slightly more trades.

### `post_5_30s_trade_events_per_second`

Definition:

```text
post_5_30s_trade_count / 25 seconds
```

This is the same signal as trade count because the window length is fixed.

In-sample:

```text
continuation median = 30.16
reversal median     = 23.22
AUC                 = 0.620
Cliff's delta       = 0.240
```

Holdout:

```text
continuation median = 28.16
reversal median     = 30.56
raw AUC             = 0.461
separation AUC      = 0.539
Cliff's delta       = -0.079
```

Same conclusion: failed and flipped.

## Did The Evidence Strengthen, Weaken, Or Disappear?

| Feature idea | Result |
|---|---|
| Post-sweep MBP event intensity | Weakened hard. Direction remained but effect became tiny. |
| Post-sweep trade activity | Disappeared / flipped. Not reliable. |
| First-5-second directional size change | Direction survived, but evidence is still weak. |
| Prior-day level continuation context | Strengthened. It survived very cleanly. |

## Important Holdout Observation

The strongest holdout-ranked feature was:

```text
pre_60s_directional_aggressive_trade_ratio
```

Holdout stats:

```text
continuation median = 0.025
reversal median     = 0.070
separation AUC      = 0.685
Cliff's delta       = -0.371
```

This says reversals had more aggressive trade activity in the sweep direction before the sweep.

But this was not one of the exact frozen top 5 from the in-sample discovery run, so we should not promote it as validated proof from this test. Treat it as a new hypothesis to freeze and validate on future data.

## Beginner Conclusion

The prior-day level context looks real enough to keep studying:

```text
prior_day_high and prior_day_low sweeps continued about two-thirds of the time in both samples.
```

The top post-sweep confirmation features did not validate strongly:

```text
event intensity weakened
trade activity flipped
size change survived direction but remained statistically weak
```

That means the core feature edge from the in-sample top 5 is not strong enough yet.

## Strategy Prototype Decision

Answer: not yet.

There is not enough evidence to justify building a simple strategy prototype from the frozen top post-sweep confirmation features.

What is justified:

1. Keep prior-day high/low sweeps as an important context.
2. Freeze `pre_60s_directional_aggressive_trade_ratio` as a new hypothesis.
3. Validate that new hypothesis only on future data or a separate untouched period.
4. Avoid optimizing thresholds from this holdout.

The best current research statement is:

```text
Prior-day sweep continuation context survived OOS.
The selected post-sweep confirmation features did not survive strongly enough for strategy construction.
```
