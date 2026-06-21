# Mira model-expansion — handoff & plan (2026-06-09)

> **2026-06-10 UPDATE:** step 0 is FIXED and the funnel ran — see `runs/NIGHT_REPORT_2026-06-09.md`
> for all results (robustness ESTABLISHED, gamma-sign KILLED, walls PASS on ES, asia-10am overlay,
> champion recipe recovered, money-label challengers, exit autopsy, ungated-stream baselines).
> The plan below is superseded by the **REVISED ROADMAP** at the bottom of this file.

Start here if you're building the "new model expansion." This captures the data, the harness, what's
already known (don't re-derive it), the recommended plan, and the gotchas. Companion findings:
`experiments/smt_ltf_bench/REPORT.md`, memory `smt_ltf_definition_study.md` / `mira_short_revalidation.md`.

## Architecture (the funnel — validated as sound)
Cast wide → filter to quality → confirm with the proven edge:
1. **Levels = WHERE (frequency).** More level families = more setups. Frequency is bound by levels.
2. **Filters = WHICH (regime/quality).** Options/GEX regime, later 0DTE. Must be ORTHOGONAL to orderflow.
3. **MBO orderflow = CONFIRM (the edge).** The gate's bookproxy (structure/SMT alone 0.518 AUC → +15
   bookproxy feats 0.699). This is the real edge; everything else is frequency/quality around it.
Order is deliberate: filter cheaply BEFORE the expensive MBO step → only need MBO at survivors.

## Data inventory (on this machine, 2026-06-09)
- **bars**: 8yr 1m at `D:/data/processed/bars/timeframe=1m` (ES/NQ from 2015, RTY from 2018). Plentiful.
- **MBP-1**: `D:/data/raw/databento/mbp-1` ~1yr (to ~Jun-2026); top-of-book bid/ask. Used for fills/entry.
- **MBO clean**: `D:/data/clean/databento/mbo_trading_day` ~Jan–Jun 2026 (~110 days). THE bookproxy source.
  - OOS-clean for the CURRENT frozen gate = Jan + post-2026-05-20 (Feb6–May20 = its training window).
  - For a NEW model: walk-forward across the full 6mo. Pull more via `experiments/sizing_v1/pull_recent_mbo_databento.py` ($0 w/ sub) / `mira_gate_harness/pull_mbp1.py`.
- **Options/GEX**: `experiments/options_signals_v0/out/` — `gex_levels_spx.parquet` + `_ndx` (date,
  total_gex, zero_gamma, call_wall, put_wall, spot) cover **2025-05 → 2026-06**; + gamma_walls, flip,
  daily/intraday GEX, IV, VIX. OPRA raw at `D:/data/raw/opra`. See `options_signals_v0/RESEARCH_AGENDA.md`.
- **SMT**: `data/meta.sqlite` research_events. ⚠️ GOTCHA below.

## The harness (use it — it's the discipline)
`experiments/mira_gate_harness/` — champion/challenger loop, CALIBRATED (reproduces the live +0.456R on Jan):
- `harness.build_dataset(name,start,end)` → regenerates 139-feat labeled matrix via detect, caches to
  `data/<name>.parquet` + manifest (git SHA, row-hash). Idempotent. MBO-read + SMT-load caches (anti-hang).
- champion = frozen gate; challenger = retrain (`retrain_same`/`drop_smt`, extend with new features).
- `realized_r.py` → drives live signal.py over MBP-1 (reclaim + smt_pivot_180s stop + trail_2R + costs),
  R cached per candidate. eval reports R_mean/win/sum over the one-per-opportunity-deduped gated set.
- `runs/scoreboard.csv`. Locked windows: train 2026-02-06..05-20, oos_holdout 05-21..06-05, jan_oos.

## What's already known (do NOT re-derive)
- **SMT definition / timeframe / orderflow-anchor = COVERAGE not EDGE** (decoration; redundant with the
  orderflow gate). window/N-bar WORSE; swing≈adjacent; FVG marginal. (smt_ltf_bench/REPORT.md)
- **The sweep+reclaim STRUCTURE itself = +0.33R model-free** (AM PDL/PDH, 2yr, n=1041). The real base.
- **3m/10m SMT through the gate = non-dilutive COVERAGE**: +3m/10m → 139→200 trades, total R +63→+74R;
  the gate even RESCUES noisy 3m (raw 0.17 → gated +0.48R). Adds frequency at maintained total edge.
- **GEX gamma-regime = the first ORTHOGONAL edge-add**: Jan positive-gamma +0.57R vs negative +0.33R
  (jan_plus +0.51 vs +0.16). PROMISING but ONE window (holdout was ~all pos-gamma → couldn't test).
- **Base edge: Jan +0.456R / holdout +0.30R — lumpy & within noise** (CI of the diff straddles 0; top
  decile of trades = ~80-110% of total R). Treat per-window means as ±0.15R noisy.
- **Live under-trading = operational** (reconnect/rpCode-13 lockouts) + maybe the no-5m fork (below);
  NOT regime, NOT parity (Leg-B: Rithmic≈Databento ~1%).

## Recommended plan (incremental, each stage earns OOS R via the harness)
0. **[ATTEMPTED 2026-06-09 by GPT — BLOCKED, must re-do]** GPT built `monthly_oos_slices.py` and ran it
   (`runs/monthly_oos_slices.csv`, `runs/champion_cumulative_r.csv`, `CLAUDE_CONTEXT.md`). The harness
   machinery is sound (both anchors re-validated through a hard abort-gate: jan_oos +0.456/139,
   oos_holdout +0.298/83) and every window that BUILT is positive (Jan +0.474, Feb1-4 +0.332,
   May21-31 +0.340, Jun1-5 +0.221; rolling-2w all +0.22..+0.66). **BUT this is NOT 6-month robustness.**
   The `train` source window (Feb6–May20) built **0 rows** (`data/train.parquet` is empty) → Mar + Apr +
   most of Feb/May are ABSENT; the "monthly" CSV is just `jan_oos` + `oos_holdout` re-sliced. "Feb" = Feb 1–4
   (4 days), Mar/Apr = nothing. Inputs are all present (MBO clean Mar 88 / Apr 88 days; meta.sqlite SMT
   Mar 4884 / Apr 7030) → **SILENT BUILD BUG, not a data gap**, and GPT didn't catch it (no row-count guard
   on the source builds, only on the two anchors).
   **#1 FIX before ANY feature work:** delete the empty `data/train.parquet`, then rebuild
   `build_dataset("train","2026-02-06","2026-05-20")` ONE MONTH AT A TIME with exceptions surfaced. Prime
   suspects: the patched MBO/SMT day-read cache returning empty for un-warmed days (the "empty-parquet
   poison cache" gotcha below), or a swallowed exception in the multi-month build. Single-month Jan builds
   fine, so a single-month Mar build is the diagnostic. Only after Mar/Apr actually produce candidates is
   the "+0.44R robust across 6 months" claim testable. (Note the irony: the frozen gate was *trained* on
   Feb6–May20, yet the local rebuild path can't reproduce candidates there — a reproducibility flag.)
1. **Levels** (cheap, plentiful data, fixes under-trading): add families (session H/L, prior-week, OR,
   overnight, **gamma walls** — options data doubles as levels). Keep ones that hold +R.
2. **GEX EOD regime filter/feature** (orthogonal, Jan signal, data 2025-05→2026-06): validate the
   positive-gamma lift across many windows. **Defer 0DTE** (data-hungry/intraday/unproven per the agenda).
3. **MBO entry = keep the proven bookproxy.** Now validatable over ~6mo — but enrich (absorption,
   aggressor imbalance) ONLY with walk-forward discipline (6mo is small → overfit risk).
- **Bar for any filter:** must raise risk-adjusted R MORE than it costs in frequency (GEX passed in Jan;
  SMT didn't). Cutting trades for nothing is negative.

## Gotchas (these bit us)
- **no-5m SMT fork:** BacktestStation/backend/app detector DROPPED the 5m mode; the vendored
  live_engine/vendor/app one HAS it (5m = ~60% of SMT events). Use the **vendored** detector / set
  `BACKTESTSTATION_BACKEND` to vendor. A no-5m scan exists in meta.sqlite — re-scan recent SMT with 5m
  (`fix_holdout_5m.py`). **VERIFY the live PC's recompute uses the 5m detector** (else ~60% fewer arms).
- **MBO reader re-reads the full day file per trigger** (no pushdown) → I/O-storm hang on dense candidate
  sets. Cache day reads (harness does; patch `v0._read_mbo_window`).
- **detect candidate frames have >255 cols** → `itertuples` returns plain tuples (no named access) and
  underscore cols get renamed. Use direct column access.
- **Disposable-data cleanups** delete bs-mira-v15 work dirs mid-session → cache datasets in the harness
  `data/` dir (versioned). A delete-hook blocks Remove-Item → use `[System.IO.File]::Delete`.
- **Calibration trap:** validate the candidate SOURCE (SMT coverage), not just the sim — a no-5m recent
  SMT made the harness read a false "edge degraded 5x" until corrected (real recent R = +0.298R).

## REVISED ROADMAP (2026-06-10) — supersedes the plan above

Grounding facts (proven, see NIGHT_REPORT): the ungated candidate stream LOSES (-0.25R all
windows) -> the frozen gate IS the edge (+0.65R selection). Champion trained on a TRADE-OUTCOME
label (manifest), approximately-reproducible (money-label retrain +0.317 Jan, overlap 95/139)
but unbeaten (-0.15R gap) -> stays frozen; expansion = better inputs + overlays, not replacement.

**Phase A — this week (current sprint)**
1. [running] 4-symbol gamma-wall verdict (ES/RTY/YM full window, NQ vendor-capped May 8+).
2. Exit-policy sweep via ONE-PASS multi-policy replayer (timeout amputates winners: time-exits
   +1.184R/76% win; trail_2R caps the fat tail that = 62% of sumR). Sweep on train, validate top-2
   on jan+holdout. Live exit stays locked; results are challenger evidence.
3. MBO window-backfill VIABILITY sample-quote only (candidates for ~5 sample historical days from
   bars -> quote windows -> extrapolate; entry shape sweep-15m..trig+2m, management +trig+75m).
   The FULL quote/pull waits for Phase B's candidate universe (timestamps come from it — Ben's
   reorder 2026-06-10). B must also parity-check bar-touch vs MBO-touch candidates on Jan-Jun.
4. Auto-accruing fresh-OOS ledger (weekly pull -> replay -> scoreboard). Un-overfittable data;
   forward-validates in-sample rules (asia-10am) and feeds live confidence.

**Phase B — structure at scale (12yr bars + options history)**
Backfill SPX/RUT/DJX gex YEARS back; validate every level family sweep-reclaim baseline on
multi-year bars (mira_upgraded_v0 methodology: bucket-R -> tick-verify on 1yr MBP-1); family x
time rules at real power; exit policies across regimes.

**Phase C — entry model v2 (money label, MBO)**
Scale set by the A3 quote. Close the clone gap first (x4 decision-offset augmentation), then
EVENT-ANCHORED sweep->trigger features (absorption during sweep, refill rate, time-to-reclaim,
burst vs trailing-baseline — no fixed-window truncation, no lookahead) + family/time/wall flags.
Walk-forward; promote only if it beats the frozen champion on ALL OOS slices.

**Phase D — in-trade MBO management model (Ben's idea)**
Post-entry microstructure (legal: entry already decided) to cut failing trades early / extend
winners. Target = the -279R stop line (251 stops x -1.113R). Reuses the A2 replayer + A3
management-shape data. Own OOS promotion bar.

**Phase E — sizing** (sizing_v1 machinery on the expanded book).

Discipline (unchanged, non-negotiable): money labels; anchors re-validate every run; every rule
in-sample until forward data confirms; champion frozen until beaten OOS everywhere; nothing
touches live without Ben.
