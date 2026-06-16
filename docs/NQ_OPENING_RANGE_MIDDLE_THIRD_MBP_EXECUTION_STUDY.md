# NQ Opening-Range Middle-Third MBP Execution Study

## Purpose

This study freezes the opening-range definitions from the validated descriptive study and zooms in on only one context:

- The 09:30-10:00 ET opening-range candle closed in the middle third of its own range.

The goal is descriptive validation, not strategy optimization.

It asks:

- When the opening-range close is in the middle third, do first breaks of the OR high or OR low continue or reverse?
- Does MBP/event-level sequencing agree with the earlier bar-based hint?
- Do any simple execution styles look stable enough to justify a frozen strategy prototype?

Beginner read: the earlier study found that "middle-third OR close" was the cleanest context where opening-range breaks continued more often. This study checks that idea with more precise event sequencing before turning it into a real strategy.

## Frozen Definitions

These definitions are unchanged from the opening-range validation study.

Opening range:

- Market: NQ continuous futures, `NQ.c.0`
- Session time zone: Eastern Time
- Opening range window: 09:30-10:00 ET
- OR high: highest price inside the opening range
- OR low: lowest price inside the opening range
- OR range: OR high minus OR low
- Required context: opening-drive close bucket equals `middle_third`

First break:

- Starts after the opening range, at 10:00 ET.
- High break: first MBP trade above the OR high.
- Low break: first MBP trade below the OR low.

Outcome labels:

- High-break continuation target: `OR high + OR range`
- High-break reversal target: `OR low`
- Low-break continuation target: `OR low - OR range`
- Low-break reversal target: `OR high`
- If neither target is reached before the end of the session, the event is `ambiguous`.

No thresholds, stops, targets, or filters were optimized in this study.

## MBP/Event-Level Sequencing

The earlier study used 1-minute bars. This study uses MBP/event-level data after 10:00 ET.

That matters because MBP rows preserve order better than bars. If price hits one level first and then the other level later, MBP sequencing can see the order. A 1-minute bar can sometimes hide that order.

Implementation files:

- `backend/app/research/nq_opening_range_mbp_execution.py`
- `backend/app/research/nq_opening_range_mbp_execution_sequence.py`
- `backend/app/research/nq_opening_range_mbp_execution_fills.py`
- `backend/app/research/nq_opening_range_mbp_execution_stats.py`
- `backend/app/research/nq_opening_range_mbp_execution_types.py`
- `backend/app/research/nq_opening_range_mbp_execution_utils.py`
- `backend/app/cli/nq_opening_range_mbp_execution.py`
- `backend/app/cli/combine_nq_opening_range_mbp_execution.py`
- `backend/tests/test_nq_opening_range_mbp_execution.py`

## Execution Styles Tested

The study compares three fixed entry styles.

Immediate break:

- Enter on the first valid quote after the MBP trade breaks the OR high or OR low.
- Longs use ask plus one tick of slippage.
- Shorts use bid minus one tick of slippage.

First retest:

- After the break, wait for price to retest the broken OR level.
- For a high break, a retest means price trades back to or below the OR high.
- For a low break, a retest means price trades back to or above the OR low.
- The retest must happen within 30 minutes.

30-second confirmation:

- Wait 30 seconds after the break.
- Enter only if the quote mid is still beyond the broken OR level.
- This is stricter, so it skips more events.

Shared execution assumptions:

- Stop: opposite side of the opening range
- Target: one OR width beyond the broken side
- Slippage: 1 tick
- Commission: $2.00 per side
- Quantity: 1 NQ contract
- Forced flat: 16:00 ET

Beginner read: these are not optimized versions. They are simple ways to ask, "If I tried to trade this same event in a realistic way, does the idea still look alive?"

## Data Produced

Combined output folder:

`data/backtests/nq_opening_range_middle_third_mbp_combined_2025-12-01_2026-05-23`

Key output files:

- `or_middle_third_source_events.csv`
- `or_middle_third_mbp_events.csv`
- `or_middle_third_mbp_attempts.csv`
- `or_middle_third_mbp_trades.csv`
- `or_middle_third_mbp_outcomes.csv`
- `or_middle_third_mbp_variant_summary.csv`
- `or_middle_third_mbp_monthly.csv`
- `or_middle_third_mbp_walk_forward.csv`
- `or_middle_third_mbp_stability.csv`
- `or_middle_third_mbp_summary.json`
- `or_middle_third_mbp_config.json`

Coverage note:

- Completed MBP-sequenced sample: 30 middle-third OR sessions.
- Completed months: December 2025, January 2026, March 2026, April 2026, and selected May 2026 sessions.
- Holdout split remains frozen at 2026-02-01.

Important limitation: the code can run a larger window, but full-window R2 reads were too slow for this interactive run. Treat this as a completed validation sample, not as the final full-data answer.

## Continuation Vs Reversal

| Scope | Break Type | Events | Labeled | Continuations | Reversals | Ambiguous | Continuation Rate |
|---|---|---:|---:|---:|---:|---:|---:|
| Full | All | 30 | 25 | 17 | 8 | 5 | 68.0% |
| Full | OR high break | 13 | 10 | 9 | 1 | 3 | 90.0% |
| Full | OR low break | 17 | 15 | 8 | 7 | 2 | 53.3% |
| In-sample | All | 13 | 9 | 6 | 3 | 4 | 66.7% |
| In-sample | OR high break | 4 | 2 | 2 | 0 | 2 | 100.0% |
| In-sample | OR low break | 9 | 7 | 4 | 3 | 2 | 57.1% |
| Holdout | All | 17 | 16 | 11 | 5 | 1 | 68.8% |
| Holdout | OR high break | 9 | 8 | 7 | 1 | 1 | 87.5% |
| Holdout | OR low break | 8 | 8 | 4 | 4 | 0 | 50.0% |

Beginner read:

- The middle-third context still looks better than the broad opening-range baseline.
- The useful signal seems concentrated in OR high breaks.
- OR low breaks were basically a coin flip in holdout.

## Execution Results

| Entry Style | Full Signals | Full Net PnL | Full Avg/Signal | Holdout Signals | Holdout Net PnL | Holdout Avg/Signal | Holdout Win Rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Immediate break | 30 | $16,400 | $546.67 | 17 | $14,237 | $837.47 | 64.7% |
| First retest | 30 | $15,900 | $530.00 | 17 | $14,087 | $828.65 | 64.7% |
| 30-second confirmation | 30 | $3,792 | $126.40 | 17 | -$1,704 | -$100.24 | 50.0% |

Beginner read:

- Immediate break and first retest both stayed positive in the holdout sample.
- First retest did not reduce trade count here because every event found a retest within the fixed 30-minute window.
- The 30-second confirmation version skipped many trades and turned negative in holdout.

## Monthly Behavior

| Entry Style | 2025-12 | 2026-01 | 2026-03 | 2026-04 | 2026-05 |
|---|---:|---:|---:|---:|---:|
| Immediate break | $1,524 | $639 | $9,150 | $7,377 | -$2,290 |
| First retest | $1,354 | $459 | $9,280 | $7,242 | -$2,435 |
| 30-second confirmation | $7,228 | -$1,732 | -$338 | $2,746 | -$4,112 |

Beginner read: the strongest months were March and April 2026. May was negative for every entry style in the completed sample. That is why the result is promising but not yet stable enough.

## Walk-Forward Read

The walk-forward check used the frozen rule of requiring at least 3 prior months before testing a new month.

| Entry Style | Walk-Forward Folds | Positive Folds | WF Net PnL | Stability Read |
|---|---:|---:|---:|---|
| Immediate break | 2 | 1 | $5,087 | too_sparse |
| First retest | 2 | 1 | $4,807 | too_sparse |
| 30-second confirmation | 2 | 1 | -$1,366 | too_sparse |

Beginner read: walk-forward is the stricter test. It asks, "If we only knew the past, did the next month work?" We only have 2 completed folds here, and one of them was negative. That is not enough proof.

## Findings

Most promising:

- OR high breaks inside the middle-third OR close context.
- Immediate break and first retest entries.

Weak or rejected:

- OR low breaks did not show a strong continuation edge.
- 30-second confirmation did not survive holdout.

What looks real:

- The middle-third context remained directionally positive under MBP sequencing.
- The OR high break split is the cleanest descriptive lead.

What may be noise:

- The very large March and April profits may be regime-specific.
- The sample is small enough that one month can heavily change the conclusion.
- First retest looking almost identical to immediate entry may depend on how often NQ revisited the broken OR level in this sample.

## Strategy Prototype Decision

This does not yet justify a fully frozen strategy prototype.

Reason:

- The holdout result is encouraging.
- The MBP/event-level sequencing did not kill the idea.
- But the completed sample is only 30 sessions.
- Walk-forward has only 2 test folds.
- May 2026 was negative for every execution style.

Best current decision:

- Keep the setup as a research candidate.
- Do not optimize anything.
- Rerun the same frozen definitions on a larger MBP window.
- If the same pattern survives with more months, the first prototype should focus on middle-third OR close plus OR high first breaks, comparing only immediate break and first retest.

## How To Reproduce

Run one chunk:

```powershell
backend\.venv\Scripts\python.exe -m app.cli.nq_opening_range_mbp_execution --events data\backtests\nq_opening_range_descriptive_2025-05-01_2026-05-23\opening_range_descriptive_events.csv --start 2026-04-01 --end 2026-05-01 --output data\backtests\nq_opening_range_middle_third_mbp_2026-04-01_2026-05-01
```

Combine completed chunks:

```powershell
backend\.venv\Scripts\python.exe -m app.cli.combine_nq_opening_range_mbp_execution --output data\backtests\nq_opening_range_middle_third_mbp_combined_2025-12-01_2026-05-23 data\backtests\nq_opening_range_middle_third_mbp_2025-12-01_2026-01-01 data\backtests\nq_opening_range_middle_third_mbp_2026-01-01_2026-02-01 data\backtests\nq_opening_range_middle_third_mbp_2026-03-01_2026-04-01 data\backtests\nq_opening_range_middle_third_mbp_2026-04-01_2026-05-01 data\backtests\nq_opening_range_middle_third_mbp_2026-05-13_2026-05-14 data\backtests\nq_opening_range_middle_third_mbp_2026-05-18_2026-05-19 data\backtests\nq_opening_range_middle_third_mbp_2026-05-19_2026-05-20 data\backtests\nq_opening_range_middle_third_mbp_2026-05-20_2026-05-21 data\backtests\nq_opening_range_middle_third_mbp_2026-05-22_2026-05-23
```
