"""Download research artifacts from the private R2 data lake.

This is the read-side companion to `app.ingest.r2_artifacts`. It reads
`_research_inventory.json`, downloads selected artifacts, and preserves the
repo-relative paths recorded by the uploader.

It never deletes local files. If R2 no longer has an artifact, any old local
copy remains until an operator removes it intentionally.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterable

from app.ingest.r2_artifacts import INVENTORY_KEY
from app.ingest.r2_client import make_s3_client

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SUMMARY = REPO_ROOT / "data" / "ml" / "logs" / "r2_artifact_download_last.json"


@dataclass(frozen=True)
class RemoteArtifact:
    group: str
    local_path: str
    r2_key: str
    size: int
    mtime_utc: str | None = None


@dataclass
class DownloadStats:
    inventory_generated_at: str | None = None
    inventory_files: int = 0
    selected: int = 0
    downloaded: int = 0
    skipped_existing: int = 0
    would_download: int = 0
    bytes_selected: int = 0
    bytes_downloaded: int = 0
    bytes_would_download: int = 0
    errors: list[str] = field(default_factory=list)


def _parse_csv(value: str | None) -> set[str] | None:
    if value is None or not value.strip():
        return None
    return {part.strip() for part in value.split(",") if part.strip()}


def _as_artifacts(inventory: dict[str, Any]) -> list[RemoteArtifact]:
    artifacts = inventory.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("_research_inventory.json has no artifact list")
    out: list[RemoteArtifact] = []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        try:
            out.append(
                RemoteArtifact(
                    group=str(item["group"]),
                    local_path=str(item["local_path"]),
                    r2_key=str(item["r2_key"]),
                    size=int(item["size"]),
                    mtime_utc=item.get("mtime_utc"),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _matches_any(value: str, patterns: Iterable[str] | None) -> bool:
    if patterns is None:
        return True
    return any(fnmatch.fnmatchcase(value, pattern) for pattern in patterns)


def _select_artifacts(
    artifacts: list[RemoteArtifact],
    *,
    groups: set[str] | None,
    prefixes: set[str] | None,
    key_patterns: set[str] | None,
) -> list[RemoteArtifact]:
    selected: list[RemoteArtifact] = []
    for item in artifacts:
        if groups is not None and item.group not in groups:
            continue
        if prefixes is not None and not any(item.r2_key.startswith(prefix) for prefix in prefixes):
            continue
        if not _matches_any(item.r2_key, key_patterns):
            continue
        selected.append(item)
    return selected


def _target_path(dest_root: Path, local_path: str) -> Path:
    target = (dest_root / local_path).resolve()
    root = dest_root.resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"refusing to write outside destination root: {target}")
    return target


def _already_current(path: Path, expected_size: int) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size == expected_size


def _download_one(client: Any, bucket: str, key: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(prefix=target.name + ".", suffix=".tmp", dir=target.parent, delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        client.download_file(bucket, key, str(tmp_path))
        os.replace(tmp_path, target)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _summary_payload(
    *,
    stats: DownloadStats,
    dry_run: bool,
    dest_root: Path,
    groups: set[str] | None,
    prefixes: set[str] | None,
    key_patterns: set[str] | None,
    selected: list[RemoteArtifact],
) -> dict[str, Any]:
    return {
        "dry_run": dry_run,
        "dest_root": str(dest_root),
        "filters": {
            "groups": sorted(groups) if groups else None,
            "prefixes": sorted(prefixes) if prefixes else None,
            "key_patterns": sorted(key_patterns) if key_patterns else None,
        },
        "stats": {
            "inventory_generated_at": stats.inventory_generated_at,
            "inventory_files": stats.inventory_files,
            "selected": stats.selected,
            "downloaded": stats.downloaded,
            "skipped_existing": stats.skipped_existing,
            "would_download": stats.would_download,
            "bytes_selected": stats.bytes_selected,
            "bytes_downloaded": stats.bytes_downloaded,
            "bytes_would_download": stats.bytes_would_download,
            "errors": stats.errors,
        },
        "selected_artifacts": [
            {
                "group": item.group,
                "local_path": item.local_path,
                "r2_key": item.r2_key,
                "size": item.size,
                "mtime_utc": item.mtime_utc,
            }
            for item in selected
        ],
    }


def _write_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> DownloadStats:
    client, bucket = make_s3_client()
    obj = client.get_object(Bucket=bucket, Key=INVENTORY_KEY)
    inventory = json.loads(obj["Body"].read())
    if not isinstance(inventory, dict):
        raise ValueError("_research_inventory.json root is not an object")

    groups = _parse_csv(args.groups)
    prefixes = _parse_csv(args.prefixes)
    key_patterns = _parse_csv(args.keys)
    artifacts = _as_artifacts(inventory)
    selected = _select_artifacts(
        artifacts,
        groups=groups,
        prefixes=prefixes,
        key_patterns=key_patterns,
    )
    if args.limit is not None:
        selected = selected[: args.limit]

    stats = DownloadStats(
        inventory_generated_at=inventory.get("generated_at"),
        inventory_files=int(inventory.get("file_count") or len(artifacts)),
        selected=len(selected),
        bytes_selected=sum(item.size for item in selected),
    )

    dest_root = args.dest_root.resolve()
    for item in selected:
        try:
            target = _target_path(dest_root, item.local_path)
            if _already_current(target, item.size):
                stats.skipped_existing += 1
                continue
            if args.dry_run:
                stats.would_download += 1
                stats.bytes_would_download += item.size
                continue
            _download_one(client, bucket, item.r2_key, target)
            stats.downloaded += 1
            stats.bytes_downloaded += item.size
        except Exception as exc:
            stats.errors.append(f"{item.r2_key}: {type(exc).__name__}: {exc}")

    if args.summary:
        payload = _summary_payload(
            stats=stats,
            dry_run=args.dry_run,
            dest_root=dest_root,
            groups=groups,
            prefixes=prefixes,
            key_patterns=key_patterns,
            selected=selected,
        )
        _write_summary(args.summary, payload)
    return stats


def _fmt_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--groups", default=None, help="Comma-separated inventory groups, e.g. ml,research_events")
    parser.add_argument("--prefixes", default=None, help="Comma-separated R2 key prefixes")
    parser.add_argument("--keys", default=None, help="Comma-separated fnmatch patterns for R2 keys")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    stats = run(args)
    print(
        f"inventory_generated_at={stats.inventory_generated_at} "
        f"inventory_files={stats.inventory_files} selected={stats.selected} "
        f"downloaded={stats.downloaded} skipped_existing={stats.skipped_existing} "
        f"would_download={stats.would_download} "
        f"bytes_selected={_fmt_bytes(stats.bytes_selected)} "
        f"bytes_downloaded={_fmt_bytes(stats.bytes_downloaded)} "
        f"bytes_would_download={_fmt_bytes(stats.bytes_would_download)} "
        f"errors={len(stats.errors)}"
    )
    if args.summary:
        print(f"wrote {args.summary}")
    return 1 if stats.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
