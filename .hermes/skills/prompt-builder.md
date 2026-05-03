# Skill: prompt-builder

Turn a messy idea dump from Ben into a strict, copy-pasteable prompt that
Claude Code or Codex CLI can act on without inventing scope.

## When to use this skill

- Ben describes a feature, fix, or refactor in conversational language.
- The work is bigger than a one-line edit.
- The next step is to hand the work off to a coding agent (Claude Code,
  Codex CLI, or another chat).

## What this skill must NOT do

- Do not write or apply the code itself. This skill only produces a prompt.
- Do not invent scope Ben did not ask for. If a section has nothing to put
  in it, write `none` rather than padding it.
- Do not skip sections. Every output must include all eight sections in the
  order below.
- Do not assume infrastructure changes (new tables, new endpoints, new
  packages) unless Ben said so. Default to "use what exists."

## Inputs

- Ben's raw idea (any length, any quality).
- Optional: file paths or modules Ben mentioned.
- Optional: links to existing tickets, notes, or chat threads.

## Output format

Every prompt-builder output must use exactly these sections, in this order:

### Goal
One or two sentences, plain English. What changes, and why.

### Scope
Bulleted list of files, modules, routes, or surfaces in play. Be concrete.

### Non-goals
Bulleted list of things that are explicitly out of scope. Pull these from
common scope-creep patterns (new tables, new endpoints, new pages, new
abstractions). When in doubt, list more non-goals, not fewer.

### Relevant context to inspect
Bulleted list of file paths the agent should read before starting. Include
the most likely entry points and any test files that already cover the area.

### Implementation requirements
Numbered list of concrete, testable requirements. Each item should be
something a reviewer can check off.

### Acceptance criteria
Bulleted list of observable behaviors that prove the work is done. Prefer
behaviors a human can verify by clicking or running a command.

### Tests / validation
Bulleted list of commands to run, pages to open, or assertions to add.
Include type-check and existing test suites that the change must not break.

### Rollback notes
One short paragraph. How to undo this if it breaks something — file revert,
config flag, database migration to roll back, etc.

## Quality checks before returning the prompt

Before handing the prompt back to Ben, walk through these checks:

1. Does the goal name a single, concrete change? If it's two changes, split
   into two prompts.
2. Does scope name actual files or routes? "The backend" is too vague.
3. Are there at least two non-goals? If not, scope is probably too loose.
4. Could a stranger run the validation steps without asking follow-up
   questions? If not, sharpen them.
5. Is the rollback honest? "Just revert the commit" is fine for pure code
   changes; data and schema changes need a real plan.

If any check fails, fix the prompt before returning it.
