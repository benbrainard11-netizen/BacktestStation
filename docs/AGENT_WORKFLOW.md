# Agent Workflow

## Roles

### Claude Code

Use Claude Code for building.

Claude should:

- Scaffold files
- Build frontend pages
- Build API endpoints
- Implement importers
- Write tests
- Refactor narrow modules

Claude should not:

- Make broad architecture changes without approval
- Add ML early
- Build Databento engine before importer/dashboard
- Hide mock behavior as real behavior

### Codex

Use Codex as skeptical reviewer and implementation planner.

Codex should:

- Inspect repo state
- Find spaghetti
- Review architecture
- Review data flow
- Review tests
- Check if Claude followed scope
- Suggest exact next patches

Codex should not:

- Randomly rewrite the repo
- Build unrelated features
- Touch large sections without a clear task

### GPT-5.5 Chat

Use GPT-5.5 Chat for:

- Turning ideas into prompts
- Planning build phases
- Reviewing Claude/Codex outputs
- Creating exact task specs
- Stress testing assumptions

## Working Loop

1. Claude builds one narrow task.
2. Codex audits the change.
3. User brings Codex findings to GPT-5.5 Chat.
4. GPT-5.5 creates the next exact Claude prompt.
5. Repeat.

## Review Standard

Every review should answer:

1. What changed?
2. What is real vs mocked?
3. Did it stay in scope?
4. Did it improve the app?
5. Did it create spaghetti?
6. Are schemas/data flow clean?
7. Are there missing tests?
8. What should be fixed next?

## Patch Rule

One task per patch.

Good:

- "Build importer for trades.csv and tests."
- "Create /backtests/[id] dashboard using imported metrics."
- "Add live_status.json reader endpoint."

Bad:

- "Build the whole app."
- "Add ML."
- "Make it more quant."
- "Refactor everything."
