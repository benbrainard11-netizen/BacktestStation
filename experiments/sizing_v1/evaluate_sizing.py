"""Pass-rate report + milking math.

Reads out/accounts/{firm}/account_*_final.json and out/trades/{firm}/.
For each firm computes:
  - Pass rate: n_passed / n_total
  - Distribution of final balances (p25 / p50 / p75 / worst / best)
  - Termination reason breakdown (passed / blown_daily / blown_dd / expired)
  - Mean days-to-pass for passing accounts
  - Milking math:
      gross = n_passed × funded_account_value_usd
      cost  = n_total × eval_fee_usd
      net   = gross - cost
      ev_per_eval = net / n_total
      break_even_pass_rate = eval_fee_usd / funded_account_value_usd

Output:
  report/v1_iter1_results.md
  out/pass_rates_aggregated.parquet

See PLAN.md §9.

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError("evaluate_sizing.py is a stub.")


if __name__ == "__main__":
    raise SystemExit(main())
