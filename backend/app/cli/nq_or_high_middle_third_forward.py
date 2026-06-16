"""Run the dormant frozen OR-high middle-third forward validator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.research.nq_opening_range_mbp_execution_stats import json_safe
from app.research.nq_or_high_middle_third_forward import (
    FORWARD_START_EXCLUSIVE,
    run_forward_validation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--forward-start-exclusive", default=FORWARD_START_EXCLUSIVE)
    parser.add_argument("--end")
    args = parser.parse_args(argv)

    result = run_forward_validation(
        events_path=args.events_path,
        output_dir=args.output_dir,
        forward_start_exclusive=args.forward_start_exclusive,
        end=args.end,
    )
    print(json.dumps(json_safe(result["summary"]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
