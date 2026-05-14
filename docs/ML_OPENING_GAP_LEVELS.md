# Opening Gap Levels

_Generated `2026-05-13`._

## Definition

Opening gaps are key levels created when a new session opens away from the prior session close.

- `ndog`: new day opening gap. Current Globex day open versus previous Globex day close.
- `nwog`: new week opening gap. Current Globex week open versus previous Globex week close.

Each event stores the full gap zone:

- `gap_high`
- `gap_low`
- `gap_mid`
- `gap_size_pts`
- `gap_direction`
- `previous_close_price`
- `current_open_price`

## Real-Time Rule

The event is knowable at the gap open only. The detector does not use future fill information.

Gap-memory context also respects this rule:

- prior gaps must have `gap_open_ts < asof.feature_cutoff_ts`
- fill/touch state is computed only from transition timestamps before the cutoff
- current or future gap fill state is never used as an input

## Current Coverage

| item | value |
|---|---:|
| total events | 9,438 |
| NDOG events | 7,815 |
| NWOG events | 1,623 |
| symbols | ES.c.0, NQ.c.0, YM.c.0 |
| span | 2015 to 2026 |
| outcome coverage | 100.0% |

## Fill Behavior

| group | 1h fill | 4h fill | 1d fill | 5d fill | 20d fill |
|---|---:|---:|---:|---:|---:|
| all | 66.5% | 76.9% | 90.8% | 95.2% | 97.4% |
| NDOG | 71.1% | 81.4% | 93.2% | 96.4% | 98.0% |
| NWOG | 44.4% | 55.1% | 78.9% | 89.6% | 94.5% |

Interpretation: daily gaps fill quickly much more often than weekly gaps. Weekly gaps are slower and may carry more useful context as levels.

## Main Datasets

| file | purpose |
|---|---|
| `data/ml/features/ogap.parquet` | raw per-event opening-gap feature matrix |
| `data/ml/anchors/opening_gap_snapshots_xctx_gapctx.parquet` | opening-gap anchor matrix with cross-concept and prior-gap context |
| `data/ml/anchors/forming_vp_snapshots_xctx_gapctx.parquet` | forming-VP matrix with opening-gap memory added |
| `data/ml/context/opening_gap_opening_gap_context.parquet` | prior-gap context rows for opening-gap anchors |
| `data/ml/context/forming_vp_opening_gap_context.parquet` | prior-gap context rows for forming-VP anchors |

## Best Current Signals

Outcome `v2` adds universal gap-zone reaction labels. The strongest stable result is still fill/unfilled prediction, especially within 4 hours.

- Best fixed split: gap-up `next_240m.unfilled_at_window_end`, AUC 0.850, top-decile unfilled rate 90.4%.
- Best walk-forward: all-gap `next_240m.fully_filled`, mean AUC 0.834, min yearly AUC 0.805, mean top-decile fill rate 97.1%.
- Support/resistance rejection labels are useful but weaker: 60m high/low rejected-inside labels screen around AUC 0.64-0.68.
- Gap size is the dominant feature. Larger gaps are much easier for the model to separate from quick-fill gaps.

## Caveats

- `touched_gap` is not a useful label because the event starts at the gap boundary and touch coverage is 100%.
- Fill/unfilled labels have high base rates, so judge them by walk-forward AUC and top-decile lift, not accuracy alone.
- Rejection labels have lower base rates and need more context before they should be treated as strong standalone targets.
- This is research data, not entry/exit logic.
