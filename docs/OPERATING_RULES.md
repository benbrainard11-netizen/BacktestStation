# OPERATING_RULES — the five non-negotiables

_Adopted 2026-05-17 per 5.5 Pro Research review + 3 independent reviewers' convergence._

These rules are deliberately short and meant to be unambiguous. If a rule conflicts with what feels convenient, the rule wins. If a rule conflicts with `CLAUDE.md`, `CLAUDE.md` wins (those are deeper engineering invariants).

## Rule 1: Facts live in parquet/R2. Decisions live in `meta.sqlite`.

Market data, bars, events, label outputs, trade tape — all parquet on R2 + local disk. Hashes recorded.

Strategies, runs, trades, trials, hypotheses, snapshots, decisions — all `meta.sqlite` (SQLAlchemy ORM).

**Do not** load a 37GB SQLite into pandas for a research scan. **Do not** store a research decision in a CSV.

## Rule 2: Every run belongs to a trial.

No orphan backtests. No "I just tested something" runs.

A run must reference:
- `trial_id` (and through that, `trial_group_id` and `hypothesis_id`)
- `dataset_snapshot_id` (the exact data state used)
- `code_commit_sha` (the exact code that produced it)
- `seed` (if any randomness)

Historical runs from before this rule landed are grandfathered as "exploratory," not orphans. New runs after 2026-05-17 must comply.

## Rule 3: Every trial belongs to a hypothesis.

No "I just wanted to see what would happen" trials.

A hypothesis is a written, falsifiable claim. Even a one-line claim is sufficient:

> "OB strict + Sweep reversed filtered will remain positive on data not seen during research."

Without a hypothesis, you can't fail. Without failure, every result is a survivor. That's how selection bias eats you.

## Rule 4: Every promotion needs a packet.

A "promotion" moves a candidate's status (per `CANDIDATE_LIFECYCLE.md`). Promotions require evidence.

A promotion packet includes:
- Hypothesis
- Dataset snapshot used for the gating run
- Trial history (all variants, not just winners)
- Backtest result with primary metrics
- Stress test results (slippage, fill torture, etc.)
- Portfolio simulation result (if applicable)
- Known weaknesses
- Decision memo (who decided, why, what's next)

Without a packet, you can't promote. The packet exists in `meta.sqlite` (linked records) OR in docs (memo-style) OR both. The point is: someone can reconstruct the decision later.

## Rule 5: AI can suggest, but cannot promote.

AI agents (Claude, 247-side, 5.5 Pro, future models) can:
- Propose detectors, labels, parameters, refactors
- Run analyses, write code, draft documentation
- Recommend status changes

AI agents **cannot**:
- Declare a candidate validated
- Promote a status without human sign-off
- Modify production data or settings autonomously
- Override the bug-fix exception process

This rule exists because AI can be confidently wrong, and confident wrongness compounds when chained. The human is the integrity gate.

## How to use these rules

When making a decision, ask:
1. Am I storing this in the right layer (rule 1)?
2. Is this run/trial tied to a hypothesis (rules 2, 3)?
3. If I'm promoting something, do I have the packet (rule 4)?
4. Am I letting an AI auto-promote (rule 5)?

If the answer is "no" to any of these, the rule is being violated. Either change what you're doing, or write down WHY the exception is justified (and re-enter the rule next time).

## Anti-patterns these rules prevent

- **Decision drift**: a strategy was promoted, but no one remembers why.
- **Data drift**: results were good, but no one can tell what data they used.
- **Trial amnesia**: 50 variants tested, 1 remembered, selection-bias compounded.
- **AI overreach**: agent moves to micro-live based on "looks good," skipping human gates.
- **Casual orphans**: a run sits in the DB with no link to any hypothesis or trial.

## When the rules are wrong

Rules can be wrong. If a rule blocks legitimate work, document the case, propose a rule update, and ship the rule change BEFORE the work that violated it.

The discipline isn't "obey blindly." It's "make any deviation visible."
