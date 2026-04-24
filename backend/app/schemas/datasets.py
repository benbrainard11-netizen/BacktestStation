"""Pydantic schemas for the datasets registry."""

from datetime import datetime

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
