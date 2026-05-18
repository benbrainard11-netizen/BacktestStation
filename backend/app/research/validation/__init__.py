"""Semantic data validation for warehouse partitions.

Per `docs/VALIDATION_DESIGN.md`: every dataset snapshot should produce a
`partition_validation_report` with explicit gate results. Gates are
schema-specific (ohlcv-1m / tbbo / mbp-1 / research_events) and run
against a single partition DataFrame at a time.

This package owns the gate framework + per-schema gate catalogs + the
runner that walks a snapshot. It does NOT own the DB tables — those
live in `app/db/models.py` and are 247's lane (Q2 of the execution
queue).

Public surface:

  from app.research.validation import schema_gates
  from app.research.validation import gates_ohlcv, gates_tbbo, ...
  from app.research.validation.schema_gates import Gate, GateResult,
      run_gates_on_partition, GATES_BY_SCHEMA

The runner module (`runner.py`) is the snapshot-walker; it depends on
the validation report tables existing and is wired in once 247's Q2
lands.
"""

from __future__ import annotations

from app.research.validation.schema_gates import (  # noqa: F401
    GATES_BY_SCHEMA,
    Gate,
    GateResult,
    Severity,
    register_gate,
    run_gates_on_partition,
)

# Side-effect imports: each gates_* module registers its gates against
# GATES_BY_SCHEMA at import time. Mirrors the detector registry pattern.
from app.research.validation import (  # noqa: E402,F401
    gates_mbp1,
    gates_ohlcv,
    gates_research_events,
    gates_tbbo,
)
