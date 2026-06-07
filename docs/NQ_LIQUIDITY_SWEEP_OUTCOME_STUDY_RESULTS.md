# NQ Liquidity Sweep Outcome Study Results

## Status

Implemented and run across the full available NQ MBP-1 window in this workspace.

This is still research only. No thresholds were optimized, no entry rules were created, and no trading strategy was built from these results.

## Where The Outputs Are

Local export folder:

```text
data/backtests/nq_liquidity_sweep_outcomes_available_mbp1_2026-03-02_2026-05-01/
```

Exported files:

```text
liquidity_sweep_events.csv
liquidity_sweep_features.csv
liquidity_sweep_feature_rankings.csv
liquidity_sweep_top5_features.csv
liquidity_sweep_feature_distributions.csv
liquidity_sweep_monthly_stability.csv
liquidity_sweep_examples.csv
liquidity_sweep_summary.json
liquidity_sweep_config.json
liquidity_sweep_feature_metadata.csv
liquidity_sweep_sessions.csv
liquidity_sweep_daily_loads.csv
```

The `data/` folder is intentionally gitignored because it can contain local market data. This report records the important results in git without committing raw generated data.

## Beginner Summary

The study looked at what happened after NQ swept four important liquidity levels:

| Level type | Beginner meaning |
|---|---|
| `prior_day_high` | Yesterday's regular-session high |
| `prior_day_low` | Yesterday's regular-session low |
| `overnight_high` | The high made before the 09:30 ET open |
| `overnight_low` | The low made before the 09:30 ET open |

For each sweep, the study asked:

```text
Did price continue through the level, or did it fail and reverse?
```

Then it measured MBP-1 order book and trade activity features around the sweep to see which features separated continuations from reversals.

## Run Window And Sample Size

| Item | Value |
|---|---:|
| Symbol | `NQ.c.0` |
| Available MBP-1 window tested | `2026-03-02` through `2026-05-01` |
| Sessions with sweep events | 42 |
| Total sweep events | 90 |
| Non-ambiguous labeled sweeps | 87 |
| Continuation breakouts | 47 |
| Failed breakout / reversals | 40 |
| Ambiguous | 3 |
| Calendar months represented | 2 |

Important caveat: the original spec says we should prefer at least 100 non-ambiguous sweeps and at least 3 calendar months before calling a feature truly promising. This run has 87 usable sweeps across 2 months, so every result is labeled `early_evidence_only`.

## Leakage Safety

The study was built to avoid lookahead bias:

- Prior-day highs/lows use only the previous completed RTH session.
- Overnight highs/lows freeze at 09:30 ET.
- Sweeps are detected from MBP-1 trade prints, not future bars.
- Sweep detection starts at 09:35 ET to skip the noisiest first five minutes.
- Features are measured before the outcome window begins.
- Outcome labels start after the feature window.
- The feature rankings only include features marked `knowable_before_entry = true`.
- No thresholds were optimized on these results.

Beginner translation: the study does not let itself cheat by using information from after the answer was already known.

## Level Type Results

| Level type | Continuations | Reversals | Ambiguous | Non-ambiguous | Continuation rate |
|---|---:|---:|---:|---:|---:|
| `prior_day_high` | 16 | 7 | 2 | 23 | 69.6% |
| `prior_day_low` | 13 | 7 | 0 | 20 | 65.0% |
| `overnight_high` | 10 | 13 | 1 | 23 | 43.5% |
| `overnight_low` | 8 | 13 | 0 | 21 | 38.1% |

The prior-day levels produced the clearest continuation behavior in this sample. Sweeps of prior-day high and prior-day low continued more often than they reversed.

The overnight levels leaned more toward failed breakout / reversal behavior, especially `overnight_low`.

This is useful session context, but not enough by itself to trade. Each level type only has about 20 to 23 usable examples.

## Feature Group Results

| Feature group | Best rank | Best separation AUC | Median separation AUC | Beginner read |
|---|---:|---:|---:|---|
| `trade_activity` | 1 | 0.698 | 0.563 | Strongest group. Trade pressure before the sweep mattered most. |
| `spread` | 2 | 0.672 | 0.552 | Useful early-confirmation group. Spread behavior changed around continuations. |
| `imbalance` | 3 | 0.650 | 0.522 | One top-book feature looked useful, but the group was not broadly strong. |
| `size_changes` | 4 | 0.637 | 0.581 | Several features showed signal, but interpretation needs care. |
| `event_intensity` | 14 | 0.599 | 0.527 | Weakest group. Raw book-update speed was not very predictive here. |

Separation AUC is the easier number to read here:

```text
0.50 = no separation
0.60 = mild separation
0.70 = useful-looking separation
```

None of the groups reached strong evidence. The best group, `trade_activity`, came close to 0.70 on its best feature.

## Top 5 Eligible Features

All five features below are eligible in the leakage sense, but they are not all known at the same time:

- `pre_sweep`: known before the sweep print.
- `at_sweep`: known once the sweep print happens.
- `post_sweep_confirmation`: known only after the confirmation window closes. A future strategy would have to wait.

| Rank | Feature | Group | Timing | Sample | Separation AUC | Cliff's delta | Permutation p | Beginner meaning |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | `pre_60s_directional_aggressive_trade_ratio` | `trade_activity` | `pre_sweep` | 87 | 0.698 | -0.395 | 0.010 | More aggressive trading in the sweep direction before the sweep was associated with more reversals. |
| 2 | `sweep_0_5s_spread_widening` | `spread` | `post_sweep_confirmation` | 87 | 0.672 | 0.344 | 0.257 | Spread widening during the first 5 seconds after the sweep leaned toward continuation. |
| 3 | `directional_sweep_top_book_imbalance` | `imbalance` | `at_sweep` | 87 | 0.650 | 0.299 | 0.297 | Top-of-book imbalance at the sweep leaned toward continuation when it supported the sweep direction. |
| 4 | `sweep_0_5s_mean_ask_size` | `size_changes` | `post_sweep_confirmation` | 87 | 0.637 | -0.274 | 0.010 | Lower average ask size in the first 5 seconds was associated with continuations in this combined sample. |
| 5 | `pre_10s_trade_volume` | `trade_activity` | `pre_sweep` | 87 | 0.636 | -0.272 | 0.030 | More trade volume in the 10 seconds before the sweep was associated with more reversals. |

## Top Feature Details

### 1. `pre_60s_directional_aggressive_trade_ratio`

This measures how much aggressive trading happened in the sweep direction during the 60 seconds before the sweep.

| Metric | Value |
|---|---:|
| Continuation median | 0.020 |
| Reversal median | 0.070 |
| Median difference | -0.049 |
| Separation AUC | 0.698 |
| Cliff's delta | -0.395 |
| March separation AUC | 0.718 |
| April separation AUC | 0.678 |

Interpretation: reversals had more aggressive trading in the sweep direction before the sweep. That can mean the market was already chasing into the level and had less fuel left after the sweep.

This is the cleanest feature because it is known before the sweep and had the same direction in both months.

### 2. `sweep_0_5s_spread_widening`

This measures whether the bid/ask spread widened during the first 5 seconds after the sweep.

| Metric | Value |
|---|---:|
| Continuation median | 0.25 |
| Reversal median | 0.00 |
| Median difference | 0.25 |
| Separation AUC | 0.672 |
| Cliff's delta | 0.344 |
| March separation AUC | 0.694 |
| April separation AUC | 0.647 |

Interpretation: continuations showed more spread widening right after the sweep. That may represent instability or urgency after the level breaks.

Weakness: the permutation p-value was not strong, so this could still be noisy.

### 3. `directional_sweep_top_book_imbalance`

This measures whether the top-of-book size at the sweep print leaned with or against the sweep direction.

| Metric | Value |
|---|---:|
| Continuation median | 0.000 |
| Reversal median | -0.333 |
| Median difference | 0.333 |
| Separation AUC | 0.650 |
| Cliff's delta | 0.299 |
| March separation AUC | 0.617 |
| April separation AUC | 0.702 |

Interpretation: continuations had less negative, and sometimes more supportive, top-book imbalance at the sweep print.

Weakness: March was basically flat by median difference, while April was stronger. This needs more months before trusting it.

### 4. `sweep_0_5s_mean_ask_size`

This measures average ask-side size during the first 5 seconds after the sweep.

| Metric | Value |
|---|---:|
| Continuation median | 1.882 |
| Reversal median | 2.060 |
| Median difference | -0.178 |
| Separation AUC | 0.637 |
| Cliff's delta | -0.274 |
| March separation AUC | 0.724 |
| April separation AUC | 0.610 |

Interpretation: continuations had lower average ask size in the first 5 seconds.

Weakness: raw bid/ask size features can be harder to interpret across both high sweeps and low sweeps. Before strategy work, this should be checked separately by sweep side.

### 5. `pre_10s_trade_volume`

This measures total trade volume in the 10 seconds before the sweep.

| Metric | Value |
|---|---:|
| Continuation median | 285.0 |
| Reversal median | 374.5 |
| Median difference | -89.5 |
| Separation AUC | 0.636 |
| Cliff's delta | -0.272 |
| March separation AUC | 0.687 |
| April separation AUC | 0.562 |

Interpretation: reversals had more trade volume right before the sweep. Like the number-one feature, this supports an exhaustion idea: if the market uses a lot of energy just to reach the level, the sweep may fail more often.

Weakness: April was weaker than March.

## Monthly Stability

| Feature | March effect | April effect | Stability read |
|---|---|---|---|
| `pre_60s_directional_aggressive_trade_ratio` | Reversal higher, separation AUC 0.718 | Reversal higher, separation AUC 0.678 | Best stability in this run |
| `sweep_0_5s_spread_widening` | Continuation higher, separation AUC 0.694 | Continuation higher, separation AUC 0.647 | Stable but needs stronger significance |
| `directional_sweep_top_book_imbalance` | Flat by median, separation AUC 0.617 | Continuation higher, separation AUC 0.702 | Interesting, not yet stable enough |
| `sweep_0_5s_mean_ask_size` | Reversal higher, separation AUC 0.724 | Reversal higher, separation AUC 0.610 | Direction stable, strength faded |
| `pre_10s_trade_volume` | Reversal higher, separation AUC 0.687 | Reversal higher, separation AUC 0.562 | Direction stable, weak in April |

The effects are directionally stable for four of the five features across March and April. But two months is not enough to call the effects robust.

## What Looks Most Likely Real

The most believable finding is the pre-sweep trade-activity cluster:

- `pre_60s_directional_aggressive_trade_ratio`
- `pre_10s_trade_volume`
- `pre_10s_directional_aggressive_trade_ratio`
- `pre_10s_trade_count`
- `pre_10s_trade_events_per_second`

These all tell a similar story: heavy trade activity into the sweep often looked more like exhaustion than clean continuation.

The second believable clue is early spread behavior. `sweep_0_5s_spread_widening` was stable by month and had a medium effect size, but its p-value was weak. I would treat it as a watchlist feature, not proof.

The level-type context also looks useful:

- Prior-day high/low sweeps leaned continuation.
- Overnight high/low sweeps leaned reversal.

That may become a useful context filter later, but the level-type sample sizes are still small.

## What Looks Like Noise Or Needs Caution

Raw top-book and raw bid/ask size features need caution. They can be real, but they can also be side-dependent. For example, ask size may mean something different for high sweeps than for low sweeps.

Event intensity was weak. Counting how many MBP events happened was less useful than measuring what trades and spread actually did.

Anything that only worked in one month should be treated as noise until more months confirm it.

## Strategy Prototype Decision

Answer: not yet.

There is enough evidence to justify continued research, but not enough to justify building a real strategy prototype from these features today.

Why:

- The study found 87 usable labeled sweeps, below the 100-sweep guideline.
- It only covered 2 calendar months, below the 3-month guideline.
- The top pre-sweep feature is genuinely interesting, but it still needs a larger validation window.
- Some top features are early-confirmation features, meaning a strategy would have to wait for the feature window to close.
- No thresholds have been validated out of sample.

The best next research step is not optimization. It is validation:

```text
Run the same exact study on more NQ MBP-1 data, then check whether the same feature groups stay near the top.
```

If the same pre-sweep trade-activity exhaustion signal survives more months, then it would be reasonable to design a simple strategy prototype around sweep failure versus continuation behavior.

## Implementation Map

| Area | File |
|---|---|
| CLI runner for one study window | `backend/app/cli/nq_liquidity_sweep_outcomes.py` |
| CLI combiner for shard outputs | `backend/app/cli/combine_nq_liquidity_sweep_outcomes.py` |
| Config and result types | `backend/app/research/nq_liquidity_sweep_outcomes_types.py` |
| Session levels and time windows | `backend/app/research/nq_liquidity_sweep_outcomes_sessions.py` |
| Feature definitions and timing tags | `backend/app/research/nq_liquidity_sweep_outcomes_feature_defs.py` |
| Sweep detection, labels, features | `backend/app/research/nq_liquidity_sweep_outcomes_features.py` |
| Chunked data loading and study orchestration | `backend/app/research/nq_liquidity_sweep_outcomes_chunked.py` |
| Statistical ranking | `backend/app/research/nq_liquidity_sweep_outcomes_stats.py` |
| AUC, effect size, bootstrap, permutation helpers | `backend/app/research/nq_liquidity_sweep_outcomes_stats_metrics.py` |
| Summary and examples output helpers | `backend/app/research/nq_liquidity_sweep_outcomes_stats_outputs.py` |
| Tests | `backend/tests/test_nq_liquidity_sweep_outcomes.py` |

## Reproduction Notes

The full available run was executed as date shards and then combined:

```powershell
$env:PYTHONPATH='backend'

backend\.venv\Scripts\python.exe -m app.cli.nq_liquidity_sweep_outcomes --start 2026-03-02 --end 2026-03-16 --bootstrap-iterations 25 --permutation-iterations 25 --output-dir data\backtests\nq_liquidity_sweep_outcomes_2026-03-02_2026-03-16
backend\.venv\Scripts\python.exe -m app.cli.nq_liquidity_sweep_outcomes --start 2026-03-16 --end 2026-04-01 --bootstrap-iterations 25 --permutation-iterations 25 --output-dir data\backtests\nq_liquidity_sweep_outcomes_2026-03-16_2026-04-01
backend\.venv\Scripts\python.exe -m app.cli.nq_liquidity_sweep_outcomes --start 2026-04-01 --end 2026-04-17 --bootstrap-iterations 25 --permutation-iterations 25 --output-dir data\backtests\nq_liquidity_sweep_outcomes_2026-04-01_2026-04-17
backend\.venv\Scripts\python.exe -m app.cli.nq_liquidity_sweep_outcomes --start 2026-04-17 --end 2026-05-01 --bootstrap-iterations 25 --permutation-iterations 25 --output-dir data\backtests\nq_liquidity_sweep_outcomes_2026-04-17_2026-05-01

backend\.venv\Scripts\python.exe -m app.cli.combine_nq_liquidity_sweep_outcomes --input-dir data\backtests\nq_liquidity_sweep_outcomes_2026-03-02_2026-03-16 --input-dir data\backtests\nq_liquidity_sweep_outcomes_2026-03-16_2026-04-01 --input-dir data\backtests\nq_liquidity_sweep_outcomes_2026-04-01_2026-04-17 --input-dir data\backtests\nq_liquidity_sweep_outcomes_2026-04-17_2026-05-01 --bootstrap-iterations 100 --permutation-iterations 100 --output-dir data\backtests\nq_liquidity_sweep_outcomes_available_mbp1_2026-03-02_2026-05-01
```

The chunk runs used 25 resampling passes for speed while loading MBP-1 data. The final combined ranking used 100 bootstrap/permutation passes on the combined event table.
