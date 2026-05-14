# Order-block geometry context

_Generated `2026-05-14`._

## What It Adds

`obgeom.*` columns describe nearby order-block zones as of each anchor row's real feature cutoff.

This is not entry logic. It is database context for ML:

- nearest OB zone above, below, or containing the anchor price
- whether the OB was `fresh`, `entry_tapped`, `body_touched`, `body_filled`, or `invalidated`
- same-primary-symbol context and any-symbol market context
- bullish, bearish, and any-side OB groupings
- distance, age, body width, range width, and deepest known tap depth
- counts of nearby OBs within 10, 25, 50, and 100 points

## Timing Rule

The builder uses `data/ml/features/ob.parquet` plus the detector lag rules in `snapshot_feature_registry.py`.

Final OB outcomes are not used directly. Tap and invalidation outcomes are first converted to transition timestamps. A state is only visible if the transition timestamp is strictly before `asof.feature_cutoff_ts`.

Untapped and partially tapped states expire after the v1 reaction horizon because the later state is unknown. Filled and invalidated states persist once observed.

## Built Artifacts

| artifact | rows | columns | obgeom columns | audit |
|---|---:|---:|---:|---|
| `data/ml/anchors/sweep_snapshots_xctx_fvggeom_obgeom.parquet` | 52,946 | 2,073 | 661 | 0 issues / 0 warnings |
| `data/ml/anchors/fvg_snapshots_xctx_fvggeom_obgeom.parquet` | 209,339 | 2,090 | 661 | 0 issues / 0 warnings |

Context-only parquet files:

- `data/ml/context/sweep_ob_geometry_context.parquet`
- `data/ml/context/fvg_ob_geometry_context.parquet`

## Current Read

The sweep model comparison says OB geometry is useful but not universally better.

- It improves some harder sweep labels, especially level recovery and one-sided manipulation outcomes.
- It does not materially improve the already-easy `label.ob_confirmation.did_confirm` label because that base rate is already about 97%.
- Walk-forward deltas are small but mostly positive for the harder recovery/manipulation labels.

Use the OB-augmented matrices as richer training data, not proof that OB context alone is a strategy.
