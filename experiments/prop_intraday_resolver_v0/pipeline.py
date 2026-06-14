"""End-to-end orchestration -- the spine that connects the four layers.

This is the reason prop_intraday_resolver_v0 exists as its own project: the
layers live in other modules; this wires them into one deterministic pass.

Phase 1 (now): run_research reproduces market_state Stage 1 (ES, PDH/PDL,
OFI-only) THROUGH this spine, so the event frame is byte-comparable to
market_state/out/zone_events_ES.parquet. Verified by verify_phase1.py.

Later phases extend events/features/labels/resolver/conditioner/governor without
touching this control flow's shape.
"""

from __future__ import annotations

import _paths  # noqa: F401
import datetime as _dt
from pathlib import Path

import numpy as np
import pandas as pd

import events
import features
import labels
import resolver  # noqa: F401  (re-exported for callers; used by verify_phase1)
import zone_events as ze

OUT = Path(__file__).resolve().parent / "out"


def _process_day(ctx, pdh: float, pdl: float) -> list[dict]:
    """One day's event rows. Cooldown is sequenced here (per level) because the
    Stage-1 reference couples it with resolution: a touch that times out does NOT
    reset the cooldown clock; only a resolved touch does."""
    rows: list[dict] = []
    last_t = {"PDH": None, "PDL": None}
    for i0, t0, role, L, dr in events.iter_candidates(ctx, pdh, pdl):
        lt = last_t[role]
        if lt is not None and (t0 - lt) < ze.COOLDOWN:
            continue
        lab = labels.label_event(ctx, t0, L, dr)
        if lab is None:
            continue
        feats = features.build_features(ctx, i0, t0, dr)
        last_t[role] = t0
        rows.append({"ts": t0, "level": role, "dir": dr, **feats, "label": lab})
    return rows


def run_research(
    symbols=("ES",),
    families=("pdh", "pdl"),
    days_limit=None,
    reader="trading_day",
    write=True,
    out_name=None,
) -> pd.DataFrame:
    """Scan -> features -> labels for the whole sample; return the event frame.

    Phase 1 scope is ES / PDH-PDL (exactly what Stage 1 ran). days_limit evenly
    samples N days for a fast smoke; omit for the full reproduce. reader selects
    the read window: 'trading_day' (CME session, the canonical data-discipline
    default since Step 1b) or 'raw' (calendar day, the Stage-1 audit path).
    """
    if tuple(symbols) != ("ES",) or tuple(families) != ("pdh", "pdl"):
        raise NotImplementedError(
            "Phase 1 reproduce is ES / PDH-PDL only; extend in Phase 2."
        )
    if out_name is None:
        out_name = f"events_ES_{reader}.parquet"

    levels = events.precompute_levels()
    days = events.available_days()
    if days_limit and days_limit < len(days):
        idx = np.linspace(0, len(days) - 1, days_limit).round().astype(int)
        days = [days[i] for i in sorted(set(idx.tolist()))]

    rows: list[dict] = []
    for k, day in enumerate(days):
        # Trading-day labels are Mon-Fri only; weekend calendar partitions
        # (e.g. the Sunday-evening session) fold into the adjacent trading day's
        # read window, so we don't process them as standalone day labels.
        if reader == "trading_day" and _dt.date.fromisoformat(day).weekday() >= 5:
            continue
        lv = levels.get(_dt.date.fromisoformat(day))
        if not lv:
            continue
        ctx = events.load_day(ze.SYM, day, reader=reader)
        if ctx is None:
            continue
        rows.extend(_process_day(ctx, lv["pdh"], lv["pdl"]))
        if (k + 1) % 20 == 0:
            print(f"  ..{k + 1}/{len(days)} days, {len(rows)} events")

    df = pd.DataFrame(rows).set_index("ts").sort_index()
    if write:
        OUT.mkdir(parents=True, exist_ok=True)
        df.to_parquet(OUT / out_name)
    return df


def decide_live(candidate, account_state, firm):
    """Live decision path (Phase 4): resolver -> conditioner -> governor."""
    raise NotImplementedError(
        "Phase 4: assemble resolver -> conditioner -> governor decision."
    )
