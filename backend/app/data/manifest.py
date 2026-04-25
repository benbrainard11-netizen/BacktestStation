"""Read/write/validate ingest-run manifest JSON files.

Manifests live at:

    {BS_DATA_ROOT}/manifests/ingest_runs/{date}_{schema}_manifest.json

One manifest per (UTC date, data schema). Records the source DBN, all
parquet outputs produced (raw + bars), validation results, generator
metadata, and final status. Independent audit trail — files on disk
remain the source of truth, manifests are the ledger.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

ManifestStatus = Literal["complete", "partial", "failed"]
OutputKind = Literal["raw_parquet", "bars_1m", "features"]


@dataclass
class ManifestSource:
    kind: str  # "dbn"
    path: str  # absolute or warehouse-relative
    sha256: str
    size_bytes: int


@dataclass
class ManifestOutput:
    kind: str  # OutputKind
    schema: str | None  # "tbbo" / "mbp-1" / "ohlcv-1m" — None for features for now
    symbol: str
    path: str
    rows: int
    size_bytes: int
    ts_event_min: str | None = None
    ts_event_max: str | None = None
    sha256: str | None = None


@dataclass
class ManifestValidation:
    row_count_ok: bool
    schema_columns_ok: bool
    duplicate_ts_event_count: int
    monotonic_ts_event: bool
    warnings: list[str] = field(default_factory=list)


@dataclass
class ManifestGenerator:
    name: str
    version: str
    started_at: str  # ISO 8601 UTC
    completed_at: str | None = None  # set when run finishes


@dataclass
class IngestManifest:
    schema_version: int
    date: str  # YYYY-MM-DD UTC
    data_schema: str  # "tbbo" / "mbp-1"
    source: ManifestSource
    outputs: list[ManifestOutput]
    validation: ManifestValidation
    generator: ManifestGenerator
    status: ManifestStatus
    errors: list[str] = field(default_factory=list)


# --- IO ----------------------------------------------------------------


def manifest_path(data_root: Path, date: str, data_schema: str) -> Path:
    return (
        data_root
        / "manifests"
        / "ingest_runs"
        / f"{date}_{data_schema}_manifest.json"
    )


def write_manifest(data_root: Path, manifest: IngestManifest) -> Path:
    """Write atomically (tmp + rename). Returns the path written."""
    target = manifest_path(data_root, manifest.date, manifest.data_schema)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".json.tmp")
    payload = asdict(manifest)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=_json_default)
    tmp.replace(target)
    return target


def read_manifest(path: Path) -> IngestManifest:
    """Load a manifest from disk. Raises if malformed."""
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    return IngestManifest(
        schema_version=payload["schema_version"],
        date=payload["date"],
        data_schema=payload["data_schema"],
        source=ManifestSource(**payload["source"]),
        outputs=[ManifestOutput(**o) for o in payload.get("outputs", [])],
        validation=ManifestValidation(**payload["validation"]),
        generator=ManifestGenerator(**payload["generator"]),
        status=payload["status"],
        errors=payload.get("errors", []),
    )


def _json_default(obj: object) -> object:
    if isinstance(obj, (dt.date, dt.datetime)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"not JSON-serializable: {type(obj).__name__}")


# --- Helpers for producers ----------------------------------------------


def sha256_of_file(path: Path, *, chunk_size: int = 64 * 1024) -> str:
    """Stream sha256 of a file. Used by producers when filling Manifest.source."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def now_utc_iso() -> str:
    """ISO-8601 UTC timestamp suitable for manifest fields."""
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def ts_event_to_iso(ts: dt.datetime | None) -> str | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.isoformat()


def relative_to_root(path: Path, data_root: Path) -> str:
    """Render `path` relative to `data_root` if possible, else absolute."""
    try:
        return str(path.relative_to(data_root))
    except ValueError:
        return str(path)


def validate_manifest_status(m: IngestManifest) -> str | None:
    """Cheap consistency check on a manifest. Returns error string or None."""
    if m.status == "complete":
        if not m.validation.row_count_ok or not m.validation.schema_columns_ok:
            return "status=complete but validation.*_ok=False"
        if m.errors:
            return "status=complete but errors[] non-empty"
    if m.status == "failed" and not m.errors:
        return "status=failed but errors[] empty"
    return None


# Make the env-var resolver callable both from this module and producers.
def data_root_from_env() -> Path:
    default = "C:/data" if os.name == "nt" else "./data"
    return Path(os.environ.get("BS_DATA_ROOT", default))
