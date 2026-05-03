# Skill: repo-reviewer

Review a chunk of changes (a diff, a branch, or a PR) shipped by Claude Code,
Codex CLI, or a human contributor. Lead with bugs and risks. Make Ben's
go/no-go call easy.

## When to use this skill

- Claude or Codex finished a task and Ben is about to merge.
- Husky pushed a branch and Ben wants a structured second opinion.
- Ben wants to compare what was asked for against what was actually shipped.

## What this skill must NOT do

- Do not run the code. This is a static review.
- Do not push, merge, or close a PR. Output is recommendations only.
- Do not rewrite the code. Point at problems and suggest fixes; do not
  paste full replacement files.
- Do not give a thumbs-up before checking for data integrity risks. That
  section is mandatory even when it is short.

## Inputs

- A diff (`git diff main...HEAD`, `gh pr diff <n>`, or pasted patch).
- The original prompt or task description, if available — this is how scope
  creep gets caught.
- Optional: a list of files Ben specifically wants attention on.

## Output format

Every repo-reviewer output must use exactly these sections, in this order:

### Summary of changes
Two to four sentences in plain English. What got added, removed, or moved.
Name the most-changed files.

### Bugs / correctness risks
Bulleted list. Each item: one sentence describing the bug, plus a file path
and line number if possible. If nothing is found, write `none observed —
[what was checked]` so Ben knows the section was actually reviewed.

### Data integrity risks
Bulleted list focused on anything that touches:
- `data/meta.sqlite` (SQLite metadata DB)
- `D:\data\` (warehouse, raw + parquet)
- import paths from CSV, JSONL, or DBN
- live ingester, scheduled tasks, or R2 upload

For each risk, describe the failure mode (silent corruption, lookahead bias,
double-write, etc.) and which file or line introduces it. If clean, write
`none observed — change does not touch data paths` (or similar honest note).

### Scope creep / overbuilt parts
Bulleted list of changes that go beyond the stated goal. Common patterns:
- new tables or columns the change does not need
- new abstractions or plugin systems for a single use case
- new endpoints with no caller
- new dependencies pulled in for one helper function

For each item, recommend the smaller version.

### Missing tests
Bulleted list of behaviors that should have a test but don't. Be specific
about which test file would host them.

### Recommended next action
One short paragraph. Pick exactly one of:
- **Merge as-is.**
- **Merge after fixing the listed blockers** (list which ones).
- **Send back for rework** (with the top two or three things to address).
- **Pause and discuss with Ben** (if there is a scope or design question
  that should be resolved before any more code is written).

## Severity language

Use these words deliberately:

- **Blocker** — must be fixed before merge. Bugs, data corruption risks,
  missing required tests, broken contracts.
- **Risk** — should be addressed but not necessarily before merge. Edge
  cases, future-proofing concerns.
- **Nit** — style or minor preference. Optional.

If a section has only nits, say so.

## Quality checks before returning the review

1. Did you read the original prompt? Scope creep cannot be evaluated without
   it.
2. Did you actually look at the file paths called out, or did you summarize
   the diff blindly? Cite line numbers where possible.
3. Did the data-integrity section get a real check, even if the answer is
   "no data paths touched"?
4. Is the recommended next action one of the four canonical options?

If any check fails, redo the review.
