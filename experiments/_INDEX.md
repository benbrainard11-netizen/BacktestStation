# experiments/ — research index

The master map of every research line + its verdict. **Last rebuilt 2026-06-21.**

This lab's rule: **the repo lives, hypotheses die.** Most lines below are honest NULLs — kept on
purpose so we don't re-chase them. The few live ones are at the top.

- **Data** lives in the single home `D:\data\` and is reached through `data_io.py` (see `docs/DATA_MANIFEST.md`).
- **Don't physically move active lines** — they cross-reference each other by hard-coded path (~40 files
  read `experiments\*\out\walls_*` etc.). This index *is* the organization; relocating dirs breaks imports.
- Truly-dead standalone lines (nothing references them) can be moved to `_archive/`.

---

## 🟢 Active — what we're actually building (the "models")
| dir | what | state |
|---|---|---|
| `market_state_options_v0` | options-regime **market-state CONTEXT** for manual prop trading (decision-support, not a signal) | **ACTIVE.** gamma→RANGE/vol regime is real + additive; gamma→DIRECTION is NULL (locked guardrail). Honest role = sizing/regime context |
| `prop_model_v0` | the prop business as a 3-layer model (firm rules → eval EV → vehicle) | **ACTIVE lane.** Firm audit done w/ citations; eval-EV calc + bankroll risk-of-ruin sim |
| `sizing_v1` | prop-firm sizing, fleet sims, Mira exit replays (the money layer) | **ACTIVE/validated.** Confirmed Mira +0.44R, fragility-tested; the path from edge → contracts |
| `mira_gate_harness` | robustness harness for the Mira reclaim + drift×zone MBP-1 edge | **load-bearing.** 6-mo robustness established; gamma-wall family probed (NDX gap) |
| `fuhhhhh` | options-informed **intraday ES** objective model (growable, model-first) | **iterating.** v3 event-triggered (sweep/SMT→wall→EOD); sealed holdout preserved. Also hosts canonical walls builders |

## ✅ Validated edges (real, survived honest testing)
| dir | what | verdict |
|---|---|---|
| `xsectional_rv_v0` | cross-asset cointegration RV scan | ✅ **the RV edge origin** — energy/grains/curve cointegration holds OOS |
| `energy_rv_v0` | energy + diversified RV book as a runnable bot | ✅ **deployable** — OOS Sharpe +1.44 (CL/BZ +1.54). The lab's one robust edge — but **MULTI-DAY** (killed by prop flat-by-close) |
| `mira_upgraded_v0` | SMT sweep-reclaim, continuous-magnitude gate (read-only of Mira live) | ✅ **generalizes** across the index complex (+0.46..0.75R, tick-fill-verified). Separate construction from Mira-live's MBO edge |
| `edge_hunt_v0` | TSMOM + energy-RV re-confirm | energy ✅ confirmed; TSMOM 🟡 parked (drought) |

## 🔧 Infrastructure / inputs (load-bearing for the above)
| dir | what |
|---|---|
| `options_signals_v0` | the **gamma-walls + options DATA pipeline** (ThetaData → walls/GEX/panels). Regime gate itself was NULL, but the data infra is the durable asset — powers `market_state_options_v0` + the canonical walls now in `D:\data\processed\walls` |
| `sync_regime_v0` | builds `out/daily_returns.parquet` — the validated daily returns the RV work depends on |
| `asset_profiles_v0` | 26-asset behavioral profiles + routing + `out/clean_bars/` (the legacy-bar-artifact discovery) |

## ❌ Tested and DEAD (don't re-chase — kept for the record)
| dir | what | verdict |
|---|---|---|
| `breakout_ranker_v0` | sector-relative breakout + (+2R/-1R) ranker (from pasted advice) | ❌ **NULL** (2026-06-21) — worse than a random liquid day; negative even gross; 4-agent verified |
| `stock_strategies_v0` | the equities line (breakouts / RS / earnings / overnight) | ❌ breakouts DEAD, RS ties SPY, earnings thin; **overnight premium = the one unverified live lead** |
| `intraday_stocks_v0` | opening-drive / gap-continuation intraday stocks | ❌ DOWNGRADED — gap-continuation = 2020-COVID + microcap artifact (holdout preserved) |
| `stock_options_flow_v0` | single-stock dealer-gamma / options flow / earnings-convex | ❌ NULL (sealed-holdout, 4-agent KILL); convex-options = a regime bet |
| `mstr_gamma_v0` | MSTR own-gamma → direction/vol/walls | ❌ NULL across all hypotheses (walls inverted — momentum-amplifying) |
| `btc_edge_v0` | CME BTC anomaly screen (hours-to-days) | ❌ NULL — trend survivor = drift not alpha; minutes-scale dead (9-tick spread) |
| `btc_model_v0` | BTC ML modeling program (intraday + walk-forward) | ❌ BTC line is null (see `btc_edge_v0`); ML follow-on did not rescue it |
| `prop_futures_v0` | best CME instrument + day-flat intraday edge for prop | ❌ **FINAL: no robust OOS-validated deployable day-flat edge** (ORB + 5 families × 6 instruments) |
| `prop_rv_intraday_v0` | does the multi-day RV edge revert INTRADAY (day-flat)? | ❌ NULL — reversion causally real but cost-killed + doesn't generalize (17 pairs, 0 generalizers) |
| `index_internals_v0` | mega-cap breadth/divergence → predict NQ | ❌ NULL OOS (residual-IC −0.021). Now lives in the `index-stock-vol-alpha`/flowstate repo |
| `index_options_realized_vs_implied_v0` | SPX realized-vs-implied straddle audit | ❌ SHELVED — no pass; NDX replication inverted (multiple-comparisons noise) |
| `level_scalp_v0` | level-reaction scalp (touch atlas → maker execution physics) | ❌ NULL at registered spec — adverse selection + stop gap-through (−2.7t/fill); holdout never read |
| `orderflow_divergence_v0` | orderflow reversal/continuation/sweep-reclaim | ❌ artifacts/dead on clean MBP-1 bars |
| `phase_model_v0` | are consolidation/expansion phases forecastable? | vol ✅ forecastable, trendiness ❌ not |
| `tgif_v0` | TGIF + fractal expansion→reversion | ❌ null (noisy / beta) |
| `smt_ltf_bench` | does a better LTF cross-asset SMT definition add edge? | ❌ coverage-not-edge — keep adjacent-candle SMT (window/N-bar significantly worse) |

## 🅿️ Parked / inconclusive (revivable with a concrete consumer)
| dir | what | state |
|---|---|---|
| `prop_intraday_resolver_v0` | integration spine (resolver=market_state, governor=sizing) | PARKED — 2c NULL (OFI=vol proxy) + 2d inconclusive; revive only with a concrete consumer |
| `move_env_gate_v0` | move-environment gate study | see dir README (gate research; not promoted) |
| `orderflow_asset_discovery_v0` | which assets carry tradeable orderflow | see dir README / BUILD_PLAN |

## Reports
- `STRATEGY_REPORT_2026-06-02.md`, `OVERNIGHT_2026-06-02.md` — portfolio-state snapshots.
- Per-line detail lives in each dir's `README.md` / `LEDGER.md`. Cross-lab memory: `~/.claude/.../memory/MEMORY.md`.

---
*Maintenance: when a line gets a verdict, update its row here in the same session. A stale index is a bug.*
