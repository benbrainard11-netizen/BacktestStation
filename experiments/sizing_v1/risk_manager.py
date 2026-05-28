"""Take/skip decision — the gatekeeper.

Given a model signal and an account, decide:
  - SKIP if: account inactive, FLAT prediction, confidence < threshold,
            close to DLL, close to trailing DD floor, in news blackout,
            consistency rule would be violated.
  - TAKE otherwise, with size from sizing.py.

This is THE most important module for v1 because mistakes here = blown accounts.

See PLAN.md §6 for the full decision flow.

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError("risk_manager.py is a stub.")


if __name__ == "__main__":
    raise SystemExit(main())
