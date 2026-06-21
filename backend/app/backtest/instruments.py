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
    # NYMEX energy (full-size). CL: 1,000 bbl -> $1000/pt, tick 0.01 = $10.
    # NG: 10,000 MMBtu -> $10,000/pt, tick 0.001 = $10.
    "CL":  InstrumentSpec(tick_size=0.01,  contract_value=1000.0),
    "NG":  InstrumentSpec(tick_size=0.001, contract_value=10000.0),
    # Micro WTI crude (MCL): 100 bbl -> $100/pt, tick 0.01 = $1. The prop vehicle for CL.
    "MCL": InstrumentSpec(tick_size=0.01,  contract_value=100.0),
    # COMEX gold. GC: 100 oz -> $100/pt, tick 0.10 = $10. MGC (micro): 10 oz -> $10/pt, tick 0.10 = $1.
    "GC":  InstrumentSpec(tick_size=0.10,  contract_value=100.0),
    "MGC": InstrumentSpec(tick_size=0.10,  contract_value=10.0),
    # CME crypto. BTC: 5 BTC -> $5/pt, tick 5.0 = $25. ETH: 50 ETH -> $50/pt, tick 0.5 = $25.
    # MBT (micro BTC): 0.1 BTC -> $0.1/pt, tick 5.0 = $0.50.
    "BTC": InstrumentSpec(tick_size=5.0,      contract_value=5.0),
    "ETH": InstrumentSpec(tick_size=0.5,      contract_value=50.0),
    "MBT": InstrumentSpec(tick_size=5.0,      contract_value=0.1),
    # Grains/rates. ZS: 5000 bu, 1/4 cent tick = $12.50 (price in cents). ZN: 10y note, 1/64 = $15.625.
    "ZS":  InstrumentSpec(tick_size=0.25,     contract_value=50.0),
    "ZN":  InstrumentSpec(tick_size=0.015625, contract_value=1000.0),
    "ZF":  InstrumentSpec(tick_size=0.0078125, contract_value=1000.0),  # 5y note, 1/4 of 1/32 = $7.8125
    "ZB":  InstrumentSpec(tick_size=0.03125,  contract_value=1000.0),  # 30y bond, 1/32 = $31.25
    "ZT":  InstrumentSpec(tick_size=0.0078125, contract_value=2000.0),  # 2y note, $200k face -> $2000/pt
    # ICE Brent (Databento BZ): 1000 bbl -> $1000/pt, tick 0.01 = $10 (same economics as CL).
    "BZ":  InstrumentSpec(tick_size=0.01,     contract_value=1000.0),
    # NYMEX products: 42,000 gal -> $420/pt (=$42000 per $1), tick 0.0001 = $4.20.
    "HO":  InstrumentSpec(tick_size=0.0001,   contract_value=42000.0),
    "RB":  InstrumentSpec(tick_size=0.0001,   contract_value=42000.0),
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
