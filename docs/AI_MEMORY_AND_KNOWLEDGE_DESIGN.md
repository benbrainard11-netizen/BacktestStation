# AI Memory & Knowledge Design

> **Status: future vision / non-binding design.**
> This document describes *categories* of memory the AI Command Center will eventually need. It is **not** a final schema and does **not** authorize new tables. Most categories are already covered by existing models. New tables only land when an existing category cannot reasonably accommodate the data and there is concrete evidence the missing piece blocks real research work.
>
> See [`AI_COMMAND_CENTER_SPEC.md`](AI_COMMAND_CENTER_SPEC.md) for the umbrella vision and [`ARCHITECTURE.md` §0](ARCHITECTURE.md) for the project's anchor vision.

## Core principle

> **Exact facts go in the database. Style/process/terminology go in adapters.**

The memory system is the BacktestStation database (and adjacent files), not the model weights. Fine-tuning a model on your strategy results is a category error: results change, weights don't update. Retrieval over a structured DB is the right pattern.

## External AI memory rule

**Default: manual capture.** When you get a useful answer from Claude/GPT, save the salient takeaway as a Note (with `note_type` = `decision`, `hypothesis`, `observation`, etc.), an Experiment, or a Research Artifact. Do **not** assume bulk capture of every external AI prompt and answer is the right pattern.

Bulk session tracking is an **open question**. It only earns its keep if the user repeatedly hits "I wish I could search my old GPT conversations." Until that pain shows up, manual capture into existing Note/Experiment/Decision shapes is sufficient.

## The categories

Each category below has:

- **What it means** — definition
- **Why the assistant needs it** — why retrieval over this would be useful
- **Existing repo coverage** — what already covers this (with file paths)
- **When a new table might be justified later** — concrete trigger for re-evaluating
- **What should NOT be stored there** — boundaries
- **Example object** — one realistic instance

---

### 1. Strategies

**What:** the named research-track for a hypothesis (e.g., "ORB Fade", "Fractal AMD").

**Why the assistant needs it:** every retrieval starts here. "Tell me about all my volatility-breakout strategies" is a strategy-level query.

**Existing coverage:** `Strategy` model in [`backend/app/db/models.py`](../backend/app/db/models.py) — id, name, slug, description, status, tags, created_at, versions[].

**When a new table justifies:** never (this is the right shape).

**Should NOT store here:** version-specific rules (those go on `StrategyVersion`), per-run results (those go on `BacktestRun`).

**Example:**
```
{
  "id": 4,
  "name": "Fractal AMD",
  "slug": "fractal-amd",
  "status": "research",
  "description": "Daily→Session SMT with FVG retrace + ROF gate",
  "tags": ["nq", "intraday", "smt"]
}
```

---

### 2. Strategy versions

**What:** a specific ruleset (entry/exit/risk markdown) under a strategy. Versions iterate as the rules change.

**Why the assistant needs it:** comparing v1 vs v2 vs v3 rules + their backtest results is the heart of strategy evolution analysis.

**Existing coverage:** `StrategyVersion` — entry_md, exit_md, risk_md, archived_at, git_commit_sha, created_at.

**When a new table justifies:** never.

**Should NOT store:** specific run results (those go on `BacktestRun`), implementation code (already linked via `git_commit_sha`).

**Example:**
```
{
  "id": 12,
  "strategy_id": 4,
  "version": "v3",
  "entry_md": "Enter on 1m FVG retrace after 5m SMT confirmation; gate by ROF 1-3.",
  "exit_md": "Stop = FVG low - 5pt buffer; target = 3R.",
  "risk_md": "Max 2 trades/day, 09:30-13:59 ET only."
}
```

---

### 3. Backtest runs

**What:** an execution of a strategy version against a dataset, with imported or generated results.

**Why the assistant needs it:** "show me all winning runs of v3 across 2024-2026" type queries.

**Existing coverage:** `BacktestRun` — strategy_version_id, symbol, name, timeframe, session_label, start_ts, end_ts, status, tags.

**When a new table justifies:** never. Tags + filtering already give you everything.

**Should NOT store:** raw trade data (that's on `Trade`), config (on `ConfigSnapshot`), metrics rollup (on `RunMetrics`).

**Example:**
```
{
  "id": 87,
  "strategy_version_id": 12,
  "symbol": "NQ",
  "name": "v3 Q1 2026 baseline",
  "tags": ["validated", "baseline"]
}
```

---

### 4. Trades

**What:** individual entries/exits from a backtest run.

**Why the assistant needs it:** trade-level analysis. "Find all losing Friday trades across all my NQ strategies."

**Existing coverage:** `Trade` — backtest_run_id, entry_ts, exit_ts, side, entry_price, exit_price, stop_price, target_price, size, pnl, r_multiple, exit_reason, tags.

**When a new table justifies:** never. The tags column is the extension point.

**Should NOT store:** computed indicators (regenerate from price data), notes about the trade (use `Note` with `trade_id` set).

---

### 5. Metrics

**What:** the rollup statistics for a backtest run.

**Why the assistant needs it:** "rank my v3 runs by net_r," "show all runs with profit_factor > 1.5."

**Existing coverage:** `RunMetrics` — net_pnl, net_r, win_rate, profit_factor, max_drawdown, avg_r, trade_count, etc.

**When a new table justifies:** if you start computing fundamentally different metric families (e.g., Sharpe distribution, regime-conditional metrics) and want them queryable independently. Wait for the engine to ship before deciding.

**Should NOT store:** per-trade metrics (those are derivable), live signals (those are `LiveSignal`).

---

### 6. Configs

**What:** the parameter JSON snapshot a backtest was run with.

**Why the assistant needs it:** reproducibility. "What stop buffer did this run use?"

**Existing coverage:** `ConfigSnapshot` — payload (JSON).

**When a new table justifies:** never.

**Should NOT store:** the strategy rules (those are on `StrategyVersion.entry_md/exit_md/risk_md`).

---

### 7. Notes

**What:** human-authored research artifacts attached to a strategy, version, run, or trade.

**Why the assistant needs it:** notes are where reasoning lives. Every retrieval over "what did I conclude" hits this.

**Existing coverage:** `Note` — body, note_type (observation/hypothesis/question/decision/bug/risk_note), tags, attachments to strategy/version/run/trade, created_at, updated_at.

**When a new table justifies:** if you start needing structured fields per note_type (e.g., a hypothesis needs predicted_outcome + actual_outcome columns). Wait for that pain to show up.

**Should NOT store:** raw cloud LLM responses verbatim. The salient takeaway, paraphrased and tagged, IS what should land in a Note.

**Example:**
```
{
  "id": 142,
  "strategy_id": 4,
  "note_type": "decision",
  "tags": ["roof-gate", "validated"],
  "body": "Removed ROF gate after 4-month forward test. WR didn't degrade; trade frequency went from 3.2/day to 4.8/day. Net effect: +12R/month vs gated."
}
```

---

### 8. Screenshots / research artifacts

**What:** chart screenshots, exported CSVs, PDFs, prompt outputs, multi-paragraph research write-ups.

**Why the assistant needs it:** sometimes a chart pattern is the memory. "Show me the equity curve I screenshotted from the Sept 2025 v2 run."

**Existing coverage:** **partial.** No structured artifacts table yet. Files can land in `data/research_artifacts/` with a Note pointing at them. Manual.

**When a new table justifies:** when there are >50 artifacts and finding them is a real friction. The minimum viable shape: `id, kind (image/pdf/text), file_path, attached_to (strategy/version/run/note), description, created_at`.

**Should NOT store:** the artifact bytes themselves (filesystem is fine), strategy results (those are in proper tables).

---

### 9. Hypotheses

**What:** "I think X causes Y under conditions Z."

**Why the assistant needs it:** to surface untested or partially-tested hypotheses when the user is planning the next experiment.

**Existing coverage:** `Note` with `note_type = "hypothesis"`. Good enough for now.

**When a new table justifies:** if you want hypotheses to have structured fields like `predicted_effect`, `tested_via_experiment_id`, `outcome` (confirmed/refuted/inconclusive). At that point a `Hypothesis` model becomes a thin wrapper over a Note pattern.

**Should NOT store:** speculative pattern observations (those are `note_type=observation`), conclusions (those are `note_type=decision`).

---

### 10. Feature definitions

**What:** the definition of an indicator/feature used by a strategy (e.g., "ROF score: 1-3 scale based on TBBO aggressor side and trade rate").

**Why the assistant needs it:** strategies share features. Knowing what features are defined where lets the assistant correlate across strategies.

**Existing coverage:** **none structured.** Currently lives in code (`backend/app/services/...` for the existing live-bot work) and in version markdown.

**When a new table justifies:** when you have ≥3 strategies that share features and you find yourself manually cross-referencing how the same feature was used in each. Minimum shape: `id, name, definition_md, code_link (file:line), created_at, used_by_versions[]`.

**Should NOT store:** feature *values* (those are run-time, not memory).

---

### 11. Feature test results

**What:** "Did adding feature X to strategy Y improve metric Z?"

**Why the assistant needs it:** to avoid retesting things that were already tested.

**Existing coverage:** `Experiment` model — hypothesis, baseline_run_id, variant_run_id, change_description, decision (pending/promote/reject/retest/forward_test/archive), notes. This is **already the right shape** for feature test results.

**When a new table justifies:** never. `Experiment` is the answer.

**Should NOT store:** general research notes (those are `Note`).

---

### 12. Failed ideas

**What:** strategies, features, or hypotheses that were tested and rejected.

**Why the assistant needs it:** "Have I tried this before? What went wrong?" — saves cycles on bad ideas re-emerging.

**Existing coverage:** `Note` with `note_type = "decision"` and body explaining why it failed; OR `Experiment` with `decision = "reject"`. Both work.

**When a new table justifies:** never. The existing patterns cover it; failed ideas are first-class citizens via the existing `note_type` and `decision` vocabularies.

**Should NOT store:** ideas that are still being tested (those are `pending`), ideas that worked (those are `promote`).

---

### 13. Conclusions

**What:** what the user *decided* about something, in a form quotable to future-self or another reader.

**Why the assistant needs it:** "what's my position on X?" — the assistant should be able to answer with the user's actual recorded conclusion.

**Existing coverage:** `Note` with `note_type = "decision"`. Optionally `Experiment.decision` for experiment-scoped conclusions.

**When a new table justifies:** never.

**Should NOT store:** observations (those are `note_type=observation`), open questions (those are `note_type=question`).

---

### 14. Prompt packages

**What:** the bundled context-and-mode prompts the Command Center generates and the user copies out to Claude/GPT.

**Why the assistant needs it:** to recall "what did I ask Claude about this strategy three weeks ago?" without re-typing the question.

**Existing coverage:** **none.** The current Prompt Generator generates a prompt and shows it; nothing persists. The user can manually copy the prompt text into a Note.

**When a new table justifies:** when the user finds themselves regenerating similar prompts repeatedly. Minimum shape: `id, strategy_id, mode, focus_question, prompt_text, char_count, created_at, salient_response_note_id (FK back to a Note)`.

**Should NOT store:** the cloud LLM's response verbatim (paraphrase salient parts into a Note).

---

### 15. Code context snapshots

**What:** the git SHA + file:line references that a strategy version or run was tied to.

**Why the assistant needs it:** "what code was this v3 run actually using?"

**Existing coverage:** `StrategyVersion.git_commit_sha` and `BacktestRun.git_commit_sha` (per the architecture spec; verify in models). Standard.

**When a new table justifies:** never. Git is the snapshot system.

**Should NOT store:** the code itself (it's in git).

---

### 16. Decisions / verdicts

**What:** the formal "we decided X" markers — distinct from Notes in that they carry weight: "this is the verdict, future questioning of it should reference this."

**Why the assistant needs it:** to surface the highest-confidence claims when answering questions.

**Existing coverage:** `Note` with `note_type = "decision"` for general decisions, `Experiment.decision` for experiment-bound verdicts.

**When a new table justifies:** if you start needing decisions with formal lineage (decision A overrules decision B, requires X to remain true). At that point a `Decision` model with `supersedes_id`, `applies_until` becomes useful. Wait for the friction.

**Should NOT store:** in-progress thinking (Note as observation/question), informal opinions (Notes are fine).

---

### 17. Selective external AI takeaways

**What:** the salient bits from useful Claude/GPT conversations.

**Why the assistant needs it:** to retain hard-won insights from cloud LLM sessions without storing the entire conversation.

**Existing coverage:** `Note` (manual paste of paraphrased takeaway, tagged with the source mode/date).

**When a new table justifies:** **open question.** If the user repeatedly says "I wish I could search my old GPT conversations," consider a lightweight `ExternalAITakeaway` model with `id, source (claude/gpt/...), date, original_question, paraphrased_takeaway, related_strategy_id`. Otherwise: don't.

**Should NOT store:** the verbatim conversation transcript. It's noisy, mostly irrelevant later, and creates a privacy/data-volume problem.

---

## What this design means in practice

Of 17 categories, **12 are already fully covered** by existing models. Three are partially covered (Notes can absorb hypotheses, failed ideas, conclusions, takeaways but might justify their own tables eventually). Two have no current home (research artifacts, prompt packages) and would need new tables — but only when concrete need arises.

**The takeaway:** the BacktestStation schema is mostly already right for the AI Command Center. The work isn't "design a memory schema." The work is "build retrieval over what already exists, plus a small handful of new tables only when proven necessary."

This document is intentionally NOT a migration plan. It's a checklist for future-you (or Husky, or a future Claude session): when considering "do I need a new table for X?", first check this doc to see if X already has a home.

## Future implementation note — start simple

When retrieval over this memory eventually gets built (Phase C-D in [`AI_ROADMAP.md`](AI_ROADMAP.md)):

> **Start with simple embedding + retrieval using existing BacktestStation records and pgvector before introducing external RAG/agent frameworks.**

Concretely: embed each Note body, Strategy description, version markdown, and experiment hypothesis with a small open embedding model; store the vectors next to the source row; query with cosine similarity + structured filters. **Cited source records always travel with the answer** — no untraceable summaries.

Avoid:
- LangChain, LlamaIndex, LangGraph, or other framework stacks until the simple loop has shipped and proven useful
- Vector DBs that are separate services (Pinecone, Weaviate) — keep retrieval co-located with the source DB
- Re-embedding the entire corpus on every model swap; design for incremental embedding from day one
