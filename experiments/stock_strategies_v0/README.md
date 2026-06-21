# stock_strategies_v0 — equities research line

Started 2026-06-18. A new research line for **trading stocks** — deliberately separate
from the futures/options work that fills the rest of `experiments/`. Two strategies,
each with a detailed source document, land here.

## Status

- **Both strategy docs ingested + scaffolded 2026-06-18** (text + diagrams). No code yet.
- Branch: `ben/stock-strategies`.
- Working mode (Ben): capture both, keep planning light, deep-dive only when one is chosen
  to focus on.

## The two strategies

| # | Folder | What | Claimed stats |
|---|---|---|---|
| 1 | [momentum_trend_v0](momentum_trend_v0/README.md) | High Tight Flag: thrust → tight base into 10/20MA → volume breakout near HOD | ~30% win, 3–4:1 R, ~20% DD |
| 2 | [earnings_gap_v0](earnings_gap_v0/README.md) | Earnings gap-up continuation: long base → >7.5% gap above resistance on volume | ~40% win, 3:1 R, ~14% DD |

Both come from the same source (discord.gg/sartrading) and **share an entire execution
shell** — identical 1-min entry trigger, stop = LOD, 1/2 partial → breakeven at day +3–5,
trail/exit on close below MA10/20, and 1%/2% sizing with 30% max exposure. They differ
**only in the setup detector** (technical flag breakout vs. earnings gap-up). The earnings
doc explicitly says to run the two together.

**Architecture implication:** build **one shared execution + sizing + honest-fill engine**
and **two detectors** on top of it, not two separate backtesters. The discretion in both
becomes shared models (§ below).

## Modeling the discretion (Ben's direction)

Replace hand-coded judgment with learned models, shared across both strategies:
- **Strength/weakness** — cross-sectional relative-strength ranking of sectors + stocks.
- **Cycle/rotation** — market-cycle phase + which sectors are receiving rotation.
- **Setup-quality / gap-continuation** — learns the "is this a good one?" score
  (5-star flag quality; good-gap vs. fade) → calibrated P(follow-through) for an EV layer.

See each strategy's SPEC §6 / §6.5 for detail.

## Data on hand (no pull needed to start)

| Asset | What | Coverage | Location |
|---|---|---|---|
| 133 stocks (NDX-100+) | EOD bars | 2023-06-01 → 2026-06-12 | `D:\data\processed\stocks\eod\<T>.parquet` |
| same 133 | 1-minute bars | 2023-06-01 → 2026-06-12 | `D:\data\processed\stocks\m1\<T>.parquet` |

- Cols: EOD `date,open,high,low,close,volume`; 1m adds `ts_et,ms_of_day` (ET market clock).
- The 2023-06 floor is the ThetaData equities-sub start, not a gap.
- Need more tickers / longer history / a different bar size? `pull_stock_bars.py` in
  `experiments/options_signals_v0/`. Stock options walls: `build_walls_stock.py` there too.
- Run Python with `backend\.venv\Scripts\python.exe` (has pandas/lightgbm; `.venv-ml` does not).

## Per-strategy doc convention

Each strategy subfolder mirrors the discipline used elsewhere in this repo
(see `experiments/fuhhhhh/` for the reference shape):

| File | What |
|---|---|
| `README.md` | What the strategy is, the question it answers, status. |
| `SPEC.md` | The constitution: hypothesis, universe/window, hard rules, controls, **verdict discipline**. Binding — tests that violate it don't count. |
| `LEDGER.md` | Every test's construction, result, verdict, diagnosis. Append-only. |
| `DATA.md` | Concrete local data inventory + loaders the strategy uses (if it differs from above). |
| code | Loaders, features, labels, walk-forward eval — kept causal by construction. |

## Carry-over rules that still apply (equities edition)

These repo rules are asset-agnostic and hold here:

- **No lookahead.** Features at decision time t only; assert it at build time.
- **Honest fills.** Stop-vs-target ties → stop wins. Model slippage + commission
  explicitly (equities: per-share/ticket commission, spread, borrow for shorts).
- **No random splits.** Purged/embargoed walk-forward; mandatory shuffled-target control.
- **Realized return is the objective**, not accuracy/AUC.
- **Replication before belief.** Single-window lifts are presumed noise.
- **Results as Parquet, never pickle.**

## What's different from the futures lines (flag when scoping each strategy)

- No prop-firm risk shell / payout model (that's futures-only — `prop_model_v0`).
- Equities frictions instead: PDT rule, locate/borrow + hard-to-borrow fees for shorts,
  per-share commission, wider/again-different spreads, halts, splits/dividends adjustment.
- Overnight gap risk is real (futures lines were day-flat) — hold horizon must be explicit.
- Survivorship/de-listing bias on any cross-sectional universe claim.

---

*Drop the strategy docs and I'll scaffold each one into its subfolder per the table above.*
