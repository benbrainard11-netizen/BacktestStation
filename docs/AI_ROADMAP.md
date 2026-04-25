# AI Roadmap

> **Status: future vision / non-binding plan.**
> Phases are gated by triggers, not dates. None of the phases past A are committed work. The roadmap exists to give the AI Command Center a long-arc shape; pick up the next phase only when its trigger fires.
>
> Anchors: [`ARCHITECTURE.md` §0 Vision](ARCHITECTURE.md), [`AI_COMMAND_CENTER_SPEC.md`](AI_COMMAND_CENTER_SPEC.md), [`AI_MEMORY_AND_KNOWLEDGE_DESIGN.md`](AI_MEMORY_AND_KNOWLEDGE_DESIGN.md), [`AI_AGENT_MODES.md`](AI_AGENT_MODES.md), [`AI_LOCAL_CLOUD_WORKFLOW.md`](AI_LOCAL_CLOUD_WORKFLOW.md).

## How to read this

Each phase has:
- **Goal**
- **What ships**
- **What's deferred**
- **Trigger to start the next phase** — a concrete observable, not a calendar date

Skipping or rearranging phases is fine if the triggers say so. **Don't pre-build later phases just because the doc names them.**

---

## Phase A — Vision capture (current)

**Goal:** capture the long-arc AI direction so future work doesn't drift, without taking on any implementation debt.

**What ships:**
- This document set: SPEC, MEMORY_AND_KNOWLEDGE_DESIGN, AGENT_MODES, LOCAL_CLOUD_WORKFLOW, ROADMAP
- A short reference in `docs/ARCHITECTURE.md` linking here
- The already-shipped Prompt Generator (in production today) is implicitly Phase A's first deliverable — vision realized in one concrete feature

**What's deferred:**
- Everything else. No new code, schemas, dependencies, or routes.

**Trigger to advance:** Phase 1 of BacktestStation is "stable." Concretely:
- Backtest engine ships and produces byte-reproducible runs
- Forward Drift Monitor detects live-vs-backtest divergence
- Live data has accumulated continuously for ≥3 months on the warehouse
- The strategy workstation (lifecycle, notes, experiments, prompt generator) has been used in real research for ≥2 months

Until **all four** are true, stay in Phase A. Use the docs to inform decisions; do not start building Phase B.

---

## Phase B — Memory revisit (after Phase 1 is stable)

**Goal:** validate that the existing schema actually covers the AI memory needs, identify the small handful of missing pieces, and decide what new tables (if any) earn their place.

**What ships:**
- A re-read of [`AI_MEMORY_AND_KNOWLEDGE_DESIGN.md`](AI_MEMORY_AND_KNOWLEDGE_DESIGN.md) against ≥6 months of real research data
- A short delta document listing categories where the existing schema fell short
- New tables ONLY where the delta document proves the existing schema can't reasonably absorb the data
- Likely candidates per the design doc: `ResearchArtifact` (files), `PromptPackage` (history of generated prompts). Maybe nothing.

**What's deferred:**
- All retrieval / RAG infra
- Local model runner
- Any UI for the assistant

**Trigger to advance:** the new tables (if any) are landed and tested, and you have a clear "I want to query my research like this" example that the schema now supports.

---

## Phase C — Local assistant prototype

**Goal:** prove a local model can usefully retrieve over your research and summarize. No production dependency yet — this is a prototype the user runs intentionally.

**What ships:**
- A local model runner (probably Ollama or llama.cpp) — pick at the time, not now
- Read-only retrieval pipeline over BacktestStation's DB + notes + parquet summaries
- A CLI or thin web UI for asking memory questions outside the main app
- Likely the `/research` mode from [`AI_AGENT_MODES.md`](AI_AGENT_MODES.md) implemented first

**What's deferred:**
- SQL/Python tool access (Phase D)
- AI Command Center UI inside BacktestStation (Phase E)
- Cloud automation
- Autonomous trading anything (forever)

**Trigger to advance:** the prototype answers ≥10 real research questions usefully across a week of usage. If it can't reliably retrieve and summarize, the model or pipeline is wrong; iterate within Phase C rather than advancing.

---

## Phase D — Tool-assisted research

**Goal:** give the local assistant tools so it can do more than retrieval — run analysis, generate charts, summarize backtests automatically.

**What ships:**
- SQL read access (probably via a sandboxed query runner — read-only on the metadata DB)
- Python analysis script runner (sandboxed, read-only on data files)
- Chart-from-data tool (matplotlib or plotly via Python)
- Backtest review summary generator (autopsy + metrics + notes → markdown report)

**What's deferred:**
- Engine invocation (Phase E or beyond — only if the engine exists and is solid)
- Write access to any tables
- External API calls

**Trigger to advance:** tools save you measurable time. "Generating a backtest review used to take me 30 min, now it takes 2 min" — that's the trigger. If tools are slower or more fragile than doing it manually, the abstraction is wrong.

---

## Phase E — AI Command Center UI

**Goal:** integrate the assistant into BacktestStation's UI so it's one click away from research work, not a separate CLI session.

**What ships:**
- A new `/ai` route or panel
- Ask-research-memory query box (powered by the Phase C-D pipeline)
- Experiment summarizer (auto-generates a summary of an experiment's status)
- Prompt packager extension: ad-hoc questions on top of the existing per-strategy bundling
- Save-back UX: cloud LLM takeaways → Note/Experiment/Decision with one click

**What's deferred:**
- Fine-tuned adapters (Phase F)
- Predictive ML models (separate quant/ML work)
- Multi-model orchestration

**Trigger to advance:** users (Ben + Husky) actually use the in-app AI for >50% of memory queries. If they're still using ad-hoc Claude/GPT chats outside the app for most things, the UI isn't earning its keep — re-design within Phase E.

---

## Phase F — Optional advanced intelligence layer

**Goal:** make the local assistant *better* at the user's specific style of research and reporting via fine-tuned adapters.

**What ships (if pursued at all):**
- LoRA adapters trained on the user's note-writing style, decision format, code review tone
- Possibly: domain-specific embedding model fine-tuned on the user's research vocabulary (if generic embeddings underperform)
- Possibly task-specific predictive models (setup quality scorer, regime classifier, risk governor) — but **these are separate deferred quant/ML work**, not the core Command Center. Treat them as tools the assistant can call, not as the assistant itself.

**What's deferred:**
- Fine-tuning on factual content. Hard rule. Never put strategy results, trade outcomes, or market data into model weights.
- Multi-agent orchestration

**Trigger to advance:** there is no Phase G. Phase F is the end of the planned roadmap. After Phase F, the Command Center either earns its keep and gets incremental polish, or it doesn't and gets reconsidered.

---

## What NOT to build at any phase

These remain off-limits regardless of phase progression:

- **In-app LLM chat** that calls cloud APIs from production code. Hard rule.
- **Autonomous trading actions.** The assistant never places, modifies, or cancels orders. Period.
- **Auto-applied configuration changes.** Strategy version edits, sizing rule changes, lifecycle status moves all require explicit user action.
- **Bulk capture of cloud LLM transcripts.** Manual takeaway capture is the default. Revisit only if real evidence shows search-old-conversations is a recurring need.
- **Multi-tenant anything.** Personal-first.
- **Subscriptions / billing inside the app.** Ben uses Max + Plus subs externally; the app stays single-user offline.

## How this protects current Phase 1

Three structural protections:

1. **Phase A is docs-only.** No backend, no frontend, no schemas. Phase 1 development is unaffected.
2. **Phase B's trigger requires Phase 1 to be done.** Engine + drift monitor + 3 months of data + 2 months of usage. By definition Phase 1 finishes before Phase B starts.
3. **Future phases reuse existing models.** Per [`AI_MEMORY_AND_KNOWLEDGE_DESIGN.md`](AI_MEMORY_AND_KNOWLEDGE_DESIGN.md), 12 of 17 memory categories are already covered. The AI work mostly *uses* what Phase 1 builds, not parallels it.

## How this builds on `ARCHITECTURE.md` §0

`ARCHITECTURE.md` §0 lays out:
- The research loop: idea → thesis → rules → version → experiment → backtest → analysis → decision → forward/live monitor → refine
- The pillar list, with AI Prompt Generator as a "Later" pillar
- The existing safety rules: DB is source of truth, no destructive cascades, human-reviewed AI suggestions

The AI Command Center is the eventual realization of that "Later" pillar. The Prompt Generator was the first deliverable; this roadmap describes the rest. Nothing here contradicts §0; everything builds on it.

## Reading order for someone new

If a future you / Husky / Claude session lands on this repo and wants to understand the AI direction:

1. **`ARCHITECTURE.md` §0** — the canonical product vision
2. **`AI_COMMAND_CENTER_SPEC.md`** — what the AI layer is and isn't
3. **`AI_LOCAL_CLOUD_WORKFLOW.md`** — how the parts compose
4. **`AI_MEMORY_AND_KNOWLEDGE_DESIGN.md`** — what the memory looks like
5. **`AI_AGENT_MODES.md`** — what kinds of queries the assistant handles
6. **`AI_ROADMAP.md`** (this doc) — what to build when

If any of those docs contradict each other, `ARCHITECTURE.md` §0 wins, then `AI_COMMAND_CENTER_SPEC.md`, then the rest.
