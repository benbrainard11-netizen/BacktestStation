"""BacktestStation data warehouse access layer.

The on-disk layout, columns, and validation rules are documented in
[`docs/DATA_FORMAT.md`](../../../docs/DATA_FORMAT.md). This package
provides the readable API:

    from app.data import read_tbbo, read_mbp1, read_bars
    from app.data.schema import TBBO_SCHEMA, BARS_1M_SCHEMA

Producers (parquet_mirror, historical puller) read from
`app.data.schema` to know what columns to emit and from
`app.data.manifest` to write audit manifests.
"""

from app.data.reader import read_bars, read_mbp1, read_tbbo
from app.data.schema import (
    BARS_1M_SCHEMA,
    GENERATOR_VERSION,
    MBP1_SCHEMA,
    SCHEMA_VERSION,
    TBBO_SCHEMA,
    DataSchema,
)

__all__ = [
    "BARS_1M_SCHEMA",
    "DataSchema",
    "GENERATOR_VERSION",
    "MBP1_SCHEMA",
    "SCHEMA_VERSION",
    "TBBO_SCHEMA",
    "read_bars",
    "read_mbp1",
    "read_tbbo",
]
