# experiments/ — index

Map of the live research lines + verdicts (as of 2026-06-02). Dead/empty stubs moved to `_archive/`.
Active lines are KEPT IN PLACE (they cross-reference each other by hardcoded path — don't move them).

## Active (in build)
| dir | what | status |
|---|---|---|
| `level_scalp_v0` | level-reaction scalp study: touch atlas → maker (queue-model) execution physics | ❌ **NULL at registered spec (2026-06-12)** — real gross reaction at ES/RTY levels, but adverse selection + stop gap-through eat it (−2.7t/fill net on honest MBO fills); holdout never read; keeper: retest/overshoot table, behind-you fill harness, constitution. Successor avenues documented in report/phase1_mode_a.md |

## Validated edges (real, survived honest testing)
| dir | what | verdict |
|---|---|---|
| `xsectional_rv_v0` | cross-asset cointegration RV scan | ✅ **the RV edge origin** — energy/grains/curve cointegration holds OOS |
| `energy_rv_v0` | energy + diversified RV book as a runnable bot | ✅ **deployable** — diversified book OOS Sharpe +1.44; CL/BZ +1.54; robust |
| `edge_hunt_v0` | TSMOM + energy-RV re-confirm | energy ✅ confirmed; TSMOM 🟡 parked (drought) |
| `sizing_v1` | prop-firm sizing, fleet sims, Mira exit replays | ✅ **the milk money-layer** — confirmed Mira +0.44R, fragility-tested |

## Infrastructure / inputs (load-bearing for the above)
| dir | what |
|---|---|
| `sync_regime_v0` | builds `out/daily_returns.parquet` — the VALIDATED daily returns the RV work depends on |
| `asset_profiles_v0` | 26-asset behavioral profiles + `out/clean_bars/` (the legacy-bar-artifact discovery lives here) |

## Tested and DEAD (don't re-chase — kept for the record)
| dir | what | verdict |
|---|---|---|
| `orderflow_divergence_v0` | orderflow reversal/continuation/sweep-reclaim | ❌ artifacts/dead on clean MBP-1 bars |
| `phase_model_v0` | are consolidation/expansion phases forecastable? | vol ✅ forecastable, trendiness ❌ not |
| `tgif_v0` | TGIF + fractal expansion→reversion | ❌ null (noisy / beta) |
| `options_signals_v0` | options/gamma (GEX) regime gate | ❌ regime gate null (5 cuts); GEX data + pipeline reusable |

## Reports
- `OVERNIGHT_2026-06-02.md`, `STRATEGY_REPORT_2026-06-02.md` — the current state of the portfolio.

## Confirm-before-archiving (left in place pending Ben — may be Mira/live-referenced)
`tsfm_milk_v0` (209 files), `mira_v*`, `mira_*`, `atlas_v0`, `mbo_features_v0`, `l3_features_v0`,
`db_backups`, `gpu_runs`, `orderflow_lgbm_probe_v0`, `risk_conditioner_v0`, `mbo_r2_backfill`, `bulk_pull_v2`.
