# Asset Universe Manifest

_Generated `2026-05-15T19:14:26+00:00`._

This pins the data identity behind the current ML/research build.

## Identity

| Field | Value |
|---|---|
| Universe id | `futures_core_v1` |
| Dataset fingerprint | `1e4a60b6829bcc09178de52f64f60894b6b55b2b66d878cd3c36ee01fe06a622` |
| Git commit | `ae79ae87ec7cf0308da3bd8a873d0d64e831ef82` |
| Git dirty when generated | `True` |
| Warehouse root | `D:\data` |
| Active symbols | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| Research events | 710,224 |
| Feature matrices | 16 |
| Anchor/model artifacts | 276 |
| Active 1m bar coverage | 2015-01-01 -> 2026-05-14 |

## Active Research Universe

| Symbol | Name | Kind | Bars start | Bars end | 1m partitions | 1m rows | Research events |
|---|---|---|---|---|---|---|---|
| `ES.c.0` | E-mini S&P 500 | continuous_front_month | 2015-01-01 | 2026-05-14 | 3,467 | 3,879,579 | 237,320 |
| `NQ.c.0` | E-mini Nasdaq-100 | continuous_front_month | 2015-01-01 | 2026-05-14 | 3,467 | 3,822,693 | 240,593 |
| `YM.c.0` | E-mini Dow | continuous_front_month | 2015-01-01 | 2026-05-14 | 3,466 | 3,777,993 | 232,311 |

## Warehouse-Only Symbols

These exist on disk but are not yet part of the current research/ML matrices.

| Symbol | Kind | Bars start | Bars end | 1m partitions | 1m rows |
|---|---|---|---|---|---|
| `ESM6` | specific_contract | 2026-04-27 | 2026-05-14 | 13 | 16,450 |
| `NQM6` | specific_contract | 2026-04-27 | 2026-05-14 | 13 | 16,451 |
| `RTY.c.0` | continuous_front_month | 2026-03-01 | 2026-05-14 | 44 | 48,490 |
| `RTYM6` | specific_contract | 2026-04-27 | 2026-05-14 | 13 | 16,235 |
| `YMM6` | specific_contract | 2026-04-27 | 2026-05-14 | 13 | 16,226 |

## Research Events By Feature

| Feature | Rows | Symbols | Event types | First event | Last event | Outcome coverage |
|---|---|---|---|---|---|---|
| `fvg_formation` | 209,339 | 3 | 4 | 2015-01-01 23:30:00.000000 | 2026-05-08 20:00:00.000000 | 99.9% |
| `swing_pivot` | 76,786 | 3 | 5 | 2015-01-02 07:00:00.000000 | 2026-05-07 20:00:00.000000 | 100.0% |
| `equal_levels` | 60,338 | 3 | 7 | 2015-01-02 14:00:00.000000 | 2026-05-07 15:00:00.000000 | 100.0% |
| `liquidity_sweep` | 52,946 | 3 | 14 | 2015-01-04 23:00:00.000000 | 2026-05-08 14:00:00.000000 | 100.0% |
| `order_block` | 46,331 | 3 | 14 | 2015-01-05 01:00:00.000000 | 2026-05-08 15:00:00.000000 | 100.0% |
| `forming_volume_profile` | 43,150 | 3 | 1 | 2015-01-02 03:00:00.000000 | 2026-05-08 18:00:00.000000 | 98.5% |
| `displacement_candle` | 38,747 | 3 | 3 | 2015-01-02 19:00:00.000000 | 2026-05-07 16:00:00.000000 | 100.0% |
| `interval_true_range` | 36,095 | 3 | 5 | 2015-01-02 06:59:00.000000 | 2026-05-08 20:59:00.000000 | 98.6% |
| `volume_profile` | 36,095 | 3 | 5 | 2014-12-28 23:00:00.000000 | 2026-05-08 13:30:00.000000 | 95.2% |
| `opening_range_breakout` | 34,040 | 3 | 4 | 2015-01-02 00:00:00.000000 | 2026-05-08 14:00:00.000000 | 99.9% |
| `time_profile` | 19,414 | 3 | 4 | 2014-12-28 23:00:00.000000 | 2026-05-07 22:00:00.000000 | 99.8% |
| `macro_event_anchor` | 18,414 | 3 | 113 | 2015-01-02 14:59:00.000000 | 2026-05-12 12:29:00.000000 | 99.5% |
| `psp_candle_divergence` | 15,827 | 3 | 3 | 2015-01-02 00:00:00.000000 | 2026-05-07 20:00:00.000000 | 99.2% |
| `first_third_range` | 10,373 | 3 | 2 | 2015-01-02 06:38:00.000000 | 2026-05-08 05:39:00.000000 | 99.9% |
| `opening_gap_levels` | 9,438 | 3 | 2 | 2015-01-04 23:00:00.000000 | 2026-05-07 22:00:00.000000 | 100.0% |
| `smt_htf_reference_divergence` | 2,891 | 3 | 2 | 2015-01-08 16:00:00.000000 | 2026-05-05 00:00:00.000000 | 100.0% |

## Feature Matrices

| Short | Feature | Rows | Columns | Symbols |
|---|---|---|---|---|
| `disp` | `displacement_candle` | 38,747 | 91 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `eql` | `equal_levels` | 60,338 | 81 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `ft` | `first_third_range` | 10,373 | 97 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `fvg` | `fvg_formation` | 209,339 | 169 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `fvp` | `forming_volume_profile` | 43,150 | 592 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `itr` | `interval_true_range` | 36,095 | 172 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `macro` | `macro_event_anchor` | 18,414 | 468 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `ob` | `order_block` | 46,331 | 297 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `ogap` | `opening_gap_levels` | 9,438 | 487 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `orb` | `opening_range_breakout` | 34,040 | 99 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `psp` | `psp_candle_divergence` | 15,827 | 88 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `smt` | `smt_htf_reference_divergence` | 2,891 | 121 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `sweep` | `liquidity_sweep` | 52,946 | 155 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `swing` | `swing_pivot` | 76,786 | 73 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `tp` | `time_profile` | 19,414 | 84 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| `vp` | `volume_profile` | 36,095 | 212 | `ES.c.0`, `NQ.c.0`, `YM.c.0` |

## Warnings

- Warehouse contains symbols not present in current research/ML universe: ESM6, NQM6, RTY.c.0, RTYM6, YMM6
- DB datasets registry is empty; manifest used direct warehouse path scan.

## Rule

If another machine adds assets, regenerate this manifest before comparing model results.
Different active symbols or date coverage means a different dataset, even if the code is identical.
