# btc_model_v0 — the real modeling program (draft pending Ben's data manifest)

Question upgrade from btc_edge_v0: not "does rule X work" but **"is there ANY learnable
predictive structure in BTC at hours-to-days horizons, extractable by a properly
validated model, net of measured costs?"** A strong model scoring ~zero OOS is evidence
of absence; a model scoring positive gives us something to distill into a strategy.

## The four pillars ("good modeling" = all four, not just a big model)

### 1. Feature space — wide and mechanism-spanning (target 150-300 features)
- **Price/trend ladder:** returns at 1h/4h/1d/3d/10d/30d, MA-state ladder, drawdown
  depth/duration, distance-from-high, breakout ages
- **Vol structure:** realized vol ladder + vol-of-vol + vol regime (the one thing we
  KNOW forecasts, rho 0.32), range ratios, gap stats
- **Microstructure dailies (from 1m bars, free):** volume profile of the day, trade
  intensity, Amihud illiquidity, close-location value, session-relative volume
- **Calendar:** hour/day/week/month, session flags, CME expiry/roll distance, the
  unconfirmed Monday effect lives here
- **Cross-asset state (bars already in the lake):** NQ/ES correlation + beta regime,
  DXY proxy via 6E, GC co-movement, risk-on/off composite, relative strength
- **From Ben's incoming downloads (manifest TBD):** spot/perp data -> FUNDING RATE +
  CME-spot basis (the two documented institutional-grade BTC signals); options data ->
  IV level/skew/term structure, put-call flow (timing rules per options constitution:
  prior-day only unless intraday-stamped)

### 2. Labels — money-shaped, not direction-shaped
Triple-barrier at measured-cost-aware geometry (e.g. +2R/-1R at vol-scaled distances,
24h-72h horizons), stop-aware first-touch resolution, plus a pure next-k-return
regression target as the sanity twin. Label horizon ladder: 4h / 24h / 72h.
Rule: judged on replayed net PnL at the 60-pt wall, never on AUC alone (label != money).

### 3. Validation — the part that separates this from chart-pattern ML graveyards
- Purged walk-forward: train/test split on trading days, embargo >= max label horizon
- feature_window <= decision_time asserted at build time (the constitution, rule 5)
- **Negative controls run FIRST, every refit:** shuffled-target must score ~0 and
  random-feature-subset must match noise — if controls score, the harness leaks, stop
- Ablation ruler per feature block (which mechanism carries any signal found)
- Per-trade both-sides expectancy (not long-biased equity curves — the btc_edge lesson:
  drift wears costumes)

### 4. Confirmation — honest, given what's already been seen
DISCLOSED CONTAMINATION: the 2025-06->2026-06 year was unsealed by btc_edge_v0's
holdout shot (we know it was a -47% bear). Therefore:
- Design + walk-forward on 2017-12 -> 2026-06 with the WF folds as the evidence
- The TRUE confirmation is FORWARD data only: the model freezes, new calendar accrues
  (Ben's ongoing downloads), evaluation on data that did not exist at freeze time.
  No backward holdout can be honest anymore on this asset for this researcher.

## Status
- [ ] Ben's data manifest: what exactly is downloading (source, instrument, granularity,
      history depth)? Spot? Perps+funding? Deribit options? More CME depth?
- [ ] Harness skeleton (purged WF + controls + cost-judged eval) — buildable now on
      bars already on disk; feature blocks slot in as data lands
- Infrastructure to reuse: wf_gate pattern (mira), hold_break_model ablation ruler
  (market_state), block bootstraps, sizing_v1 money layer downstream
