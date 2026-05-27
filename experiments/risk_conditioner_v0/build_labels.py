"""Build labels for each candidate trade.

Input:  out/trades_universe.parquet
Output: out/labels.parquet

Shared labels (all detector families):
  y_mae_r              = clip(MAE_R, 0, 3.0)
  y_time_to_target_sec = seconds from ts_entry until first target touch,
                         capped at T_cap_i, set to T_cap_i + 1 if never touched.
  y_target_before_stop = 1 if target touched before stop,
                         0 if stop touched before target,
                         null if neither touched before T_cap / session exit.

Type A label (predictive families only):
  y_bad  = 1 if MAE_R >= 1.0 before target is reached, else 0

Type B label (confirmatory families only):
  y_tail = 1 if MAE_R > 2.0, else 0

R definition:
  risk_ticks_i = abs(entry_price_i - stop_price_i) / tick_size_symbol

Reject any sample where risk_ticks <= 0, null, or entry/stop is null.

Label window ends at the earliest of:
  - target hit
  - stop hit
  - strategy exit
  - T_cap timeout (default 60 minutes)
  - session close / forced flat time

For longs:
  adverse(τ)   = max(0, entry - low_or_bid_proxy(τ)) / tick_size
  favorable(τ) = max(0, high_or_ask_proxy(τ) - entry) / tick_size

For shorts: flip high/low.

  MAE_R = max(adverse(τ)) / risk_ticks  over τ ∈ (ts_entry, label_end]
  MFE_R = max(favorable(τ)) / risk_ticks

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError(
        "build_labels.py is a stub. "
        "Implement after build_trade_universe.py produces a valid universe "
        "and PLAN §10.3 (exit logic) is resolved."
    )


if __name__ == "__main__":
    raise SystemExit(main())
