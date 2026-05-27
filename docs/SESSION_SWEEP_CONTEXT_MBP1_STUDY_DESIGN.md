# Session Sweep Context + MBP-1 Study Design

## Beginner Summary

The prior final-15m study did not prove a simple next-day direction edge.

The strongest hints were narrower:

- Which side gets swept first next session.
- What price does after the first sweep.
- Whether full-session context matters more than the final candle alone.
- Whether MBP-1 order-book imbalance into the close improves the read.

This study should answer a more focused question:

```text
At the end of a completed Globex session, can we predict:
1. whether next session sweeps the prior high or prior low first,
2. whether that sweep continues or reverses,
3. whether MBP-1 imbalance into the close improves the prediction?
```

This is a research study, not a trading strategy. The goal is to find whether the effect is real enough to deserve a strategy test later.

## 1. Core Objects

### Anchor session

The anchor session is the completed Globex session we are studying:

```text
18:00 ET previous calendar day -> 17:00 ET current calendar day
```

At 17:00 ET, this session is fully known. That means these are safe inputs:

- session open, high, low, close
- session range
- session close position
- final 15m candle
- prior sessions
- MBP-1 events before the 17:00 ET close

### Next session

The next session is the following Globex session:

```text
18:00 ET anchor day -> 17:00 ET next trading day
```

Anything from the next session is an outcome label. It is the answer, not an input.

## 2. First Sweep Behavior

### Beginner idea

A liquidity sweep means price trades just beyond an obvious level where stops may be resting.

For this study, the obvious levels are:

- anchor session high
- anchor session low

### Objective definition

Let:

```text
prior_high = anchor session high
prior_low = anchor session low
buffer = minimum extra distance required to count as a real sweep
```

Default buffer:

```text
0.25 NQ points
```

That is one NQ tick. We can also test 0.00, 0.50, and 1.00 points as sensitivity checks.

High sweep:

```text
price trades above prior_high + buffer
```

Low sweep:

```text
price trades below prior_low - buffer
```

First sweep side:

| Label | Meaning |
|---|---|
| `prior_high_swept_first` | next session swept the anchor high before the anchor low |
| `prior_low_swept_first` | next session swept the anchor low before the anchor high |
| `both_same_bar` | bar data shows both were swept in the same bar, so sequence is uncertain |
| `both_same_mbp_timestamp` | MBP-1 sequence cannot separate the two events |
| `none` | neither side swept during the measurement window |

### Bar version vs MBP-1 version

The bar version is useful for broad testing, but it can be ambiguous.

Example:

```text
A 15m candle has high above prior_high and low below prior_low.
```

With only OHLC bars, we do not know which side happened first.

MBP-1 improves this because it preserves ordered top-of-book events. When MBP-1 exists, the study should find the first event where the top book or trade crosses the sweep threshold, then use event time and sequence to decide which side happened first.

## 3. Sweep Timing Windows

We should not only ask what happened across the whole next session. We should split time into windows:

| Window | Definition | Why it matters |
|---|---|---|
| `full_next_session` | 18:00 ET to 17:00 ET | broadest label |
| `overnight` | 18:00 ET to 09:30 ET | Globex continuation or reversal before cash open |
| `rth_morning` | 09:30 ET to 12:00 ET | most active morning behavior |
| `rth_first_60m` | 09:30 ET to 10:30 ET | early-session momentum |
| `post_or30` | after 10:00 ET | opening range break behavior |

Primary first version:

```text
Use full_next_session for first sweep side.
Also record which window the first sweep occurred in.
```

Reason:

This avoids throwing away useful sweeps that happen overnight, while still letting us compare overnight sweeps versus RTH sweeps later.

## 4. Continuation Vs Reversal After Sweep

### Beginner idea

After price sweeps a level, two broad things can happen:

- Continuation: price accepts beyond the level and keeps going.
- Reversal: price rejects the level and returns back inside the prior range.

### Direction-aware definitions

If the first sweep is a high sweep:

- continuation means price keeps pushing upward after taking the high
- reversal means price falls back inside the prior range after taking the high

If the first sweep is a low sweep:

- continuation means price keeps pushing downward after taking the low
- reversal means price rallies back inside the prior range after taking the low

### Objective labels

After the first sweep timestamp, start a fixed measurement horizon.

Recommended horizons:

```text
15 minutes
30 minutes
60 minutes
session close
```

For each horizon, calculate:

| Label | Meaning |
|---|---|
| `sweep_continuation_pts` | maximum favorable move beyond the swept level |
| `sweep_reversal_pts` | maximum move back inside the prior range |
| `sweep_close_back_inside` | whether price closed back inside the prior range by horizon end |
| `sweep_acceptance_close` | whether price closed beyond the swept level by horizon end |
| `sweep_continuation_first` | continuation target hit before reversal target |
| `sweep_reversal_first` | reversal target hit before continuation target |
| `sweep_outcome` | `continuation`, `reversal`, `chop`, or `ambiguous` |

### Target-before-stop version

This is the cleanest label because it asks which event happened first.

For a high sweep:

```text
continuation target = prior_high + continuation_target_pts
reversal target = prior_high - reversal_target_pts
```

For a low sweep:

```text
continuation target = prior_low - continuation_target_pts
reversal target = prior_low + reversal_target_pts
```

Default targets:

```text
continuation_target_pts = 20
reversal_target_pts = 20
```

Also test normalized targets:

```text
0.25x anchor session range
0.50x anchor session range
```

Beginner translation:

```text
Instead of asking "did it end green or red?", we ask:
after the sweep, did it move 20 points farther in the sweep direction first,
or 20 points back against the sweep first?
```

## 5. Full-Session Context Features

These are safe because they are known when the anchor session closes at 17:00 ET.

### Primary context features

| Feature | Beginner meaning | Math |
|---|---|---|
| `session_direction` | Did the whole anchor session close up or down? | `session_close - session_open` |
| `session_close_position` | Did the session close near its high or low? | `(close - low) / (high - low)` |
| `session_close_bias` | Bullish, neutral, or bearish session close | bucketed close position |
| `session_range_pts` | How large was the session? | `high - low` |
| `prior20_range_regime` | Was today wide or narrow versus recent sessions? | percentile of current range versus prior 20 ranges |
| `prior_session_direction` | Was the previous session up or down? | previous session close minus open |
| `day_name_et` | Day of week | Monday-Friday |
| `final_close_bias` | Did final 15m candle close near its high or low? | final candle close position |
| `final_body_direction` | Did final 15m candle close above or below its open? | `final_close - final_open` |

### Candidate context interactions

Do not explode into hundreds of combinations. Start with a small pre-declared list:

1. `session_close_bias + final_close_bias`
2. `session_direction + final_close_bias`
3. `prior_session_direction + final_close_bias`
4. `prior20_range_regime + final_close_bias`
5. `session_close_bias + mbp_close_imbalance_bucket`

Beginner translation:

```text
We are asking whether the final candle only matters in certain situations,
like after a bearish full session or after a low-volatility day.
```

## 6. MBP-1 Imbalance Into The Close

### What MBP-1 gives us

MBP-1 is top-of-book data. It tells us the best bid, best ask, bid size, and ask size over time.

It does not show the full order book. It does not prove hidden orders. But it can show whether the visible top of book was leaning bid-heavy or ask-heavy into the close.

### Basic imbalance math

Top-of-book imbalance:

```text
imbalance = (bid_size - ask_size) / (bid_size + ask_size)
```

Interpretation:

| Value | Meaning |
|---:|---|
| `+1.00` | all visible size is on bid side |
| `0.00` | bid and ask size are balanced |
| `-1.00` | all visible size is on ask side |

Beginner translation:

```text
Positive imbalance means the best bid looks heavier.
Negative imbalance means the best ask looks heavier.
```

### Close-window features

Compute these using only MBP-1 events before the 17:00 ET close.

Recommended windows:

```text
last 5 minutes
last 15 minutes
last 30 minutes
```

Features:

| Feature | Meaning |
|---|---|
| `mbp_close_5m_mean_imbalance` | average top-book imbalance in final 5 minutes |
| `mbp_close_15m_mean_imbalance` | average top-book imbalance in final 15 minutes |
| `mbp_close_30m_mean_imbalance` | average top-book imbalance in final 30 minutes |
| `mbp_close_15m_imbalance_slope` | whether imbalance increased or decreased into close |
| `mbp_close_15m_bid_size_change` | whether best-bid size built or faded |
| `mbp_close_15m_ask_size_change` | whether best-ask size built or faded |
| `mbp_close_15m_spread_ticks_mean` | whether spread was normal or unstable |
| `mbp_close_15m_event_rate` | how active the book was into close |
| `mbp_close_15m_mid_return_pts` | midpoint move during the close window |

### Direction-aligned imbalance

For predicting high sweep:

```text
aligned_imbalance_for_high_sweep = raw_imbalance
```

For predicting low sweep:

```text
aligned_imbalance_for_low_sweep = -raw_imbalance
```

Reason:

- High sweep may be helped by bid support or upward pressure.
- Low sweep may be helped by ask pressure, so we flip the sign.

Use raw imbalance for the model comparison first. Use aligned imbalance only when evaluating a specific side after a prediction or side split.

## 7. Prediction Questions

Do not test everything at once. Use a small hierarchy.

### Question A: first sweep direction

Rows:

```text
one row per completed anchor session
```

Outcome:

```text
first_sweep_side = high_first vs low_first
```

Exclude from the primary model:

- `none`
- ambiguous same-bar or same-timestamp cases

Keep excluded cases in a separate diagnostic table.

### Question B: continuation vs reversal after first sweep

Rows:

```text
one row per session where a first sweep happened
```

Outcome:

```text
sweep_outcome_60m = continuation vs reversal
```

Exclude from the primary model:

- chop
- ambiguous
- no sweep

Again, keep them in diagnostics.

### Question C: RTH first 60m behavior

Rows:

```text
one row per completed anchor session
```

Outcome:

```text
next_rth_first_60m_direction = bullish vs bearish
```

This is a secondary check because the earlier study showed a hint here.

## 8. Does MBP-1 Improve Predictive Power?

Use model comparison, not just one big model.

### Model sets

| Model | Inputs | Purpose |
|---|---|---|
| Baseline | majority class only | dumb benchmark |
| Context only | full-session context | tests whether session context matters |
| Context + final candle | context plus final 15m features | tests whether final candle adds value |
| Context + MBP-1 close | context plus MBP close-window features | tests whether order book adds value |
| Context + final candle + MBP-1 | all predeclared safe features | full candidate model |

### Beginner interpretation

If MBP-1 helps, we should see:

- better out-of-sample accuracy or balanced accuracy
- lower log loss
- better calibration
- more stable results across walk-forward folds
- not just one lucky subgroup

If MBP-1 only improves in-sample results, assume overfitting.

## 9. Anti-Overfitting Rules

These rules matter more than fancy modeling.

### Use time-based splits

Do not randomly shuffle sessions.

Recommended split for 1 year:

```text
Train: first 70% of sessions
Test: last 30% of sessions
```

Better split when we have more data:

```text
Walk-forward folds:
- train 6 months, test next 1 month
- roll forward one month
```

### Pre-declare features

Before running the study, lock the feature list in code/config.

Do not keep adding features until one looks good.

### Require minimum sample sizes

Minimum group sizes:

```text
descriptive context bucket: at least 30 rows
model training class: at least 50 rows per class
test fold class: at least 20 rows per class
```

If a class is too small, mark it as `class_imbalance` and do not trust it.

### Use simple models first

Start with:

- contingency tables
- logistic regression
- shallow decision tree with max depth 2

Do not start with complex ML. With one year of daily rows, we only have about 250 samples.

### Correct for multiple testing

If we run many comparisons, some will look good by luck.

Use:

- holdout test results as the main read
- confidence intervals
- false discovery rate correction for many p-values
- a separate future out-of-sample period before trading

## 10. Leakage Rules

### Safe pre-sweep prediction features

These can be used to predict first sweep side:

- anchor session OHLC
- anchor session close position
- final 15m candle features
- prior session features
- prior 20-session range regime
- MBP-1 events ending at or before 17:00 ET

### Unsafe features for first sweep prediction

Do not use:

- next session open, high, low, close
- sweep timestamp
- sweep side
- RTH opening range
- overnight return
- any MBP-1 event after 17:00 ET

### Safe post-sweep research features

If the question is continuation vs reversal after a sweep, we may create a second study where the input time is the sweep timestamp.

For that second study, safe features can include:

- which side swept
- sweep time of day
- overshoot size at the sweep event
- MBP-1 imbalance immediately before the sweep
- spread/event rate around the sweep

But those features are not safe for predicting first sweep side before the next session starts.

Beginner translation:

```text
There are two different clocks:
1. At 17:00 ET, before the next session, we can predict which side may sweep first.
2. After the sweep happens, we can predict whether that sweep may continue or reverse.

Do not mix those clocks.
```

## 11. Proposed Output Files

```text
rows.csv
sweep_side_stats.csv
sweep_outcome_stats.csv
context_sweep_stats.csv
mbp_close_feature_stats.csv
model_comparison.csv
walk_forward_folds.csv
leakage_report.json
summary.json
```

Important columns in `rows.csv`:

- `session_date`
- `session_high`
- `session_low`
- `session_close_bias`
- `final_close_bias`
- `prior20_range_regime`
- `mbp_close_15m_mean_imbalance`
- `first_sweep_side`
- `first_sweep_window`
- `first_sweep_ts`
- `sweep_outcome_15m`
- `sweep_outcome_30m`
- `sweep_outcome_60m`
- `sweep_outcome_session_close`

## 12. Implementation Plan

Recommended files:

- `backend/app/research/session_sweep_context.py`
- `backend/app/cli/session_sweep_context_study.py`
- `backend/tests/test_session_sweep_context.py`
- `docs/SESSION_SWEEP_CONTEXT_MBP1_STUDY_DESIGN.md`

Build order:

1. Implement bar-based sweep labels and continuation/reversal labels.
2. Add session context features by reusing final-15m study logic.
3. Add MBP-1 close-window features.
4. Add model comparison outputs.
5. Add walk-forward validation.
6. Upgrade first-sweep sequencing to MBP-1 where available.

Why this order:

The bar version can run across the full 1-year dataset immediately. MBP-1 can then be layered in for the smaller period where it exists, without blocking the study design.

## 13. First Pass Acceptance Criteria

The first implementation is useful if it can answer:

- How often does NQ sweep the prior high first versus prior low first?
- Does session close bias improve that read?
- After a high or low sweep, how often does price continue versus reverse within 60 minutes?
- Do MBP-1 imbalance features into the close improve out-of-sample prediction versus context-only?
- Are results stable in time-based validation?

If the answer is no, that is still useful. It means we avoid building a strategy on a weak idea.

## 14. Current Best Hypothesis

Based on the previous study, the best focused hypothesis is:

```text
Full-session close context predicts first liquidity sweep direction better than the final 15m candle alone.
MBP-1 imbalance into the 17:00 ET close may improve this read when it agrees with session close bias.
After the first sweep, continuation/reversal should be tested as a separate post-sweep decision problem.
```

This keeps the research honest:

- one pre-session question: which side sweeps first?
- one post-sweep question: does the sweep continue or reverse?
- one additive-value question: does MBP-1 improve over bars/context alone?

First strategy candidate built from this design:

- `docs/STRATEGY_CANDIDATE_NQ_SESSION_SWEEP_REACTION_V1.md`
