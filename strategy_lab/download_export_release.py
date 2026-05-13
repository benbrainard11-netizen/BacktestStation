"""Download and verify the current strategy-lab export from GitHub Releases."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent
INDEX_PATH = THIS_DIR / "EXPORT_INDEX.json"


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _default_tag(package_name: str) -> str:
    return package_name.replace("_", "-")


def download(args: argparse.Namespace) -> Path:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    tag = args.tag or _default_tag(index["current_package"])
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_path = output_dir / index["zip_name"]
    if zip_path.exists() and not args.force:
        print(f"zip already exists: {zip_path}")
    else:
        if zip_path.exists():
            zip_path.unlink()
        _run([
            "gh",
            "release",
            "download",
            tag,
            "--pattern",
            index["zip_name"],
            "--dir",
            str(output_dir),
        ])

    actual_hash = _sha256(zip_path)
    if actual_hash != index["sha256"]:
        raise ValueError(
            f"zip checksum mismatch: expected {index['sha256']}, got {actual_hash}"
        )
    print(f"verified {zip_path.name} sha256={actual_hash}")

    if args.extract:
        extract_root = output_dir / index["current_package"]
        if extract_root.exists() and args.force:
            shutil.rmtree(extract_root)
        if extract_root.exists():
            print(f"extract folder already exists: {extract_root}")
        else:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(output_dir)
            print(f"extracted to {extract_root}")
        return extract_root

    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("strategy_lab_data"))
    parser.add_argument("--tag", help="Release tag. Defaults to current_package with hyphens.")
    parser.add_argument("--extract", action="store_true", help="Extract the zip after verification.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing zip/extract folder.")
    args = parser.parse_args()
    download(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
