# AI Local + Cloud Workflow

> **Status: future vision / non-binding design.**
> Describes how local models, Claude Code, GPT/Claude web, and the BacktestStation app eventually compose. No code, dependencies, or model integrations land from this document.
>
> Anchors: [`ARCHITECTURE.md` §0 Vision](ARCHITECTURE.md), [`AI_COMMAND_CENTER_SPEC.md`](AI_COMMAND_CENTER_SPEC.md).

## The four roles

```
┌─────────────────────────────────────────────────────────────────────┐
│  LOCAL MODEL                                                        │
│  ───────────                                                        │
│  Job:        personal memory, routing, summarization, prompt        │
│              packaging, basic Q&A over your research                │
│  Hardware:   RTX 5080 (16 GB) on Ben's main PC; sufficient for      │
│              7-13B param models with LoRA                           │
│  Cost:       free under existing hardware                           │
│  Privacy:    data never leaves the local network                    │
│  Trust:      low-stakes assistant; humans review all outputs        │
│  When used: every query first; for hard reasoning, packages a       │
│              prompt for the cloud                                   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  CLAUDE CODE (during development)                                   │
│  ─────────────                                                      │
│  Job:        writing code, debugging, refactoring, generating       │
│              tests, writing docs                                    │
│  Cost:       flat-rate under Ben's Claude Max sub                   │
│  Boundary:   development tool only. The running BacktestStation     │
│              app does NOT depend on Claude Code being available     │
│              and does NOT call out to it at runtime.                │
│  When used:  intentionally, when working on the codebase            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  GPT / CLAUDE WEB (manually, intentionally)                         │
│  ────────────────                                                   │
│  Job:        hard reasoning, code review, novel research questions, │
│              architectural critique, statistical analysis           │
│  Cost:       flat-rate under Ben's ChatGPT Plus / Claude Max subs   │
│  Boundary:   user pastes prompts in manually; receives answers      │
│              manually; salient takeaways saved back manually        │
│  When used:  when the local model can't answer well, or when a      │
│              fresh perspective from a larger model is worth the     │
│              context-switch cost                                    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  BACKTESTSTATION (the source of truth)                              │
│  ──────────────                                                     │
│  Job:        long-term memory, exact facts, structured data,        │
│              decision audit trail                                   │
│  Coverage:   strategies, versions, runs, trades, metrics, notes,    │
│              experiments, autopsy, decisions                        │
│  Boundary:   never stores model weights, never makes API calls to   │
│              external LLMs from production code                     │
│  When used:  always — every memory query goes here first            │
└─────────────────────────────────────────────────────────────────────┘
```

## Hard rules

### No hidden API billing

The production BacktestStation app **never** makes API calls to Anthropic, OpenAI, or any cloud LLM provider. This is a binding rule (see Ben's hard subscription policy in `CLAUDE.md`).

The Prompt Generator (already shipped) is the right pattern: the app generates prompt **text**, the user pastes it into Claude/GPT manually. No bill.

If a future feature seems to need automatic cloud API calls, that feature is wrong-shaped. Re-examine whether the local model could handle it, or whether the user should be in the loop.

### Cloud answers don't auto-save

Useful Claude/GPT answers don't flow back into BacktestStation automatically. The user reads them, paraphrases the salient takeaway, and saves it as a Note (with appropriate `note_type`), Experiment, or Decision. This is the human review principle.

Why: cloud LLM outputs are noisy. ~70% of any conversation is exposition, hedging, formatting. The 30% that's a real conclusion or hypothesis is what should land in your memory. Manual capture forces you to extract the gold.

### Cloud is not the long-term memory source

BacktestStation is. Every "what did I conclude about X" answer should be answerable from your local DB, not from a cloud LLM's training data or your old chat transcripts.

Cloud LLMs are **compute**, not **memory**. They reason over context you give them. Your job is to feed them the right context — the local model + retrieval handle that.

### Don't route everything through the biggest local model

> **Avoid routing all tasks through the largest available local model. Prefer fast, stable, composable local models and escalate to GPT/Claude only for tasks that genuinely need stronger reasoning, coding, or research.**

The temptation: "I have a 70B-class local model running, send everything to it." Don't. Reasons:

- A small fast model (3-8B) handles routing, summarization, and tag suggestion with sub-second latency. A 70B model handles the same in 5-30s. The user feels every bit of that latency.
- Smaller models are more *stable* — easier to swap, less infrastructure-fragile, less GPU memory contention with other work.
- Composability matters: a small model that calls retrieval + a small model that summarizes + escalation to cloud for hard reasoning beats one giant model trying to do everything.
- Hard reasoning, novel research, and large-context coding still go to GPT/Claude manually. The local stack doesn't have to be best-at-everything; it has to be fast and good enough for the routine 80%.

Escalation criteria worth thinking about: complexity of the question, length of context required, novelty (cloud LLMs see far more variety in their training data), correctness stakes (decisions that affect money go to the bigger model).

## The prompt packaging workflow

This is the canonical flow for "I have a question that needs Claude/GPT-level reasoning":

```
1. User asks the assistant a question
   ───────────────────────────────────
   "Is my v3 stop logic vulnerable to lookahead bias?"

2. Local assistant gathers context
   ────────────────────────────────
   - Strategy 'Fractal AMD' metadata
   - All v3 versions' entry/exit/risk markdown
   - Last 20 notes scoped to Fractal AMD
   - Latest backtest run + metrics
   - Latest autopsy
   - The user's actual question

3. Local assistant builds a clean prompt
   ──────────────────────────────────────
   Markdown blob, ~2-10 KB, with section headers:
   ## Strategy
   ## Versions
   ## Recent notes
   ## Latest run + metrics
   ## Autopsy
   ## Your task: lookahead-bias review

4. User reviews the packaged prompt and copies it out
   ──────────────────────────────────────────────────
   Pastes into a fresh Claude or GPT session manually.
   This is intentional friction — the user sees what's
   being sent and can edit it.

5. Cloud LLM responds
   ───────────────────
   Long answer with reasoning. Probably 1-3 KB of text.

6. User extracts salient takeaway
   ───────────────────────────────
   Reads the response. Picks the actually-useful bit
   (one decision, two hypotheses to test, one action item).
   Saves as Note(s) and/or Experiment(s) authored by them,
   with tags + reference to the question that triggered it.

7. The takeaway is now part of long-term memory
   ─────────────────────────────────────────────
   Searchable. Cited. Owned by the user.
   The cloud transcript itself can be discarded.
```

This is exactly what the existing Prompt Generator implements at step 3 today. Steps 1-2 (local-assistant context gathering) and step 6 (manual save-back) are the future work.

## Why this hybrid is right

Three forces shape the design:

1. **Privacy.** Strategies are edge. Edges sent to OpenAI's training data can become OpenAI's training data. The local model handles the bulk of memory queries; only specific, scoped questions go cloud. When they go cloud, the user reviews exactly what's sent.

2. **Cost.** Even on Max/Plus subs, automatic cloud calls in production would burn through quotas fast. Local + manual cloud = predictable cost.

3. **Quality.** Cloud LLMs are better reasoners than any 13B model on a 16GB GPU. Hard questions deserve cloud-level reasoning. Routine memory queries don't — they just need retrieval and summarization, which local handles fine.

The hybrid lets each tool do what it's best at without giving up on the others.

## What this workflow is NOT

- **Not a chat app.** No persistent conversation history with cloud LLMs in BacktestStation. Each cloud session is self-contained; you bring context to it.
- **Not autonomous.** No agent loop running unsupervised. Human-in-the-loop at every step.
- **Not a model marketplace.** No "switch model providers" UI. The user picks where they paste manually.
- **Not a transcript archive.** Don't store the full back-and-forth. Save the takeaway, not the conversation.

## Open questions for later

These don't need answers now. Flagging for when they become relevant:

- **Which local model?** Llama 3.x 8B is a reasonable default at 16 GB VRAM. Better options will exist by the time Phase C arrives. Don't pick now.
- **Embedding model for retrieval?** Same — pick when Phase D arrives. Sentence-transformers / nomic-embed are standard.
- **Local model runtime?** Ollama, vLLM, llama.cpp, LM Studio — pick when Phase C arrives.
- **Should takeaways flow into memory automatically?** Default: **no**, manual capture only. Revisit if the user repeatedly says "I wish takeaways saved themselves."

## Connection to the existing Prompt Generator

The Prompt Generator already implements:
- Step 2: gather context (server-side bundling of strategy + versions + notes + experiments + run + autopsy)
- Step 3: build a clean prompt (markdown sections, mode-specific preamble, soft+hard size caps)
- Step 4: copy-out UX (textarea + Copy button + clipboard fallback)

What it does NOT yet do (future Phase E work, when the time comes):
- Step 1: ad-hoc question entry (currently bound to per-strategy mode preambles)
- Step 6: structured save-back (currently the user has to manually create a Note)

The future Command Center extends the Prompt Generator along these two axes. It does not replace it.
