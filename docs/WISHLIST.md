# Wishlist — improvements & new ideas

Compiled overnight 2026-04-30. Ben asked for: improvements to existing surfaces + new things to build, and specifically for thoughts on a more sophisticated research tab/workflow.

Ranked roughly by impact-to-effort. Pick the ones that feel right.

---

## Highest-leverage adds

### 1. Research workspace (your gut)
**Status:** new tab. **Effort:** large (1-2 weeks).

A dedicated `/research` route that's *not* about running backtests. It's about thinking out loud, tracking what you've tried, and using AI as an actual research partner instead of just chat. Shape:

- **Hypothesis tracker** — record what you *think* the strategy does ("I expect long entries on Monday opens to outperform"), tag with status (untested / running / confirmed / rejected), and link to the backtest config that would test it. Closes the "I had this idea three weeks ago and forgot" loop.
- **Decision log** — "I changed the FVG threshold from 0.4 to 0.6 because run #14 showed weak edges below 0.5." Each entry links to before/after backtest IDs. Becomes a permanent history of every choice that shaped a strategy. Useful when training the model — labels become "Ben thought this was a good change."
- **Question queue** — backlog of "I should test X" entries. Drag-drop into a sequenced experiment plan.
- **AI research assistant** — Claude or Codex with *tools*: ability to query the database, run a backtest with config X, fetch a metric, and report findings inline in a notebook-style log. Different from the current per-strategy chat: this one can DO things, not just talk. Stage 3 schema's `section` column already supports a "research" thread.
- **Saved research notebooks** — lightweight Markdown + embedded backtest results. Looks like a long Notion page; behaves like a journal entry.

The pitch: today you research by running backtests and forgetting the context. With this, every research session leaves a paper trail that compounds.

### 2. ML training pipeline prep
**Status:** new infra + small UI. **Effort:** medium (3-5 days).

You've said you want to train your own model on the RTX 6000 Blackwell when it arrives. This sets up the data pipeline now so you're ready when the hardware lands.

- **Trade feature exporter** — backend service that joins every DB trade with the feature values that would have been computed at entry, dumps to a parquet file ready for ingest into PyTorch / sklearn / whatever.
- **Manual labeling UI** — for any historical trade, click "good entry / bad entry / unsure" and persist the label. Builds a supervised-learning dataset incrementally.
- **Auto-export per strategy** — one-click "give me the training set for this strategy" — trades + features + outcomes + your manual labels.
- **Feature schema versioning** — when you add a feature to the composable library, all training datasets become aware of the new column.

You'd then unblock: "train a classifier on my labeled trades to predict trade quality" without any extra plumbing.

### 3. Walk-forward analysis surface
**Status:** new sub-page on the backtest workspace. **Effort:** medium (3 days).

Standard quant practice; not in the app yet. Splits a backtest's date range into N windows, runs the strategy on each, reports in-sample vs out-of-sample metrics. Catches overfitting before you ship to live.

UI: pick a strategy, set window size (e.g. 90 days), set step size, hit "run walk-forward." Get back: a chart of metric stability over time + a clear "is this strategy degrading?" signal.

This would have caught the trusted-strategy lookahead bias months earlier.

---

## Improvements to existing surfaces

### Backtest workspace
- **Per-strategy engine settings persistence** — currently localStorage global; should be per-strategy so different plugins have different defaults remembered.
- **"Re-run with last params" quick button** — saves typing for the iterate-fast loop.
- **Param sweep on the runner** — pick one param (e.g. `min_co_score`), set range, get N runs comparing the metric you care about.
- **Trade entry heatmap** — time-of-day × day-of-week grid showing where this strategy actually trades. Catches "I'm only trading at the open and didn't realize."
- **Bring `/backtests/compare` into the workspace** — currently a separate global route; A/B compare belongs *next to* the run history.

### Replay
- **Feature-value tooltip on entry click** — "this trade fired because: prior_level_sweep=true, decisive_close body_pct=0.72, vol_regime=not_low." Closes the "why did this trigger" question without re-reading code.
- **TBBO tick zoom-in** — the global `/trade-replay` already has the tick chart; embed it as a toggle on the replay page.
- **Step-through synchronization** — clicking a trade in the trade list scrolls the chart; scrolling the chart highlights the trade list row.

### Prop-sim
- **Confidence sub-score explanations** — you compute 7 sub-scores but the UI shows them as numbers. Each should have a tooltip ("Sampling method quality: how representative is the bootstrap of unseen days").
- **Firm-rule sweep** — pick a trade pool, sweep all firms with the same pool, get a "best firm for this strategy" leaderboard.
- **Drawdown trajectory band** — fan chart of equity over the eval period, p10/p50/p90.
- **"Will I pass before I run out of time"** — Monte Carlo over the eval-period clock too, not just trade outcomes.

### Drift monitor
- **More signals** — currently win-rate + entry-time. Add R-distribution drift, exit-reason drift, hour-of-day drift, day-of-week drift.
- **Drift history chart** — daily snapshot, render trend over time. "Has it always been WARN, or did it just turn?"
- **Auto-alert when drift transitions to WARN** — webhook / email / desktop notification.
- **Drift-vs-volume overlay** — was the recent week LOW volume, in which case "drift" is just noise?

### Composable visual builder
- **Recipe templates** — "save this recipe as a template" to share between strategies. Bootstraps new strategies fast.
- **Visual entry preview** — pick a recent day, render where this recipe *would have* fired on that chart, before you run a full backtest. Tight feedback loop.
- **Param sweep on a feature** — slider over a feature's threshold, live-update entry count + win rate as you drag.

### Strategies grid
- **Sparkline per card** — last 30 runs equity, gives the strategy card more glance-information.
- **Sort + filter** — sort by net_r, win_rate, max_dd; filter by status, plugin, tag.
- **Visual diff** — pick two strategy cards, see side-by-side comparison.

### Live monitoring
- **Live tick tape** — TBBO data is already being collected; render a small tick stream so you SEE the bot has fresh data.
- **Heartbeat visualization** — green/yellow/red over the last hour.
- **Alert when bot stops emitting heartbeats** — already detectable by the silent-failure rule, but currently quiet.

---

## Smaller new surfaces

### Mistake tracker
Tag a trade as "shouldn't have happened" with a reason. Filter for mistakes; the tags become labels for your future ML model. Pairs with #2 above.

### Position sizing simulator
Replay a finished backtest with different sizing rules (Kelly, fixed-fractional, vol-targeted). See how each sizing changes equity + drawdown.

### Live trade reconciliation
Daily auto-job comparing live trades to what the backtest engine would've produced for the same bars. Surfaces slippage, missed entries, stop-drift the moment they happen — not after the divergence has compounded.

### Data quality dashboard
- Missing days per symbol
- Bar gaps (time discontinuities)
- Last-trade-time per symbol
- VWAP NaN density per source

A page you only visit when something feels off; saves the "is my data real" anxiety.

---

## Things to deliberately *not* do (yet)

- **No-code strategy DSL** — the visual builder is good enough; a DSL is over-engineering until you have 10 strategies.
- **Multi-account portfolio simulator** — until you have ≥3 live strategies, premature.
- **Cloud / multi-user** — local-first is a feature.
- **Web app version** — Tauri is fine.
- **Real-time alerts via SMS / push** — you check the desktop app daily; pager-grade alerting isn't needed.

---

## My honest top 3

If forced to pick what to build next:

1. **Research workspace (#1)** — biggest pay-off. Compounds every session. Sets you up to remember what you've tried.
2. **Walk-forward analysis (#3)** — would've caught the trusted lookahead. Cheap insurance against future "looks great, doesn't replicate" mistakes.
3. **ML training pipeline prep (#2)** — long lead time before the GPU lands; no reason not to start the data side now.

Everything else is nice-to-have.
