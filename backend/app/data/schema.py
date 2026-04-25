"""Column schemas for the BacktestStation data warehouse.

Every parquet file produced by the ingest pipeline must conform to one
of these schemas. The reader library uses them to validate on load.

See [`docs/DATA_FORMAT.md`](../../../docs/DATA_FORMAT.md) for the
on-disk layout these schemas live in.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pyarrow as pa

# Bumped when ANY schema changes. Embedded in parquet metadata as
# `bs.schema.version`. Readers refuse to load files with a future
# version; old version files are upgraded in-memory by the reader.
SCHEMA_VERSION = "1"

# Bumped when the producer (parquet_mirror) changes its output behavior
# in a way that downstream consumers might care about. Embedded as
# `bs.generator.version`. Distinct from SCHEMA_VERSION because a
# generator change can ship without a schema change.
GENERATOR_VERSION = "2"


@dataclass(frozen=True)
class DataSchema:
    """One named schema: a column list + which columns are required.

    `pa_schema` is a pyarrow Schema; we keep it as the canonical source
    so producers can pass it directly to write_table. Validation is
    column-name-and-type, not stricter (pyarrow handles the type check).
    """

    name: str
    pa_schema: pa.Schema
    required_columns: tuple[str, ...] = field(default_factory=tuple)
    sort_key: str = "ts_event"

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(self.pa_schema.names)

    def field_for(self, name: str) -> pa.Field:
        return self.pa_schema.field(name)

    def validate_table(self, table: pa.Table) -> list[str]:
        """Return a list of human-readable validation errors. Empty list = OK."""
        errors: list[str] = []
        # Every required column must be present.
        for col in self.required_columns:
            if col not in table.schema.names:
                errors.append(f"missing required column: {col}")
        # Every column we emit must match expected type if it's in the schema.
        for col in table.schema.names:
            if col in self.column_names:
                expected = self.field_for(col).type
                actual = table.schema.field(col).type
                if not _types_compatible(expected, actual):
                    errors.append(
                        f"column {col!r} has type {actual!s}, expected {expected!s}"
                    )
        return errors


def _types_compatible(expected: pa.DataType, actual: pa.DataType) -> bool:
    """Loose type compatibility check.

    pyarrow type equality is strict (timestamp[ns,UTC] != timestamp[us,UTC]),
    but for our purposes a timestamp with a different unit is fine — the
    parquet round-trip will preserve the original. We only fail on
    fundamentally different types.
    """
    if expected.equals(actual):
        return True
    # Both timestamps with timezones: compatible regardless of unit.
    if pa.types.is_timestamp(expected) and pa.types.is_timestamp(actual):
        return expected.tz == actual.tz
    # Integer width drift is OK in practice (uint32 vs int64) — pandas
    # frequently widens.
    if pa.types.is_integer(expected) and pa.types.is_integer(actual):
        return True
    if pa.types.is_floating(expected) and pa.types.is_floating(actual):
        return True
    if pa.types.is_string(expected) and (
        pa.types.is_string(actual) or pa.types.is_dictionary(actual)
    ):
        return True
    return False


# --- TBBO ----------------------------------------------------------------

TBBO_SCHEMA = DataSchema(
    name="tbbo",
    pa_schema=pa.schema(
        [
            ("ts_event", pa.timestamp("ns", tz="UTC")),
            ("ts_recv", pa.timestamp("ns", tz="UTC")),
            ("symbol", pa.string()),
            ("action", pa.string()),
            ("side", pa.string()),
            ("price", pa.float64()),
            ("size", pa.uint32()),
            ("bid_px", pa.float64()),
            ("ask_px", pa.float64()),
            ("bid_sz", pa.uint32()),
            ("ask_sz", pa.uint32()),
            ("publisher_id", pa.int16()),
            ("instrument_id", pa.uint32()),
            ("sequence", pa.uint32()),
        ]
    ),
    required_columns=("ts_event", "symbol", "price", "size", "bid_px", "ask_px"),
)

# --- MBP-1 ---------------------------------------------------------------

MBP1_SCHEMA = DataSchema(
    name="mbp-1",
    pa_schema=pa.schema(
        [
            ("ts_event", pa.timestamp("ns", tz="UTC")),
            ("ts_recv", pa.timestamp("ns", tz="UTC")),
            ("ts_in_delta", pa.int32()),
            ("symbol", pa.string()),
            ("action", pa.string()),
            ("side", pa.string()),
            ("depth", pa.uint8()),
            ("price", pa.float64()),
            ("size", pa.uint32()),
            ("flags", pa.uint8()),
            ("bid_px", pa.float64()),
            ("ask_px", pa.float64()),
            ("bid_sz", pa.uint32()),
            ("ask_sz", pa.uint32()),
            ("bid_ct", pa.uint32()),
            ("ask_ct", pa.uint32()),
            ("publisher_id", pa.int16()),
            ("instrument_id", pa.uint32()),
            ("sequence", pa.uint32()),
        ]
    ),
    required_columns=("ts_event", "symbol", "price", "size", "bid_px", "ask_px"),
)

# --- OHLCV-1m bars (computed) -------------------------------------------

BARS_1M_SCHEMA = DataSchema(
    name="ohlcv-1m",
    pa_schema=pa.schema(
        [
            ("ts_event", pa.timestamp("ns", tz="UTC")),
            ("symbol", pa.string()),
            ("open", pa.float64()),
            ("high", pa.float64()),
            ("low", pa.float64()),
            ("close", pa.float64()),
            ("volume", pa.uint64()),
            ("trade_count", pa.uint32()),
            ("vwap", pa.float64()),
        ]
    ),
    required_columns=(
        "ts_event",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ),
)


SCHEMA_BY_NAME: dict[str, DataSchema] = {
    "tbbo": TBBO_SCHEMA,
    "mbp-1": MBP1_SCHEMA,
    "ohlcv-1m": BARS_1M_SCHEMA,
}


def get_schema(name: str) -> DataSchema:
    """Return the schema by name. Raises KeyError if unknown."""
    if name not in SCHEMA_BY_NAME:
        known = ", ".join(SCHEMA_BY_NAME.keys())
        raise KeyError(f"unknown schema {name!r}; known: {known}")
    return SCHEMA_BY_NAME[name]
