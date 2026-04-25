# AI Command Center — spec

> **Status: future vision / not implementation-ready.**
> No code, dependencies, routes, models, or schemas land from this document. It exists to capture the long-term direction so future work doesn't drift. Phase 1 (imported results + dashboard + replay + monitor) remains the priority.
>
> See [`ARCHITECTURE.md` §0 Vision](ARCHITECTURE.md) for the canonical product vision. This doc is a sub-spec for the AI layer that eventually sits on top.

## What it is

A personal local-first AI layer that understands the user's trading research — strategies, versions, backtests, notes, experiments, decisions, conclusions, failed ideas, codebase, and prompts — and acts as a research operator across that history.

Not:
- A trading bot that places orders
- A magical predictor of markets
- A replacement for the user's judgment
- A cloud service shared with anyone else

It is:
- A personal research operator
- A memory layer over the BacktestStation database and notes
- A prompt packager that bundles relevant context for cloud LLMs
- An analysis assistant that summarizes, correlates, and surfaces patterns
- A workflow accelerator: less time re-loading context, more time deciding

## Why it exists

Trading research generates a lot of context that is expensive to re-load mentally each session: which version of which strategy was tested under which regime with which feature set, what was concluded, what failed, what's still open. Cloud LLMs lose continuity between conversations. Without a memory layer, the user pays the context-rebuild cost over and over.

The eventual win is compounding: every conclusion, hypothesis, failed idea, and decision feeds future decisions. After a year, queries like "what did I learn about Friday afternoon performance across all strategies" are answerable instantly instead of being lost.

## What problems it solves (concretely)

1. **Lost context across sessions.** "What did I conclude about ROF gating in Q1?" requires no re-reading.
2. **Prompt packaging cost.** The user already has the [Prompt Generator](../backend/app/services/prompt_generator.py) that does this for one strategy; the future Command Center extends that to ad-hoc questions, multi-strategy comparisons, and historical research.
3. **Cross-strategy pattern detection.** "Have I seen this kind of equity-curve shape before in any strategy version?" — only possible with searchable memory.
4. **Decision auditability.** Every decision logged with the context it was made under. Future questioning of past calls becomes traceable.

## How it connects to BacktestStation

```
            ┌────────────────────────────────────────────────────┐
            │  BacktestStation = the source of truth             │
            │                                                    │
            │  Strategies, Versions, Runs, Trades, Metrics,      │
            │  Notes, Experiments, ConfigSnapshots, Autopsy      │
            │  (already implemented in Phase 1)                  │
            └─────────────────────┬──────────────────────────────┘
                                  │ read-only retrieval
                                  ▼
            ┌────────────────────────────────────────────────────┐
            │  AI Command Center (future)                        │
            │                                                    │
            │  Local model: routing, memory, summarization       │
            │  Retrieval: query the DB + notes + artifacts       │
            │  Tools: SQL (read), Python scripts, chart gen      │
            │  Prompt packager: bundles context for cloud LLMs   │
            └─────────────────────┬──────────────────────────────┘
                                  │ produces
                                  ▼
            ┌────────────────────────────────────────────────────┐
            │  Outputs that flow back into BacktestStation       │
            │                                                    │
            │  New Notes (observation/hypothesis/decision/etc.)  │
            │  New Experiments                                   │
            │  Updated Strategy/Version statuses                 │
            │  Saved cloud LLM takeaways (manual capture)        │
            └────────────────────────────────────────────────────┘
```

The Command Center reads BacktestStation. BacktestStation never depends on the Command Center to function. Phase 1 keeps working without any AI layer at all.

## The Prompt Generator is the first shipped feature

The existing [`PromptGeneratorPanel`](../frontend/components/strategies/PromptGeneratorPanel.tsx) on the strategy dossier is the first AI-adjacent feature in the Command Center direction. It already:

- Bundles strategy, versions, recent notes, recent experiments, latest run, autopsy
- Produces a single markdown blob the user pastes into Claude/GPT externally
- Has 6 modes (researcher, critic, statistician, risk_manager, engineer, live_monitor)
- Stays model-agnostic — no API calls, no provider lock-in

Future Command Center work **extends this** rather than replacing it. The first user-facing experience of the Command Center is "the Prompt Generator gets smarter and supports ad-hoc questions, not just per-strategy bundling."

## Roles in the eventual stack

### Local model (future)
- **Job:** routing, summarization, memory queries, prompt packaging, basic Q&A over local research
- **Why local:** privacy (your strategies are your edge), cost (free under existing hardware), latency (no network round-trip)
- **Hardware budget:** Ben's RTX 5080 (16 GB VRAM) is enough for 7-13B parameter models with LoRA. Larger models (70B) need cloud or paid local hardware.
- **Constraint:** Local models are not the long-term memory. Facts live in BacktestStation's database; the local model retrieves and reasons.

### Cloud models (Claude / GPT, used manually)
- **Job:** hard reasoning, code review, novel research questions, architectural critique, statistical analysis
- **When to use:** when the local model can't answer well, or when the question benefits from a fresh perspective
- **How:** the Command Center packages a prompt with context, the user pastes into Claude/GPT externally, the answer comes back, the user manually saves the salient takeaway as a Note/Decision/Experiment
- **No automatic API calls from the production app.** This is a hard rule (Ben uses Max/Plus subscriptions; production app must not bill Anthropic API per token).

### Claude Code (during development, not production)
- **Job:** writing code, refactoring, debugging, generating tests, documentation
- **Boundary:** Claude Code is a development tool. The running BacktestStation app does not depend on Claude Code being available. No agent-driven actions in production.

### Memory / retrieval
- **Job:** exact-fact lookup. Strategy metadata, run metrics, note bodies, experiment decisions.
- **Where it lives:** BacktestStation's existing SQLite metadata DB + the parquet warehouse + future retrieval index
- **What it returns:** structured rows the local model can format into prompts or answer fragments

### Tools
- **Job:** SQL queries, Python analysis, chart generation, backtest replay, autopsy generation
- **Future tools include:** SQL read access, Python notebook runner, chart-from-data tool, prompt-packager
- **Constraint:** all tools are read-only on production data. The Command Center never writes to existing tables without explicit human review (see human review principle below).

## Human review principle

Every AI output that would become a decision MUST pass through a human review step before persisting. This includes:
- Strategy lifecycle changes
- Notes / experiments / decisions auto-generated from cloud answers
- Configuration changes
- Any action that affects future trading

The pattern: AI proposes → user reviews → user accepts → it persists as a Note/Experiment/Decision authored by the user.

This rule already shapes the existing [`ARCHITECTURE.md` §0 Safety rules](ARCHITECTURE.md): "AI suggestions become human-reviewed notes, experiments, or decisions — never automatic strategy changes."

## Do Not Build Yet

These are **explicitly deferred** until the Command Center reaches the appropriate roadmap phase:

- ❌ **Local model runner.** No Ollama, no llama.cpp, no LM Studio integration. No model downloads.
- ❌ **RAG infrastructure.** No LangChain, no LlamaIndex, no vector DB.
- ❌ **Multi-agent orchestration frameworks.** No LangGraph, no AutoGen, no CrewAI.
- ❌ **Fine-tuned adapters.** No LoRA training pipeline.
- ❌ **Predictive ML models.** Setup quality scorers, regime classifiers, etc. are deferred quant/ML work — separate from the Command Center.
- ❌ **In-app LLM chat.** Confirmed in `CLAUDE.md`. The Command Center prompts copy out to Claude/GPT externally.
- ❌ **Bulk external AI session tracking.** Salient takeaways from cloud conversations get saved manually as Notes/Decisions/Experiments. Bulk capture is an open question, not a roadmap item.
- ❌ **Auto-applied AI suggestions.** Per `CLAUDE.md`.

## Phase 1 protection

Until Phase 1 (imported results + dashboard + replay + monitor + research workspace) is fully stable, the AI Command Center exists only as docs. Concretely:

- No new backend modules under `backend/app/ai/` or similar
- No new frontend routes for AI features beyond the existing Prompt Generator
- No dependencies added (`pyproject.toml` and `package.json` stay frozen relative to AI work)
- No changes to existing models, schemas, or API contracts
- No alteration of the engine, ingester, parquet mirror, or monitor pages

When Phase 1 IS stable (engine works, drift monitor works, multi-month live data accumulated), the Command Center moves from Phase A (docs) to Phase B (memory revisit) per [`AI_ROADMAP.md`](AI_ROADMAP.md).

## What "stable" means for Phase 1

Concrete triggers, not vibes:
- Backtest engine ships, ports the live strategy, produces byte-reproducible runs
- Forward Drift Monitor detects live vs backtest divergence
- Live data has been collected continuously for at least 3 months
- The strategy workstation (lifecycle, notes, experiments, prompt generator) has been used in real research for at least 2 months

Hitting all four is the gate. Until then: docs only.
