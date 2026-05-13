"""Publish the current strategy-lab export zip to a GitHub Release.

This keeps large parquet data out of Git history while making it easy for
another PC to download the exact package referenced by EXPORT_INDEX.json.

Requires:
  - GitHub CLI (`gh`)
  - authenticated GitHub session (`gh auth login`)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent
INDEX_PATH = THIS_DIR / "EXPORT_INDEX.json"


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
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


def _default_tag(package_name: str) -> str:
    return package_name.replace("_", "-")


def _release_exists(tag: str) -> bool:
    proc = _run(["gh", "release", "view", tag], check=False)
    return proc.returncode == 0


def _notes(index: dict) -> str:
    lines = [
        f"# {index['current_package']}",
        "",
        "Strategy-lab data export package.",
        "",
        f"- Zip: `{index['zip_name']}`",
        f"- Size: `{index['size_bytes']}` bytes",
        f"- SHA256: `{index['sha256']}`",
        "",
        "## Datasets",
        "",
    ]
    for dataset in index["datasets"]:
        lines.append(
            "- `{name}`: rows `{rows}`, features `{feature_column_count}`, labels `{label_column_count}`".format(
                **dataset
            )
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Use each schema JSON's `feature_columns` as model inputs.",
            "- Never use `label.*` columns as model inputs.",
            "- Prefer walk-forward summaries over one-split leaderboards.",
        ]
    )
    return "\n".join(lines) + "\n"


def publish(args: argparse.Namespace) -> None:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    zip_path = Path(args.zip or index["source_machine_path"])
    if not zip_path.exists():
        raise FileNotFoundError(f"missing export zip: {zip_path}")

    actual_hash = _sha256(zip_path)
    if actual_hash != index["sha256"]:
        raise ValueError(
            f"zip checksum mismatch: expected {index['sha256']}, got {actual_hash}"
        )

    tag = args.tag or _default_tag(index["current_package"])
    title = args.title or index["current_package"]

    auth = _run(["gh", "auth", "status"], check=False)
    if auth.returncode != 0:
        raise RuntimeError(
            "GitHub CLI is not authenticated. Run `gh auth login` first.\n"
            + auth.stderr
        )

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(_notes(index))
        notes_path = Path(f.name)

    try:
        if _release_exists(tag):
            _run(["gh", "release", "upload", tag, str(zip_path), "--clobber"])
            print(f"updated release asset: {tag} -> {zip_path.name}")
        else:
            _run([
                "gh",
                "release",
                "create",
                tag,
                str(zip_path),
                "--title",
                title,
                "--notes-file",
                str(notes_path),
            ])
            print(f"created release: {tag} with {zip_path.name}")
    finally:
        notes_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", help="Path to export zip. Defaults to EXPORT_INDEX source_machine_path.")
    parser.add_argument("--tag", help="Release tag. Defaults to current_package with hyphens.")
    parser.add_argument("--title", help="Release title. Defaults to current_package.")
    args = parser.parse_args()
    publish(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
