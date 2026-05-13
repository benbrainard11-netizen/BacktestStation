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

The strongest opening-gap models are not basic fill labels. They are reaction labels around the gap as support/resistance.

- Best fixed split: all-gap `next_60m.resistance_rejection_3bar`, AUC 0.933, top-decile rate 87.6%.
- Best walk-forward: same label, mean AUC 0.947, min yearly AUC 0.926, mean top-decile rate 91.0%.
- Fill labels are useful but less interesting because many gaps fill at high base rates.

## Caveats

- `touched_gap` is not a useful label because the event starts at the gap boundary and touch coverage is 100%.
- The best rejection labels are very strong and should keep getting audited as new context/features are added.
- This is research data, not entry/exit logic.
