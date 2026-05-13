# Morning Report — 2026-05-08

## What was built overnight

**Milestone #1 of the research-lab roadmap shipped: labeled trade-outcomes dataset v1.**

This is the spine. Every future ML model in the trading research lab — setup-quality classifier, outcome probability, regime, anomaly — trains on this kind of dataset. Tonight we built the pipeline and backfilled it from existing logs. The dataset is small right now, but the plumbing is the point.

## Output

```
D:\data\research\labeled_outcomes\trades_v1.parquet      (19 rows × 47 cols)
D:\data\research\labeled_outcomes\trades_v1_summary.json
```

Builder script:

```
C:\Users\benbr\BacktestStation\backend\app\research\build_labeled_outcomes.py
```

Re-run anytime (idempotent — overwrites in place):

```powershell
cd C:\Users\benbr\BacktestStation\backend
python -m app.research.build_labeled_outcomes
python -m app.research.build_labeled_outcomes --dry-run   # preview only
```

## What's in the dataset

**Sources:**
- `pre10_paper_log.jsonl` — 5 paired pre10 paper trades (one duplicate replay deduped)
- `trades.jsonl` — 14 FractalAMD live trades

**Schema (47 cols):**

- **Identity**: `signal_id`, `source` (paper/live), `strategy` (pre10_vp_continuation / fractalamd), `symbol`, `ts_signal_utc`, `ts_signal_et`, `date_et`, `minute_of_day_et`, `day_of_week`
- **Trade params**: `side`, `entry_price`, `stop_price`, `target_price`, `risk_pts`, `contracts`
- **Strategy-specific** (NaN where N/A): `p_up_router`, `router_passed`, `trigger`, `exit_side`, `target_r_mode` (pre10); `rof_score` (FractalAMD)
- **Outcome labels**: `exit_reason` (SL/TP/TIMEOUT/TRAIL_STOP), `exit_price`, `realized_r`, `pnl_gross`, `pnl_net`, `held_minutes`, `mfe_pts`, `mae_pts`, `n_trail_moves`
- **Quality bucket** (A/B/C/D from realized_r): A ≥ 1.5R, B ≥ 0.5R, C ≥ -0.5R, D < -0.5R
- **Bar-context features** (no-leak — strict ≤ signal_ts): `bar_{open,high,low,close,volume}`, `atr_5`, `atr_15`, `prior_5bar_return_pts`, `prior_15bar_return_pts`, `range_from_rth_open_pts`, `session_high_at_signal`, `session_low_at_signal`, `distance_from_session_{high,low}_pts`, `rth_volume_to_signal`
- **Provenance**: `bars_available` flag (true/false)

**Summary stats:**

| Metric | Value |
|---|---|
| Total rows | 19 |
| Date range | 2026-04-09 → 2026-05-07 |
| Bars available | 9 |
| Bars missing (outside parquet window) | 10 |
| Quality A/B/C/D | 6 / 2 / 1 / 10 |
| Win rate | 47.4% |
| Expectancy (R) overall | 0.49 |
| Expectancy (R) paper | 0.62 |
| Expectancy (R) live | 0.45 |

## Known gaps + caveats

1. **Dataset is too small to train anything.** 19 rows is pipeline validation, not a training set. Models need hundreds-to-thousands of labeled trades. The realistic timeline: 6–12 months of live + paper trades, OR augment with backtest-generated trades from `pre10_vp_continuation_backtest.py` running over the 2022–2025 historical bar archive.

2. **Bar context missing for 10 rows.** The 1m NQ parquet at `C:\Fractal-AMD\data\raw\NQ_ohlcv-1m_2026.parquet` only covers 2026-04-27 to 2026-05-06. Trades before 04-27 (the April 9–24 FractalAMD trades) and on 05-07 have NaN bar features. The MBP-1 raw DBN files at `D:\data\raw\databento\mbp-1\symbol=NQ.c.0\` go back to 2026-03-01, so this gap is closeable — needs a DBN→1m aggregator to extend the parquet.

3. **pre10 features-at-signal-time are thin in the log.** The paper log records `p_up_router`, `router_passed`, `trigger`, `exit_side`, `target_r_mode` — but the *richer* features the signal engine actually computes (developing VP shape, distance outside VA, profile bar count, etc.) aren't logged. To get them into the dataset, either:
    - Add a single log line at signal emission with the full feature dict (cheap, future-only)
    - Replay the strategy over 1m bars at each historical signal time (expensive, retroactive)

4. **Schema heterogeneity.** Pre10 paper and FractalAMD live trades have different feature universes — `p_up_router` is paper-only, `rof_score` is FractalAMD-only. The unified schema fills the other side with NaN. Fine for now; if/when pre10 goes live and FractalAMD stays shelved, we converge to one schema.

5. **No backtest-derived trades yet.** `pre10_vp_continuation_backtest.py` over 2022–2025 history would produce hundreds of synthetic trades. Adding a third source loader to `build_labeled_outcomes.py` is a one-evening task.

## Next steps (priority order)

1. **Add per-signal feature log line in pre10_live_runner.py.** Single JSONL line at signal emission with the full feature dict the engine sees. This gives every future trade rich features without replay. Cheapest, highest-leverage next step.

2. **Backtest-generated rows.** Run `pre10_vp_continuation_backtest.py` over `NQ.c.0_ohlcv-1m_2022_2025.parquet` (when that file is locally available — it isn't on this PC, only on the main PC according to backtest script default path), then add a `build_backtest_rows()` loader to the script.

3. **MBP-1 → 1m aggregator** to fill the 10 missing-bar trades. `D:\data\raw\databento\mbp-1\symbol=NQ.c.0\date=YYYY-MM-DD\*.dbn` → 1m OHLCV parquet. Databento Python SDK has `dbn` reader.

4. **Don't train a model yet.** With 19 rows we'd just memorize the dataset. Wait until we have at least 200+ labeled trades from a combination of (a) live + paper accumulation and (b) backtest augmentation.

5. **Shadow-mode plumbing (parallel track).** Once we DO train a model, we need infrastructure to run it live alongside Pre10 with no execution authority — log predictions to a sibling parquet, compare predictions vs realized outcomes weeks later. This unlocks honest validation.

## Roadmap context

This dataset is **milestone 1 of 5** for the local trading research lab (see `project_research_lab_roadmap.md` in user memory). Remaining milestones (all GPU-agnostic, doable on current hardware):

- Feature store with leakage discipline ← partially in place via this script's strict no-leak feature computation
- Reusable walk-forward harness
- Shadow-mode plumbing
- Anomaly telemetry

Hardware (Blackwell GPU + L3 data) remains gated on consistent TPT funded payouts. Nothing in this milestone needs new hardware.

## Validation

```python
import pandas as pd
df = pd.read_parquet(r'D:\data\research\labeled_outcomes\trades_v1.parquet')
assert df.shape == (19, 47)
assert df['signal_id'].is_unique
assert df['ts_signal_utc'].is_monotonic_increasing
```

All pass.

---

Built by Claude overnight 2026-05-08 ~05:38 UTC.
