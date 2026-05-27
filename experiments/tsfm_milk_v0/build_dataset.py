"""Build the multivariate dataset for tsfm_milk_v0.

Inputs:
  D:/data/processed/bars/timeframe=1m/symbol=<X>/date=<Y>/*.parquet
    where X ∈ {ES.c.0, NQ.c.0, YM.c.0, RTY.c.0}

Output:
  out/dataset/fold_{fold_id}_{phase}.parquet  where phase ∈ {train, val, test}
  out/dataset/holdout.parquet

Per anchor row (one row per RTH minute, per fold/phase):
  ts_decision     — anchor timestamp (UTC)
  inputs          — (240, 32) tensor flattened to columns or stored as nested
  labels          — int class codes per (symbol, horizon)
  metadata        — feature_version, label_version, fold_id, phase

Strict no-lookahead: all inputs use bars with ts < ts_decision. Labels use
bars with ts > ts_decision.

See PLAN.md §1 (channel schema), §2 (label rules), §3 (folds).

NOT YET IMPLEMENTED. Phase: dataset ambiguity audit (PLAN §9).
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError(
        "build_dataset.py is a stub. "
        "Resolve PLAN.md §9 ambiguities first (gap audit, tick sizes, "
        "cross-symbol alignment, class balance, vol regime distribution)."
    )


if __name__ == "__main__":
    raise SystemExit(main())
