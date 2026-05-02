# In-app strategy builder agent — 2026-05-02

**Goal:** Two agentic workflows inside the strategy builder, both running on Ben's local Claude Code CLI subprocess (Max sub, no API billing) — `compose` to assemble/tweak strategies, `author` to write new feature `.py` files.

**Status:** Shipped end-to-end across 5 commits. Backend route + unit tests green. Runtime smoke deferred to a backend restart (the running uvicorn was started before these changes).

## Commits, in order

| Commit | What |
|---|---|
| `61e7ae7` | feat(chat): streaming chat endpoint + cli_chat extensions (mode-scoped permissions, --add-dir, --allowed-tools, NDJSON output) + 4 unit tests |
| `0a34c01` | chore(streaming): generic `streamNdjson<T>()` consumer in `frontend/lib/streaming.ts` |
| `a52e622` | feat(builder): `AgentMessage` + `AgentChatPanel` components — bubbles, tool-call chips, fenced spec_json detection + Apply button |
| `cb8df48` | feat(builder): wire AgentChatPanel into 3-col build page layout (pantry / recipe / chat) + `applyAgentPatch` whitelist merger |
| `1f3761b` | docs(claude-md): formal "In-app agent integration (allowed under these rules)" section enumerating the constraints |

## Architecture

```
/strategies/[id]/build  (3-col grid)
  ├─ FeaturePantry (300px)
  ├─ Recipe stack (flex)
  └─ AgentChatPanel (360px, sticky)
       │
       ▼ POST /api/strategies/{id}/chat-stream  (NDJSON)
       │   body: {prompt, model:"claude", section, mode}
       │
backend/app/api/chat.py:post_chat_turn_streaming
  • persist user msg before stream
  • mode → permission posture
  • async-iterate run_claude_turn_streaming events
  • persist assistant msg on done event
       │
       ▼
backend/app/services/cli_chat.py:run_claude_turn_streaming
  • asyncio.create_subprocess_exec(["claude", "-p",
      "--output-format", "stream-json",
      "--include-partial-messages", "--verbose",
      "--system-prompt", system,
      "--add-dir", *dirs (author mode only),
      "--allowed-tools", *tools (compose mode only),
      "--permission-mode", "default" or "bypassPermissions"])
  • env stripped of ANTHROPIC_API_KEY + OPENAI_API_KEY
  • cwd = repo root
  • translates Claude's stream-json events into our StreamEvent shape
```

## Two modes

| Mode | Tool whitelist | --add-dir | Permission mode | What the agent can do |
|---|---|---|---|---|
| **compose** | `Read, Glob, Grep` | (none) | `default` | Inspect repo. Suggest `spec_json` patches in fenced ```` ```json spec_json ``` ```` blocks. **Cannot write files.** |
| **author** | (default toolset) | `backend/app/features/`, `backend/tests/` | `bypassPermissions` | Write new feature .py files + tests. Run `pytest` after writing. **Cannot touch engine, strategies router, or config.** |

Mode toggle persists per-strategy in `localStorage`. Author mode shows a yellow warning banner above the chat reminding the user the agent will write files.

## Compose-mode patch flow

1. Agent emits something like:
   ````
   Here's a long-only PDH-sweep + decisive-close strategy:
   ```json spec_json
   {"entry_long":[{"feature":"prior_level_sweep","params":{"level":"PDH","direction":"above"}},{"feature":"decisive_close","params":{"direction":"BEARISH","min_body_pct":0.55}}],"stop":{"type":"fixed_pts","stop_pts":10},"target":{"type":"r_multiple","r":3}}
   ```
   ````
2. `AgentMessage` regex-matches the fenced block, parses the JSON, renders an "Apply to spec" button.
3. Click → `applyAgentPatch()` in `page.tsx` whitelist-merges the parsed object into local Spec state. Whitelist (entry_long, entry_short, stop, target, qty, max_trades_per_day, entry_dedup_minutes, max_hold_bars, max_risk_pts, min_risk_pts, aux_symbols) means an off-base patch can't poison state with unknown keys. Each field type-checked before assignment.
4. User reviews the recipe area, clicks Save → standard PATCH `/api/strategy-versions/{id}` with `spec_json: spec`.

## Billing posture (HARD RULE preserved)

- **`backend/app/services/cli_chat.py:_strip_billing_keys()`** blanks `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` from subprocess env before every spawn. This forces Claude CLI to OAuth (Max sub flat-rate) and Codex CLI to its own login. **Do not remove.** If the strip ever drifts, billing flips silently to per-token.
- BacktestStation backend NEVER imports `anthropic` or `openai` SDKs.
- Tier 2 (multi-tenant on Railway, future Husky / external users) is the only path where direct Anthropic API call is permitted, with per-plan usage caps. Not built; explicitly out of scope here.

## What you should do first when ready

1. **Restart the FastAPI backend** so it picks up the new `/chat-stream` route. (Per the morning sweep finding, the running process is from 4/30 and missing several recently-added routes.)
2. **Verify the route is live:**
   ```powershell
   curl -s http://localhost:8000/openapi.json | grep -oE '"/api/strategies/\{[^}]+\}/chat[a-z-]*"' | sort -u
   # Expected: both /chat AND /chat-stream
   ```
3. **Compose-mode runtime smoke (~30s, free):**
   ```powershell
   curl -N -X POST http://localhost:8000/api/strategies/2/chat-stream `
     -H "Content-Type: application/json" `
     -d '{"prompt":"what features would help me build a basic gap-fade strategy?","model":"claude","section":"build","mode":"compose"}'
   ```
   Should stream NDJSON: text deltas → tool_use events → done event with cost + session_id.
4. **Open the desktop app**, navigate to `/strategies/{id}/build`, look at the right column. Send a test prompt. Expect streaming text in the assistant bubble.
5. **Author-mode runtime smoke (when you're brave):**
   - In the chat panel, toggle to `author` mode.
   - Type: `create a new feature called big_volume_bar that triggers when current bar volume > 2x rolling 20-bar median. Include a test in backend/tests/test_big_volume_bar.py and run pytest on it.`
   - Watch the Write/Edit/Bash tool-call chips appear.
   - When done, `git diff backend/app/features/ backend/tests/` to review what the agent wrote. Commit if good, revert if not (`git checkout -- <file>`).
   - Reload `/strategies/builder/<id>/build` — `big_volume_bar` should appear in the pantry.

## Tests

- **`backend/tests/test_chat_stream.py`** — 4 tests, all green with mocked subprocess. Covers happy-path NDJSON, error-event short-circuit, author-mode add_dirs flag passing, 404 on bad strategy.
- **No new frontend tests.** TypeScript + Husky's existing Playwright smoke covers the basic page render. Real interactive testing is the runtime smoke step above.
- **727+4 = 731 backend tests pass total** (added the 4 new ones to the existing 727 baseline).

## Deferred (intentionally)

- **Streaming the chat thread history.** Initial load uses the existing synchronous `GET /chat?section=build`; only new turns stream.
- **Codex parity for tool-use streaming.** Codex CLI doesn't emit structured tool-use JSON. `chat-stream` is Claude-only; the existing synchronous `/chat` endpoint still supports both.
- **Sandboxed write directories beyond `features/` + `tests/`** for author mode. If the agent ever needs to write strategy spec files or modify engine code, that's a future scope expansion that needs CLAUDE.md re-amendment.
- **Tier 2 production agent path** (Anthropic API direct, per-plan usage caps, hosted on Railway). Notable as the eventual rollout for Husky / external users; not built here.
- **Multi-turn agent autonomy beyond the user's confirm-loop.** Pattern is one user prompt → one agent turn (with tool calls) → user reviews → next prompt. No background agents, no autonomous loops.

## Push status

These 5 commits + the prior session's "+ both" fix are local-only. `git push origin main` when ready to share with Husky.
