"""Multi-account simulator. One signal → N accounts.

For each firm:
  - Spawn N=100 simulated accounts (each with its own jitter seed)
  - Run simulator.py per account against the same model signals
  - Aggregate outcomes: pass / blown / expired

Output:
  out/trades/{firm}/account_{n}.parquet
  out/accounts/{firm}/account_{n}_final.json
  out/pass_rates.parquet (per firm)

See PLAN.md §8.

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError("multi_account_router.py is a stub.")


if __name__ == "__main__":
    raise SystemExit(main())
