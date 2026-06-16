"""Run descriptive regime analysis for the frozen OR-high middle-third prototype."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.research.nq_opening_range_mbp_execution_stats import json_safe
from app.research.nq_or_high_middle_third_regime import run_regime_analysis


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--combined-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--vix-path", type=Path)
    args = parser.parse_args(argv)

    result = run_regime_analysis(
        combined_dir=args.combined_dir,
        output_dir=args.output_dir,
        vix_path=args.vix_path,
    )
    print(json.dumps(json_safe(result["summary"]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
