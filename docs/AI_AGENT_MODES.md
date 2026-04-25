# AI Agent Modes

> **Status: future vision / non-binding design.**
> These are *possible* modes for the eventual AI Command Center, not implemented agents and not committed routes. The first implementation may only need 2-3 modes; the rest exist on paper as direction, not commitments.
>
> Refer back to [`AI_COMMAND_CENTER_SPEC.md`](AI_COMMAND_CENTER_SPEC.md) for the umbrella vision and the existing Prompt Generator's 6 modes (`researcher`, `critic`, `statistician`, `risk_manager`, `engineer`, `live_monitor`) which already ship today and are the ancestor of these.

## Two tiers

The modes split into two confidence tiers:

**Initial likely modes (build first when the time comes):**
1. `/research`
2. `/code`
3. `/memory`

**Future possible modes (speculative):**
4. `/quant`
5. `/backtest`
6. `/feature`
7. `/deploy`
8. `/risk`
9. `/prompt`

Don't build all 9 at once. The initial 3 cover ~80% of practical use; the future 6 are slots that may or may not earn their keep.

---

## Initial likely modes

### `/research`

**Job:** answer "what do I know about X?" by retrieving over notes, experiments, decisions, and run results, then summarizing.

**Memory scope:** read access to Strategy, StrategyVersion, BacktestRun, RunMetrics, Note, Experiment, Autopsy. No writes.

**Possible tools:** SQL read query, semantic search over note bodies, structured filters by strategy/version/date/symbol.

**Example prompts:**
- "What did I conclude about ROF gating across all my NQ strategies?"
- "Show me all the failed hypotheses I tested in Q1 2026."
- "Summarize what I learned about Friday afternoon performance."

**Expected output:**
- A brief markdown summary with the user's actual decisions/conclusions quoted
- Citations: `Note #142 (2026-01-15)`, `Experiment #7 — decision: reject`
- A "what I'm not sure about" section that flags gaps

**Failure modes to avoid:**
- Inventing conclusions the user didn't actually reach
- Quoting cloud LLM output as if it were the user's decision
- Generating answers when retrieval found nothing — say "no relevant memory" instead

---

### `/code`

**Job:** explain or generate code in the BacktestStation repo, with full repo context loaded.

**Memory scope:** read access to all repo files. Write access only via the standard PR/branch flow (just like Claude Code today). No autonomous commits.

**Possible tools:** repo file read, grep, AST search, run tests, generate diffs.

**Example prompts:**
- "Where do I add a new note_type if I want a `verdict` category?"
- "Why does this test for the experiment validation pass when I expect it to fail?"
- "Refactor the parquet mirror to skip files smaller than N bytes."

**Expected output:**
- Direct answer (with file:line citations) for explanation questions
- A diff or full-file rewrite for generation, with a brief rationale
- A test plan when generating

**Failure modes to avoid:**
- Hallucinating file paths or function names — always verify before quoting
- Bypassing existing patterns (use existing schemas/services before creating new ones)
- Producing code without tests for non-trivial changes

---

### `/memory`

**Job:** the meta-mode for managing the assistant's own memory — saving cloud LLM takeaways, organizing artifacts, surfacing forgotten work.

**Memory scope:** read+write Notes (with explicit user approval per write), read everything else.

**Possible tools:** create Note (with confirmation), tag suggestion, find-stale-notes, find-orphan-experiments.

**Example prompts:**
- "Save this Claude response as a hypothesis tagged with strategy 'Fractal AMD'."
- "Find notes I haven't touched in 60+ days that might be stale."
- "What artifacts under `data/research_artifacts/` aren't linked to any note?"

**Expected output:**
- A proposed Note (or list of stale items) for the user to approve
- Never persists without confirmation

**Failure modes to avoid:**
- Auto-saving without confirmation (violates the human review principle)
- Mass-tagging without showing the user the proposed tags first
- Hallucinating notes/experiments/decisions that don't exist

---

## Future possible modes

These are speculative. Each may earn its keep, may get folded into `/research`, or may never get built. Don't take them as commitments.

### `/quant`

**Job:** statistical analysis on backtest results — Sharpe distributions, regime conditional metrics, monte carlo, walk-forward.

**Memory scope:** read Trades, RunMetrics, EquityPoints across all runs.

**Possible tools:** Python notebook runner, scipy/statsmodels, chart-from-data.

**Example prompts:**
- "What's the Sharpe distribution across all my v3 NQ runs?"
- "Run a 1000-iteration monte carlo on this run's trade sequence; what's the 5th percentile drawdown?"

**Expected output:**
- Tabular results + chart references + a brief interpretation
- Caveats about sample size and regime stability

**Failure modes:** giving statistical confidence numbers without flagging small-sample caveats; pretending the user's 30 trades support claims they don't.

**May fold into:** `/research` if statistical questions are infrequent.

---

### `/backtest`

**Job:** run or replay backtests via the eventual in-app engine (when it exists).

**Memory scope:** read Strategy/Version/Config; write new BacktestRun results.

**Possible tools:** engine runner, parameter sweep, replay viewer.

**Example prompts:**
- "Run v3 against Q4 2024 data, both with and without the ROF gate."
- "Replay run #87 with stop buffer = 7pts instead of 5pts."

**Expected output:** new run IDs + a summary comparison.

**Failure modes:** running expensive sweeps without explicit confirmation; persisting bad-quality runs without flags.

**Blocked on:** the actual backtest engine existing (see [`AI_ROADMAP.md`](AI_ROADMAP.md) Phase 1 prerequisites).

---

### `/feature`

**Job:** define, document, and analyze quantitative features (indicators, signals, gates).

**Memory scope:** read FeatureDefinitions (when that table exists), Versions that use them, related Experiments.

**Possible tools:** feature-correlation analyzer, feature-coverage report.

**Example prompts:**
- "What features does my Fractal AMD v3 use that no other strategy uses?"
- "Define a new `daily_volatility_zscore` feature and document it."

**Expected output:** a feature definition with code-link, used_by_versions list, and example values.

**Failure modes:** creating duplicate features under different names; not linking back to the code that computes them.

**May fold into:** `/code` + `/memory`.

---

### `/deploy`

**Job:** prep for putting a strategy live — checks that the strategy version, latest backtest, autopsy, prop-firm sim, and risk profile all align.

**Memory scope:** read everything. Write a "deployment readiness report" Note.

**Possible tools:** drift-monitor preview, risk-profile validator, autopsy summarizer.

**Example prompts:**
- "Is v3 ready to go live on a TPT account?"
- "Generate a pre-flight checklist for deploying Fractal AMD."

**Expected output:** a structured readiness report with red/yellow/green per check.

**Failure modes:** giving green light without enough sample data; ignoring autopsy red flags.

**Blocked on:** Forward Drift Monitor + Risk Profile Manager existing.

---

### `/risk`

**Job:** sizing, daily loss caps, max drawdown projections, kill-switch logic.

**Memory scope:** read RunMetrics + Trades; reference RiskProfile rules (when that exists).

**Possible tools:** position-sizer, drawdown projector, prop-firm rule validator.

**Example prompts:**
- "What position size on a $25K TPT account given my v3 trade distribution?"
- "What's the worst 10-day drawdown in my historical results?"

**Expected output:** sized recommendations with confidence intervals.

**Failure modes:** sizing for live without a Forward-Drift-Monitor green light; assuming historical worst case is the future worst case.

**Blocked on:** Risk Profile Manager existing.

---

### `/prompt`

**Job:** generate prompts for cloud LLMs — extends the existing Prompt Generator beyond per-strategy bundles to ad-hoc questions.

**Memory scope:** read everything; output is text only.

**Possible tools:** context bundler, persona/mode picker, length cap.

**Example prompts:**
- "Build me a prompt asking Claude whether my v3 stop logic has lookahead bias."
- "Give me a critic-mode prompt comparing all my Q1 strategies."

**Expected output:** a markdown prompt the user copies into Claude/GPT externally.

**Failure modes:** stuffing too much context into the prompt; missing relevant notes/experiments.

**May fold into:** the existing Prompt Generator's evolution. This mode is just "the Prompt Generator gets smarter."

---

## Implementation order when the time comes

Per [`AI_ROADMAP.md`](AI_ROADMAP.md):

1. The existing **Prompt Generator** is already a proto-`/prompt` mode shipped in Phase 1.
2. Phase B-C: experiment with `/research` over existing memory (notes, experiments, runs).
3. Phase D: add `/code` and `/memory` if the local model proves capable of useful retrieval.
4. Phase E+: evaluate the future 6 modes one at a time. Most won't ship; that's fine.

**Don't build all 9 modes.** Build the 2-3 you actually use. Decommission modes that don't earn their keep.
