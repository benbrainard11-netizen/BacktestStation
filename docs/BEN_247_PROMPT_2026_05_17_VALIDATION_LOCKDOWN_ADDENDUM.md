# 247 prompt — ADDENDUM to validation-lockdown

_2026-05-17 PM / benpc → ben-247._

## Read first

This is an addendum to `docs/BEN_247_PROMPT_2026_05_17_VALIDATION_LOCKDOWN.md`. The original prompt's freeze list + trial-registry build are still correct, but the validation plan got significantly stronger after two new pieces of information landed:

1. **External methodology review** (GPT-5 Pro Research) returned a strict two-lock walk-forward protocol that's tighter than what the original prompt assumed.
2. **We actually have 2015-2026 data** — 11 years of bars, 8 years of events. The v13-v19 audits only used 2020-2025. **2018-2019 + 2026 YTD are genuinely untouched** holdout windows we never peeked at.

So the original prompt is necessary but not sufficient. This addendum updates the picture.

## What changed

### We have real out-of-sample data

Verified anchor-matrix coverage on the existing release zips:

| Matrix | 2015-2019 events | 2020-2025 events |
|---|---:|---:|
| OB strict | ~20,800 | ~24,700 |
| FVG (xctx_fvggeom_obgeom) | ~90,100 | ~116,500 |
| Sweep (xctx_fvggeom) | ~23,600 | ~28,700 |

The anchor matrices ALREADY cover 2015-2019 — your strict-label build was right-sized for the full historical period, not just 2020-2025. We just never ran the audits against those years because `TEST_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]` in `rigorous_backtest_v1.py`.

**No new compute on your end** to make 2018-2019 available as a holdout. The data is there. We just need to point the simulator at it.

### The walk-forward protocol got stricter

Summary of GPT-5 Pro Research's protocol (full version: `docs/RESEARCH_VALIDATION_PACKET_2026_05_17.md` or ping me):

```
Two-lock protocol:
  Lock 1 (pre-validation): freeze candidate set + selection rules BEFORE validation window
  Lock 2 (pre-test):       freeze final candidate BEFORE test window
  Final:                   run final window exactly ONCE

Windows for our case (revised given 2018-2019 availability):
  Training/exploratory data: 2020-2025  (already explored — research-only)
  Locked holdout 1:          2018-2019  (never peeked at — primary test)
  Locked holdout 2:          2026 YTD   (also untouched — secondary test)
```

Note: this is NOT the classic "train 2020-22 / validate 2023 / test 2024-25" split because all of 2020-2025 is contaminated by exploration. Instead, the existing v13-v19 deploy candidate is **the locked candidate** (frozen exactly as-is, including hour filter, slippage, cap=10) and we test it against data it has never seen.

If the candidate survives both 2018-2019 AND 2026 YTD with comparable per-trade R and 6/6 (for 2018-2019) and pro-rated-positive (for 2026 YTD), it's much closer to validated. If either fails, we learn it's overfit to 2020-2025 regime.

### The trial registry needs to support multi-window locks

The original prompt's `trial_groups` + `trials` schema is good but needs ONE more table to support the locked walk-forward protocol:

```sql
CREATE TABLE trial_lock_records (
    id INTEGER PRIMARY KEY,
    trial_group_id INTEGER NOT NULL REFERENCES trial_groups(id),
    lock_type TEXT NOT NULL,                       -- 'pre_validation' | 'pre_test' | 'final'
    locked_at TIMESTAMP NOT NULL,
    candidate_set_yaml TEXT,                       -- inline YAML or file ref
    candidate_set_hash TEXT NOT NULL,              -- sha256 of candidate config
    dataset_snapshot_id TEXT NOT NULL,             -- which data snapshot
    code_commit_sha TEXT NOT NULL,                 -- git SHA at lock time
    pre_registration_md TEXT,                      -- expected result, falsifiable claims
    window_train TEXT,                             -- e.g., "2020-01-01:2023-01-01"
    window_validation TEXT,
    window_test TEXT,
    window_final TEXT,
    status TEXT NOT NULL,                          -- 'active' | 'superseded' | 'abandoned' | 'completed'
    bug_exceptions_after_lock_json TEXT,           -- array of bug-fix exception records
    superseded_by_lock_id INTEGER REFERENCES trial_lock_records(id),
    notes TEXT
);
CREATE INDEX idx_lock_group ON trial_lock_records(trial_group_id);
CREATE INDEX idx_lock_status ON trial_lock_records(status);
```

This lets us prove a candidate's lock chain matches the protocol it claims to follow. Every trial result should reference its `trial_lock_record_id` so reviewers can verify the lock was in place before the run.

## What to do now

The original prompt said: "propose a plan for Ask 2 (trial registry schema) before writing code."

**Updated ask**: incorporate `trial_lock_records` into the design. Otherwise the registry can't represent locked-walk-forward protocols and we get all the schema work done but still can't prove a clean validation.

Proposed plan structure (you can keep, modify, push back on):

1. `Hypothesis` (1 table) — what's being tested + why
2. `TrialGroup` (1 table) — a hypothesis + a parameter search space
3. `Trial` (1 table) — individual run with results
4. `TrialLockRecord` (1 table — NEW per this addendum) — multi-window lock chain
5. Migration via `_run_data_migrations` pattern
6. Backfill: 1 trial_group per major historical audit (v8a OGAP, v13 registry, v15 FVG slip, v16 Sweep verify, v17 Sweep slip), 1 trial per existing `backtest_run`, no `TrialLockRecord` for historical (everything pre-this-date is exploratory by definition)

## What benpc does next (FYI, no change from original)

While you build the schema, benpc:
1. Roll integrity check (continuous futures back-adjustment risk)
2. Day/week bootstrap statistics
3. Fill-model torture test
4. **NEW**: Run the existing v13-v19 deploy candidate **frozen** against 2018-2019 + 2026 YTD using the GPT-5 protocol. Writes a YAML lockfile first, then runs once. Either survives both windows → much stronger validation. Or fails → reveals overfit.

The locked-walk-forward run on 2018-2019 + 2026 YTD takes ~2-4 hours of compute. Result is the biggest single piece of evidence we'll generate this week.

## Coordination

Whatever you were about to do based on the original prompt — pause for 30 seconds and confirm:

1. You read this addendum
2. The trial registry plan includes `TrialLockRecord` (4 tables total, not 3)
3. You're not mid-modifying anything on the freeze list

Then propose your plan before writing code. The original "no code until plan confirmed" still applies.

## Source pointers

- Full GPT-5 Pro protocol: `docs/RESEARCH_VALIDATION_PACKET_2026_05_17.md` (the writeup section) + the reviewer's response (paste-in-chat from benbr)
- Original lockdown prompt: `docs/BEN_247_PROMPT_2026_05_17_VALIDATION_LOCKDOWN.md`
- The 4 frozen deploy-family definitions: same as original prompt (no change)
- v13-v19 candidate exactly as-is: `docs/TYPE_B_DEPLOY_CANDIDATE_2026_05_17.md` is the canonical writeup
