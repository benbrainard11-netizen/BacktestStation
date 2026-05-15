# Expanded Universe Build Report

- Universe id: `futures_expanded_v1`
- Phase: `outcomes`
- Dry run: `False`
- Window: `2018-05-01` to `2026-04-25`
- Active symbols: `NQ.c.0, ES.c.0, YM.c.0, RTY.c.0, 6E.c.0, 6B.c.0, 6S.c.0, 6A.c.0, 6C.c.0, 6N.c.0, CL.c.0, BZ.c.0, RB.c.0, HO.c.0, ZT.c.0, ZF.c.0, ZN.c.0, ZB.c.0, ZC.c.0, ZS.c.0, ZW.c.0, 6J.c.0, NG.c.0`
- Failed tasks: `0`

## Correlated Clusters

- `index_triads`: `NQ.c.0, ES.c.0, YM.c.0, RTY.c.0`
- `fx_europe`: `6E.c.0, 6B.c.0, 6S.c.0`
- `fx_commodity`: `6A.c.0, 6C.c.0, 6N.c.0`
- `oil_products`: `CL.c.0, BZ.c.0, RB.c.0, HO.c.0`
- `rates_curve`: `ZT.c.0, ZF.c.0, ZN.c.0, ZB.c.0`
- `grains`: `ZC.c.0, ZS.c.0, ZW.c.0`

## Warehouse-Only Symbols

- `GC.c.0`: sparse 1m bars in warehouse inventory
- `SI.c.0`: sparse 1m bars in warehouse inventory
- `HG.c.0`: sparse 1m bars in warehouse inventory
- `PL.c.0`: sparse 1m bars in warehouse inventory
- `PA.c.0`: sparse 1m bars in warehouse inventory

## Task Summary

| status | label | elapsed_s | key counts |
|---|---|---:|---|
| ok | `outcomes displacement_reactions_v1` | 2313.7 | n_errors=0; n_candidates=187595; n_updated=187563; n_skipped_already_current=0; n_skipped_no_data=32 |
| ok | `outcomes equal_levels_reactions_v1` | 1.0 | n_errors=0; n_candidates=0; n_updated=0; n_skipped_already_current=0; n_skipped_no_data=0 |
| ok | `outcomes first_third_reactions_v1` | 3475.3 | n_errors=0; n_candidates=52791; n_updated=52603; n_skipped_already_current=0; n_skipped_no_data=188 |
| ok | `outcomes forming_volume_profile_reactions_v1` | 13204.4 | n_errors=0; n_candidates=1132868; n_updated=1097982; n_skipped_no_data=34886 |
| ok | `outcomes fvg_reactions_v1` | 2535.7 | n_errors=0; n_candidates=1243757; n_updated=1240341; n_skipped_already_current=0; n_skipped_no_data=3416 |
| ok | `outcomes interval_true_range_reactions_v1` | 3360.5 | n_errors=0; n_candidates=190192; n_updated=185769; n_skipped_no_data=4423 |
| ok | `outcomes liquidity_sweep_reactions_v1` | 1621.7 | n_errors=0; n_candidates=237569; n_updated=237546; n_skipped_already_current=0; n_skipped_no_data=23 |
| ok | `outcomes opening_gap_reactions_v1` | 275.5 | n_errors=0; n_candidates=36944; n_updated=36944; n_skipped_no_data=0 |
| ok | `outcomes orb_reactions_v1` | 2632.1 | n_errors=0; n_candidates=158941; n_updated=151336; n_skipped_already_current=0; n_skipped_no_data=7605 |
| ok | `outcomes order_block_reactions_v1` | 1135.8 | n_errors=0; n_candidates=198069; n_updated=198063; n_skipped_already_current=0; n_skipped_no_data=6 |
| ok | `outcomes psp_reactions_v1` | 134.8 | n_errors=0; n_candidates=73278; n_updated=72592; n_skipped_already_current=0; n_skipped_no_data=686 |
| ok | `outcomes smt_htf_reactions_v1` | 52.3 | n_errors=0; n_candidates=10889; n_updated=10889; n_skipped_already_current=0; n_skipped_no_data=0 |
| ok | `outcomes swing_pivot_reactions_v1` | 880.2 | n_errors=0; n_candidates=345702; n_updated=345672; n_skipped_already_current=0; n_skipped_no_data=30 |
| ok | `outcomes time_profile_reactions_v1` | 169.6 | n_errors=0; n_candidates=105819; n_updated=105124; n_skipped_already_current=0; n_skipped_no_data=695 |
| ok | `outcomes volume_profile_reactions_v2` | 1344.4 | n_errors=0; n_candidates=183662; n_updated=173798; n_skipped_already_current=0; n_skipped_no_data=9864 |