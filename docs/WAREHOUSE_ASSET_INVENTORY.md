# Asset Universe Manifest

_Generated `2026-05-13T22:42:30+00:00`._

This pins the data identity behind the current ML/research build.

## Identity

| Field | Value |
|---|---|
| Universe id | `warehouse_inventory_v1` |
| Dataset fingerprint | `607f4deb49e01288bd3bc7d7f3bafee94707e262991585721862776d4ba9e67c` |
| Git commit | `6cd92e9dd0677ffa61772aeb12a5f9e8348b67d2` |
| Git dirty when generated | `True` |
| Warehouse root | `D:\data` |
| Active symbols |  |
| Research events | - |
| Feature matrices | - |
| Anchor/model artifacts | - |
| Active 1m bar coverage | None -> None |

## Active Research Universe

| Symbol | Name | Kind | Bars start | Bars end | 1m partitions | 1m rows | Research events |
|---|---|---|---|---|---|---|---|

## Warehouse-Only Symbols

These exist on disk but are not yet part of the current research/ML matrices.

| Symbol | Kind | Bars start | Bars end | 1m partitions | 1m rows |
|---|---|---|---|---|---|
| `6A.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,351 | 902,877 |
| `6B.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,331 | 872,295 |
| `6C.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,260 | 790,787 |
| `6E.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,410 | 1,003,612 |
| `6J.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,374 | 938,460 |
| `6N.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,485 | 2,399,182 |
| `6S.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,483 | 2,258,483 |
| `BZ.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,481 | 1,786,531 |
| `CL.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,484 | 2,645,370 |
| `ES.c.0` | continuous_front_month | 2015-01-01 | 2026-05-04 | 3,527 | 3,948,707 |
| `GC.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,106 | 95,386 |
| `HG.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,122 | 60,017 |
| `HO.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,476 | 1,637,013 |
| `NG.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,484 | 2,363,245 |
| `NQ.c.0` | continuous_front_month | 2015-01-01 | 2026-05-05 | 3,528 | 3,893,190 |
| `PA.c.0` | continuous_front_month | 2018-05-30 | 2026-04-14 | 440 | 4,532 |
| `PL.c.0` | continuous_front_month | 2018-05-11 | 2026-04-23 | 691 | 12,925 |
| `RB.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,476 | 1,540,193 |
| `RTY.c.0` | continuous_front_month | 2018-05-01 | 2026-05-04 | 2,494 | 2,633,007 |
| `SI.c.0` | continuous_front_month | 2018-05-01 | 2026-04-23 | 1,787 | 46,672 |
| `YM.c.0` | continuous_front_month | 2015-01-01 | 2026-05-04 | 3,526 | 3,846,440 |
| `ZB.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,449 | 1,937,240 |
| `ZC.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,007 | 1,280,885 |
| `ZF.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,345 | 1,721,224 |
| `ZN.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,458 | 2,112,335 |
| `ZS.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 1,993 | 1,207,507 |
| `ZT.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 2,297 | 1,442,001 |
| `ZW.c.0` | continuous_front_month | 2018-05-01 | 2026-04-24 | 1,946 | 1,234,895 |

## Research Events By Feature

| Feature | Rows | Symbols | Event types | First event | Last event | Outcome coverage |
|---|---|---|---|---|---|---|

## Feature Matrices

| Short | Feature | Rows | Columns | Symbols |
|---|---|---|---|---|

## Warnings

- Warehouse contains symbols not present in current research/ML universe: 6A.c.0, 6B.c.0, 6C.c.0, 6E.c.0, 6J.c.0, 6N.c.0, 6S.c.0, BZ.c.0, CL.c.0, ES.c.0, GC.c.0, HG.c.0, HO.c.0, NG.c.0, NQ.c.0, PA.c.0, PL.c.0, RB.c.0, RTY.c.0, SI.c.0, YM.c.0, ZB.c.0, ZC.c.0, ZF.c.0, ZN.c.0, ZS.c.0, ZT.c.0, ZW.c.0
- DB datasets registry is empty; manifest used direct warehouse path scan.
- Research event database was not available.

## Rule

If another machine adds assets, regenerate this manifest before comparing model results.
Different active symbols or date coverage means a different dataset, even if the code is identical.
