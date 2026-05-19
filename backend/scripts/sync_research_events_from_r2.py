"""One-off: pull research_events parquet artifacts from R2 to local.

Reads the _research_inventory.json from R2, filters to the
research_events group, downloads any artifacts that don't already
exist locally (matched by sha256 if present, else by size+mtime).

Usage:
    cd backend
    python scripts/sync_research_events_from_r2.py --dry-run
    python scripts/sync_research_events_from_r2.py
    python scripts/sync_research_events_from_r2.py --feature macro_event_anchor

This is intentionally not the canonical R2 reader -- that's in
`app.ingest.r2_artifacts_download` on the main branch (commit fbc5f8f).
This script is a stripped-down version that works against the inventory
naming used by this branch (`_research_inventory.json`, group="research_events").
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ingest.r2_client import make_s3_client  # noqa: E402


RESEARCH_INVENTORY_KEY = "_research_inventory.json"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", default=None,
                        help="Limit to a single feature_name=X (e.g. 'macro_event_anchor').")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dest-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()

    client, bucket = make_s3_client()
    print(f"Reading inventory from r2://{bucket}/{RESEARCH_INVENTORY_KEY}")
    obj = client.get_object(Bucket=bucket, Key=RESEARCH_INVENTORY_KEY)
    inv = json.loads(obj["Body"].read())
    print(f"  generated_at: {inv['generated_at']}")
    print(f"  total artifacts in inventory: {inv['file_count']}")

    artifacts = [
        a for a in inv["artifacts"]
        if a.get("group") == "research_events"
    ]
    if args.feature:
        marker = f"feature_name={args.feature}/"
        artifacts = [a for a in artifacts if marker in a.get("r2_key", "")]
    print(f"  research_events artifacts (filtered): {len(artifacts)}")
    if not artifacts:
        print("nothing to do")
        return 0

    n_downloaded = 0
    n_skipped = 0
    n_planned = 0
    bytes_downloaded = 0
    for a in artifacts:
        local_path = args.dest_root / a["local_path"]
        r2_key = a["r2_key"]
        size = int(a.get("size", 0))
        expected_sha = a.get("sha256")
        # Skip if local already matches
        if local_path.exists():
            ok = True
            if local_path.stat().st_size != size:
                ok = False
            if ok and expected_sha:
                # SHA256 check is expensive; only do it if size matches
                if _sha256(local_path) != expected_sha:
                    ok = False
            if ok:
                n_skipped += 1
                continue

        n_planned += 1
        if args.dry_run:
            print(f"  WOULD DOWNLOAD: {r2_key} -> {local_path} ({size:,} bytes)")
            continue

        # Download to a temp file, then move into place
        local_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = local_path.with_suffix(local_path.suffix + ".tmp")
        try:
            client.download_file(bucket, r2_key, str(tmp_path))
            tmp_path.replace(local_path)
            n_downloaded += 1
            bytes_downloaded += size
            print(f"  downloaded: {r2_key} ({size:,} bytes)")
        except Exception as exc:
            print(f"  FAILED: {r2_key}: {exc}")
            if tmp_path.exists():
                tmp_path.unlink()

    print()
    print(f"Summary:")
    print(f"  skipped (already up-to-date): {n_skipped}")
    if args.dry_run:
        print(f"  would download: {n_planned}")
    else:
        print(f"  downloaded: {n_downloaded}")
        print(f"  bytes downloaded: {bytes_downloaded:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
