# Forward Drift Monitor — design starting points

> Status (2026-04-24): **design notes for Ben + Husky to review**, not a build spec yet. Don't write code from this — discuss first, then write a real plan.

## What we're trying to answer

When a strategy goes live, how do we know early — *before* burning real capital — that it's not behaving like the backtest predicted?

This is the "operational" half of BacktestStation. The research half (notes, experiments, prompt generator) helps us *decide* to go live. The drift monitor is what watches the live run vs the backtest baseline and screams when they diverge.

## The data we have to compare

| Source | What it gives us | When |
|---|---|---|
| Live signals | what the live bot decided to do (entries, exits, sizes, fills) | now-ish, written by the bot to disk + read by `/monitor` |
| Live ticks (TBBO) | what the market did | now, via `app.ingest.live` |
| Backtest run + autopsy | what we *expected* live to look like | imported, in BacktestStation DB |

Joining these gives us "live's actual behavior vs the backtest baseline's expected distribution."

## Five drift signals worth considering

Pick 2-3 to start. More signals = more noise = more false alarms = ignored alerts. Cardinality matters.

### 1. Win-rate drift (most obvious)
Compare rolling live WR vs backtest WR over the last N completed trades.
- Threshold: "live WR is more than X% below backtest WR over last N trades" → alert
- Tunable: N (window), X (deviation), maybe regime-aware (different threshold for high-vol vs low-vol days)
- **Pro:** simple, easily explained, you'll feel it in your gut anyway
- **Con:** lagging by N trades — useless on day 1 of a strategy

### 2. Entry-time drift
Backtest distributes entries across an expected hour-bucket distribution. Live should match.
- Compare hourly entry counts via χ² or KS test against the backtest distribution
- **Why this is real:** Fractal AMD's previous live-bot bug (per memory) was that live was firing in pre-RTH hours that backtest never traded. A simple hour-bucket histogram would have caught it on day 2.
- **Pro:** catches structural bugs fast (5-10 trades) before WR has any signal
- **Con:** requires the backtest to have stable hour patterns

### 3. Trade-frequency drift
Live takes wildly more or fewer trades per day than backtest expected.
- Threshold: "live trades/day deviates by > Y% from backtest mean over last K days"
- **Pro:** catches "gate accidentally too loose / tight" failures early
- **Con:** sensitive to market-condition shifts (low-vol days reduce frequency naturally)

### 4. Slippage / fill drift
Live fills are systematically worse than backtest assumptions.
- For each live entry: compare actual entry price to the price the backtest engine would have assumed for the same setup
- **Pro:** catches broker/connectivity/data quality issues
- **Con:** requires the engine to be running on the same data live saw — can't do until the backtest engine is in-app

### 5. P&L distribution drift (statistical)
Run a KS test or Anderson-Darling on the live R-multiple distribution vs the backtest distribution.
- Statistically rigorous, captures shape changes (not just mean)
- **Pro:** gold standard once you have N≥30 live trades
- **Con:** N≥30 takes weeks; useless for fast warning

## Recommendation for v1

Build #1 (WR) and #2 (entry-time) first. Both can run with TBBO data and run-level bot output:

- **WR drift:** rolling 20-trade window, alert if live WR < backtest WR − 15 percentage points
- **Entry-time drift:** χ² test of live hourly buckets vs backtest hourly buckets, alert if p < 0.05 over rolling 10 trades

Skip #3, #4, #5 until you have:
- More data (#5 needs ≥30 trades)
- The in-app engine (#4 needs to replay backtest fills against the same ticks)

## Interaction shape (UI)

Add to existing `/monitor` page below the IngesterStatusPanel + LiveStatusView. Two new panels:

```
┌─────────────────────────────────────────┐
│  Drift: WR                              │
│                                         │
│  Live WR   42.0% (last 20)              │
│  Expected  56.0% ± 8% (backtest)        │
│  Deviation -14.0% ▼  [WARN]             │
│                                         │
│  ────────────────────────────────       │
│  Sparkline of rolling WR last 50 trades │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Drift: Entry-hour distribution         │
│                                         │
│  09 ─────────────                       │
│  10 ████████████          live          │
│  11 ████░░░░               expected     │
│  12 ░░                                  │
│  13 ░░                                  │
│  14 ░░░░░░                              │
│                                         │
│  χ² p-value: 0.003  [WARN]              │
└─────────────────────────────────────────┘
```

Status states: `OK` (green) / `WATCH` (amber) / `WARN` (red).

## Where the comparison data comes from

Live side:
- Live signals/trades read from the bot's output (Rithmic CSVs per the audit). Need a small ingester that reads new rows and inserts as `BacktestRun` rows with `source="live"` so the existing UI can display them. This is its own small chunk of work.

Backtest side:
- Pick a "baseline run" per strategy version (the run the user explicitly designated as the live-trading expectation). Maybe a flag on `BacktestRun` or a single FK on `StrategyVersion`.
- All drift comparisons are against that baseline.

## What's blocked on what

```
                    ┌───────────────────────────────────┐
                    │   parquet mirror running on data  │
                    └────────────┬──────────────────────┘
                                 │  (already done)
                                 ▼
                    ┌───────────────────────────────────┐
                    │   live signals/trades ingester    │  <- needed first
                    │   reads bot's Rithmic CSVs into   │
                    │   BacktestRun(source="live")      │
                    └────────────┬──────────────────────┘
                                 │
                                 ▼
                    ┌───────────────────────────────────┐
                    │   "designate baseline" UX         │  <- small new feature
                    │   per StrategyVersion             │
                    └────────────┬──────────────────────┘
                                 │
                                 ▼
                    ┌───────────────────────────────────┐
                    │   drift comparisons (#1, #2)      │  <- the actual work
                    │   compute on demand or cached     │
                    └────────────┬──────────────────────┘
                                 │
                                 ▼
                    ┌───────────────────────────────────┐
                    │   /monitor panels + alerts        │
                    └───────────────────────────────────┘
```

So before we can build the drift monitor itself, we need:
- Live trade ingester (~1-2 hours, reads existing Rithmic CSVs)
- Baseline-designation UI on the strategy dossier (~1 hour)
- THEN the drift logic (~3-4 hours total for v1 with WR + entry-time)

Total: a real 1-2 day chunk, not a 2-hour drop-in.

## Open questions for Ben + Husky

1. **What's an "alert"?** Just a UI badge? An email/SMS? A Discord webhook? A sound? Pick one — probably start with UI-only and add channels later.
2. **Per-strategy or global thresholds?** Different strategies have different expected variance.
3. **Pause-on-drift, or just notify?** Some firms auto-flat positions on drift — ours probably should not in v1.
4. **What's the baseline?** "The most recent fully-backtested run on the live version" is reasonable but worth confirming.
5. **Husky's prop-firm simulator overlap.** That work also involves rule-violation detection on live behavior — make sure drift alerts and prop-firm rule alerts don't end up duplicating each other. Probably they share a common "alerts" table eventually.

## Suggested next step

After Husky's prop-simulator merge lands, sit down for 30 min and pick:
- One signal (WR or entry-time)
- One alert channel (UI only)
- One baseline source (most-recent run)

Then I plan the build out of those concrete picks. Don't try to spec all 5 signals at once.
