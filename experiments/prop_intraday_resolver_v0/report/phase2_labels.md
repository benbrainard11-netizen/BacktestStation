# Phase 2a/2b — multi-head label dataset (results)

Built 2026-06-14 by `verify_phase2_labels.py` (full 342-day trading-day run, git `55226f08`+).
The dataset itself lives at `out/dataset_ES_trading_day.parquet` (gitignored). This file is
the committed record of what it contains and what it means.

## What was built

`labels.label_event_multihead` + `dataset.py` turn the canonical trading-day touch events into
a multi-head labeled frame, in **two honest coordinate frames** (both measured strictly after the
feature window):

- **branch (level-relative, == the frozen Phase-1 judge):** `ze.label_touch` first-hit of L+B
  (break) vs L−R (hold) → `y_break / y_hold / y_chop_or_timeout`.
- **trade economics (entry-relative, break-direction frame, 1R = B = 8 ticks):** entry = mid at the
  decision boundary; target = entry+dr·B, stop = entry−dr·R → `y_target_before_stop`, `realized_R`,
  `mae_R`, `mfe_R`, `time_to_resolution_sec`, `y_tail_1R`, `y_tail_2R`.

Chop/timeout is now a **kept class** (not dropped). The cooldown clock advances **only on resolved
touches** (judge_mode), so the resolved subset stays byte-identical to Phase 1 and chop rows are
purely additive.

## Acceptance — all five guards PASS

| guard | result |
|---|---|
| A no-lookahead (`feature_end ≤ decision < label_start`, every row) | **PASS** |
| B determinism (rebuild → byte-identical) | **PASS** |
| C judge-preserved (resolved subset == frozen Phase-1 frame, n=2877) | **PASS** |
| D signal-intact (break-rate monotone across OFI terciles) | **PASS** |
| E clean labels (0 nulls, 0 same-row ambiguity) | **PASS** |

## Dataset shape (n = 5420)

| | |
|---|---|
| total events | 5420 |
| resolved (break/hold) | 2877 (== Phase 1, byte-identical) |
| chop/timeout | 2543 (46.9%) |
| branch mix (of all) | break 0.202 / hold 0.328 / chop 0.469 |
| `y_target_before_stop` rate | 0.358 |
| tail rates | >1R 0.405, >2R 0.278 |
| `realized_R` (all) | mean +0.072 [p5 −1.00, p50 +0.12, p95 +1.00] |
| `mae_R` / `mfe_R` (all) | mean 1.99 / 1.98 (p95 7.75 / 7.51) |
| time-to-resolution | median 524s, mean 811s |

## Signal preservation — OFI tercile (resolved subset)

| OFI tercile | n | break_rate | mean realized_R | tbs_rate |
|---|---|---|---|---|
| low | 962 | 0.278 | −0.084 | 0.454 |
| mid | 967 | 0.371 | −0.078 | 0.451 |
| high | 948 | 0.497 | +0.002 | 0.499 |

## The headline finding

**OFI predicts resolution. OFI does not yet define a profitable trade.**

- Break-rate rises cleanly with OFI (0.28 → 0.37 → 0.50) — the validated signal survived the new
  labels intact.
- But `realized_R` on the naive ±8-tick / 30-min trade is **≤ 0 in every tercile** (best is the
  high-OFI bucket at ~breakeven). The MAE/MFE are large and ~symmetric (~2R mean), i.e. the tight
  8-tick box is blown through both ways inside 30 min.

This is the first honest separation of **alpha evidence** from **executable strategy** — and it is a
*useful* result: it blocks the classic mistake of training a fancy model on a bad trade wrapper.
Treat the ±8-tick/30-min result as a **failed wrapper, not a failed signal**.

> Note: `realized_R` mean is +0.072 over ALL events but negative on the resolved terciles — the
> chop/timeout subset pulls the overall up. The 2c by-branch diagnostic must explain this before any
> policy conclusions.

## Two modes (do not mix) — for Phase 2c

- **judge_mode (this dataset):** cooldown advances only on resolved touches → resolved subset ==
  frozen judge. Proves plumbing. Correct for the label scaffold.
- **live_mode (required for 2c economics):** every actionable touch consumes cooldown / open-position
  state; chop/timeout consume time and opportunity; no double-counting trades that could not coexist
  live. Proves tradability. To be implemented as a builder mode for the policy audit.

## Next — Phase 2c (policy-geometry audit, not model training)

The key question that gates the path: *is the high-OFI bucket losing because it never gets enough
MFE, or because it gets MFE the naive exit fails to capture?* Answered first by the OFI bucket ×
branch diagnostic (MFE/MAE magnitude + timing), then by a pre-registered policy sweep
(branch × entry timing × barrier geometry) with holdout discipline and day-block bootstrap CIs.
No policy survives unless OOS `expected_R` clears zero after costs; if none does, document NULL.
