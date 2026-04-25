"""Estimate Databento Historical pull costs before running.

Wraps `databento.Historical.metadata.get_cost` to report what a
proposed pull would cost in USD. Runs strictly read-only against
the metadata API -- never downloads the actual data.

CLI:
    # Single estimate:
    python -m app.ingest.cost_estimator \\
        --symbols NQ.c.0,ES.c.0 --schema tbbo \\
        --start 2025-01-01 --end 2026-01-01

    # Universe summary (all asset categories x sane defaults):
    python -m app.ingest.cost_estimator --universe

The universe summary is the recommended starting point: shows you
what every reasonable pull would cost so you can pick a budget.

Note on plan inclusions: OHLCV-* schemas are typically free on the
$180/mo plan (returns $0). TBBO and MBP-1 are billed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

try:
    import databento as db
except ImportError:  # pragma: no cover
    sys.stderr.write("databento not installed; pip install databento\n")
    sys.exit(1)


DATASET = "GLBX.MDP3"

# Asset universe. Add new continuous symbols here as the user's
# trading interests broaden.
UNIVERSE: dict[str, list[str]] = {
    "equity_index": ["ES.c.0", "YM.c.0", "RTY.c.0", "NQ.c.0"],
    "metals":       ["GC.c.0", "SI.c.0", "PL.c.0", "PA.c.0", "HG.c.0"],
    "energy":       ["CL.c.0", "HO.c.0", "RB.c.0", "NG.c.0", "BZ.c.0"],
    "forex":        ["6E.c.0", "6B.c.0", "6J.c.0", "6A.c.0", "6C.c.0", "6S.c.0", "6N.c.0"],
    "rates":        ["ZN.c.0", "ZB.c.0", "ZF.c.0", "ZT.c.0"],
    "agriculture":  ["ZC.c.0", "ZS.c.0", "ZW.c.0"],
}


def estimate(
    client: "db.Historical",
    symbols: list[str],
    schema: str,
    start: str,
    end: str,
) -> float:
    """Return USD cost; 0 if the request is free under the user's plan."""
    return float(
        client.metadata.get_cost(
            dataset=DATASET,
            schema=schema,
            symbols=symbols,
            stype_in="continuous",
            start=start,
            end=end,
        )
    )


def universe_summary(client: "db.Historical") -> None:
    """Print a structured cost summary for sane default pull windows."""
    today = dt.date.today()
    yr = today.year

    rows: list[tuple[str, str, str, float]] = []

    def estimate_or_err(syms, schema, start, end):
        try:
            return estimate(client, syms, schema, start, end)
        except Exception as e:
            return -1.0 if "data_end_after_available_end" not in str(e) else -2.0

    print(f"=== OHLCV-1m: {yr - 8} - {yr} (8 years) ===")
    for cat, syms in UNIVERSE.items():
        c = estimate_or_err(syms, "ohlcv-1m", f"{yr - 8}-01-01", f"{yr}-01-01")
        rows.append(("ohlcv-1m 8y", cat, ",".join(syms), c))
        print(f"  {cat:<14s} ({len(syms)}): ${c:>8.2f}")

    print(f"\n=== OHLCV-1s: {yr - 8} - {yr} (8 years) ===")
    for cat, syms in UNIVERSE.items():
        c = estimate_or_err(syms, "ohlcv-1s", f"{yr - 8}-01-01", f"{yr}-01-01")
        rows.append(("ohlcv-1s 8y", cat, ",".join(syms), c))
        print(f"  {cat:<14s} ({len(syms)}): ${c:>8.2f}")

    print(f"\n=== TBBO: {yr - 1} - {yr} (1 year) ===")
    total = 0.0
    for cat, syms in UNIVERSE.items():
        c = estimate_or_err(syms, "tbbo", f"{yr - 1}-01-01", f"{yr}-01-01")
        rows.append(("tbbo 1y", cat, ",".join(syms), c))
        if c > 0:
            total += c
        print(f"  {cat:<14s} ({len(syms)}): ${c:>8.2f}")
    print(f"  -- TBBO 1y total: ${total:.2f}")

    print(f"\n=== TBBO: {yr - 3} - {yr} (3 years) ===")
    total = 0.0
    for cat, syms in UNIVERSE.items():
        c = estimate_or_err(syms, "tbbo", f"{yr - 3}-01-01", f"{yr}-01-01")
        rows.append(("tbbo 3y", cat, ",".join(syms), c))
        if c > 0:
            total += c
        print(f"  {cat:<14s} ({len(syms)}): ${c:>8.2f}")
    print(f"  -- TBBO 3y total: ${total:.2f}")

    print("\n(MBP-1 not estimated -- depends on the specific date window;")
    print(" use --schema mbp-1 with a closed past month for a single estimate.)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Estimate Databento Historical pull cost before pulling."
    )
    p.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated continuous symbols.",
    )
    p.add_argument(
        "--schema",
        type=str,
        default="ohlcv-1m",
        help="Databento schema (mbp-1, tbbo, ohlcv-1m, ohlcv-1s, ohlcv-1h, ohlcv-1d).",
    )
    p.add_argument("--start", type=str, default=None)
    p.add_argument("--end", type=str, default=None)
    p.add_argument(
        "--universe",
        action="store_true",
        help="Print a structured cost summary across the full asset universe.",
    )
    args = p.parse_args(argv)

    api_key = os.environ.get("DATABENTO_API_KEY")
    if not api_key:
        sys.stderr.write("DATABENTO_API_KEY not set in environment.\n")
        return 1
    client = db.Historical(key=api_key)

    if args.universe:
        universe_summary(client)
        return 0

    if not (args.symbols and args.start and args.end):
        sys.stderr.write(
            "Single-estimate mode needs --symbols, --start, and --end. "
            "Or pass --universe for a summary.\n"
        )
        return 1
    syms = [s.strip() for s in args.symbols.split(",") if s.strip()]
    cost = estimate(client, syms, args.schema, args.start, args.end)
    print(f"${cost:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
