# Expanded Equal Levels Build

_Generated `2026-05-17T15:59:24.268517+00:00`._

This builds equal-high/equal-low events from expanded swing-pivot parquet without importing the full expanded lake into SQLite.

- Symbols: `ES.c.0, NQ.c.0, YM.c.0, RTY.c.0`
- Scope: `equity index symbols only; absolute point tolerances are not asset-normalized`
- Events with outcomes: `61,185`
- Feature matrix: `C:\Users\benbr\BacktestStation\data\ml\features\eql.parquet`
- Feature rows/columns: `61,185` x `83`
- Research manifest rows after merge: `4,219,261`

## Counts

| Symbol | Mode | Side | Rows |
|---|---|---|---|
| `ES.c.0` | `eq_pivot_3_1h_15pts` | `high` | 3,418 |
| `ES.c.0` | `eq_pivot_3_1h_15pts` | `low` | 3,292 |
| `ES.c.0` | `eq_pivot_3_1h_5pts` | `high` | 2,358 |
| `ES.c.0` | `eq_pivot_3_1h_5pts` | `low` | 2,183 |
| `ES.c.0` | `eq_pivot_3_4h_15pts` | `high` | 858 |
| `ES.c.0` | `eq_pivot_3_4h_15pts` | `low` | 745 |
| `ES.c.0` | `eq_pivot_5_1h_15pts` | `high` | 2,007 |
| `ES.c.0` | `eq_pivot_5_1h_15pts` | `low` | 1,928 |
| `ES.c.0` | `eq_pivot_5_1h_5pts` | `high` | 1,246 |
| `ES.c.0` | `eq_pivot_5_1h_5pts` | `low` | 1,170 |
| `ES.c.0` | `eq_pivot_5_4h_15pts` | `high` | 459 |
| `ES.c.0` | `eq_pivot_5_4h_15pts` | `low` | 416 |
| `ES.c.0` | `eq_pivot_5_daily_30pts` | `high` | 64 |
| `ES.c.0` | `eq_pivot_5_daily_30pts` | `low` | 64 |
| `NQ.c.0` | `eq_pivot_3_1h_15pts` | `high` | 2,112 |
| `NQ.c.0` | `eq_pivot_3_1h_15pts` | `low` | 1,883 |
| `NQ.c.0` | `eq_pivot_3_1h_5pts` | `high` | 1,030 |
| `NQ.c.0` | `eq_pivot_3_1h_5pts` | `low` | 864 |
| `NQ.c.0` | `eq_pivot_3_4h_15pts` | `high` | 390 |
| `NQ.c.0` | `eq_pivot_3_4h_15pts` | `low` | 308 |
| `NQ.c.0` | `eq_pivot_5_1h_15pts` | `high` | 1,122 |
| `NQ.c.0` | `eq_pivot_5_1h_15pts` | `low` | 992 |
| `NQ.c.0` | `eq_pivot_5_1h_5pts` | `high` | 524 |
| `NQ.c.0` | `eq_pivot_5_1h_5pts` | `low` | 431 |
| `NQ.c.0` | `eq_pivot_5_4h_15pts` | `high` | 192 |
| `NQ.c.0` | `eq_pivot_5_4h_15pts` | `low` | 164 |
| `NQ.c.0` | `eq_pivot_5_daily_30pts` | `high` | 23 |
| `NQ.c.0` | `eq_pivot_5_daily_30pts` | `low` | 21 |
| `RTY.c.0` | `eq_pivot_3_1h_15pts` | `high` | 3,847 |
| `RTY.c.0` | `eq_pivot_3_1h_15pts` | `low` | 3,740 |
| `RTY.c.0` | `eq_pivot_3_1h_5pts` | `high` | 2,911 |
| `RTY.c.0` | `eq_pivot_3_1h_5pts` | `low` | 2,742 |
| `RTY.c.0` | `eq_pivot_3_4h_15pts` | `high` | 1,089 |
| `RTY.c.0` | `eq_pivot_3_4h_15pts` | `low` | 937 |
| `RTY.c.0` | `eq_pivot_5_1h_15pts` | `high` | 2,265 |
| `RTY.c.0` | `eq_pivot_5_1h_15pts` | `low` | 2,290 |
| `RTY.c.0` | `eq_pivot_5_1h_5pts` | `high` | 1,600 |
| `RTY.c.0` | `eq_pivot_5_1h_5pts` | `low` | 1,569 |
| `RTY.c.0` | `eq_pivot_5_4h_15pts` | `high` | 599 |
| `RTY.c.0` | `eq_pivot_5_4h_15pts` | `low` | 545 |
| `RTY.c.0` | `eq_pivot_5_daily_30pts` | `high` | 100 |
| `RTY.c.0` | `eq_pivot_5_daily_30pts` | `low` | 93 |
| `YM.c.0` | `eq_pivot_3_1h_15pts` | `high` | 1,444 |
| `YM.c.0` | `eq_pivot_3_1h_15pts` | `low` | 1,315 |
| `YM.c.0` | `eq_pivot_3_1h_5pts` | `high` | 645 |
| `YM.c.0` | `eq_pivot_3_1h_5pts` | `low` | 535 |
| `YM.c.0` | `eq_pivot_3_4h_15pts` | `high` | 247 |
| `YM.c.0` | `eq_pivot_3_4h_15pts` | `low` | 188 |
| `YM.c.0` | `eq_pivot_5_1h_15pts` | `high` | 732 |
| `YM.c.0` | `eq_pivot_5_1h_15pts` | `low` | 663 |
| `YM.c.0` | `eq_pivot_5_1h_5pts` | `high` | 314 |
| `YM.c.0` | `eq_pivot_5_1h_5pts` | `low` | 261 |
| `YM.c.0` | `eq_pivot_5_4h_15pts` | `high` | 122 |
| `YM.c.0` | `eq_pivot_5_4h_15pts` | `low` | 92 |
| `YM.c.0` | `eq_pivot_5_daily_30pts` | `high` | 17 |
| `YM.c.0` | `eq_pivot_5_daily_30pts` | `low` | 19 |

## Caveat

- Current equal-level tolerances are absolute price points inherited from the index workflow.
- This build intentionally defaults to equity-index symbols only.
- FX, energy, grains, and rates need an asset-normalized tolerance model before broad equal-level expansion.
- The manifest is filtered to the latest R2 artifact download plus generated equal-level partitions, so stale local-only parquet does not inflate shared counts.
