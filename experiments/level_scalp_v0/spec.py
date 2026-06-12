"""level_scalp_v0 constants + guards — the typed config module (CLAUDE.md rule 7).

Every script imports windows, touch constants, costs and guards from here.
Values are FROZEN at the first atlas run per PLAN.md; amend only before then.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).resolve().parent
OUT = MODULE / "out"
sys.path.insert(0, str(REPO / "backend"))

from app.backtest.instruments import lookup  # noqa: E402

SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
TICK = {s: lookup(s).tick_size for s in SYMBOLS}
POINT_VALUE = {s: lookup(s).contract_value for s in SYMBOLS}

# --- windows (PLAN §Windows) -------------------------------------------------
SELECTION = ("2025-05-01", "2025-12-31")
CONFIRMATION = ("2026-01-01", "2026-03-31")
HOLDOUT_START = "2026-04-01"  # 2 lifetime reads, manifest-gated; see holdout_ledger.md


def guard_window(start: str, end: str, allow_confirmation: bool = False) -> None:
    """Refuse any read that touches HOLDOUT; CONFIRMATION needs an explicit flag."""
    if end >= HOLDOUT_START:
        raise RuntimeError(
            f"window [{start},{end}] touches the HOLDOUT (>= {HOLDOUT_START}). "
            "Holdout reads go through the ledger protocol, never through this path."
        )
    if end > SELECTION[1] and not allow_confirmation:
        raise RuntimeError(
            f"window [{start},{end}] enters CONFIRMATION; pass allow_confirmation=True "
            "only for a pinned-manifest confirmation run (PLAN Phase 1)."
        )


# --- touch constants (FROZEN at first atlas run) ------------------------------
EPS_TICKS = 2  # touch = mid within 2 ticks of level
COOLDOWN = "15min"  # per level_id, keyed off RAW onsets (unconditional)
APPROACH_WIN = "60s"  # pre-onset window for approach side/speed
HORIZON = "30min"  # reaction horizon (atlas stage; unused by power table)
GRID_TICKS = [2, 4, 6, 8, 12, 16]  # (k, j) reaction grid (atlas stage)

# --- costs (stressed; spreads MEASURED, see PLAN §Cost walls) ------------------
COMMISSION_RT = 3.80  # $ round-turn
SPREAD_TICKS_RTH = {"ES.c.0": 1.0, "NQ.c.0": 3.0, "YM.c.0": 2.0, "RTY.c.0": 2.0}

# --- round-number grids (points) ----------------------------------------------
ROUND_GRID_PTS = {"ES.c.0": 25.0, "NQ.c.0": 100.0, "YM.c.0": 100.0, "RTY.c.0": 10.0}

# --- time-of-day buckets (ET minutes since midnight) ---------------------------
TOD_BUCKETS = [  # (name, start_min, end_min) within the Globex trading day
    ("on", 1080, 1440 + 240),  # 18:00 -> 04:00 (wraps midnight)
    ("pre", 240, 570),  # 04:00 -> 09:30
    ("open", 570, 630),  # 09:30 -> 10:30
    ("late_am", 630, 690),  # 10:30 -> 11:30
    ("lunch", 690, 810),  # 11:30 -> 13:30
    ("pm", 810, 960),  # 13:30 -> 16:00
    ("post", 960, 1020),  # 16:00 -> 17:00
]


def tod_bucket(minutes_et: int) -> str:
    m = minutes_et
    if m >= 1080 or m < 240:
        return "on"
    for name, a, b in TOD_BUCKETS[1:]:
        if a <= m < b:
            return name
    return "post"


# --- roll excision (PLAN rule A8; conservative pre-freeze, tighten if measured) -
def _third_friday(year: int, month: int) -> dt.date:
    d = dt.date(year, month, 15)
    while d.weekday() != 4:
        d += dt.timedelta(days=1)
    return d


def roll_poison_days(start: str, end: str) -> set[dt.date]:
    """Trading days within [3rd Friday - 9cd, 3rd Friday] of Mar/Jun/Sep/Dec.

    .c.0 splices land in this window; days here are excised from touch
    detection, and any level whose source span crosses one is dropped.
    """
    s, e = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    out: set[dt.date] = set()
    for year in range(s.year, e.year + 1):
        for month in (3, 6, 9, 12):
            f = _third_friday(year, month)
            d = f - dt.timedelta(days=9)
            while d <= f:
                if d.weekday() < 5 and s <= d <= e:
                    out.add(d)
                d += dt.timedelta(days=1)
    return out


# --- manifest (PLAN rule C27) ---------------------------------------------------
def write_manifest(path: Path, params: dict, n_rows: int) -> None:
    if n_rows == 0:
        raise RuntimeError(f"refusing to write 0-row dataset manifest for {path}")
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True
    ).stdout.strip()
    manifest = {"git_sha": sha, "params": params, "n_rows": n_rows}
    path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
