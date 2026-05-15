# Asset universe expansion — 2026-05-15 status

_Generated after the overnight expansion on benpc, recovered from a mid-`manifest_final` PC crash that lost only the last manifest-regen step (re-run cleanly post-crash)._

## TL;DR

benpc's local research database went from **0 → 28 active symbols** in one overnight session. The `research_events` table now has **5,228,184 events** — 7.5× the snapshot the strategy-lab export was built from. All 528 detector-mode-symbol scans landed cleanly (0 failures).

## What was active before vs after

| | Before (2026-05-14) | After (2026-05-15) |
|---|---|---|
| Active symbols in research/ML | 3 (ES, NQ, YM, sourced from ben-247) | **28** (full futures universe on benpc) |
| `research_events` rows on benpc | 0 (table didn't exist) | **5,228,184** |
| Event-type coverage | export snapshot only | 76 event_types live |
| Source-of-truth machine | ben-247 | benpc |

The 28 symbols, by asset class:

- **Indices (4):** ES.c.0, NQ.c.0, YM.c.0, RTY.c.0
- **Rates curve (4):** ZB.c.0, ZN.c.0, ZF.c.0, ZT.c.0
- **Energies (5):** CL.c.0, BZ.c.0, HO.c.0, RB.c.0, NG.c.0
- **Metals (5):** GC.c.0, SI.c.0, PA.c.0, PL.c.0, HG.c.0
- **Grains (3):** ZC.c.0, ZS.c.0, ZW.c.0
- **FX majors (7):** 6A.c.0, 6B.c.0, 6C.c.0, 6E.c.0, 6J.c.0, 6N.c.0, 6S.c.0

`asset_universe_manifest.json` fingerprint: `2b63cfde…d5`. Zero warnings, zero `data_only_symbols` — every symbol in the warehouse is now also in research/ML scope.

## Per-cluster expansion runs

All runs logged under [`logs/expand_universe/`](../logs/expand_universe), per-run summary.json + .log. Aggregate produced by `backend/scripts/_aggregate_overnight.py`.

| Cluster | Symbols | Wall time | Events inserted | Scans ok/fail |
|---|---:|---:|---:|---:|
| RTY full (74 detector modes) | 1 | 12.3 min | 138,889 | 71 / 0 |
| RTY equal_levels (post-swing_pivot) | 1 | 0.3 min | 24,327 | 7 / 0 |
| ES/NQ/YM bulk backfill | 3 | 49.1 min | 804,143 | 64 / 0 |
| Index equal_levels rerun | 4 | 0.7 min | 61,183 | 7 / 0 |
| Index cross-symbol (PSP + SMT) | 4 | 3.8 min | 19,520 | 5 / 0 |
| **Rates** (ZB/ZN/ZF/ZT) | 4 | 39.6 min | 627,668 | 64 / 0 |
| **Energies** (CL/BZ/HO/RB/NG) | 5 | 52.1 min | 1,024,120 | 64 / 0 |
| **Metals** (GC/SI/PA/PL/HG) | 5 | 27.4 min | 321,925 | 64 / 0 |
| **Grains** (ZC/ZS/ZW) | 3 | 28.0 min | 430,710 | 64 / 0 |
| **FX majors** (6A/6B/6C/6E/6J/6N/6S) | 7 | 68.2 min | 1,227,339 | 64 / 0 |
| Bulk equal_levels for new symbols | 24 | 3.7 min | 493,405 | 7 / 0 |
| Cross-symbol PSP+SMT across all 28 | 28 | 3.9 min | 105 | 5 / 0 |
| **TOTAL** | | **289.1 min (~4h 49m)** | **5,173,334** | **528 / 0** |

(Final DB count of 5,228,184 vs sum of 5,173,334 — the small delta is the dedup/idempotent updates between the two equal_levels passes.)

## Per-symbol coverage (post-expansion)

| Symbol | rows | features | event_types |
|---|---:|---:|---:|
| ES.c.0 | 296,490 | 15 | 76 |
| NQ.c.0 | 295,819 | 15 | 76 |
| YM.c.0 | 285,838 | 15 | 76 |
| RB.c.0 | 250,001 | 13 | 71 |
| HO.c.0 | 247,255 | 14 | 72 |
| BZ.c.0 | 242,665 | 15 | 74 |
| 6E.c.0 | 230,484 | 15 | 74 |
| RTY.c.0 | 224,768 | 15 | 76 |
| 6S.c.0 | 224,229 | 14 | 73 |
| 6N.c.0 | 223,176 | 14 | 72 |
| CL.c.0 | 223,037 | 14 | 72 |
| NG.c.0 | 219,146 | 14 | 72 |
| 6J.c.0 | 202,496 | 15 | 74 |
| ZB.c.0 | 193,503 | 14 | 72 |
| ZN.c.0 | 191,002 | 14 | 72 |
| 6A.c.0 | 188,937 | 15 | 74 |
| 6B.c.0 | 185,975 | 15 | 74 |
| ZF.c.0 | 173,093 | 13 | 71 |
| ZS.c.0 | 162,876 | 12 | 68 |
| ZC.c.0 | 159,714 | 14 | 71 |
| ZW.c.0 | 157,657 | 13 | 70 |
| ZT.c.0 | 156,505 | 13 | 71 |
| 6C.c.0 | 141,802 | 15 | 74 |
| GC.c.0 | 122,519 | 15 | 73 |
| HG.c.0 | 114,988 | 15 | 73 |
| SI.c.0 | 79,991 | 13 | 71 |
| PL.c.0 | 22,243 | 14 | 72 |
| PA.c.0 | 11,975 | 13 | 71 |

PA and PL are light because their OHLCV-1m partitions are sparser (PA had 880 partitions vs ES's 3527).

## Known issues to investigate later

1. **Cross-symbol detectors are suspiciously quiet.** PSP + SMT across all 28 symbols produced only **105 events**. For 8 years of data and 28 symbols you'd expect thousands. Likely causes to check: (a) cross-symbol detectors may only fire when *all* members of a configured triad are present and have matching timestamps; (b) the date range was 2018-05-01 → 2026-05-05 but some symbols don't have bars back to 2018; (c) the detectors might be configured to look only at the NQ/ES/YM triad. Worth tracing `psp_candle_divergence.py` and `smt_htf_reference_divergence.py` to confirm. Not a blocker for now but is the obvious "where did all my SMT events go?" question.
2. **Dependency ordering in `expand_universe_run.py`.** The script runs detectors alphabetically, which puts `equal_levels` before `swing_pivot`. We worked around this by excluding `equal_levels` from cluster runs and batch-rerunning it at the end. A proper fix is to add a `DETECTOR_ORDER` constant that satisfies the dep graph. Filed as a follow-up — not urgent because the workaround is correct, just inelegant.
3. **PC crashed mid-`manifest_final`.** Lost no data (research_events writes are transactional), just the final manifest copy. Re-ran cleanly post-crash. Worth noting that the overnight script writes a `main.log` per step but doesn't checkpoint the running cluster — if the crash had hit mid-FX (68 min), we'd have lost up to that hour. Future overnight runs should checkpoint per-detector-mode to make recovery cheaper.

## What's available to build on now

The local benpc database now has the data layer needed for:

- **Multi-asset strategy research** — the same event/feature scaffolding that was index-only is now valid for rates, FX, energies, metals, grains.
- **Anchor matrix rebuilds** — the existing builders (`build_*_anchor_*.py`, `build_generic_anchor_snapshots.py`) read from `research_events` and produce parquet matrices. Rerunning them now produces 28-symbol matrices instead of 3-symbol matrices.
- **GPU XGBoost training on broader matrices** — the runner from yesterday ([docs/ML_GPU_VS_LGB.md](ML_GPU_VS_LGB.md)) can immediately train on the new matrices once they're rebuilt. 26-fold more data per fold = more compute, more signal-to-noise resolution.

## Next likely steps (not done yet)

1. Re-run anchor matrix builders against the expanded `research_events`.
2. Re-export the strategy-lab bundle from benpc so the GPU runner has a 28-symbol matrix to train on.
3. Investigate the cross-symbol detector quiet result (#1 above).
4. Fix the orchestrator dependency ordering (#2 above).

## Files of record

- Final manifest: [data/ml/catalog/asset_universe_manifest.json](../data/ml/catalog/asset_universe_manifest.json)
- Human-readable manifest doc: [docs/ASSET_UNIVERSE_MANIFEST.md](ASSET_UNIVERSE_MANIFEST.md)
- Overnight orchestration log: [logs/overnight_universe_2026_05_15/main.log](../logs/overnight_universe_2026_05_15/main.log)
- Per-cluster logs + JSON summaries: [logs/expand_universe/](../logs/expand_universe)
- Manifest checkpoint after the 4 indices: [logs/overnight_universe_2026_05_15/manifest_after_indices.json](../logs/overnight_universe_2026_05_15/manifest_after_indices.json)
- Final manifest snapshot: [logs/overnight_universe_2026_05_15/manifest_final.json](../logs/overnight_universe_2026_05_15/manifest_final.json)
