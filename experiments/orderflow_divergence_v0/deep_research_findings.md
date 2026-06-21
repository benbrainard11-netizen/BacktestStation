# Deep-research findings — cross-asset orderflow-divergence thesis (2026)

Run via the Claude deep-research harness (fan-out web search → fetch → 3-vote adversarial
verification → cited synthesis). 24 sources, 114 claims, 25 verified (16 confirmed, 9 killed).

## Bottom line: thesis is REAL but the evidence reshapes the design two ways

**1. SHORT-HORIZON signal — minutes, not 15–60 min.** Cross-asset order-flow edge concentrates at
**~1–5 min, decays past 5–10 min** (Cont, Cucuringu & Zhang 2023, *Quant Finance* 23(10),
arXiv:2112.13213; corroborated by SPY/E-mini OFR WP 19-04 — dissipates in seconds). A 15–60 min
play has weak support. ⇒ fast/intraday/execution-adjacent model; converges with the live_engine/MBO
line; explains why the prior 15–60 min work was dead (alpha already decayed).

**2. Cross-asset is a small INCREMENT — own-asset OFI dominates.** Lagged cross-asset OFI *does*
improve return forecasts (3-0 confirmed), but the gain *over* own-asset OFI is real-but-small.
(The strong-standalone framing AND the "<1% of impact" dismissal were both killed.) Own-asset OFI
is the workhorse; cross-asset divergence is the enhancer, not the engine.

## Rock-solid (build on these)
- **OFI > trade volume** for short-horizon price change — Cont-Kukanov-Stoikov 2014 (arXiv:1011.6402),
  the most replicated microstructure result.
- **Multi-level OFI beats top-of-book** but naive deep levels OVERFIT (multicollinear); remedy =
  integrated/PCA OFI or Ridge, diminishing past ~4–5 levels (Xu-Gould-Howison arXiv:1907.06230;
  Cont-Cucuringu-Zhang). Deep-OFI gains are MBO-only (you have MBO on 4 symbols).
- **Micro-price (Stoikov 2018)** = standard imbalance→price estimator, BUT a denoised nowcast of the
  next mid, NOT tradeable alpha after costs. Feature, not signal.
- **Stationarity dominates** — OFI (stationary) beats raw LOB; simple models match complex ones
  (Kolm-Turiel-Westray 2023, *Math Finance*). Literature-validates the MBO-over-structure finding.
- **Order-flow alpha OOS R² ≈ 1–1.25%**, predicts ~2 price changes ahead; profitable only because
  the horizon is so short.
- **Tick size governs forecastability** — large-tick MCC ~0.29 vs small-tick ~0.11/near-random
  (Briola-Bartolucci-Aste 2025, arXiv:2403.09267). Edge concentrates in a few large-tick futures.
- **High AUC/F1 ≠ tradeable** (same paper) — transaction-aware eval needed. Validates the path-aware
  label + after-cost-OOS bar.
- **Architecture template:** cross-asset-OFI + Stock-Time attention blueprint (KOSPI-200, ICAIF'25,
  DOI 10.1145/3768292.3770432) — close to the asset/pair/global token design — but its "beats
  baselines" efficacy claim was KILLED (0-3) for non-equity settings. Design pattern only.

## Honest caveats
- 🔴 **Equities, not your futures.** Every high-confidence source is US/Korean equities. Cross-asset-
  class commodity/rates/index futures transfer is plausible but UNPROVEN — only your data answers it.
- 🔴 **Effect sizes tiny** (R²~1%); must clear after-cost/real-stop bar separately.
- 🔴 **Edge uneven** (large-tick only).
- 🟡 Most results are CONTEMPORANEOUS (partly mechanical); only lagged-cross-OFI is genuinely forecasting.

## Open (killed/unverified — for the GPT-5.5 Research Pro pass)
- **RQ5** pretrained TSFMs (Moirai/Chronos/TimesFM/TTM/Toto) on microstructure — no verified evidence.
- **RQ6** triple-barrier / meta-labeling / path-aware label design — open.
- **RQ7** real-time cointegration-breakdown detection — open.

Key sources: arXiv:2112.13213, 1011.6402, 1907.06230; Stoikov micro-price (SSRN 2970694); Kolm-Turiel-
Westray (mafi.12413); Briola-Bartolucci-Aste (arXiv:2403.09267); OFR WP 19-04; ICAIF'25 KOSPI blueprint.
