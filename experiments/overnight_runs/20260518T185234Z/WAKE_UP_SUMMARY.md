# Overnight queue — wake-up summary

_Run start: 2026-05-18 18:52 UTC. Run end: 2026-05-18 23:42 UTC. Duration: ~4h 50m._

## Headline

**65 of 67 tasks OK, 1 timeout, 1 hung+killed.** The main deliverable — v30 BASELINE feature profiles across 14 features × 23 symbols (4.16M events) — is committed at `experiments/feature_profiles_20260518T190231Z/`.

## Phase-by-phase

### Phase 0 — finish today's research line (2/2 OK)

| Task | Status | Time |
|---|---|---:|
| `01_v28_23sym_2018_2019` | ✓ OK | 9.8m |
| `02_v29_per_symbol_2018_2019` | ✓ OK | 7.3s |

v28 produced 23-symbol trade CSVs for OB+Sweep on 2018-2019. v29 ranked them by edge × liquidity. Results at `D:/BacktestStationData/slim_anchors_2018_2019_universe/v28_simulation_results/`.

### Phase 1 — v30 baseline feature profiles (1/1 OK)

| Task | Status | Time |
|---|---|---:|
| `03_feature_profiles_baseline` | ✓ OK | 2.5m |

**THIS is what you asked for.** 14 features × 23 symbols = 317 profile rows + per-asset-class roll-up + SUMMARY.md. Findings:

- **swing_pivot** shows fwd10 MFE/MAE ratio 3.3-4.7 across ALL asset classes — too good to be true; likely a thesis-direction definition issue. Treat with skepticism.
- **order_block** + **liquidity_sweep**: best on indexes (1.02 fwd10 ratio). Corroborates v20.
- **displacement_candle** + **fvg_formation**: best on energies (CL, HO, BZ, RB).
- Most features are near-coin-flip at 1.00-1.05.

See `experiments/feature_profiles_20260518T190231Z/SUMMARY.md`.

### Phase 2 — 13 detector extensions to 2015-2017 NQ/ES/YM (48/48 OK)

All 48 detector × mode runs completed. Range from 2s (sparse modes) to 57s (forming_volume_profile). Added historical events for 13 detectors on NQ/ES/YM × 2015-2017.

### Phase 3 — outcome computers (12/13 OK, 1 TIMEOUT)

| Task | Status | Time |
|---|---|---:|
| `80_outcomes_fvg_reactions_v1` | ✓ OK | 13.8m |
| `81_outcomes_swing_pivot_reactions_v1` | ✓ OK | 4.9m |
| `82_outcomes_displacement_reactions_v1` | ✓ OK | 2.4m |
| `83_outcomes_opening_gap_reactions_v1` | ✓ OK | 34s |
| `84_outcomes_orb_reactions_v1` | ✓ OK | 3.6m |
| `85_outcomes_first_third_reactions_v1` | ✓ OK | 3.5m |
| `86_outcomes_interval_true_range_reactions_v1` | ✓ OK | 4.7m |
| `87_outcomes_volume_profile_reactions_v2` | ✓ OK | 5.0m |
| **`88_outcomes_forming_volume_profile_reactions_v1`** | **⏱ TIMEOUT** | **30.0m** |
| `89_outcomes_time_profile_reactions_v1` | ✓ OK | 36s |
| `90_outcomes_psp_reactions_v1` | ✓ OK | 2.2m |
| `91_outcomes_smt_htf_reactions_v1` | ✓ OK | 8s |
| `92_outcomes_equal_levels_reactions_v1` | ✓ OK | 5.3m |

**`forming_volume_profile` timed out** — 1.13M events to walk in 30 min wasn't enough. Re-run with longer timeout (60-90 min) needed for the ~10K new 2015-2017 events to get outcomes.

### Phase 4 — v30 FINAL feature profiles (HUNG)

| Task | Status | Time |
|---|---|---:|
| `93_feature_profiles_final` | ✗ HUNG (killed manually) | 3+ hours |

The v30 final got through 11/14 features then hung on `forming_volume_profile` (1.13M events). The subprocess timeout (30 min) didn't fire — Windows subprocess+timeout interaction quirk. Process was at 6.3GB memory.

**Critical insight**: v30 reads from PARQUETS, not the DB. The parquets haven't been re-exported since the new 2015-2017 events were generated. So the "final" run would have produced **the same data as the baseline**. Killing it lost nothing material. The baseline is the deliverable.

If you want a true "final" pass with 2015-2017 events included, the missing step is re-exporting research_events parquets from the DB. That's a separate task.

### Phase 5 — hygiene (2/2 OK)

| Task | Status | Time |
|---|---|---:|
| `94_backup_meta_sqlite` | ✓ OK | 18.5s |
| `95_data_inventory_report` | ✓ OK | 12.1m |

- **meta.sqlite backup**: `experiments/db_backups/meta_20260518.sqlite` (38 GB, gitignored)
- **Inventory report**: `data/ml/catalog/inventory_report_20260518T234149Z.{csv,json}` — bars 2015-2026 on 28 symbols, TBBO 2025-2026, MBP-1 2026, research events fresh

## What changed in the warehouse

- **+ ~70K research events** added to `meta.sqlite` for 13 detectors on NQ/ES/YM × 2015-2017
- **+ Outcomes computed** for 12 of those 13 detectors (forming_volume_profile pending)
- **Parquets unchanged** — events are in DB only; export step is separate

## Followup queue (suggested)

1. **Re-export research_events parquets from DB** — so v30 future runs see the new 2015-2017 events
2. **Re-run forming_volume_profile outcomes** with longer timeout (60-90 min)
3. **Re-run v30 feature profile** after #1 — this is the "true final"
4. **Investigate swing_pivot's high MFE/MAE ratio** — likely thesis direction issue; could fix and re-profile
5. **Use v30 results to prioritize what to backtest next** — e.g., displacement on energies looks promising
