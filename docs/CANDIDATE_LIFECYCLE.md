# CANDIDATE_LIFECYCLE — strategy candidate state machine

_Adopted 2026-05-17. Companion to `OPERATING_RULES.md`._

A "candidate" is a strategy configuration that's being evaluated for deploy. Every candidate has exactly one status at a time, drawn from this taxonomy.

## States

### `draft`

**Just created. No validation yet.**

What's true:
- Has a name + config (parameters, families, trade rule)
- May or may not have a hypothesis
- No backtest results required yet
- Not safe to use

Allowed transitions: → `research_only`, → `killed`, → `archived`

### `research_only`

**Used for exploration. Findings are hypotheses, not validated.**

What's true:
- Has a hypothesis (rule 3)
- Backtests exist but on exploratory data only
- Results inform research, do not justify deploy
- Not safe to deploy

This is where most strategies live for most of their lives.

Allowed transitions: → `needs_more_validation`, → `paper_ready` (rare; only with locked walk-forward pass), → `killed`, → `archived`

### `needs_more_validation`

**Promising research finding; specific gates remain.**

What's true:
- Survived initial exploratory testing
- Specific known gaps documented (e.g., "no roll integrity check," "no portfolio sim")
- Not yet ready to paper trade
- Not safe to deploy

Allowed transitions: → `paper_ready` (when gates pass), → `research_only` (demotion if gates reveal problems), → `killed`, → `archived`

### `paper_ready`

**Cleared for paper-trade execution validation.**

What's true:
- Passed locked walk-forward on out-of-sample data
- Has a frozen config (no edits during paper trade)
- Promotion packet exists per rule 4
- Paper trade is for execution realism (latency, fills, missed signals), NOT for deciding whether the strategy "works"
- Not yet safe for real money

Allowed transitions: → `micro_live` (after paper-trade results land), → `research_only` (demotion if paper-trade reveals problems), → `killed`, → `archived`

### `micro_live`

**Approved for tiny-size real-money execution test.**

What's true:
- Paper trade demonstrated execution math matches backtest math within tolerance
- Hard daily loss cap, hard weekly cap, hard size cap
- 1 contract maximum, micros preferred
- Not a "profit-seeking deployment" — it's the next-step validation
- Every fill/miss/conflict logged

Allowed transitions: → `scale_candidate` (after sustained period of clean micro-live), → `paper_ready` (demotion), → `killed`, → `archived`

### `scale_candidate`

**Validated through micro-live; ready to consider scaling capital.**

What's true:
- Sustained micro-live period (4+ weeks minimum) showed expected R-rate
- Live-vs-backtest drift report is within tolerance
- Risk controls verified at higher size
- THIS IS WHERE REAL CAPITAL DECISIONS HAPPEN

Allowed transitions: → `micro_live` (demotion if scale reveals problems), → `killed`, → `archived`. **No further "promotion" — scaling capital is a sizing decision, not a status promotion.**

### `killed`

**Failed at some gate. Won't be revisited under this configuration.**

What's true:
- Has a documented failure mode (which gate failed, why)
- Underlying ideas may still be useful for research_only candidates
- Do not silently revive a killed candidate; create a new candidate with new config and new hypothesis

### `archived`

**Out of active workspace. Reference-only.**

What's true:
- Not part of operational system
- Kept for historical understanding
- Can be unarchived if a question genuinely requires it

## Required gates per transition

The exact gates are pre-registered per candidate (some candidates need extra family-specific checks). Standard gates by transition:

### `research_only` → `paper_ready`

Required:
- ✓ Locked walk-forward pass on out-of-sample data
- ✓ Roll integrity check (continuous vs contract-native, OR roll-anomaly approximation if per-contract unavailable)
- ✓ Day/week block bootstrap (top-N-days contribution within thresholds)
- ✓ Fill-model torture (target-through, slippage variants)
- ✓ Single-account portfolio simulator (if multi-family)
- ✓ Promotion packet (rule 4)

### `paper_ready` → `micro_live`

Required:
- ✓ Paper-trade period completed (minimum 1 month or N signals, whichever is greater)
- ✓ Live-vs-backtest drift report shows execution realism
- ✓ Missed-signal rate documented and within tolerance
- ✓ Risk caps explicitly written
- ✓ Promotion packet updated

### `micro_live` → `scale_candidate`

Required:
- ✓ Sustained micro-live period (4+ weeks)
- ✓ Drift report: realized R-rate vs backtest within ±50%
- ✓ No operational red flags (margin issues, unexpected fills, system crashes)
- ✓ Promotion packet updated with live evidence

## Recording

Every status change is recorded in `meta.sqlite`. The recommended location is on a `strategy_versions` row (which already has a `status` column from the original schema).

For audit history, every transition writes a row to a separate log table (TBD — could be `strategy_status_transitions(strategy_version_id, from_status, to_status, decided_at, decided_by, evidence_link, notes)`). Until that table lands, write a memo doc:
`docs/candidate_promotions/<candidate>_<date>.md`.

## Current candidates (as of 2026-05-17)

| Candidate | Status | Notes |
|---|---|---|
| 4-family Type B (FVG strict + OB strict + Swing reversed + Sweep reversed filtered) | `killed` | Failed v20 locked walk-forward; Swing was a regime artifact, FVG regime-dependent |
| 2-family core (OB strict + Sweep reversed filtered) | `needs_more_validation` | Survived v20; pending roll-anomaly + bootstrap + fill torture + portfolio sim |
| Swing reversed (any direction) | `killed` | Direction flip falsifier hit both holdouts |
| FVG strict (standalone) | `research_only` | Regime-conditional; not deploy-core; could become candidate with regime classifier |
| v8a OGAP rejection | `research_only` | Original Type A finding (+79R); superseded by Type B work but retains research value |

## What this fixes

Before this doc:
- Candidates lived in tribal knowledge ("I think OB is good?")
- Promotions happened by enthusiasm, not gates
- "Killed" wasn't a real status — failed experiments got casually re-explored
- No clear bar for what "paper-ready" actually meant

After this doc:
- Every candidate has exactly one status
- Status changes require specific gates
- Promotion gates are pre-defined, not improvised
- Killed candidates stay killed (unless a NEW candidate emerges from the same underlying idea)
