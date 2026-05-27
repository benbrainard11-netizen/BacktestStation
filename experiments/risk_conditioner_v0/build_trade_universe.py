"""Build the candidate-trade universe from existing detector fires.

One row per detector fire in the Path A training universe
(2025-05-01 → 2026-05-22). Output: out/trades_universe.parquet.

Columns:
  trade_id, symbol, detector_name, family_type, side,
  ts_signal, ts_decision, ts_entry,
  entry_price, stop_price, target_price, risk_ticks,
  target_ticks, reward_risk_ratio, T_cap_sec,
  session_date, instrument_id, raw_symbol, roll_boundary_flag

Source: existing detector outputs in the BacktestStation engine.
See PLAN.md §1 for the canonical timestamp/price definitions
and §10 for the ambiguities Codex must resolve before implementing.

NOT YET IMPLEMENTED. Phase: ambiguity audit (PLAN §10).
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError(
        "build_trade_universe.py is a stub. "
        "Resolve PLAN.md §10 ambiguities first (stop source, exec timestamp, "
        "exit logic, roll boundaries, sample counts), then implement."
    )


if __name__ == "__main__":
    raise SystemExit(main())
