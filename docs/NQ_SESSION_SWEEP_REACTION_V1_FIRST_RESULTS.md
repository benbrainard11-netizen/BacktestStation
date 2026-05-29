# NQ Session Sweep Reaction V1 First Results

Generated from the available NQ MBP-1 window in R2:

- Tested anchor sessions: `2026-03-02` through `2026-04-30`
- Completed sessions analyzed: `43`
- Excluded session: `2026-03-27`
- Exclusion reason: the next-session MBP-1 read for the weekend transition stalled during the full-window run
- Combined output folder: `data/backtests/nq_session_sweep_reaction_v1_available_mbp1_2026-03-02_2026-05-01_combined/`

This is not a one-year MBP-1 result. The R2 inventory currently shows NQ MBP-1 partitions from `2026-03-02` through `2026-05-01`.

## Beginner Summary

The strategy did not take any trades in this first real MBP-1 run.

That does not mean the idea is dead. It means V1 is currently too restrictive before it ever reaches the actual entry logic. The most important discovery is structural: the strategy looks for the first sweep from the start of the next Globex session, but entry is not allowed until `09:35 ET`. Most armed-side sweeps happen overnight or before `09:35 ET`, so the setup is invalidated before it can become a trade.

## Headline Stats

| Metric | Value | Plain-English Meaning |
|---|---:|---|
| Sessions | 44 | Number of anchor sessions in the available test window |
| Completed sessions | 43 | Sessions successfully analyzed |
| Excluded sessions | 1 | One R2 read stalled |
| Trades | 0 | No session reached entry |
| Net PnL | 0 | No trades, so no profit/loss |
| Net R | 0 | No trades, so no risk-adjusted result |
| Max drawdown | 0 | No equity movement |

## Setup Funnel

| Outcome | Count | Share of 44 Sessions | Meaning |
|---|---:|---:|---|
| Armed side swept before entry start | 20 | 45.5% | Correct level swept, but too early for V1 |
| Neutral session bias | 7 | 15.9% | Prior session close was not bullish/bearish enough |
| Range sanity failed | 6 | 13.6% | Prior session range was too unusual versus recent sessions |
| No sweep before cutoff | 6 | 13.6% | Armed level did not sweep by `10:30 ET` |
| Opposite side first | 4 | 9.1% | Wrong side swept first |
| Excluded R2 stall | 1 | 2.3% | Data read problem, not a strategy outcome |

No sessions reached MBP-1 confirmation, reclaim, entry, stop, or target.

## Equity Curve

The equity curve is flat.

That is not a positive or negative performance result. It simply means no trades fired. A flat equity curve here tells us V1 is more of a filter/invalidation study than a tradable strategy candidate in its current form.

## Trade Distribution

There is no trade distribution yet because there are no trades.

The useful distribution is the rejection distribution above. The big concentration is `armed_side_swept_before_entry_start`, which points to a timing-definition conflict rather than an execution or stop/target issue.

## Regime Analysis

### By Close Bias

| Derived Bias | Main Observation |
|---|---|
| Bullish sessions | More common than bearish in this sample; most failures were early high sweeps or no sweep |
| Bearish sessions | Fewer observations; early low sweeps were still common |
| Neutral sessions | Correctly skipped by the current spec |

### By Range Regime

| Range Regime | Main Observation |
|---|---|
| Normal range | Most armed sessions came from here, but still no entries |
| Expanded range | Often failed range sanity or swept early |
| Compressed range | Also produced early sweeps; no evidence yet that compression improves V1 |

Because there are zero trades, these regime notes are about setup availability only. They are not evidence of profitability.

## Month By Month

| Month | Sessions | Trades | Early Armed Sweep | No Sweep | Opposite First | Neutral | Range Failed | Excluded |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-03 | 22 | 0 | 11 | 1 | 2 | 4 | 3 | 1 |
| 2026-04 | 22 | 0 | 9 | 5 | 2 | 3 | 3 | 0 |

March and April tell the same story: the strategy is mostly blocked before confirmation/entry.

## Replay Inspection Workflow

Use these files:

- `sessions.csv`: one row per anchor session and the skip reason
- `replay_events.csv`: replay markers such as `session_armed` and `first_sweep`
- `daily_loads.csv`: MBP-1 row counts and exact loaded time windows

Suggested workflow:

1. Start with sessions where `skip_reason = armed_side_swept_before_entry_start`.
2. Open the matching `session_date` in `replay_events.csv`.
3. Plot the anchor high/low from the replay row.
4. Mark the first sweep timestamp.
5. Check whether the sweep happened overnight, pre-market, or near RTH open.
6. Compare that to the fixed `09:35 ET` entry start.

The key visual question is: did the overnight sweep create useful context for RTH, or should it really invalidate the setup?

## Structural Weaknesses

1. The first-sweep window and entry window conflict.

V1 watches from the next Globex session start, but it refuses entries before `09:35 ET`. This makes many otherwise relevant sweeps become invalidations.

2. MBP-1 confirmation was never tested.

The strategy never reached the 30-second imbalance gate, so we learned nothing yet about whether the MBP-1 feature improves entries.

3. The sample is small.

This is 43 completed sessions and zero trades. It is useful for debugging the setup definition, not for estimating edge.

4. Remote R2 reads are heavy.

The combined run loaded about `207.6M` filtered MBP-1 rows from about `575.8M` raw rows scanned. For repeated research, local caching of the needed MBP-1 partitions would be much smoother.

## Edge Versus Noise

Likely real finding:

- V1's timing rules are too restrictive. This is structural and repeated across March and April.

Not proven:

- Whether sweep reaction has an edge.
- Whether MBP-1 imbalance helps.
- Whether stop/target assumptions are good.
- Whether bullish versus bearish context matters.

Noise / not enough evidence:

- Any month-to-month difference.
- Any range-regime performance difference.
- Any PnL or win-rate conclusion.

## Careful Next Refinements

Do not optimize thresholds yet. There are no trades to optimize.

Best next research variants:

1. Keep V1 frozen as the baseline.
2. Create a V1.1 research variant that defines the first actionable sweep from `09:35 ET` onward.
3. Separately track whether the same level already swept overnight as context, not as an automatic invalidation.
4. Keep the same MBP-1 imbalance thresholds at first.
5. Keep stop/target unchanged until the strategy produces enough trades to inspect.
6. Run V1.1 on the same March-April MBP-1 window, then on future/new MBP-1 data without changing rules.

The right next question is not "which parameter makes money?" It is "can we define an actionable RTH sweep-reaction event that actually reaches confirmation and entry without leaking future data?"
