"""Pass-rate / cash-flow report + milking math for sizing_v1.

Reads per-account JSONs from out/accounts/{firm}/ and produces:
  report/v1_iter1_results.md
  out/account_results_{firm}.parquet

Funded-phase metrics (PLAN §9):
  - Survival rate, blow breakdown
  - Distribution of total $ collected
  - Payout statistics
  - The revenue-rate math
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent


def load_account_results(accounts_dir: Path) -> dict[str, pd.DataFrame]:
    """Returns {firm: DataFrame of per-account records}."""
    out: dict[str, pd.DataFrame] = {}
    for firm_dir in sorted(accounts_dir.iterdir()):
        if not firm_dir.is_dir():
            continue
        recs = []
        for jf in sorted(firm_dir.glob("*.json")):
            recs.append(json.loads(jf.read_text(encoding="utf-8")))
        if recs:
            out[firm_dir.name] = pd.DataFrame(recs)
    return out


def render_report(firm_results: dict[str, pd.DataFrame], out_path: Path) -> None:
    lines = [
        "# sizing_v1 — Iteration 1 Results (funded phase)",
        "",
        f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        "",
        "Funded-phase simulation: N accounts with staggered start dates,",
        "each run forward up to `sim_max_days`. Model = milk-v1 LightGBM",
        "ensemble. Sizing = fixed 1 contract. Exit = time-only at horizon.",
        "",
        "**Headline metric: total $ collected per account (profit + payouts).**",
        "",
        "---",
        "",
    ]

    for firm, df in firm_results.items():
        n = len(df)
        n_alive = int((df["status"] == "completed").sum())
        n_blown_daily = int((df["status"] == "blown_daily").sum())
        n_blown_dd = int((df["status"] == "blown_dd").sum())
        n_payout = int((df["n_payouts"] > 0).sum())
        total_collected = df["total_collected"]
        total_payouts = df["total_payouts"]

        lines.append(f"## {firm.upper()} — {n} accounts")
        lines.append("")
        lines.append("| metric | value |")
        lines.append("|---|---|")
        lines.append(f"| survived to end | {n_alive} ({100*n_alive/n:.0f}%) |")
        lines.append(f"| blown daily limit | {n_blown_daily} ({100*n_blown_daily/n:.0f}%) |")
        lines.append(f"| blown trailing DD | {n_blown_dd} ({100*n_blown_dd/n:.0f}%) |")
        lines.append(f"| got ≥1 payout | {n_payout} ({100*n_payout/n:.0f}%) |")
        lines.append(f"| mean $ collected | ${total_collected.mean():,.0f} |")
        lines.append(f"| median $ collected | ${total_collected.median():,.0f} |")
        lines.append(f"| p25 / p75 | ${total_collected.quantile(.25):,.0f} / ${total_collected.quantile(.75):,.0f} |")
        lines.append(f"| worst / best | ${total_collected.min():,.0f} / ${total_collected.max():,.0f} |")
        lines.append(f"| mean payouts/account | {df['n_payouts'].mean():.2f} |")
        lines.append(f"| mean $ paid out | ${total_payouts.mean():,.0f} |")
        lines.append(f"| mean trades/account | {df['n_trades'].mean():.1f} |")
        lines.append("")

        # Milking math
        lines.append("### Revenue-rate math")
        lines.append("")
        mean_collected = float(total_collected.mean())
        lines.append("```")
        lines.append(f"Mean $/account over sim window:   ${mean_collected:,.0f}")
        lines.append(f"If you run 50 funded accounts:     ${mean_collected * 50:,.0f} expected")
        lines.append(f"Blow rate:                         {100*(n_blown_daily+n_blown_dd)/n:.0f}%")
        lines.append(f"Payout-reaching rate:              {100*n_payout/n:.0f}%")
        lines.append("```")
        lines.append("")

        # Best-account detail
        best = df.loc[df["total_collected"].idxmax()]
        lines.append(f"**Best account ({best['account_id']}):** started {best['start_date']}, "
                     f"collected ${best['total_collected']:,.0f}, {int(best['n_payouts'])} payouts, "
                     f"{int(best['n_trades'])} trades, status={best['status']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## Verdict + next steps")
    lines.append("")
    lines.append("See report narrative. Key v1 finding: time-only exits + tight daily")
    lines.append("loss limit → high blow rate. v1.5 levers: per-trade stops, micro")
    lines.append("contracts, daily trade caps.")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--accounts-dir", default=str(EXPERIMENT_DIR / "out" / "accounts"))
    p.add_argument("--report-path", default=str(EXPERIMENT_DIR / "report" / "v1_iter1_results.md"))
    args = p.parse_args(argv)

    accounts_dir = Path(args.accounts_dir)
    if not accounts_dir.exists():
        print(f"No accounts dir at {accounts_dir}. Run multi_account_router.py first.")
        return 1

    firm_results = load_account_results(accounts_dir)
    if not firm_results:
        print("No account results found.")
        return 1

    for firm, df in firm_results.items():
        df.to_parquet(EXPERIMENT_DIR / "out" / f"account_results_{firm}.parquet", index=False)

    render_report(firm_results, Path(args.report_path))
    print(f"Wrote {args.report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
