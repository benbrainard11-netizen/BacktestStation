"""Daily MBO-to-R2 mirror orchestration.

This module intentionally does not call Databento. It only validates and
uploads local MBO parquet that already exists under BS_DATA_ROOT.

Flow:
  1. Run r2_upload in dry-run mode for schema=mbo.
  2. Abort if no MBO partitions exist or any partition is refused.
  3. Run r2_upload for schema=mbo, which merges MBO entries into the existing
     R2 inventory instead of rebuilding from this machine's partial disk view.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.core.paths import warehouse_root
from app.ingest import r2_upload
from app.ingest.r2_upload import UploadStats

logger = logging.getLogger(__name__)

RUN_LOG_NAME = "mbo_r2_mirror_runs.json"
MBO_SCHEMA_FILTER = {"mbo"}


@dataclass
class MboMirrorResult:
    dry_run: UploadStats
    upload: UploadStats | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def run(
    *,
    dry_run_only: bool = False,
    allow_empty: bool = False,
    log_to_file: bool = True,
) -> MboMirrorResult:
    """Validate and optionally upload local MBO partitions to R2."""
    root = warehouse_root()
    handler: logging.Handler | None = None
    if log_to_file:
        log_dir = root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_dir / "mbo_r2_mirror.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    result = MboMirrorResult(dry_run=UploadStats())
    try:
        logger.info("=== mbo_r2_mirror start | dry_run_only=%s", dry_run_only)
        try:
            dry_stats = r2_upload.run(dry_run=True, schemas=MBO_SCHEMA_FILTER)
        except Exception as exc:
            result.errors.append(f"dry-run failed: {type(exc).__name__}: {exc}")
            return result
        result.dry_run = dry_stats

        if dry_stats.errors:
            result.errors.extend(f"dry-run error: {err}" for err in dry_stats.errors)
        if dry_stats.refused:
            result.errors.append(f"dry-run refused {dry_stats.refused} MBO partitions")
        if dry_stats.enumerated == 0 and not allow_empty:
            result.errors.append("no local MBO partitions found under BS_DATA_ROOT")

        if result.errors or dry_run_only or dry_stats.enumerated == 0:
            return result

        try:
            upload_stats = r2_upload.run(dry_run=False, schemas=MBO_SCHEMA_FILTER)
        except Exception as exc:
            result.errors.append(f"upload failed: {type(exc).__name__}: {exc}")
            return result
        result.upload = upload_stats
        if upload_stats.errors:
            result.errors.extend(f"upload error: {err}" for err in upload_stats.errors)
        if upload_stats.refused:
            result.errors.append(f"upload refused {upload_stats.refused} MBO partitions")
        return result
    finally:
        _persist_run_summary(root, result, dry_run_only=dry_run_only)
        logger.info(
            "=== mbo_r2_mirror done | ok=%s dry_enumerated=%s dry_refused=%s "
            "uploaded=%s skipped_existing=%s errors=%s",
            result.ok,
            result.dry_run.enumerated,
            result.dry_run.refused,
            result.upload.uploaded if result.upload else 0,
            result.upload.skipped_existing if result.upload else 0,
            len(result.errors),
        )
        if handler is not None:
            logger.removeHandler(handler)
            handler.close()


def _stats_dict(stats: UploadStats | None) -> dict | None:
    if stats is None:
        return None
    return asdict(stats)


def _persist_run_summary(
    root: Path,
    result: MboMirrorResult,
    *,
    dry_run_only: bool,
) -> None:
    runs_path = root / "logs" / RUN_LOG_NAME
    summaries: list[dict] = []
    if runs_path.exists():
        try:
            loaded = json.loads(runs_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                summaries = loaded
        except Exception:
            summaries = []

    summaries.append(
        {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "dry_run_only": dry_run_only,
            "ok": result.ok,
            "dry_run": _stats_dict(result.dry_run),
            "upload": _stats_dict(result.upload),
            "errors": result.errors[:20],
        }
    )
    summaries = summaries[-200:]
    runs_path.parent.mkdir(parents=True, exist_ok=True)
    runs_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and mirror local MBO parquet to Cloudflare R2."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate local MBO only; do not upload",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="return success when no local MBO partitions are present",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    result = run(dry_run_only=args.dry_run, allow_empty=args.allow_empty)
    upload = result.upload
    print(
        "ok={ok} dry_enumerated={dry_enumerated} dry_refused={dry_refused} "
        "uploaded={uploaded} skipped_existing={skipped_existing} errors={errors}".format(
            ok=result.ok,
            dry_enumerated=result.dry_run.enumerated,
            dry_refused=result.dry_run.refused,
            uploaded=upload.uploaded if upload else 0,
            skipped_existing=upload.skipped_existing if upload else 0,
            errors=len(result.errors),
        )
    )
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
