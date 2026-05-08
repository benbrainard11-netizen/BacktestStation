"""CLI: run an outcome computer over already-detected ResearchEvents.

Looks up an OutcomeComputer by name from the
`app.research.outcomes` registry, iterates matching events, calls
`computer.compute(event, bar_reader)`, and writes the returned dict
to `event.outcomes`.

Idempotent + version-aware. Re-running with an unchanged
`outcome_version` skips already-current rows. Bumping the version
recomputes everything (or use --force to recompute regardless).

Usage:

    # List registered computers
    python -m app.cli.compute_research_outcomes --list

    # Compute outcomes for every smt_htf_reference_divergence event
    python -m app.cli.compute_research_outcomes \\
        --computer smt_htf_reactions_v1

    # Force recomputation (e.g. after a bug fix at the same version)
    python -m app.cli.compute_research_outcomes \\
        --computer smt_htf_reactions_v1 --force

    # Spot-check on a small sample without writing
    python -m app.cli.compute_research_outcomes \\
        --computer smt_htf_reactions_v1 --limit 5 --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from app.data.reader import read_bars
from app.db.session import create_all, make_engine, make_session_factory
from app.research import outcomes as outcome_registry
from app.research.outcomes.runner import run_outcomes

logger = logging.getLogger("compute_research_outcomes")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list",
        action="store_true",
        help="List registered outcome computers and exit.",
    )
    parser.add_argument(
        "--computer",
        type=str,
        help="Outcome computer name (registered in app.research.outcomes).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Recompute outcomes even if outcome_version already matches. "
            "Default behavior is to skip already-current rows."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most this many events (useful for spot-checks).",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="SQLAlchemy URL. Default: app.db.session resolution.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the computer but roll back instead of committing.",
    )
    args = parser.parse_args(argv)
    _setup_logging()

    if args.list:
        names = outcome_registry.list_names()
        if not names:
            print("(no outcome computers registered)")
            return 0
        for name in names:
            c = outcome_registry.get(name)
            print(
                f"{name}  feature={c.feature_name}  "
                f"version={c.outcome_version}"
            )
        return 0

    if not args.computer:
        parser.error("--computer is required (unless --list).")

    computer = outcome_registry.get(args.computer)

    engine = make_engine(args.database_url) if args.database_url else make_engine()
    create_all(engine)
    session_factory = make_session_factory(engine)

    with session_factory() as db:
        result = run_outcomes(
            computer=computer,
            bar_reader=read_bars,
            db=db,
            force=args.force,
            limit=args.limit,
        )
        if args.dry_run:
            db.rollback()
            logger.info(
                "--dry-run: rolled back %d updates", result.n_updated,
            )
        else:
            db.commit()

    print(json.dumps(result.as_dict(), indent=2, default=str))
    return 0 if result.n_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
