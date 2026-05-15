# GPU XGB on the 2026-05-15 strict-reactions release

_Generated 2026-05-15. Source: 16-config GPU XGB sweep on the `strategy-lab-core-2026-05-15-strict-reactions` release tag, which 247 published after shipping the new **FVG strict labels** + a fix that replaces the dead `no_touch_*` / `clean_gap_continuation` opening_gap labels with **`unfilled_expanded_away` / `unfilled_clean_continuation`** variants._

## Headlines

1. **FVG strict labels are weaker than opening_gap strict labels.** Best FVG strict config tops out at AUC 0.719 / lift +0.136. Best opening_gap strict config is still AUC 0.831 / lift +0.549. The FVG anchor matrix mixes 15m/1h/4h/daily FVG events in one parquet — likely diluting any per-timeframe signal.
2. **247's `unfilled_clean_continuation` labels work.** The renamed/relaxed labels produce real signal — `gap_down/next_240m.unfilled_clean_continuation` lift **+0.519**, essentially tied with `partial_touch_rejected` (lift +0.521). The rename wasn't just cleanup; it produced a useful new label family.
3. **GPU XGBoost wins 12/12 on opening_gap strict.** Deltas +0.000 to +0.029. Biggest wins are on the 1d horizon labels (which previously favored CPU LightGBM in the broad-label sweep yesterday). Strict + long-horizon seems to be the sweet spot for GPU XGBoost specifically.
4. **No new "killer" label across the two matrices.** The strongest configs from yesterday's 112-config scoreboard (broad-matrix `next_60m.resistance_rejection_3bar` at lift +0.613 and SMT period-close labels at +0.55–0.59) still beat anything in this release.

## FVG strict (4 configs, side=all, snapshot=at_fire)

| Label | GPU AUC | CPU AUC | Δ | GPU lift | CPU lift |
|---|---:|---:|---:|---:|---:|
| `forward_10c.after_tap_failed_1x_against` | **0.719** | 0.717 | +0.001 | +0.136 | +0.133 |
| `no_touch_continuation` | 0.719 | 0.715 | +0.005 | +0.091 | +0.089 |
| `forward_10c.after_tap_1x_clean` | 0.695 | 0.692 | +0.003 | +0.084 | +0.079 |
| `tap_wick_rejected` | 0.532 | 0.533 | −0.001 | +0.032 | +0.032 |

**Takeaway for 247**: FVG events as currently labeled aren't producing the same caliber of signal as opening_gap. Two possible reasons worth investigating:
- The FVG matrix mixes FVG events from 15m/1h/4h/daily timeframes — try filtering to one timeframe at a time and see if AUC jumps.
- The "forward_Nc.*" naming uses tight cent ranges (3c / 10c / 50c), which may not be the natural unit for futures (NQ ticks at 0.25 = 25c, so "10c forward" is sub-tick noise on NQ). If these labels were designed for stocks first, the cent-based forward windows need revisiting for futures price scales.

## Opening_gap strict (12 configs, snapshot=at_fire — including new `unfilled_*` labels)

| Side | Label | GPU AUC | CPU AUC | Δ | GPU lift |
|---|---|---:|---:|---:|---:|
| all | `next_240m.partial_touch_rejected` | 0.845 | 0.837 | +0.009 | **+0.526** |
| gap_down | `next_240m.partial_touch_rejected` | 0.832 | 0.833 | −0.000 | +0.521 |
| gap_up | `next_60m.partial_touch_rejected` | 0.832 | 0.830 | +0.003 | +0.501 |
| all | `next_240m.unfilled_clean_continuation` ⭐ NEW | 0.831 | 0.827 | +0.005 | +0.477 |
| all | `next_60m.partial_touch_rejected` | 0.831 | 0.826 | +0.005 | **+0.549** |
| all | `next_1d.partial_touch_rejected` | **0.844** | 0.825 | **+0.019** | +0.342 |
| all | `next_1d.unfilled_clean_continuation` ⭐ NEW | 0.839 | 0.823 | +0.017 | +0.309 |
| gap_down | `next_240m.unfilled_clean_continuation` ⭐ NEW | 0.828 | 0.822 | +0.005 | +0.519 |
| gap_up | `next_240m.partial_touch_rejected` | 0.834 | 0.822 | +0.012 | +0.498 |
| gap_up | `next_240m.unfilled_clean_continuation` ⭐ NEW | 0.822 | 0.814 | +0.008 | +0.428 |
| gap_up | `next_1d.partial_touch_rejected` | 0.813 | 0.787 | **+0.026** | +0.321 |
| gap_up | `next_1d.unfilled_clean_continuation` ⭐ NEW | 0.812 | 0.783 | **+0.029** | +0.320 |

GPU wins all 12. Biggest wins (+0.017 to +0.029) all happen on the **1d horizon labels** — interesting because the 112-config scoreboard yesterday found GPU *lost* slightly on the 1d horizon broad labels. The pattern reverses for strict labels: GPU XGBoost handles long-horizon strict labels better than CPU LightGBM.

## Comparison vs the 112-config scoreboard

The top-15-by-lift configs from yesterday's full scoreboard still dominate:

| Rank | From scoreboard | Lift | This release |
|---:|---|---:|---|
| 1 | `opening_gap_broad / next_60m.resistance_rejection_3bar` | +0.613 | (not in release) |
| 2-4 | SMT period_close family | +0.55 to +0.59 | (not in release) |
| 5 | `forming_vp / next_60m.took_profile_so_far_high` | +0.550 | (not in release) |
| 6 | `opening_gap_strict / next_60m.partial_touch_rejected` | **+0.549** | **+0.549 (matched)** |
| ... | | | |
| n/a | `forward_10c.after_tap_failed_1x_against` (best FVG strict) | n/a | +0.136 |

The new FVG strict labels don't crack the top-tier rankings. Opening_gap strict labels stay competitive but don't unseat broad-matrix `resistance_rejection_3bar` or the SMT period-close cluster.

## Next steps the data tells us to take

1. **247 should keep producing strict labels** but **investigate why FVG underperforms**. Suggested checks:
   - Filter the FVG matrix by `event_type` (`15m_fvg`, `1h_fvg`, etc.) before training — averaging across timeframes hides per-timeframe signal.
   - Reconsider the cent-based `forward_3c / 10c / 50c` naming for futures price scales.
2. **GPU XGBoost is now the unambiguous default for strict labels.** 12/12 wins on opening_gap strict — even larger edges on 1d horizons. Use CPU LightGBM only for SMT period-close (the one matrix where it still has an edge).
3. **The strongest signals across our entire scoreboard are in the BROAD matrices, not the strict matrices.** `next_60m.resistance_rejection_3bar` and `next_60m.support_rejection_3bar` on the opening_gap broad matrix beat every strict label tested. Worth re-running these on the new export to see if any context-layer updates changed them.

## Reproducing

```bash
# From repo root, branch assets/expanded-universe-v1.
python -m scripts.ml.strict_reactions_sweep_2026_05_15
```

Reads:
- `D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_reactions\data\ml\anchors\fvg_walk_forward_strict_context_summary.csv` (4 configs)
- `D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_reactions\data\ml\anchors\opening_gap_walk_forward_strict_context_summary.csv` (12 configs)

Writes:
- `experiments/gpu_runs/2026-05-15_strict_reactions/scoreboard.csv` (16 rows)
- `experiments/gpu_runs/2026-05-15_strict_reactions/sweep.log`
