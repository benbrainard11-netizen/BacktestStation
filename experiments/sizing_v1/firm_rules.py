"""Per-firm rule engines for sizing_v1.

Loads YAML configs from config/firms/. Each firm exposes:
  - can_trade(account, signal) -> bool
  - daily_loss_breach(account) -> bool
  - trailing_dd_breach(account) -> bool
  - profit_target_hit(account) -> bool
  - min_trade_days_met(account) -> bool
  - consistency_check(account, day_pnl) -> bool

Firms supported (v1): Topstep, Tradeify, Apex, MFFU, Ludic, TPT.

See PLAN.md §3 for the universal YAML schema and §6 for the take/skip logic.

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError(
        "firm_rules.py is a stub. Confirm rule numbers in config/firms/ first."
    )


if __name__ == "__main__":
    raise SystemExit(main())
