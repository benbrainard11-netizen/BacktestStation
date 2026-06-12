# Deep-research prompt (copy into GPT-5.5 Pro / Claude deep research)

Copy everything below the line. Paste the answer back into `report/external_research.md`
and reconcile it against PLAN.md before Phase 1 design is frozen.

---

I am building a level-reaction scalping study on CME equity index futures (ES, NQ, YM,
RTY). I have: 13 months of MBP-1 (every top-of-book change + every trade, ns timestamps),
5 months of full depth-by-order MBO, 11 years of 1-minute bars, and EOD options chains
with greeks/OI for SPX/NDX/RUT/DJX (2015→present). Retail-grade execution via Rithmic
(assume 5–50ms order latency, no colocation). I want a rigorous, citation-backed survey —
academic literature AND credible practitioner evidence — on the following. For every claim,
distinguish: (a) documented with data, (b) practitioner folklore with plausible mechanism,
(c) folklore likely false. Flag every result that likely fails after realistic costs.

1. **Which price-level types have *documented* short-horizon reaction effects in equity
   index futures or equities?** Cover: prior-day high/low/close, overnight/session
   extremes, opening range, round numbers (price clustering & limit-order clustering
   literature), VWAP and VWAP bands (institutional benchmark execution behavior), volume
   profile nodes (HVN/LVN/POC), options strike pinning and dealer-gamma walls (max-pain,
   delta-hedging flows near strikes), large visible resting liquidity in the order book,
   prior swing highs/lows ("liquidity pools"). For each: effect size, horizon, decay over
   the years (post-2015 especially), and whether the effect is *reaction* (bounce) or
   *attraction* (magnet) — these need different trade constructions.

2. **Passive (maker) fill modeling from MBO data.** Best-practice queue-position models:
   queue-reactive models (Huang-Lehalle-Rosenbaum), Cont-Kukanov-Stoikov order-flow
   frameworks, Moallemi & Yuan queue-value work, anything newer (2020+). Concretely: given
   depth-by-order data, how should I estimate P(fill | limit at level, placed T seconds
   before touch) and the conditional adverse selection E[move | filled] vs E[move |
   touched]? What queue-position assumptions are defensible for a retail order (joins the
   back, no pro-rata — ES is FIFO)? What does the literature say about the *adverse
   selection cost of passive fills at salient levels* specifically?

3. **The economics of scalping with retail latency.** Published or credible evidence on
   whether seconds-to-minutes mean-reversion scalps at reference levels can clear costs
   (~$3.80 RT commission + spread) without colocation. Where exactly does the line sit
   between "needs HFT infrastructure" and "capturable at 5–50ms"? Which trade
   constructions are latency-robust (resting orders placed well in advance) vs
   latency-fragile (reacting to order-book events)?

4. **Stop placement and stop-hunting around salient levels.** Evidence on price revisiting
   swept extremes, optimal stop offsets beyond a level, and clustering of stop orders
   (Osler's work and successors). Anything quantitative on "level retest within k ticks
   after first rejection" base rates.

5. **Known pitfalls in backtesting limit-order strategies** — the canonical list of ways
   limit-fill backtests lie (fill-on-touch optimism, ignoring queue, ignoring
   cancel-and-replace latency, last-look on the close of the bar, survivorship of touched
   levels). Cite who documented each.

6. **What do prop/HFT practitioners say actually works at levels in 2024–2026 index
   futures** — absorption/iceberg detection at a level, book-imbalance confirmation,
   time-of-day effects (open vs lunch vs close), first-touch vs later-touch quality?
   Separate evidenced claims from marketing.

Output format: ranked list of level families by evidence strength for *reaction* trades;
a recommended queue/fill model implementable from MBO with its key parameters; a list of
"do not bother" findings; full citations.
