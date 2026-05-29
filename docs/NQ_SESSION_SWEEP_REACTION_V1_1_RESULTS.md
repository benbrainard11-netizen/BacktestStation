# NQ Session Sweep Reaction V1.1 Results

## Beginner Summary

V1.1 keeps the original V1 strategy frozen and changes only the session logic around sweeps.

V1 treated the first sweep after the next Globex session opened as decisive. That meant an overnight sweep could automatically kill the setup before regular trading hours started. V1.1 changes the question:

- Overnight and pre-09:35 ET sweeps are context only.
- The first actionable sweep is the first RTH sweep from 09:35 ET through 10:30 ET.
- Execution, stop, target, slippage, commission, and MBP-1 confirmation settings are unchanged.

In plain English: V1.1 says, "I care what price did overnight, but I only act on the first real RTH sweep after the opening five minutes."

## What Changed

V1 remains untouched. V1.1 adds separate research modules:

- `backend/app/research/nq_session_sweep_reaction_v1_1.py`
- `backend/app/research/nq_session_sweep_reaction_v1_1_chunked.py`
- `backend/app/research/nq_session_sweep_reaction_v1_1_session.py`
- `backend/app/research/nq_session_sweep_reaction_v1_1_trade_flow.py`
- `backend/app/research/nq_session_sweep_reaction_v1_1_simulation.py`
- `backend/app/research/nq_session_sweep_reaction_v1_1_context.py`
- `backend/app/cli/nq_session_sweep_reaction_v1_1_chunked.py`

The new comparison utility is:

- `backend/app/cli/compare_nq_session_sweep_reaction.py`

Tests are in:

- `backend/tests/test_nq_session_sweep_reaction_v1_1.py`

## Leakage Protections

The study still avoids lookahead:

- The prior session range, close position, and armed side are known before the next RTH session.
- Overnight context uses only data before 09:35 ET.
- The actionable RTH sweep is detected only after 09:35 ET.
- MBP-1 confirmation uses the 30 seconds after the sweep, then entry can only happen after confirmation and a reclaim bar close.
- Stop, target, and exit simulation use only data after entry.
- No stop, target, reward, or threshold optimization was done.

## Output Location

Combined V1.1 full available MBP-1 output:

`data/backtests/nq_session_sweep_reaction_v1_1_available_mbp1_2026-03-02_2026-05-01_combined/`

Important files:

- `summary.json`
- `sessions.csv`
- `trades.csv`
- `replay_events.csv`
- `daily_loads.csv`
- `v1_v1_1_comparison.json`
- `v1_v1_1_skip_reason_comparison.csv`
- `v1_v1_1_funnel_comparison.csv`
- `sweep_context_counts.csv`
- `sweep_context_by_skip_reason.csv`
- `rth_sweep_by_overnight_sweep.csv`
- `mbp_confirmation_attempts.csv`
- `mbp_confirmation_distribution.csv`

## Full Window Run

Available MBP-1 window tested:

- Start: 2026-03-02
- End: 2026-05-01
- Sessions: 44
- Completed sessions: 44
- Excluded sessions: 0
- Trades: 0
- Net PnL: 0
- Net R: 0

V1.1 was able to process March 27, which the first V1 combined result had marked as an R2 stall exclusion.

## V1 vs V1.1

| Metric | V1 | V1.1 |
|---|---:|---:|
| Sessions | 44 | 44 |
| Completed sessions | 43 | 44 |
| Excluded sessions | 1 | 0 |
| Trades | 0 | 0 |
| Trade frequency | 0.0% | 0.0% |
| Pre-09:35 sweep invalidations | 20 | 0 |
| RTH/actionable sweep sessions | 4 | 17 |
| Aligned sweep sessions | 0 | 14 |
| MBP confirmation failures | 0 | 14 |

The structural change worked: V1.1 no longer kills the setup just because the level was swept overnight. But it still does not produce trades because the current MBP-1 imbalance filter is too strict for this sample.

## V1.1 Skip Reasons

| Skip reason | Sessions |
|---|---:|
| no_actionable_sweep_before_cutoff | 14 |
| mbp_confirmation_failed | 14 |
| neutral_session_bias | 7 |
| range_sanity_failed | 6 |
| opposite_side_first | 3 |

This says 14 sessions had no RTH sweep by 10:30 ET, and 14 sessions had the right RTH sweep but failed MBP confirmation.

## Sweep Context

Overnight sweep direction:

- None: 19
- High: 13
- Low: 12

RTH first sweep direction:

- None: 27
- High: 10
- Low: 7

Overnight vs RTH relationship:

- None: 19
- Aligned: 16
- Overnight only: 8
- Conflicted: 1

This is useful research data even without trades, because we can now see whether overnight behavior agrees or disagrees with the first RTH sweep.

## MBP-1 Confirmation Finding

There were 14 aligned RTH sweep attempts that reached MBP confirmation. All 14 failed the current threshold.

The 30-second MBP-1 imbalance values were tightly clustered near zero:

- Mean: 0.0042
- Median: 0.0060
- Min: -0.0189
- Max: 0.0327

The current thresholds are +0.20 for long confirmation and -0.20 for short confirmation. In this sample, none of the aligned RTH sweeps came close.

## Interpretation

Trade frequency is still not reasonable for a strategy backtest because V1.1 produced zero trades. That means we do not have a meaningful trade sample for win rate, expectancy, drawdown, or equity curve analysis.

The core session-sweep idea is not dead. V1.1 shows that first RTH sweeps do occur often enough to study: 17 out of 31 armed sessions had an RTH sweep, and 14 were aligned with the planned side. What did not survive is the full V1.1 entry rule as a tradable strategy candidate, because the MBP-1 confirmation feature filtered every aligned attempt.

The careful next step is not to optimize targets or stops. The next research step is to inspect the 14 MBP confirmation attempts and study the imbalance feature as a continuous diagnostic instead of a hard entry gate.
