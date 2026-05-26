"""Upload BacktestStation research artifacts to Cloudflare R2.

`r2_upload.py` mirrors the raw/read-side warehouse (`raw/databento` and
`processed/bars`). This module mirrors the derived research lake:

  - data/ml/          feature matrices, anchor matrices, catalogs, contexts
  - data/research/    curated research source files
  - data/research_events/  parquet export of the research_events table
  - exports/*.zip     exact strategy-lab packages
  - experiments/      optional backtest/GPU result artifacts

The bucket stays private. Friends get read-only R2 credentials; write keys stay
on trusted builder machines.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from app.ingest.r2_client import (
    make_s3_client,
    object_exists_with_size,
    put_json,
    upload_file,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
INVENTORY_KEY = "_research_inventory.json"
RUN_LOG_NAME = "r2_artifact_upload_runs.json"
RUN_LOG_KEEP = 200
DEFAULT_EXCLUDES = (
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".DS_Store",
    "*.tmp",
    "*.bak",
    "*.lock",
    "tmp",
    "tmp_*",
    "*_tmp",
    "tmp_patch",
    "*.patch",
)


@dataclass(frozen=True)
class ArtifactSpec:
    name: str
    source: Path
    key_prefix: str
    recursive: bool = True
    patterns: tuple[str, ...] = ("**/*",)
    required: bool = False


@dataclass(frozen=True)
class Artifact:
    group: str
    local_path: Path
    rel_path: str
    r2_key: str
    size: int
    mtime_utc: str
    sha256: str | None = None


@dataclass
class UploadStats:
    enumerated: int = 0
    uploaded: int = 0
    skipped_existing: int = 0
    skipped_missing_roots: int = 0
    inventory_items: int = 0
    bytes_seen: int = 0
    bytes_uploaded: int = 0
    errors: list[str] = field(default_factory=list)


def _posix(path: Path) -> str:
    return path.as_posix()


def _default_specs(*, include_experiments: bool, include_sqlite: bool) -> list[ArtifactSpec]:
    specs = [
        ArtifactSpec("ml", REPO_ROOT / "data" / "ml", "data/ml"),
        ArtifactSpec("research", REPO_ROOT / "data" / "research", "data/research", required=False),
        ArtifactSpec(
            "research_events",
            REPO_ROOT / "data" / "research_events",
            "data/research_events",
            required=False,
        ),
        ArtifactSpec(
            "exports",
            REPO_ROOT / "exports",
            "exports",
            patterns=("*.zip",),
            required=False,
        ),
        ArtifactSpec(
            "export_index",
            REPO_ROOT / "strategy_lab" / "EXPORT_INDEX.json",
            "strategy_lab/EXPORT_INDEX.json",
            recursive=False,
            required=False,
        ),
    ]
    if include_experiments:
        specs.append(
            ArtifactSpec("experiments", REPO_ROOT / "experiments", "experiments", required=False)
        )
    if include_sqlite:
        specs.append(
            ArtifactSpec(
                "meta_sqlite_snapshot",
                REPO_ROOT / "data" / "meta.sqlite",
                "data/meta.sqlite",
                recursive=False,
                required=False,
            )
        )
    return specs


def _excluded(path: Path, root: Path, excludes: Iterable[str]) -> bool:
    rel = _posix(path.relative_to(root)) if path != root else path.name
    parts = path.parts
    for pattern in excludes:
        if any(fnmatch.fnmatch(part, pattern) for part in parts):
            return True
        if fnmatch.fnmatch(rel, pattern):
            return True
    return False


def _excluded_r2_key(key: str, excludes: Iterable[str]) -> bool:
    parts = key.split("/")
    for pattern in excludes:
        if any(fnmatch.fnmatch(part, pattern) for part in parts):
            return True
        if fnmatch.fnmatch(key, pattern):
            return True
    return False


def _matches(path: Path, root: Path, patterns: Iterable[str]) -> bool:
    rel = _posix(path.relative_to(root))
    for pattern in patterns:
        if fnmatch.fnmatch(rel, pattern):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatch(rel, pattern[3:]):
            return True
    return False


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _artifact_from_file(
    *,
    spec: ArtifactSpec,
    file_path: Path,
    source_root: Path,
    repo_root: Path,
    with_hash: bool,
) -> Artifact:
    stat = file_path.stat()
    if spec.source.is_file():
        rel_path = _posix(spec.source.relative_to(repo_root))
        r2_key = spec.key_prefix.rstrip("/")
    else:
        rel_under_source = _posix(file_path.relative_to(source_root))
        rel_path = _posix(file_path.relative_to(repo_root))
        r2_key = f"{spec.key_prefix.rstrip('/')}/{rel_under_source}"
    mtime = dt.datetime.fromtimestamp(stat.st_mtime, tz=dt.timezone.utc).isoformat()
    return Artifact(
        group=spec.name,
        local_path=file_path,
        rel_path=rel_path,
        r2_key=r2_key,
        size=int(stat.st_size),
        mtime_utc=mtime,
        sha256=_sha256(file_path) if with_hash else None,
    )


def enumerate_artifacts(
    specs: list[ArtifactSpec],
    *,
    excludes: Iterable[str] = DEFAULT_EXCLUDES,
    with_hash: bool = False,
    repo_root: Path = REPO_ROOT,
) -> tuple[list[Artifact], int]:
    artifacts: list[Artifact] = []
    missing_roots = 0
    for spec in specs:
        source = spec.source
        if not source.exists():
            if spec.required:
                raise FileNotFoundError(source)
            missing_roots += 1
            continue
        if source.is_file():
            if not _excluded(source, source.parent, excludes):
                artifacts.append(
                    _artifact_from_file(
                        spec=spec,
                        file_path=source,
                        source_root=source.parent,
                        repo_root=repo_root,
                        with_hash=with_hash,
                    )
                )
            continue
        paths = source.rglob("*") if spec.recursive else source.glob("*")
        for path in paths:
            if not path.is_file():
                continue
            if _excluded(path, source, excludes):
                continue
            if not _matches(path, source, spec.patterns):
                continue
            artifacts.append(
                _artifact_from_file(
                    spec=spec,
                    file_path=path,
                    source_root=source,
                    repo_root=repo_root,
                    with_hash=with_hash,
                )
            )
    artifacts.sort(key=lambda item: item.r2_key)
    return artifacts, missing_roots


def _inventory_payload(artifacts: list[Artifact], *, profile: str, dry_run: bool) -> dict:
    groups: dict[str, dict[str, int]] = {}
    for item in artifacts:
        group = groups.setdefault(item.group, {"files": 0, "bytes": 0})
        group["files"] += 1
        group["bytes"] += item.size
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "schema_version": 1,
        "profile": profile,
        "dry_run": dry_run,
        "repo_root": str(REPO_ROOT),
        "file_count": len(artifacts),
        "total_bytes": sum(item.size for item in artifacts),
        "groups": groups,
        "artifacts": [
            {
                "group": item.group,
                "local_path": item.rel_path,
                "r2_key": item.r2_key,
                "size": item.size,
                "mtime_utc": item.mtime_utc,
                **({"sha256": item.sha256} if item.sha256 else {}),
            }
            for item in artifacts
        ],
    }


def _is_exact_key_spec(spec: ArtifactSpec) -> bool:
    """Return true for file-backed specs that should scan an exact R2 key."""
    if spec.source.exists():
        return spec.source.is_file()
    return not spec.recursive and bool(spec.source.suffix)


def _discover_r2_only_artifacts(
    client: Any,
    bucket: str,
    specs: list[ArtifactSpec],
    local_keys: set[str],
) -> list[Artifact]:
    """Return R2 objects under managed prefixes that are absent locally.

    Publishing from one PC must not delete another PC's artifacts from
    `_research_inventory.json`. This keeps inventory equal to the union of
    local artifacts plus matching objects already present in R2.
    """
    found_by_key: dict[str, Artifact] = {}
    paginator = client.get_paginator("list_objects_v2")
    for spec in specs:
        prefix = spec.key_prefix.rstrip("/")
        if not prefix:
            continue
        scan_prefix = prefix if _is_exact_key_spec(spec) else prefix + "/"
        for page in paginator.paginate(Bucket=bucket, Prefix=scan_prefix):
            for obj in page.get("Contents", []):
                key = str(obj.get("Key", ""))
                if not key or key in local_keys or key == INVENTORY_KEY:
                    continue
                if _excluded_r2_key(key, DEFAULT_EXCLUDES):
                    continue
                last_modified = obj.get("LastModified")
                if isinstance(last_modified, dt.datetime):
                    if last_modified.tzinfo is None:
                        last_modified = last_modified.replace(tzinfo=dt.timezone.utc)
                    mtime_utc = last_modified.isoformat()
                else:
                    mtime_utc = dt.datetime.now(dt.timezone.utc).isoformat()
                found_by_key[key] = Artifact(
                    group=spec.name,
                    local_path=Path("<r2-only>"),
                    rel_path=key,
                    r2_key=key,
                    size=int(obj.get("Size", 0)),
                    mtime_utc=mtime_utc,
                    sha256=None,
                )
    return [found_by_key[key] for key in sorted(found_by_key)]


def run(
    *,
    profile: str = "core",
    dry_run: bool = False,
    rebuild: bool = False,
    limit: int | None = None,
    with_hash: bool = False,
    include_sqlite: bool = False,
) -> UploadStats:
    include_experiments = profile in {"experiments", "all"}
    include_core = profile in {"core", "all"}
    if profile not in {"core", "experiments", "all"}:
        raise ValueError("profile must be one of: core, experiments, all")

    specs: list[ArtifactSpec] = []
    if include_core:
        specs.extend(_default_specs(include_experiments=False, include_sqlite=include_sqlite))
    if include_experiments:
        specs.append(ArtifactSpec("experiments", REPO_ROOT / "experiments", "experiments", required=False))

    artifacts, missing_roots = enumerate_artifacts(
        specs,
        with_hash=with_hash,
        repo_root=REPO_ROOT,
    )
    stats = UploadStats(
        enumerated=len(artifacts),
        skipped_missing_roots=missing_roots,
        bytes_seen=sum(item.size for item in artifacts),
    )
    if dry_run:
        stats.inventory_items = len(artifacts)
        _persist_run_summary(stats, dry_run=True, profile=profile)
        return stats

    client, bucket = make_s3_client()
    uploaded_or_existing: list[Artifact] = []
    for item in artifacts:
        already_present = not rebuild and object_exists_with_size(
            client, bucket, item.r2_key, item.size
        )
        if already_present:
            stats.skipped_existing += 1
            uploaded_or_existing.append(item)
            continue
        if limit is not None and stats.uploaded >= limit:
            continue
        try:
            upload_file(client, bucket, item.local_path, item.r2_key)
            stats.uploaded += 1
            stats.bytes_uploaded += item.size
            uploaded_or_existing.append(item)
            logger.info("UPLOADED %s (%s bytes)", item.r2_key, item.size)
        except Exception as e:
            stats.errors.append(f"{item.r2_key}: {e}")
            logger.error("UPLOAD FAILED %s: %s", item.r2_key, e)

    local_keys = {item.r2_key for item in uploaded_or_existing}
    r2_only = _discover_r2_only_artifacts(client, bucket, specs, local_keys)
    inventory_artifacts = uploaded_or_existing + r2_only

    put_json(
        client,
        bucket,
        INVENTORY_KEY,
        _inventory_payload(inventory_artifacts, profile=profile, dry_run=False),
    )
    stats.inventory_items = len(inventory_artifacts)
    _persist_run_summary(stats, dry_run=False, profile=profile)
    return stats


def _persist_run_summary(stats: UploadStats, *, dry_run: bool, profile: str) -> None:
    log_dir = REPO_ROOT / "data" / "ml" / "logs"
    runs_path = log_dir / RUN_LOG_NAME
    summaries: list[dict] = []
    if runs_path.exists():
        try:
            loaded = json.loads(runs_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                summaries = loaded
        except Exception:
            pass
    summaries.append(
        {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "profile": profile,
            "dry_run": dry_run,
            "enumerated": stats.enumerated,
            "uploaded": stats.uploaded,
            "skipped_existing": stats.skipped_existing,
            "skipped_missing_roots": stats.skipped_missing_roots,
            "inventory_items": stats.inventory_items,
            "bytes_seen": stats.bytes_seen,
            "bytes_uploaded": stats.bytes_uploaded,
            "errors": stats.errors[:10],
        }
    )
    summaries = summaries[-RUN_LOG_KEEP:]
    log_dir.mkdir(parents=True, exist_ok=True)
    runs_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")


def _fmt_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("core", "experiments", "all"), default="core")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--hash", action="store_true", help="include sha256 for every artifact in inventory")
    parser.add_argument(
        "--include-sqlite",
        action="store_true",
        help="also upload data/meta.sqlite; prefer parquet research_events export when possible",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    stats = run(
        profile=args.profile,
        dry_run=args.dry_run,
        rebuild=args.rebuild,
        limit=args.limit,
        with_hash=args.hash,
        include_sqlite=args.include_sqlite,
    )
    print(
        f"profile={args.profile} dry_run={args.dry_run} "
        f"enumerated={stats.enumerated} uploaded={stats.uploaded} "
        f"skipped_existing={stats.skipped_existing} "
        f"inventory_items={stats.inventory_items} "
        f"bytes_seen={_fmt_bytes(stats.bytes_seen)} "
        f"bytes_uploaded={_fmt_bytes(stats.bytes_uploaded)} "
        f"errors={len(stats.errors)}"
    )
    return 1 if stats.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
