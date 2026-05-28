"""Account state machine for sizing_v1 simulations.

One Account instance = one simulated prop firm evaluation account.
Tracks balance, daily P&L, drawdown floor (trailing), trading days, status.

See PLAN.md §5 for the full state schema and §6 for the take/skip flow.

NOT YET IMPLEMENTED. Phase: ambiguity audit (PLAN §12).
"""

from __future__ import annotations


class Account:
    """Stub. Will implement per PLAN.md §5 after firm rules are confirmed."""


def main() -> int:
    raise NotImplementedError(
        "account.py is a stub. Resolve PLAN.md §12 firm-rule ambiguities first."
    )


if __name__ == "__main__":
    raise SystemExit(main())
