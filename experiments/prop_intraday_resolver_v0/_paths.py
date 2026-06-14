"""sys.path bootstrap so the flat modules here can import each other and the
market_state Stage-1 kernels they reuse.

Import this FIRST in every module (`import _paths  # noqa: F401`). It makes
available:
  - this package dir (so `import config`, `import events`, ... resolve)
  - market_state/intraday (so `import zone_events`, `import hold_break_model`)
  - market_state/validation (harness, pulled in by zone_events)
  - backend (so app.data.reader resolves)

Everything runs from the repo root with backend/.venv, matching how the
market_state scripts are invoked.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]  # experiments/<this> -> experiments -> repo root

for _p in (
    str(_HERE),
    str(_ROOT / "market_state" / "intraday"),
    str(_ROOT / "market_state" / "validation"),
    str(_ROOT / "backend"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)
