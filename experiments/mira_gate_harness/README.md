# Mira gate — champion/challenger harness

Durable structure to evolve the gate model over time. **Champion** = the frozen live gate. A
**challenger** (new features / retrain) is promoted only if it beats the champion on a **frozen OOS
holdout**. Everything is cached + versioned so datasets are never re-derived or lost.

## Decision model (why it's structured this way)
The strategy makes ~5 decisions; only some are models:
- **Where setups are** (levels swept) → rules (detectors). The *frequency* lever. Not modeled here.
- **Take this trade?** → the **gate** (one model). The *edge* lever. **This harness evolves it.**
- Direction → rule. Sizing → separate layer. Exit → rule (trail_2R).
"Many models" = different *decisions* (gate + sizing), NOT many competing gates. Split one decision
into specialists only when a segment is both large AND demonstrably different (discovered via this loop).

## Locked windows
- `train` = 2026-02-06 … 05-20 (champion's training window)
- `oos_holdout` = 2026-05-21 … 06-05 (post-training, fresh — the real holdout)
- `jan_oos` = 2026-01-02 … 02-04 (secondary pre-training OOS); `jan_smoke` = tiny validation slice

## Usage
```
# one-time (slow detect regen; cached after) — build the datasets:
python harness.py --build train
python harness.py --build oos_holdout

# baseline: the frozen live model on the frozen holdout -> scoreboard row
python harness.py --eval-champion --oos oos_holdout

# a challenger -> trains on `train`, evals on the SAME holdout -> scoreboard row
python harness.py --challenger retrain_same --train train --oos oos_holdout   # reproducibility check
python harness.py --challenger drop_smt    --train train --oos oos_holdout   # confirm SMT low-importance
```
Promote a challenger only if it beats the champion on `oos_holdout` by a real margin. Compare in
`runs/scoreboard.csv`.

## Metric
Label = `target.60m.extreme_hold_move` (the pipeline's own forward outcome). Reported: AUC, gated
count, gated success-rate (precision at the prev_q75 threshold), base rate, lift. **Realized-R is an
optional add-on** (needs the MBP-1 fill sim rebuilt) so the scoreboard can read in R, not AUC.

## Notes / gotchas
- `build_dataset` patches `v0._read_mbo_window` to **cache the day's MBO** — the vendored reader
  re-reads the full day file per trigger (no pushdown), which causes an I/O-storm hang on dense
  candidate sets. The cache makes it 1 read/symbol-day.
- Datasets + manifests live in `data/` (git-ignore the parquets; keep the manifests). This dir is the
  fix for the "gate-validation work dir got cleaned" problem — treat it as the durable cache.
- Add new orderflow features as a challenger by extending the encoder/feature list, then run it through
  the same loop. SMT-definition variants are NOT worth pursuing (see ../smt_ltf_bench/REPORT.md).
