"""Rebuild and publish the strategy-lab export in one controlled flow.

Typical source-machine use:

  python strategy_lab/sync_export_to_github.py --all --name strategy_lab_core_2026_05_13

This will:

  1. Build a fresh export folder + zip under /exports
  2. Update strategy_lab/EXPORT_INDEX.json to point at the new package
  3. Commit the index update
  4. Push main
  5. Publish/update the GitHub Release asset

Use --verify-current to check the current repo index against the local zip and
GitHub Release without changing anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UTC = timezone.utc
THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent
EXPORT_INDEX = THIS_DIR / "EXPORT_INDEX.json"
EXPORTS_DIR = REPO_ROOT / "exports"


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(cmd))
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=False,
        check=check,
    )


def _capture(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _default_name() -> str:
    return f"strategy_lab_core_{datetime.now(UTC).strftime('%Y_%m_%d')}"


def _tag_for_name(name: str) -> str:
    return name.replace("_", "-")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _build_export(name: str, *, force: bool) -> tuple[Path, Path]:
    cmd = [
        sys.executable,
        "backend/scripts/ml/export_strategy_lab.py",
        "--name",
        name,
        "--zip",
    ]
    if force:
        cmd.append("--force")
    _run(cmd)
    export_root = EXPORTS_DIR / name
    zip_path = EXPORTS_DIR / f"{name}.zip"
    if not export_root.exists():
        raise FileNotFoundError(export_root)
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    return export_root, zip_path


def _index_from_export(export_root: Path, zip_path: Path) -> dict[str, Any]:
    manifest = _load_json(export_root / "MANIFEST.json")
    zip_hash = _sha256(zip_path)
    package = export_root.name
    datasets = []
    for dataset in manifest["datasets"]:
        datasets.append(
            {
                "name": dataset["name"],
                "matrix": dataset["matrix"],
                "schema": dataset["schema"],
                "rows": dataset["rows"],
                "feature_column_count": dataset["feature_column_count"],
                "label_column_count": dataset["label_column_count"],
            }
        )

    generated = manifest.get("generated_utc") or datetime.now(UTC).isoformat()
    generated_date = generated.split("T", 1)[0]
    return {
        "current_package": package,
        "zip_name": zip_path.name,
        "release_tag": _tag_for_name(package),
        "source_machine_path": str(zip_path),
        "size_bytes": int(zip_path.stat().st_size),
        "sha256": zip_hash,
        "generated_utc": generated,
        "generated_local_date": generated_date,
        "datasets": datasets,
        "rules": [
            "Use each schema JSON's feature_columns as model inputs.",
            "Never use label.* columns as model inputs.",
            "Prefer walk-forward summaries over one-split leaderboards.",
            "Completed VP artifacts are completed-period profiles, not live forming VP.",
        ],
    }


def _update_index(export_root: Path, zip_path: Path) -> None:
    index = _index_from_export(export_root, zip_path)
    _write_json(EXPORT_INDEX, index)
    print(f"updated {EXPORT_INDEX}")


def _commit_index(message: str) -> None:
    _run(["git", "add", "--", "strategy_lab/EXPORT_INDEX.json"])
    diff = _capture(["git", "diff", "--cached", "--quiet"], check=False)
    if diff.returncode == 0:
        print("no staged EXPORT_INDEX changes to commit")
        return
    _run(["git", "commit", "-m", message])


def _push_main() -> None:
    _run(["git", "push", "origin", "main"])


def _publish(zip_path: Path, tag: str, title: str) -> None:
    _run([
        sys.executable,
        "strategy_lab/publish_export_release.py",
        "--zip",
        str(zip_path),
        "--tag",
        tag,
        "--title",
        title,
    ])


def _verify_current() -> None:
    index = _load_json(EXPORT_INDEX)
    zip_path = Path(index["source_machine_path"])
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    actual_hash = _sha256(zip_path)
    if actual_hash != index["sha256"]:
        raise ValueError(
            f"local zip checksum mismatch: expected {index['sha256']}, got {actual_hash}"
        )
    print(f"local zip OK: {zip_path}")
    print(f"sha256={actual_hash}")

    tag = index.get("release_tag") or _tag_for_name(index["current_package"])
    proc = _capture(["gh", "release", "view", tag, "--json", "tagName,assets,url"], check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"release not found or gh auth failed for tag {tag}:\n{proc.stderr}")
    release = json.loads(proc.stdout)
    asset = next((a for a in release["assets"] if a["name"] == index["zip_name"]), None)
    if asset is None:
        raise RuntimeError(f"release {tag} has no asset {index['zip_name']}")
    digest = asset.get("digest") or ""
    if digest and digest != f"sha256:{index['sha256']}":
        raise ValueError(f"release digest mismatch: {digest}")
    if int(asset["size"]) != int(index["size_bytes"]):
        raise ValueError(f"release size mismatch: {asset['size']} != {index['size_bytes']}")
    print(f"release OK: {release['url']}")
    print(f"asset OK: {asset['name']} size={asset['size']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default=None, help="Export package name. Defaults to today's UTC date.")
    parser.add_argument("--build", action="store_true", help="Build export folder and zip.")
    parser.add_argument("--update-index", action="store_true", help="Update strategy_lab/EXPORT_INDEX.json.")
    parser.add_argument("--commit", action="store_true", help="Commit strategy_lab/EXPORT_INDEX.json.")
    parser.add_argument("--push", action="store_true", help="Push main to origin.")
    parser.add_argument("--publish", action="store_true", help="Publish the zip to GitHub Releases.")
    parser.add_argument("--all", action="store_true", help="Run build, update-index, commit, push, and publish.")
    parser.add_argument("--force", action="store_true", help="Replace existing export folder when building.")
    parser.add_argument("--verify-current", action="store_true", help="Verify current index, local zip, and release.")
    parser.add_argument("--message", default=None, help="Commit message for index update.")
    args = parser.parse_args()

    if args.verify_current:
        _verify_current()
        return 0

    if args.all:
        args.build = True
        args.update_index = True
        args.commit = True
        args.push = True
        args.publish = True

    if not any((args.build, args.update_index, args.commit, args.push, args.publish)):
        parser.error("choose an action, or use --all / --verify-current")

    name = args.name or _default_name()
    export_root = EXPORTS_DIR / name
    zip_path = EXPORTS_DIR / f"{name}.zip"

    if args.build:
        export_root, zip_path = _build_export(name, force=args.force)

    if args.update_index:
        if not export_root.exists() or not zip_path.exists():
            raise FileNotFoundError(
                f"missing export artifacts for {name}; run with --build first"
            )
        _update_index(export_root, zip_path)

    if args.commit:
        message = args.message or f"Update strategy lab export index {name}"
        _commit_index(message)

    if args.push:
        _push_main()

    if args.publish:
        if not zip_path.exists():
            raise FileNotFoundError(zip_path)
        _publish(zip_path, _tag_for_name(name), name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
