# market_state — the broad market-state model (greenfield)

Kickoff doc. Open a fresh chat, point it here + at the memory, and say "let's build market_state."

## The vision
A **broad, live, multi-timeframe market-state engine.** Ingests many data sources, detects **smart-money
activity**, and outputs **what the market is doing right now** as detailed phase/state labels — a "what's
going on" brain the strategies (Mira, RV, future bots) read off of. Conditional logic like
"if order flow + regime say X → market is in phase Y."

## THE ONE RULE (non-negotiable)
**Every label/phase has to earn its place by predicting a forward outcome or improving a trade — OOS,
no-lookahead.** A model that confidently labels gorgeous phases that don't predict the next move is the
single most seductive trap in trading (that's what ICT is, and it dissolved on every honest test). The
validation harness is the center of this project, not an afterthought. **No label exists until it forward-validates.**

## Build on rock — what already earned a seat (forward-tested this research push)
- ✅ **MBO order flow** (Mira's `bookproxy` features) — the real smart-money signal (0.518 → 0.699 AUC).
- ✅ **Vol regime** — genuinely forecastable (`phase_model_v0`).
- ✅ **Cointegration / RV structure** — energy/grains/curve spreads hold OOS (`xsectional_rv_v0`).
- ❌ Gamma/GEX (null for ES, 5 cuts), chart-pattern phases, TGIF — DEAD. Do NOT seed the model with these.

The model **starts small and real** (order-flow state × vol regime) and **grows** only as new inputs/labels
forward-validate. COT positioning is one genuinely-new free input worth testing early.

## Proposed structure
```
market_state/
├── README.md          (this)
├── config/            phase taxonomy + named constants (the vocabulary)
├── data/              adapters: warehouse (D:/data via read_bars) -> clean bar/event interface
├── signals/           one module per input: order_flow, vol_regime, coint_state, cot, …
├── labels/            the phases/states made concrete
├── validation/        THE harness — forward-tests every signal→label & label→outcome (build this FIRST)
├── model/             the synthesis — composes ONLY validated pieces into the live state
├── live/              real-time "what's the market doing right now"
└── tests/
```

## Context to load in the new chat (it's all persisted)
- Memory: `MEMORY.md` index + `tsfm_milk_v0.md` (Mira/MBO edge), `xsectional_rv_v0.md` (RV), `options_gamma_gex.md` (gamma=dead).
- Repo: `experiments/STRATEGY_REPORT_2026-06-02.md` (portfolio state), `experiments/_INDEX.md` (what's validated/dead).
- Honest meta: structural/microstructure edges hold (Mira, RV); index-context prediction keeps dying. Build on the former.

## Status
Greenfield. Next step: scaffold `validation/` first (the harness), then wire the two validated inputs.
Reuses BacktestStation's data layer + validated signals (don't re-plumb).
