"""Instrument specs — tick size, contract value, default commission.

Used to populate `RunConfig` defaults when the caller doesn't pass
them explicitly. Lookup matches the symbol's leading alpha prefix
(e.g. `"NQ.c.0"`, `"NQM6"`, `"MNQ.c.0"` all resolve via "NQ" /
"MNQ"). Falls back to None when the prefix isn't known — caller can
either reject or stick with the dataclass defaults (NQ values).

Per CLAUDE.md rule 7, all instrument constants live here in one
typed module — never inline in engine or strategy code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class InstrumentSpec:
    """Per-instrument constants the engine and broker need."""

    tick_size: float
    contract_value: float  # dollars per point per contract
    commission_per_contract: float = 2.00  # round-trip estimate, conservative


INSTRUMENTS: dict[str, InstrumentSpec] = {
    # CME E-mini index futures
    "NQ":  InstrumentSpec(tick_size=0.25, contract_value=20.0),
    "ES":  InstrumentSpec(tick_size=0.25, contract_value=50.0),
    "YM":  InstrumentSpec(tick_size=1.0,  contract_value=5.0),
    "RTY": InstrumentSpec(tick_size=0.10, contract_value=50.0),
    # CME Micro index futures (1/10 size)
    "MNQ": InstrumentSpec(tick_size=0.25, contract_value=2.0),
    "MES": InstrumentSpec(tick_size=0.25, contract_value=5.0),
    "MYM": InstrumentSpec(tick_size=1.0,  contract_value=0.50),
    "M2K": InstrumentSpec(tick_size=0.10, contract_value=5.0),
}


_PREFIX_RE = re.compile(r"^([A-Z]{1,4})")


def lookup(symbol: str) -> InstrumentSpec | None:
    """Resolve an instrument spec from a symbol identifier.

    Matches the leading alpha prefix. Examples:
        "NQ.c.0"   -> INSTRUMENTS["NQ"]
        "NQM6"     -> INSTRUMENTS["NQ"]
        "MNQ.c.0"  -> INSTRUMENTS["MNQ"]
        "FOO.c.0"  -> None
    """
    if not symbol:
        return None
    m = _PREFIX_RE.match(symbol.upper())
    if m is None:
        return None
    prefix = m.group(1)
    # Prefer the longest-matching prefix (e.g. "MNQ" over "M") — try
    # the full prefix first, then truncate.
    for n in range(len(prefix), 0, -1):
        spec = INSTRUMENTS.get(prefix[:n])
        if spec is not None:
            return spec
    return None
