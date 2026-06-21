# Combined research synthesis — two independent passes

Inputs: Claude deep-research harness (`deep_research_findings.md`, adversarially fact-checked) +
GPT-5.5 Research Pro (`gpt_pass_extracted.txt`). They STRONGLY corroborate; GPT filled the 3 RQs
the harness left open (TSFMs, labeling, breakdown detection).

## Agreed by BOTH (highest confidence — bank these)
- Short-horizon, LAGGED, not contemporaneous (~event-time / ~2 avg price changes, not 15–60 min).
- Cross-asset is a SMALL increment; own-asset OFI + a common factor dominate.
- Event-based OFI > trade volume; multi-level OFI beats top-of-book but overfits → Ridge/PCA/integrated.
- Micro-price = denoised fair value, NOT alpha.
- Stationarity dominates; OFI beats raw LOB (validates MBO-over-structure).
- GBDT = hard baseline; deep (TCN/DeepLOB) only where MBO adds OOS value; transformers not auto-better.
- Equities→futures transfer = #1 risk. High AUC ≠ tradeable.

## GPT's unique high-value additions
1. **Residualize vs the complex common-flow factor** (Capponi-Cont) — THE key construct. Signal =
   idiosyncratic pressure divergence `D_ij = u_i − β_ij·u_j(t−τ_ij)`, `u_i = z_i − λ_i·f`, τ via
   Hayashi-Yoshida. Without it: "measuring the same complex-wide shove twice."
2. **Replenishment/resiliency asymmetry** (Large; Lo-Hall) = the user's "one holds while the other runs,"
   literature-backed. + hidden-liquidity/iceberg asymmetry (vs latent reserve, not visible).
3. **TSFMs (RQ5):** off-the-shelf poor zero-shot+fine-tuned on finance; only from-scratch financial
   pretraining gains (arXiv:2511.18578). Auxiliary baselines only, on regular derived series, never raw MBO.
4. **Label (RQ6):** first-touch triple-barrier; upper barrier = ex-ante liquidity objective (prev-session
   VP / current POC-from-flow-so-far / microprice zone), frozen at decision time. Bar-high/low TOO CRUDE
   → tick/event-path labeling mandatory. Meta-labeling filters a meritful primary only.
5. **Breakdown gate (RQ7):** qualify w/ Gregory-Hansen (cointegration w/ breaks); monitor w/ Wagner-Wied +
   BOCPD/CUSUM/MOSUM on residual, hedge ratio, lead-lag, idio-flow variance.
6. **7 futures-specific OOS killers:** async-clock fake lead-lag (Hayashi-Yoshida not minute bars);
   common-flow-as-divergence; CME queue/matching semantics (FIFO vs pro-rata); hidden/implied liquidity;
   intraday nonstationarity (settlement/news); roll/venue migration; execution asymmetry ("fill model is
   part of the alpha model").

## One tension
GPT cites Capponi-Cont "cross-impact <1% of impact"; the harness voted that exact figure DOWN (unverified).
Agree on "small"; disagree on the precise number → treat "small" as solid, "<1%" as one unverified datapoint.

## Convergent blueprint (both, independently)
Event-time, multi-level, DEPTH-NORMALIZED local pressure → strip complex common-flow factor →
Hayashi-Yoshida lag-align → predict OBJECTIVE RESOLUTION (tick/event-path triple-barrier), not direction →
gate on cointegration + parameter stability. GBDT baseline first; everything guilty until it beats it after costs.
