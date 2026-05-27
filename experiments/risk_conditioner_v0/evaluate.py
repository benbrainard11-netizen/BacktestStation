"""Evaluate models against statistical + economic kill criteria.

Reads:
  out/predictions/fold_*.parquet
  out/labels.parquet
  walk_forward.yaml

Reports SEPARATELY for:
  - all trades
  - Type A only
  - Type B only
  - each detector family (FVG zone_reaction ALWAYS reported standalone)
  - each symbol (ES, NQ, YM, RTY)

Statistical metrics:
  Type A:
    ROC-AUC for y_bad
    Spearman IC between predicted risk and realized MAE_R
    Brier score
    Calibration ECE
  Type B:
    ROC-AUC for y_tail
    Top-decile predicted-tail / bottom-half realized-tail ratio
    Calibration ECE

Economic metrics:
  net_R, mean_R_per_trade, median_R_per_trade,
  max_drawdown_R, MAR-like ratio,
  daily loss breach proxy,
  stop_rate, target_rate,
  avg_MAE_R, p95_MAE_R, p99_MAE_R,
  tail_event_rate (Type B), tail_R_loss (Type B),
  trade_count_retained

Kill / ship thresholds: see PLAN §6.

HARD RULE: if Type B conditioner reduces FVG zone_reaction aggregate +R
materially, the model is killed or restricted to shadow.

Output:
  report/evaluation_{run_id}.md
  out/metrics_{run_id}.parquet

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError(
        "evaluate.py is a stub. "
        "Implement after train_walkforward.py produces predictions."
    )


if __name__ == "__main__":
    raise SystemExit(main())
