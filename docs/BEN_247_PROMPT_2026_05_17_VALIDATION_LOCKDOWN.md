# 247 prompt — validation lockdown + trial registry

_2026-05-17 / benpc → ben-247._

## TL;DR

External review of today's research artifacts confirmed the simulator math is mostly honest (TBBO check: 89% R retention, 100% agreement on stop/target classification, lookahead audit clean, v8a code review clean) but identified real remaining gaps: **selection bias from the registry process, execution realism, continuous-futures roll mechanics, day-level vs trade-level statistics, portfolio concurrency, locked walk-forward**. Verdict: simulator credible as bar replay, NOT credible as deployable-return estimate.

To close out the validation honestly without thrashing, we need a freeze period and one schema-side build from your end.

## Two asks

### Ask 1 — DO NOT modify these until validation completes (~2 weeks)

```
backend/scripts/ml/rigorous_backtest_v7_stops.py    (the v8a simulator)
backend/scripts/ml/rigorous_backtest_v9_ob.py       (V8A_STOP + OB signals)

The 4 deploy-candidate family definitions:
  - OB strict       label.strict.next_60m.ob_broken_through_continuation
  - FVG strict      label.strict.forward_10c.after_tap_failed_1x_against
  - Swing reversed  label.strict.next_60m.pivot_broken_through_continuation
  - Sweep reversed  label.ob_confirmation.did_confirm  (side_aware -> REVERSED)

The slippage model: 2-tick adverse on entry, stop, time-exit
The Sweep hour filter: drop entry hours 22-06 UTC
The cap=10 concurrency rule
```

If any of these get modified mid-validation, the locked-holdout test is invalidated and we restart.

**OK to keep working on:**
- New families/detectors NOT in the deploy candidate (MTF SMT, macro news, scheduled macro taxonomy, etc.)
- Schema / DB structure work — especially Ask 2 below
- R2 tooling (incl. the inventory-overwrite bug fix from this morning's prompt)
- Doc cleanup, label vocabulary, level-reactions schema extensions (incl. the `reaction.fire_ts` ask from earlier today)
- Anything that doesn't touch the locked files above

### Ask 2 — Build the trial registry schema (item #5 in the validation list)

The external reviewer correctly identified that we have no record of all variants tried — only the survivors. That makes any selection-bias / Deflated-Sharpe-style correction impossible. You own DB structure; this is your lane.

**Proposed schema** (extend or replace existing `experiments` table — your call on the integration shape):

```sql
-- Trial groups: a hypothesis + a parameter search space
CREATE TABLE trial_groups (
    id INTEGER PRIMARY KEY,
    hypothesis TEXT NOT NULL,                      -- e.g., "OB strict labels translate to Type B edge on v8a rules"
    parent_strategy_version_id INTEGER REFERENCES strategy_versions(id),
    search_space_json TEXT,                        -- the full grid being searched
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    selection_rule TEXT,                           -- e.g., "max_cum_r_with_6_of_6_yrs_positive"
    selected_trial_id INTEGER REFERENCES trials(id),
    notes TEXT
);

-- One row per individual run; links back to backtest_runs but adds search-context
CREATE TABLE trials (
    id INTEGER PRIMARY KEY,
    trial_group_id INTEGER NOT NULL REFERENCES trial_groups(id),
    backtest_run_id INTEGER REFERENCES backtest_runs(id),   -- nullable if killed before completing
    candidate_config_id TEXT,                      -- hash of the params JSON
    params_json TEXT NOT NULL,                     -- the actual config tried
    parent_trial_id INTEGER REFERENCES trials(id), -- for staged search
    data_snapshot_sha TEXT,                        -- the dataset SHA at trial time
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status TEXT NOT NULL,                          -- queued / running / completed / failed / killed / promoted / ignored
    is_selected BOOLEAN NOT NULL DEFAULT FALSE,
    selection_reason TEXT,                         -- why this trial was picked vs siblings
    summary_metrics_json TEXT                      -- quick-lookup metrics without joining run_metrics
);

CREATE INDEX idx_trials_group ON trials(trial_group_id);
CREATE INDEX idx_trials_status ON trials(status);
CREATE INDEX idx_trials_is_selected ON trials(is_selected);
```

This makes the trial-selection problem visible: for any promoted strategy, "show me all sibling trials in this group and how the selected one beat them."

**Migration**: add via the existing `_run_data_migrations` pattern in `backend/app/db/session.py` (or via Alembic if you want to start that thread — both work).

**Backfill** for existing runs: bulk-insert one `trial_group` per major audit (v8a OGAP, v13 registry sweep, v15 FVG slippage, v16 Sweep verify, v17 Sweep slippage) and one `trials` row per `backtest_run` already in the DB. Mark `is_selected = TRUE` for the ones that ended up in the deploy candidate, the rest as `status = 'completed', is_selected = FALSE`. The point is the historical search context is preserved going forward, even if we can't perfectly reconstruct earlier exploration.

## What benpc is doing in parallel (FYI, no coordination needed)

While you build Ask 2, benpc works on:

1. **Continuous-futures roll integrity check** (~1 day) — for every v16 Sweep trade, resolve the actual front contract at fire_ts and rerun on contract-native bars. Catches whether NQ.c.0 splicing is creating fake edge.
2. **Day/week bootstrap statistics** (~1 day) — replace "6/6 years positive" trade-level stats with daily/weekly R distributions, top-20-day/week contribution, block bootstrap intervals.
3. **Fill-model torture test** (~1 day) — extend v15/v17 with stricter target-fill requirements (must trade THROUGH by 1-2 ticks, traded-volume-at-target gating). Tests whether the limit-fill assumption is load-bearing.
4. **Locked walk-forward holdout** (~2-3 days, AFTER 1-3) — train 2020-22, validate 2023, lock everything, test 2024-25, final untouched holdout 2026. Single non-negotiable validation gate before any deploy decision.

These are all read-only or compute-only on existing data. They don't touch your code paths or change R2.

After this batch, item #6 (single-account portfolio simulator with priority queue + correlated-exposure logic) — also benpc, but conditional on items 1-4 passing.

## Coordination question

**Are you currently working on anything that overlaps?** Specifically:

- Any planned changes to the experiments / promotions / trial tracking schema?
- Any planned changes to v8a simulator, slippage model, or family definitions?
- Anything that would touch the freeze list?

If yes, let me know — we can either rebase the freeze around your in-flight work, or you can pause it for ~2 weeks. Either is fine.

## Why this matters

The external review explicitly said:

> "The bar-level alpha may be real. The capital-efficiency estimate is probably inflated."
> "Your next milestone should not be 'find more edge.' It should be: prove that FVG + Sweep survive locked holdout, harsher fills, one-account portfolio constraints, and trial-selection correction."

We've spent the weekend confirming the simulator is honest. The next step is confirming what we found survives selection-bias and execution-realism stress. Trial registry is the schema-side prerequisite for that.

## Files in scope for Ask 2

- `backend/app/db/models.py` — add `TrialGroup` + `Trial` models
- `backend/app/db/session.py` — migration in `_run_data_migrations`
- `backend/tests/test_trial_registry.py` — new test (smoke + backfill)
- `docs/SCHEMA_SPEC.md` — document the new tables
- Whatever API surface you want to add (`backend/app/routers/`) — optional, can come later

## Reviewer's full verdict on the validation chain

For context, here's what the external review said about what we've already done vs. what remains:

**Already validated (this weekend):**
- Bar-integrity (60 samples): 100% pass — ghost fills ruled out
- TBBO honest-fill (9,142 trades): 89% R retention, 100% agreement on stop/target — cross-bar fill ordering ruled out
- Lookahead audit (69 classes / 13,800 events): clean — future-info leak ruled out
- v8a simulator code review (90 LOC): correct, no bugs
- FVG/OB/Sweep/Swing detector code review + 22 unit tests pass: detection logic clean

**Reviewer's verdict**: "YES, the simulator math is credible as a measure of what the strategies did on those historical 1m bars under v8a rules. NO, it is not yet trustworthy as a measure of deployable PnL or capital return."

**Remaining gaps** (the 7-item list):
1. Continuous-futures roll mechanics  ← benpc
2. Locked walk-forward holdout         ← benpc (after freeze)
3. Day/week-level statistics           ← benpc
4. Fill-model torture test             ← benpc
5. **Trial registry + DSR/PBO**        ← **247 (this prompt)**
6. Single-account portfolio simulator  ← benpc (after 1-4 pass)
7. Small live paper trade              ← later, after 1-6 pass

That's the whole picture. Once items 1-5 land, we can decide together on items 6-7.
