# Session summary — 2026-05-15

_What we accomplished in a single day, and what's queued for tomorrow. Read this first when you come back._

## Headline

**The lab went from "we have models trained" to "we have a portfolio of robust trade signals worth turning into a strategy."**

Four effective independent signals survived multi-year walk-forward, with the strongest (SMT period-close) hitting **100% top-10% precision in every year tested (2020-2025)**, edge +0.59 over base rate, on all three index symbols. The portfolio is genuinely diversified: SMT and opening-gap families have **0.00 Jaccard overlap** and complementary regime exposure (SMT held up perfectly in the year that gap-rejection struggled).

## What got built today

In rough chronological order (~14 commits, all on branch `assets/expanded-universe-v1`):

| Step | Output | Key doc |
|---|---|---|
| Universe expansion overnight (5.2M research_events across 28 symbols) | benpc DB now self-contained | [docs/ASSET_UNIVERSE_STATUS_2026_05_15.md](ASSET_UNIVERSE_STATUS_2026_05_15.md) |
| Branch + workspace consolidation (Codex's worktree merged into main repo) | One canonical workspace | [memory/branch_layout.md](../../../.claude/projects/C--Users-benbr-BacktestStation/memory/branch_layout.md) |
| 112-config GPU XGB scoreboard across 10 anchor matrices | GPU vs CPU LightGBM head-to-head | [docs/ML_FULL_SCOREBOARD_2026_05_15.md](ML_FULL_SCOREBOARD_2026_05_15.md) |
| 247's strict-reactions release ingest + 16-config sweep | FVG strict labels disconfirmed; opening_gap strict confirmed | [docs/ML_FVG_STRICT_RESULT.md](ML_FVG_STRICT_RESULT.md) |
| Per-timeframe FVG investigation | "Split FVG by timeframe" hypothesis disconfirmed | [docs/ML_FVG_PER_TIMEFRAME.md](ML_FVG_PER_TIMEFRAME.md) |
| Label registry (DuckDB-backed unified view) | 198 configs queryable in 1 SQL line | [docs/ML_LABEL_REGISTRY.md](ML_LABEL_REGISTRY.md) |
| **Proxy backtest v1 (single year, 2025)** | First signal that survives a backtest | [docs/ML_BACKTEST_RESISTANCE_REJECTION_V1.md](ML_BACKTEST_RESISTANCE_REJECTION_V1.md) |
| **Multi-year walk-forward v2 (2020-2025)** | 95% mean top-10 precision across 6 years | [docs/ML_BACKTEST_RESISTANCE_REJECTION_V2_WALKFORWARD.md](ML_BACKTEST_RESISTANCE_REJECTION_V2_WALKFORWARD.md) |
| **Per-symbol breakdown v3** | ES is the workhorse on gap-rejection (74/74) | `experiments/backtests/2026-05-15_resistance_rejection_v3_per_symbol/verdict.json` |
| **Label tournament across 10 candidates** | 6 ROBUST, 2 MIXED, 2 FLUKE | [docs/ML_LABEL_TOURNAMENT_2026_05_15.md](ML_LABEL_TOURNAMENT_2026_05_15.md) |
| **Portfolio overlap + SMT correlation check** | 3 SMT "signals" are really 1.5; SMT and OGAP families are 0.00-overlapping | [docs/ML_PORTFOLIO_2026_05_15.md](ML_PORTFOLIO_2026_05_15.md) |
| **Strategy v1 draft spec** | Design surface for the rigorous backtest | [docs/STRATEGY_V1_DRAFT_2026_05_15.md](STRATEGY_V1_DRAFT_2026_05_15.md) |

## What we know now

### Four effective robust signals

| Signal | Top-10% precision (mean across 6yr) | Min year | Edge | Symbols |
|---|---:|---:|---:|---|
| **SMT period_close — `n1_thesis_confirmed_strict` (high)** | 1.000 | 1.000 | +0.59 | NQ, ES, YM all 100% |
| **OGAP `resistance_rejection_3bar` (gap_down)** | 0.95 | 0.79 (2024) | +0.30 | ES dominant |
| **OGAP `support_rejection_3bar` (gap_up)** | 0.94 | 0.83 | +0.28 | per-symbol TBD |
| **OGAP strict `partial_touch_rejected@60m` (all)** | 0.88 | 0.81 | +0.55 | per-symbol TBD |

### Three signal-family characteristics

1. **SMT period_close has the strongest absolute precision** (100% mean) and the largest edge (+0.59) and generalizes across all three indices.
2. **OGAP rejection has more trades** (231+286 = 517 over 6 years vs 69 for SMT) but lower precision and ES-concentrated.
3. **OGAP strict has the most trades** (515 over 6 years) at lower precision (88%) but biggest lift over a low base rate.

### Diversification structure

- **SMT and OGAP families: Jaccard 0.00.** They fire on completely different events. Genuinely independent.
- **OGAP gap_up vs gap_down: Jaccard 0.00 by construction** (mutually exclusive side filter).
- **OGAP strict overlaps both gap-direction signals: Jaccard 0.29 each.** Adds some redundancy.
- **In 2025, the 5 signals collectively produced 75 unique date×symbol trading opportunities** — ~half consensus, ~half single-signal.

### Regime exposure

2024 was the only weak year for `resistance_rejection_3bar` (AUC 0.647, top-10% precision 0.79). **SMT sailed through 2024** (AUC 0.957, top-10% precision 1.000). Whatever regime broke gap-rejection didn't touch SMT. **The two families cover for each other.**

## What's queued for tomorrow

In order of decision-load on you:

1. **Read [STRATEGY_V1_DRAFT_2026_05_15.md](STRATEGY_V1_DRAFT_2026_05_15.md)** — 6 open design questions need your input before we build the rigorous backtest. Each has a defensible default; pinning them down avoids rework.
2. **Decide: build the rigorous OHLCV backtest.** The proxy R-curve framing answered "is the signal real" (yes). The OHLCV backtest answers "does it make dollars after slippage and commissions." That's the 4-6 hour next build.
3. **Coordinate with 247.** The label tournament showed `forming_vp` labels FAIL multi-year top-10% precision robustness despite high AUC — 247 might want to know that the metric matters more than AUC. Also flag the SMT label redundancy (`n1_thesis_confirmed_strict` ≡ `n1_primary_took_period_n_low` on side=high) — maybe 247 wants to dedupe their label library.

## The 6 open questions to answer

(Full context in [STRATEGY_V1_DRAFT_2026_05_15.md](STRATEGY_V1_DRAFT_2026_05_15.md))

1. **YM in or out?** Weak on resistance_rejection.
2. **Entry timing.** Fire at signal time or wait for confirmation?
3. **Stop/target style.** Fixed-R (Option A) or structure (Option B)?
4. **Time-exit P&L treatment.** 0R or actual close P&L?
5. **Consensus filter.** Single-signal or 2+ signal consensus?
6. **"Resistance" definition.** Prior close? Today's high? VWAP?

## State of the workspace

- **Branch:** `assets/expanded-universe-v1` @ `93cc0ee`, pushed to origin.
- **DB:** `data/meta.sqlite` (35.98 GB), 28 symbols, 5.2M research_events, 98.5% with outcomes.
- **Releases on disk:** both 2026-05-14 context_layers and 2026-05-15 strict_reactions ZIPs extracted under `D:\BacktestStationData\`.
- **No background processes running. No pending Codex tasks on benpc.**
- **247-Codex status:** finished FVG strict labels (commit `1909d5f` on `main`, release tag `strategy-lab-core-2026-05-15-strict-reactions`). Next task TBD — pending your decision.
- **Label registry:** rebuild with `python -m scripts.ml.label_registry build` and query with `python -m scripts.ml.label_registry top --by gpu_top_lift`.

## When you wake up

You can either:
- **Skim the docs above** in any order, then pick a direction.
- **Jump straight to [STRATEGY_V1_DRAFT_2026_05_15.md](STRATEGY_V1_DRAFT_2026_05_15.md)** and answer the 6 open questions — that unblocks the next big build.
- **Look at the plots** under `experiments/backtests/2026-05-15_*/` to see the signal shape visually.

Have a good nap. Today was a real win.
