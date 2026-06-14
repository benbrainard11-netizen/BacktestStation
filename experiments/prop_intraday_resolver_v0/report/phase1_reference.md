# Phase 1 reference numbers

The known-good Stage 1 result that `pipeline.py` must reproduce (PLAN.md Phase 1, Step 1a).
Captured by running the existing `market_state` scripts directly — **no new code**.

## Provenance (for byte-for-comparable reproduction)

| | |
|---|---|
| Captured | 2026-06-14 |
| git SHA | `359c22cd` (branch `ben/market-state`) |
| Interpreter | `backend/.venv/Scripts/python.exe`, lightgbm 4.6.0 |
| Scanner | `market_state/intraday/zone_events.py` (full run, no N_DAYS arg) |
| Judge | `market_state/intraday/hold_break_model.py` |
| Symbol / peers | `ES.c.0` ; peers `NQ.c.0`, `RTY.c.0`, `YM.c.0` |
| Data | ES MBP-1, 342 day partitions, 2025-05-01 .. 2026-06-09 |
| Params | `EPS`=2 ticks, `W_OFI`=2s, break/hold barrier `B=R`=8 ticks, `HORIZON`=30min, `COOLDOWN`=15min |
| OOS split | `2026-03-01` (UTC) |
| Bootstrap | `N_FOLDS`=5, `N_BOOT`=2000, seed 0 |

> Note: §1–§3 below are the **raw-read** path (`read_mbp1`, `[day, nxt)` UTC) — the Step-1a reproduce
> target and the permanent faithfulness baseline (`verify_phase1.py smoke` is pinned to it). Step 1b
> adopted the clean trading-day reader as canonical; see the next section.

---

## CANONICAL — Step 1b (trading-day reader, adopted 2026-06-14)

The default reader is now `read_mbp1_trading_day` (CME session window, per the repo's data-discipline
rule). Captured by `verify_phase1.py compare` (full 342-day scan, git `359c22cd`):

| metric | raw (§1–§3, audit) | **trading-day (CANONICAL)** |
|---|---|---|
| n events | 2856 | **2877** (+21) |
| `ofi_signed` OOS Spearman | +0.281 | **+0.299** |
| `ofi_signed` IS Spearman | +0.172 | +0.183 |
| OFI-only bootstrap AUC | 0.630 [0.597, 0.662] | **0.639 [0.603, 0.672]** |
| `qimb_signed` | NULL | NULL |
| `svol_signed` OOS | +0.139 | +0.142 |
| `nq/rty/ym_ofi` OOS | +0.230/+0.214/+0.225 | +0.231/+0.224/+0.235 |
| divergence delta | −0.012 [−0.030,+0.008] (noise) | +0.008 [−0.017,+0.032] (noise) |
| OOS days | 65 | 70 |

**Why it moved (+21 rows) — session-boundary correction, not a bug:**
- All **2,712 common (ts, level) events are byte-identical** — 0 label flips, 0 dir flips, 0 OFI changes.
  The reader swap altered no shared event; the entire RTH signal is preserved exactly.
- Every moved row is in ET hours 17–20 (the session edge): trading-day drops the 26 raw rows at ET 17
  (post-close / maintenance halt the raw calendar window mis-included) and folds the prev-evening
  session (18:00 ET+) into the correct trading day with the correct prior-day level (+net evening rows).

  ```
  ET hour   only_clean   only_raw
    17           0          26
    18         122          83
    19          40          28
    20           3           7
  ```
- Net effect: the clean reader removes post-close junk, captures legitimate evening touches, the
  headline edge ticks UP (+0.281 → +0.299), and divergence stays non-lifting. All verdicts unchanged.

**Conclusion:** the spine is faithful (common rows identical) AND the data-discipline-correct reader is
safe and mildly beneficial. Trading-day is the Phase-2 baseline.

---

## RAW audit baseline (Step 1a reproduce target)

## 1. Scanner — event set

```
EVENTS n=2856   break_rate=0.401   (PDH 1672 / PDL 1184)
train (IS) n=2186  /  OOS n=670  (65 OOS days)   OOS break_rate=0.406
break rate by signed-OFI tercile:  low 0.297 (n=967) | mid 0.401 (n=946) | high 0.509 (n=943)
```

## 2. Scanner — per-feature forward test (harness, OOS ≥ 2026-03-01)

The non-negotiable judge's raw inputs. `ofi_signed` is the baseline edge.

| feature | IS spearman | OOS spearman | OOS tercile lift | verdict |
|---|---|---|---|---|
| **ofi_signed** | +0.172 | **+0.281** | +0.305 | **PASS** |
| qimb_signed | −0.031 | −0.047 | −0.067 | **NULL** (sign flips OOS) |
| svol_signed | +0.131 | +0.139 | +0.135 | PASS |
| nq_ofi | +0.143 | +0.230 | +0.242 | PASS |
| rty_ofi | +0.126 | +0.214 | +0.220 | PASS |
| ym_ofi | +0.139 | +0.225 | +0.242 | PASS |

## 3. Judge — hold/break model (LightGBM)

Walk-forward OOS AUC across time folds (mean ± std):

| feature set | AUC | folds |
|---|---|---|
| OFI only | 0.599 ± 0.029 | 0.554, 0.609, 0.600, 0.633 |
| OFI+xindex (confirm) | 0.603 ± 0.041 | 0.555, 0.573, 0.624, 0.658 |
| OFI+divergence | 0.586 ± 0.024 | 0.552, 0.592, 0.580, 0.620 |
| xindex only (ctrl) | 0.598 ± 0.037 | 0.554, 0.571, 0.620, 0.646 |

Day-block bootstrap AUC on 2026-03-01+ holdout (median [5, 95]):

| feature set | AUC [5, 95] |
|---|---|
| OFI only | 0.630 [0.597, 0.662] |
| OFI+xindex (confirm) | 0.655 [0.623, 0.684] |
| OFI+divergence | 0.618 [0.588, 0.649] |
| xindex only (ctrl) | 0.654 [0.619, 0.687] |

**Headline delta (OFI+divergence − OFI only) = −0.012 [−0.030, +0.008] → WITHIN NOISE** (CI straddles 0).

## What this tells us (beyond "it's the reproduce target")

- **OFI-only baseline is healthy and reproduces** — OOS Spearman +0.281, bootstrap AUC 0.630. This is the bar every richer feature must clear.
- **`qimb_signed` (queue imbalance) is NULL standalone** — sign flips OOS. Confirms the SPEC's note that it was "computed but never ablated standalone, unproven." Now ablated → does not earn its seat.
- **The `es_complex_agree` divergence interaction does not add** (delta CI straddles 0) — consistent with the lab's prior that SMT/divergence is coverage, not edge.
- **Cross-index OFI is interesting but unresolved**: in the bootstrap, `xindex only` (0.654) ≈ `OFI+xindex` (0.655), both above `OFI only` (0.630) — yet the formally-tested delta here is only the *divergence* interaction. Whether the raw cross-index group beats OFI-only by a clean CI is NOT settled by this script (its `BASELINE/FULL` constants test divergence, not the confirm set). Flag for Phase 2: ablate the cross-index group properly against the OFI baseline before trusting it.

## Phase 1 acceptance — CLOSED 2026-06-14

- **Step 1a (raw reproduce):** ✅ `verify_phase1.py full raw` matched §1–§3 bit-for-comparable; `smoke` = exact row match vs `zone_events.process_day`. Spine proven faithful to market_state.
- **Step 1b (clean-reader swap):** ✅ adopted trading-day as canonical. Numbers moved by an understood, beneficial session-boundary correction (see CANONICAL section); all common rows byte-identical, all verdicts unchanged.

Permanent guard: `verify_phase1.py smoke` (pinned to raw) must stay green — it proves the decomposition still equals market_state. Phase 2 builds on the **trading-day** baseline (n=2877, `ofi_signed` OOS +0.299, OFI-only AUC 0.639, divergence non-lifting).
