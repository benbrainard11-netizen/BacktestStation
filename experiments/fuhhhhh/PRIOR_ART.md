# PRIOR_ART — the graveyard ledger (binding, per SPEC rule 11)

What this repo has already tested on gamma/options → index futures. Re-running a KILLED
construction without a registered, materially-new mechanism is a spec violation.
Compiled 2026-06-12 from: memory/options_gamma_gex.md, memory/prop_model_v0.md,
memory/mira_gate_harness_review.md, memory/mira_parity_audit_bench.md,
memory/level_scalp_v0.md, options_signals_v0/RESEARCH_AGENDA.md,
mira_gate_harness/runs/NIGHT_REPORT_2026-06-09.md, prop_model_v0/report/.

## 1. KILLED / NULL (do not re-run as-is)

| # | Construction | Grain | Result | Verdict |
|---|---|---|---|---|
| 1.1 | Daily GEX regime gate (sign/level → next-day pin-vs-trend) | daily | conditions vol (corr −0.16, redundant w/ VIX) but trendiness corr −0.004; pos/neg trendiness identical | KILLED 2026-06-02 |
| 1.2 | VIX term-structure as gamma-regime proxy | daily | vol yes (trivial), trendiness corr +0.007 | NULL 2026-06-02 |
| 1.3 | Gamma flip level + walls v1/v2 (flip-relative trendiness/fade) | daily | "suggestive" at best, flip found on only 46% of days; folded into dead tile | DEAD (board: "do not revive") |
| 1.4 | 0DTE pinning Step A (close-toward-wall by gamma sign) | EOD | pos 53% vs neg 54% toward-wall = coin-flip AND backwards | NULL 2026-06-02 |
| 1.5 | 0DTE pinning Step B (final-hour pinning, pos-gamma) | intraday-hour | the exact should-pin cell = 48% toward-wall, weaker than the 10–11am control hour | NULL 2026-06-02; explicit note: do NOT slice thinner |
| 1.6 | Gamma-SIGN day filter on Mira sweep-reclaim | day filter | Jan +0.27 lift → Feb −0.19, May −0.45, Jun −1.69; pooled INVERTS (neg-gamma better) | KILLED on 6-mo replication 2026-06-09 |
| 1.7a | GEX features in daily ES LightGBM | daily | era IC +0.133 w/ gx, +0.166 without → regime, not options; attribution −0.033 | NULL |
| 1.7b | Walls as model FEATURES (daily) | daily | attribution −0.033 | NULL |
| 1.7c | Full SPX surface features (IV30, slope, RR, P/C, VRP) | daily | delta −0.032 (hurts) | NULL |
| 1.7d | Wall-RACE as daily target | daily | distance-only IC +0.786 = pure geometry; conditioning value-add −0.004; "+0.21R" trades were 24/29 pre-decided gaps | NULL |
| 1.7e | Wall ROTATION / rejection-fade | daily | fade +0.090 but shuffled-distance placebo +0.235 → wall premium −0.144 (worse than random level) | KILLED as a wall effect |
| 1.8 | Minutes-scale directional entries from public microstructure events at retail latency (5 constructions, level_scalp et al.) | tick/minutes | all within ~1 tick of zero; adverse selection near-total at levels | Priced-to-costs meta-verdict |

**Standing verdict (prop_model_v0):** "SPX options data carries no incremental next-day
index-direction information beyond price/vol/cross-asset. Closed. Don't re-litigate
without a genuinely new construction (intraday options flow when that data lands = the
only technically-open door, low prior)."

**Meta-pattern (5 straight):** hand-crafted concept encodings (GEX, surface, race
conditioning, SMT, cross-crypto) all lost to raw price/vol/cross returns + LightGBM.

## 2. CONTAMINATED (numbers void, tooling survives)

| Construction | What happened | What survives |
|---|---|---|
| Gamma walls as price LEVELS through the frozen Mira gate (ES +0.682R/13, 6-mo) | The gate's 15 bookproxy features spanned [trig−30s,+60s) = post-trigger look-ahead; everything that gate *selected* is invalidated | The level-construction tooling and the **no-lookahead SPX→ES basis mapping** (prior-day 16:00 ET close − spot, tick-snapped; Jan basis mean +32.1, std 14.4 pts) in `mira_gate_harness/gamma_wall_levels_test.py::build_walls` |

## 3. OPEN (never properly tested — this experiment's territory)

| Avenue | Status | Notes |
|---|---|---|
| **Intraday options flow** (0DTE net gamma/vanna/charm deltas, intraday GEX dynamics) | Named "the only technically-open door" — never tested against intraday outcomes | Data exists: 5-min SPX greeks/OHLC 2025-05→2026-06; panels in `options_signals_v0/out/` (`dte0_intraday_spx.parquet`, `intraday_gex_spx.parquet`); no-lookahead feature template `mira_upgraded_v0/flow_features.py` |
| **Objective-first race at INTRADAY grain** (45-min triple barrier vs walls/levels) | Never run; the daily version was geometry-dominated, hence rule 5 | Must beat distance-only baseline + shuffled-distance placebo from day 1 |
| Gamma walls as scalp/limit levels (level_scalp whitelist) | Registered but never tested (backfill wasn't done) | The level_scalp atlas "wall" cells were RESTING-MBO-LIQUIDITY walls, not gamma walls — don't conflate |
| Futures-confirmation × options-level interaction (OFI/sweep AT walls vs away) | gamma×OFI interaction probed once in market_state (pattern only) | Phase 2d |
| Wall-touch probe (prop_model #8) | Deprioritized, never run | — |

## 4. Validated tooling to reuse (don't rebuild)

- Triple-barrier template: `prop_model_v0/features_index.py::_finish` (stop-wins-ties, vol-scaled)
- Purged WF + shuffled-target control: `btc_model_v0/model_wf.py` (+ `prop_model_v0/model_index.py` as the end-to-end clone target)
- Tick re-fill verifier: `mira_upgraded_v0/fill_realism.py`
- Maker-fill / adverse-selection harness: `level_scalp_v0/mode_a_sim.py`
- OFI primitive: `market_state/intraday/zone_events.py::cks_ofi_inc`
- Level engine + valid_from discipline: `market_state/intraday/levels.py`, `events_v2.py`
- Prop mechanics: `prop_model_v0/funnel_specs.py` + `eval_ev.py`; account replay `sizing_v1/`
- Options data access: `options_signals_v0/theta_store.py` (cache), `gex_pull.py`, `intraday_gex.py` (audit rule-2 first), `build_walls_deep.py` artifact `walls_deep.parquet` (1,038 days 2019→2026)
- Data readers: `backend/app/data/reader.py` (`read_bars`, `read_mbp1_trading_day`, `read_mbo_trading_day`); sessions: `backend/app/research/sessions.py`
