"""Pydantic schemas for the datasets registry."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Vocabulary surfaced via /api/datasets/sources etc. would go here later;
# for now these are documented by usage in the model + endpoint code.
DATASET_SOURCES: tuple[str, ...] = ("live", "historical", "imported")
DATASET_KINDS: tuple[str, ...] = ("dbn", "parquet")


class DatasetRead(BaseModel):
    # populate_by_name lets the ORM attribute "schema" map into our
    # internal "data_schema" field; the JSON serialization keeps "schema"
    # as the public key via the alias. Avoids shadowing BaseModel.schema().
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: int
    file_path: str
    dataset_code: str
    data_schema: str = Field(..., alias="schema")
    symbol: str | None
    source: str
    kind: str
    start_ts: datetime | None
    end_ts: datetime | None
    file_size_bytes: int
    row_count: int | None
    sha256: str | None
    last_seen_at: datetime
    created_at: datetime


class DatasetScanResult(BaseModel):
    """POST /api/datasets/scan response — summary of what changed."""

    scanned: int = Field(..., description="files walked")
    added: int = Field(..., description="new rows inserted")
    updated: int = Field(..., description="existing rows whose size/mtime changed")
    removed: int = Field(..., description="rows for files that no longer exist on disk")
    skipped: int = Field(..., description="files skipped (e.g. recently-modified, in-progress)")
    errors: list[str] = Field(default_factory=list)


class DatasetCoverageRow(BaseModel):
    """One row in the per-(symbol, schema, kind) coverage rollup.

    `data_schema` shadows nothing on BaseModel because we expose the
    JSON key as "schema" via the alias — same trick `DatasetRead` uses.
    """

    model_config = ConfigDict(populate_by_name=True)

    symbol: str | None
    data_schema: str = Field(..., alias="schema")
    kind: str
    partition_count: int
    total_bytes: int
    earliest_date: date | None
    latest_date: date | None
    last_seen_at: datetime | None
    stale_data: bool


class DatasetCoverageRead(BaseModel):
    """GET /api/datasets/coverage response."""

    rows: list[DatasetCoverageRow]
    last_scan_at: datetime | None
    generated_at: datetime


class DatasetReadinessRead(BaseModel):
    """GET /api/datasets/readiness response — does a backtest range
    have all the 1m bars it needs?

    `available_days` lists every date present in the registry within
    the requested range, including weekend partitions if any. Only
    `missing_days` filters weekends — see endpoint docstring.
    """

    ready: bool
    symbol: str
    timeframe: str
    source_schema: Literal["ohlcv-1m"]
    start: date
    end: date
    available_days: list[date]
    missing_days: list[date]
    latest_available_date: date | None
    message: str
