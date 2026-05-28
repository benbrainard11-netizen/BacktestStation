"""Walk-forward trade simulator for a single account.

For one Account against the time-ordered stream of model signals:
  1. Iterate signals in ts_decision order
  2. At each: route through risk_manager → take/skip decision
  3. If take: enter at next-bar open + jitter, record entry
  4. Manage open positions: hold for horizon, exit at horizon-bar open
  5. Update P&L, check breach conditions, advance account state
  6. Stop when account is blown / passed / eval window expired

See PLAN.md §7 for the exit logic and §8 for the multi-account driver.

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError("simulator.py is a stub.")


if __name__ == "__main__":
    raise SystemExit(main())
