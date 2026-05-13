# ITR - Interval True Range - Current Stats

_Generated `2026-05-13T17:57:45+00:00`._

> Generated summary. Edit stable explanation in `README.md`; regenerate this file when artifacts change.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `itr` / `interval_true_range` |
| Total feature rows | 36,095 |
| Date range | 2015-01-02 -> 2026-05-08 |
| Outcome coverage | 35,572 / 36,095 (98.6%) |

### By Event Type

| Event type | Events | Outcomes | Share |
|---|---|---|---|
| `daily_itr` | 8,630 | 8,539 | 23.9% |
| `asia_itr` | 8,630 | 8,539 | 23.9% |
| `london_itr` | 8,615 | 8,521 | 23.9% |
| `ny_itr` | 8,471 | 8,230 | 23.5% |
| `weekly_itr` | 1,749 | 1,743 | 4.8% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `NQ.c.0` | 12,033 | 33.3% |
| `ES.c.0` | 12,033 | 33.3% |
| `YM.c.0` | 12,029 | 33.3% |

### By Side

| Side | Events | Share |
|---|---|---|
| `bullish` | 19,487 | 54.0% |
| `bearish` | 16,376 | 45.4% |
| `doji` | 232 | 0.6% |

## Feature Artifacts

| Artifact | Shape | Notes |
|---|---|---|
| Feature matrix | 36,095 rows x 143 cols | ed=78, oc=38, xd=14 |
| Snapshot xctx matrix | 36,095 rows x 897 cols | xctx=748, labels=35 |
| Audit | 0 issues / 0 warnings | `docs/ML_SNAPSHOT_AUDIT_ITR_XCTX.md` |

## Primary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `compressed_range_0_75x` | 10,689 / 35,572 | 30.0% |
| `expanded_range_1_25x` | 11,695 / 35,572 | 32.9% |
| `touched_interval_mid` | 15,241 / 35,572 | 42.8% |
| `took_interval_high` | 19,543 / 35,572 | 54.9% |
| `took_interval_low` | 15,658 / 35,572 | 44.0% |
| `closed_inside_interval` | 12,638 / 35,572 | 35.5% |
| `closed_above_interval_high` | 13,440 / 35,572 | 37.8% |
| `closed_below_interval_low` | 9,494 / 35,572 | 26.7% |
| `swept_both_sides` | 2,876 / 35,572 | 8.1% |
| `same_direction_close` | 17,355 / 35,572 | 48.8% |
| `opposite_direction_close` | 17,755 / 35,572 | 49.9% |

## Snapshot Leaderboard - Combined Modes

| snapshot | side | label | test n | base | AUC | top bucket | top lift |
|---|---|---|---|---|---|---|---|
| at_fire | bullish | `label.next_interval.compressed_range_0_75x` | 3640 | 32.4% | 0.813 | 80.2% | 47.8% |
| at_fire | all | `label.next_interval.compressed_range_0_75x` | 6801 | 31.2% | 0.803 | 77.1% | 45.9% |
| at_fire | bearish | `label.next_interval.compressed_range_0_75x` | 3137 | 29.9% | 0.785 | 70.7% | 40.8% |
| at_fire | bullish | `label.next_interval.expanded_range_1_25x` | 3640 | 32.3% | 0.783 | 75.8% | 43.5% |
| at_fire | all | `label.next_interval.expanded_range_1_25x` | 6801 | 33.4% | 0.779 | 76.2% | 42.8% |
| at_fire | bearish | `label.next_interval.expanded_range_1_25x` | 3137 | 34.5% | 0.764 | 77.1% | 42.5% |
| at_fire | all | `label.next_interval.touched_interval_mid` | 6801 | 43.0% | 0.759 | 88.4% | 45.4% |
| at_fire | bullish | `label.next_interval.touched_interval_mid` | 3640 | 40.8% | 0.752 | 86.8% | 46.0% |
| at_fire | bearish | `label.next_interval.swept_both_sides` | 3137 | 8.2% | 0.751 | 26.8% | 18.6% |
| at_fire | bearish | `label.next_interval.touched_interval_mid` | 3137 | 45.6% | 0.751 | 89.2% | 43.5% |
| at_fire | all | `label.next_interval.swept_both_sides` | 6801 | 9.1% | 0.726 | 26.9% | 17.8% |
| at_fire | all | `label.next_interval.took_interval_high` | 6801 | 55.2% | 0.707 | 87.4% | 32.1% |

## Per-Mode Best Models

| event type | best label | test n | base | AUC | top bucket | top lift |
|---|---|---|---|---|---|---|
| `weekly_itr` | `label.next_interval.took_interval_high` | 333 | 61.0% | 0.826 | 94.1% | 33.2% |
| `daily_itr` | `label.next_interval.compressed_range_0_75x` | 1638 | 31.0% | 0.813 | 75.0% | 44.0% |
| `asia_itr` | `label.next_interval.compressed_range_0_75x` | 1638 | 32.0% | 0.807 | 78.7% | 46.7% |
| `london_itr` | `label.next_interval.compressed_range_0_75x` | 1626 | 32.3% | 0.804 | 83.4% | 51.1% |
| `ny_itr` | `label.next_interval.compressed_range_0_75x` | 1566 | 29.8% | 0.794 | 69.4% | 39.6% |

## Walk-Forward Check

| snapshot | side | label | folds | base | mean AUC | min AUC | mean top bucket | mean top lift |
|---|---|---|---|---|---|---|---|---|
| at_fire | bullish | `label.next_interval.compressed_range_0_75x` | 6 | 30.8% | 0.790 | 0.751 | 74.9% | 44.1% |
| at_fire | all | `label.next_interval.compressed_range_0_75x` | 6 | 29.8% | 0.786 | 0.755 | 73.2% | 43.4% |
| at_fire | bearish | `label.next_interval.compressed_range_0_75x` | 6 | 28.7% | 0.775 | 0.720 | 68.2% | 39.5% |
| at_fire | all | `label.next_interval.expanded_range_1_25x` | 6 | 32.4% | 0.766 | 0.717 | 73.6% | 41.1% |
| at_fire | bullish | `label.next_interval.expanded_range_1_25x` | 6 | 31.5% | 0.761 | 0.712 | 71.1% | 39.7% |
| at_fire | bearish | `label.next_interval.expanded_range_1_25x` | 6 | 33.3% | 0.760 | 0.719 | 73.5% | 40.2% |
| at_fire | all | `label.next_interval.touched_interval_mid` | 6 | 42.1% | 0.747 | 0.702 | 86.1% | 44.0% |
| at_fire | bullish | `label.next_interval.touched_interval_mid` | 6 | 39.7% | 0.724 | 0.658 | 80.0% | 40.3% |

## Reading

- Strongest and most stable ITR signal so far is next-interval range compression after a wide/expanded anchor interval.
- Range expansion is also learnable, but slightly weaker than compression.
- Midpoint touch and both-side sweep are useful context labels, especially as filters for mean-reversion/liquidity behavior.
- Same-direction and opposite-direction close are weak; do not treat interval candle direction by itself as predictive.
- Per-mode results are strong enough to keep daily, weekly, Asia, London, and NY ITR as separate model features instead of collapsing them.
- These are context labels for the database, not entry/exit strategy rules.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/itr.parquet` |
| Snapshot matrix | `data/ml/anchors/itr_snapshots_xctx.parquet` |
| Audit | `docs/ML_SNAPSHOT_AUDIT_ITR_XCTX.md` |
| Leaderboard | `docs/ML_SNAPSHOT_LEADERBOARD_ITR_XCTX.md` |
| Walk-forward | `docs/ML_SNAPSHOT_WALK_FORWARD_ITR_XCTX.md` |
| Mode summary | `data/ml/anchors/itr_mode_leaderboard_summary.csv` |
