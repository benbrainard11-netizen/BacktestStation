# ML Database Overview

_Generated `2026-05-17T13:32:05.985901+00:00`._

This is the high-level map of the current BacktestStation research database.

## Identity

| Field | Value |
|---|---|
| Universe id | `futures_expanded_v1` |
| Dataset fingerprint | `bcbd688d4cb9a9330b42962c5a69929ac02f72e0be9cb23cefaea6a067582257` |
| Active symbols | `ES.c.0`, `NQ.c.0`, `YM.c.0` |
| Research events | 710,224 |
| Feature matrices | 16 |
| Anchor/model artifacts | - |

## R2 Last Publish

| Field | Value |
|---|---|
| Timestamp | `2026-05-17T04:16:57.093533+00:00` |
| Profile | `core` |
| Uploaded | 121 |
| Skipped existing | 502 |
| Bytes uploaded | 986.3 MB |
| Errors | 0 |

## Phase 1 Feature Matrices

| Matrix | Rows | Columns | Size | Outcome/label cols |
|---|---|---|---|---|
| `disp` | 38,747 | 91 | 6.2 MB | 45 |
| `eql` | 60,338 | 81 | 4.9 MB | 41 |
| `ft` | 10,373 | 97 | 2.0 MB | 52 |
| `fvg` | 209,339 | 169 | 49.9 MB | 119 |
| `fvp` | 43,150 | 592 | 16.6 MB | 518 |
| `itr` | 36,095 | 172 | 9.6 MB | 66 |
| `macro` | 18,414 | 468 | 9.0 MB | 389 |
| `ob` | 46,331 | 297 | 29.6 MB | 230 |
| `ogap` | 9,438 | 487 | 7.1 MB | 442 |
| `orb` | 34,040 | 99 | 5.1 MB | 53 |
| `psp` | 15,827 | 88 | 2.6 MB | 36 |
| `smt` | 2,891 | 121 | 946.6 KB | 49 |
| `sweep` | 52,946 | 155 | 11.8 MB | 105 |
| `swing` | 76,786 | 73 | 7.6 MB | 33 |
| `tp` | 19,414 | 84 | 1.6 MB | 32 |
| `vp` | 36,095 | 212 | 8.7 MB | 144 |

## Universal Level Artifacts

| Artifact | Rows | Columns | Size |
|---|---|---|---|
| `all_level_reactions` | 455,178 | 461 | 63.5 MB |
| `equal_level_reactions` | 60,338 | 171 | 5.8 MB |
| `fvg_level_reactions` | 209,339 | 119 | 18.0 MB |
| `level_reaction_leaderboard` | 554 | 36 | 81.8 KB |
| `ob_level_reactions` | 46,331 | 143 | 6.1 MB |
| `opening_gap_level_reactions` | 9,438 | 155 | 1.2 MB |
| `sweep_level_reactions` | 52,946 | 152 | 6.2 MB |
| `swing_level_reactions` | 76,786 | 134 | 7.7 MB |

## Read This Correctly

- Phase 1 feature matrices intentionally contain `oc.*` outcome columns for research, but those are not safe model inputs.
- Snapshot matrices should use schema-declared feature columns only.
- Level tables use `level.*` as known-at-creation descriptors and `lr.*` as future reaction labels.
- R2 is the database transport; Git is for code, docs, and small metadata.
