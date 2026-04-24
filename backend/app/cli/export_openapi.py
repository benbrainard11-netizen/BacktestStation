"""Export the FastAPI app's OpenAPI schema to a JSON file.

Used by the TypeScript type generation pipeline. Run:

    python -m app.cli.export_openapi [--output PATH]

The default output path is `<repo_root>/shared/openapi.json`, which is
checked into git so the frontend can always regenerate types without
running the backend.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.core.paths import REPO_ROOT
from app.main import app

DEFAULT_OUTPUT = REPO_ROOT / "shared" / "openapi.json"


def build_openapi() -> dict:
    """Return the app's OpenAPI schema as a plain dict."""
    return app.openapi()


def write_openapi(output: Path) -> None:
    """Write the schema to `output`, creating parent dirs as needed."""
    output.parent.mkdir(parents=True, exist_ok=True)
    schema = build_openapi()
    # Stable key ordering + trailing newline so diffs are reviewable.
    output.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the output file is missing or out of date instead of writing.",
    )
    args = parser.parse_args(argv)

    if args.check:
        if not args.output.exists():
            print(f"[check] {args.output} does not exist", file=sys.stderr)
            return 1
        current = args.output.read_text(encoding="utf-8")
        fresh = json.dumps(build_openapi(), indent=2, sort_keys=True) + "\n"
        if current != fresh:
            print(
                f"[check] {args.output} is out of date — run "
                "`scripts/generate-types.sh` and commit the diff",
                file=sys.stderr,
            )
            return 1
        print(f"[check] {args.output} is up to date")
        return 0

    write_openapi(args.output)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
