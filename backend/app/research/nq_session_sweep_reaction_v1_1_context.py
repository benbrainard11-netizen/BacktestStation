"""Sweep context helpers for NQ Session Sweep Reaction V1.1."""

from __future__ import annotations

from app.research.nq_session_sweep_reaction_v1_types import SweepEvent, TradePlan

SWEEP_CONTEXT_COLUMNS = [
    "overnight_sweep_direction",
    "overnight_sweep_ts",
    "overnight_sweep_price",
    "overnight_sweep_vs_armed",
    "rth_first_sweep_direction",
    "rth_first_sweep_ts",
    "rth_first_sweep_price",
    "rth_first_sweep_vs_armed",
    "overnight_rth_sweep_relationship",
]


def sweep_context(
    *,
    plan: TradePlan,
    overnight_sweep: SweepEvent | None,
    rth_sweep: SweepEvent | None,
) -> dict[str, object]:
    return {
        "overnight_sweep_direction": (
            overnight_sweep.side if overnight_sweep else None
        ),
        "overnight_sweep_ts": overnight_sweep.ts if overnight_sweep else None,
        "overnight_sweep_price": overnight_sweep.price if overnight_sweep else None,
        "overnight_sweep_vs_armed": _vs_armed(plan, overnight_sweep),
        "rth_first_sweep_direction": rth_sweep.side if rth_sweep else None,
        "rth_first_sweep_ts": rth_sweep.ts if rth_sweep else None,
        "rth_first_sweep_price": rth_sweep.price if rth_sweep else None,
        "rth_first_sweep_vs_armed": _vs_armed(plan, rth_sweep),
        "overnight_rth_sweep_relationship": _relationship(
            overnight_sweep,
            rth_sweep,
        ),
    }


def empty_sweep_context() -> dict[str, object]:
    return {column: None for column in SWEEP_CONTEXT_COLUMNS}


def add_context(
    row: dict[str, object],
    context: dict[str, object],
) -> dict[str, object]:
    out = dict(row)
    out.update(context)
    return out


def _vs_armed(plan: TradePlan, sweep: SweepEvent | None) -> str | None:
    if sweep is None:
        return None
    return "aligned" if sweep.side == plan.armed_side else "opposite"


def _relationship(
    overnight_sweep: SweepEvent | None,
    rth_sweep: SweepEvent | None,
) -> str:
    if overnight_sweep is None and rth_sweep is None:
        return "none"
    if overnight_sweep is None:
        return "rth_only"
    if rth_sweep is None:
        return "overnight_only"
    return "aligned" if overnight_sweep.side == rth_sweep.side else "conflicted"
