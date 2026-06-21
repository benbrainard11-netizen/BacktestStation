# Gamma-wall 10-year recompute — runbook (prepped 2026-06-14)

Goal: extend the dealer gamma-wall levels from the thin 2025-26 set to ~2017-2026 so the
**lean-positive** gamma-wall reaction result (NIGHT_REPORT §24) gets a real deep design/validation
test. The 2025-26 result: gamma walls react better than generic levels; PUT walls + the frozen
patience filter held OOS (+0.067, PUT +0.161) where generic levels went negative — but validation
n was 41/19 and ES was flat. Deep history takes that to hundreds–thousands of attempts.

## Status: PREPPED, not yet run (blocked on the deep options pull finishing in the other chat)

Done (Terminal-free, safe):
- **Wall definition pinned** (workflow audit wf_84695de8): dealer GEX = `OI*gamma*spot^2*0.01*100`,
  signed (+call/-put), summed over ALL expirations in window per strike; `call_wall=argmax`,
  `put_wall=argmin` of net signed GEX by strike. Vendor gamma from ThetaData eod_greeks. NO B-S.
  Producer = `gex_pull.py` OR `gex_shard.py`+`merge_gex_shards.py` (byte-identical math). The
  `gex_compute`/`gex_deep`/`gex_flip_walls` trio and `prop_model_v0/build_walls_deep.py` are
  DIFFERENT definitions — do NOT use them.
- **Baseline snapshot** of the canonical 2025-26 walls -> `options_signals_v0/out/baseline_2025_26/`
  (the overlap gate's reference; the deep merge overwrites the live files).
- **Rogue quarantined**: `prop_model_v0/data/walls_deep.parquet` (wrong def, gamma*OI per-side max)
  renamed `*.NONCANONICAL_wrongdef.parquet`.
- **Vendor gamma coverage probed** (`coverage_probe.py`, read-only): populated gamma exists every
  year **2017->2026** (~30-42% nonzero/yr). Deep floor = 2017 for ES/YM, 2018-05 for RTY.
- **Consumer made turnkey**: `gamma_wall_legal.py` windows now AUTO-derive from the gex file extent,
  clamped to per-symbol futures floor (`FUT_FLOOR`, RTY>=2018-05). `GW_EXCLUDE=NQ.c.0` to drop NDX.
- **Overlap gate written**: `options_signals_v0/recompute_overlap_check.py`.

## The one gotcha: WINDOW_DAYS=30
The backfill (`robust_pull.py:24`) cached requests at **WINDOW=30 days** (`[exp-30, exp]`).
`gex_shard.py` defaults to 100. Running the shard at !=30 misses the cache on EVERY request and
re-pulls from the flaky Terminal. **Always pass `30` as the 6th arg to gex_shard.** The overlap gate
then confirms the 30-day window reproduces the baseline walls (if it FAILS, the baseline used a
different window — stop and resolve before deep-building).

## Coordination note (2026-06-14): do NOT consume external wall files
Another chat's workflow `complete-options-data-foundation` builds parallel wall files with its OWN
builder (it flagged RUT spot=2937 as "contamination" — FALSE ALARM: that value is in our canonical
baseline too and is a sane ~2.6 SPX/RUT ratio for this elevated-SPX dataset; absolute-level offsets
cancel in the consumer's `basis = future - spot*scale`). The canonical `out/gex_levels_{idx}.parquet`
were verified UNTOUCHED (overlap gate 100% all 4 indices, 2026-06-14). RULE: rebuild deep walls
ourselves with `gex_shard(W=30)`+`merge` from the raw cache into the canonical paths, then gate —
NEVER load the external workflow's wall parquets. Our real dependency = per-root deep GREEKS being
present in the ThetaData cache (D:/data/raw/thetadata/bulk_hist_option_eod_greeks), not their walls.

## Scope of the deep test
- **ES (SPX) 2017+, YM (DJX) 2017+, RTY (RUT) 2018-05+.** NDX/NQ EXCLUDED (no vendor greeks pre
  2026-05; self-compute is a different definition — never seam it against vendor at a year boundary).

## Runbook (when the pull is done)
```
# 0. confirm cache reached the deep start for SPX/RUT/DJX; out/_shards clean of stale shards
# 1. fan out shards per index — NOTE the trailing 30 (WINDOW_DAYS, MUST match the backfill)
py=backend\.venv\Scripts\python.exe
for INDEX in SPX RUT DJX:   # NOT NDX
  $py experiments\options_signals_v0\gex_shard.py $INDEX 2017-01-01 2026-06-14 0 4 30
  $py experiments\options_signals_v0\gex_shard.py $INDEX 2017-01-01 2026-06-14 1 4 30
  $py experiments\options_signals_v0\gex_shard.py $INDEX 2017-01-01 2026-06-14 2 4 30
  $py experiments\options_signals_v0\gex_shard.py $INDEX 2017-01-01 2026-06-14 3 4 30
# (RTY/RUT can start 2017 in the gex file; the consumer floors RTY to 2018-05 automatically)
# 2. merge each index -> out/gex_levels_<idx>.parquet
$py experiments\options_signals_v0\merge_gex_shards.py SPX
$py experiments\options_signals_v0\merge_gex_shards.py RUT
$py experiments\options_signals_v0\merge_gex_shards.py DJX
# 3. VALIDITY GATE — must PASS before trusting deep walls
$py experiments\options_signals_v0\recompute_overlap_check.py
# 4. clear stale checkpoints, re-run the honest engine over the now-deep windows
#    (delete runs\gw_legal_parts first so all years rebuild with the full wall set)
$env:GW_EXCLUDE="NQ.c.0"; $py experiments\mira_gate_harness\gamma_wall_legal.py
# 5. deep holdout: split design (e.g. 2017-2022) / validation (2023-2026) by TIME, never pooled.
#    extend gamma_wall_holdout.py SPLIT or add a year-based split. Report dropped-session counts.
```

## Methodological guards (from the audit)
- TIME-based holdout only (deep years OOS) — never re-count 2025-26 as confirmation of itself.
- Report dropped-session counts (basis-miss + >7d-stale) so deep NO_DATA bands are visible, not
  silently absorbed (known SPX 2021-22 Theta gap).
- Early-year gamma sparsity: if a year's nonzero-gamma % collapses, walls degrade — audit before
  trusting pre-2020.
- DJX x100 scale assumed historically constant (verify spot*100 tracks the Dow per sampled year).

## RUNNING NOW (2026-06-14): SPX backfill 2019-2026, 3 staggered shards

robust_pull SPX 2019-01-01..2026-06-14, NSHARDS=3, WINDOW=30, one Terminal/shard:
  s0 bk2jpdy05 :25510 config_0  |  s1 bjnq8iz4h :25511 config_1  |  s2 b5vrxc39z :25512 config_2
LESSON: 3 CONCURRENT cold starts JAM the Terminals (all hit /list/expirations at once -> upstream
choke -> TS.expirations hangs, no stdout, near-zero CPU). FIX: fresh-restart Terminals, then launch
shards STAGGERED ~40s apart so each clears its expiration-fetch before the next cold-starts. Single
TS.expirations on a fresh Terminal = 0.2s. Shards process newest-first (reverse) -> 2025-26 are cache
HITS (fast, 0 new writes); the 2019-2024 MISSES are the real slow pulls (overnight). Babysitter
restarts a shard's own Terminal on hang; genuinely-bad expirations poison-skip.

### FINISH CHAIN (run when all 3 shards report DONE) — compute is CACHE-ONLY so it can't re-stall:
cd experiments/options_signals_v0
THETA_CACHE_ONLY=1 python -u gex_shard.py SPX 2019-01-01 2026-06-14 0 1 30   # compute walls from full cache
python merge_gex_shards.py SPX                                               # -> gex_levels_spx.parquet (2019-26)
python recompute_overlap_check.py                                           # GATE: must reproduce baseline_2025_26 byte-identical
# if gate FAILS -> restore: copy out/baseline_2025_26/gex_levels_spx.parquet -> out/gex_levels_spx.parquet
# then: re-test wall-beyond on the BAR-ONLY reclaim universe 2019-2026 (ES via SPX walls) for real power
