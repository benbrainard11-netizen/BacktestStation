# breakout_ranker_v0 — LEDGER

Run-by-run record. Newest first.

## 2026-06-21 — build + verdict (one session)

**Context.** Ben pasted external advice proposing a "sector-relative breakout ranking model +
options overlay" with a v0 question (liquid stocks / top-quartile sectors / compression near 52wk
highs / +2R-before-1R after the pivot). The advice is a careful roadmap to ground the lab has
already covered (breakouts comprehensively dead across `stock_strategies_v0`). Ben chose to rebuild
it fresh anyway. This module gives the advice its full, fair shot with kill tests baked in.

**Build.** `common.py` + `barrier.py` + `build_setups.py` over clean Polygon 2016–2026 (delisted incl).
One pass emits the gated setup table AND a matched random null sample using the identical mechanic.

- First build used **stop = base low** → +2R demanded a ~+30% move → win 3.3% (degenerate label).
  Switched to **stop = pivot − 1·ATR** (the advice's tradeable option) → win ~28% (the expected ~⅓
  base rate for a 2:1 barrier). Lesson logged in the README.

**Results (triggered: gated 169,695 / null 107,827):**

- **Null control (net 15bps):** gated win 28.1% / netR −0.304 vs null 27.6% / −0.212 → delta meanR
  **−0.091**, delta>0 in **1/10 years**, mean delta −0.126. The gated setup is *worse* than a random
  liquid day in the same stock.
- **Sector top-quartile filter:** netR −0.311, delta vs null −0.099 → no help.
- **Scorecard top-decile (advice 0–100):** netR −0.307, delta>0 in 2/10 years (2022 top-decile −0.96).
- **Robustness:** gross (0bps) all-gated **−0.144** (negative before costs); ex-2020 −0.316; drop-top-1%
  gross **−0.98**; net monotonically worse with cost (15bps −0.304, 30bps −0.463).
- **ML walk-forward (predict netR, train<y→predict y, 2019–2026):** rank-IC **+0.068** (real — shuffled
  control collapses to −0.004), but top-decile OOS netR **−0.211**, positive in **0/8 years**, ex-2020
  −0.225, drop-top-1% gross −0.95. The model sorts "least-bad from bad"; no decile is profitable.
- **Sanity controls:** all 4 honest-fill paths PASS (target +2R, clean stop −1R, gap-through −2.38R,
  flat→timeout ~0) → the negative verdict is the data, not the harness.

**Verdict: NO EDGE at any level** (raw setup, sector filter, scorecard, learned ranker). Negative even
gross; the whole upside is a fat-tail lottery. Independent fresh reproduction of the lab's breakout null
against the advice's exact +2R-before-1R / sector-relative / compression-near-52wk-high spec.

**Adversarial verification (4-agent workflow, wf_2b8d00ad-a37):** all 4 skeptics returned
`would_flip_verdict=false` at high confidence.
- *Detection:* hand-verified 20 random setups from raw bars (20/20 genuinely near-52wk-high tight
  bases); every *cleaner* reading of the advice (prox≥0.99, base≤6%, tightest "ideal") is MORE
  negative. Faithful, causal, no off-by-one.
- *Null fairness:* mechanic byte-identical, days disjoint, well-diversified; the null is moot because
  the gated setup is negative even in absolute gross (a 0R do-nothing baseline beats it).
- *Label/fill/leak:* 2,000 trades re-resolved byte-for-byte; features recompute from bars≤i (0/3000
  mismatches); honest fills, no reverse-leak, no sign-flip.
- *Steelman:* exhaustive slice grid (near-high, base width, vol contraction, RS, liquidity, sector,
  scorecard quantiles, recent years, target multiples 1/1.5/2/3R) — every honest slice negative gross
  AND net; advice's own direction backwards (strong rs_6m = worst, gross −0.187; weak rs_6m least-bad).

**LET-IT-RUN exit tested (`run_letrun.py`, Ben asked "different TP / let 'em run?"):** replaced the
fixed +2R target with a chandelier trail (2.5–3×ATR, 60–120d hold), same arm + same initial 1×ATR
stop, gated vs matched null. Does NOT rescue it — slightly WORSE than the fixed target. All configs:
gated net ~−0.32 (median ~−1.12), gross ~−0.17, vs null net ~−0.23; net delta>0 in only 3/10 years;
ex-2020 ~−0.34; drop-top-1% gross collapses to ~−0.26. The trail gives back open profit on the many
pop-then-fade trades; the right tail isn't fat enough to cover the ~70% trailed out near −1R. (Fixed
targets 1/1.5/2/3R were already tested by the steelman — all negative.) Exit choice does not matter;
the entry has no edge.

**Bug found + fixed (verdict-neutral):** the steelman found `regime_up`/`spy_ret60` dead-zero and
`rs_6m` byte-identical to `ret_6m` — `load_universe()` CS-only filter dropped SPY (an ETF). Fixed
(SPY kept through the filter). Re-ran build/backtest/ML with a working regime + relative-strength:
scorecard top-decile −0.264 (was −0.307), ML rank-IC +0.077, top-decile OOS netR −0.200, **still 0/8
years positive**, ex-2020 −0.241, drop-top-1% −0.96. **Verdict unchanged: DEAD.**
