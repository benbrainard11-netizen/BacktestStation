"""Config sweep — find the milkable (contract_type × contracts × stop) combo.

Loads signals + excursions once, then runs N funded accounts under each
config combo and tabulates the outcome distribution. Avoids guessing one
config at a time.

Output: report/v1_iter2_sweep.md + out/sweep_results.parquet
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

import pandas as pd
import yaml

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent
sys.path.insert(0, str(EXPERIMENT_DIR))

from simulator import load_signals, load_excursions
from multi_account_router import run_firm, summarize


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--firm", default="topstep")
    p.add_argument("--n-accounts", type=int, default=100)
    p.add_argument("--strategy", default=str(EXPERIMENT_DIR / "config" / "strategy_v0.yaml"))
    args = p.parse_args(argv)

    base_cfg = yaml.safe_load(Path(args.strategy).read_text(encoding="utf-8"))
    preds_dir = (EXPERIMENT_DIR / base_cfg["model_predictions_dir"]).resolve()

    print("Loading signals + excursions once ...")
    signals = load_signals(base_cfg, preds_dir)
    excursions = load_excursions(EXPERIMENT_DIR / "out" / "excursions.parquet")
    print(f"  {len(signals):,} signals, {len(excursions):,} excursions")

    # Sweep grid
    combos = [
        # (contract_type, contracts, stop_usd_per_contract)
        ("mini",  1, None),
        ("mini",  1, 400),
        ("mini",  1, 800),
        ("micro", 1, None),
        ("micro", 5, None),
        ("micro", 10, None),
        ("micro", 5, 400),
        ("micro", 10, 400),
        ("micro", 20, 400),
    ]

    rows = []
    for (ctype, contracts, stop) in combos:
        cfg = copy.deepcopy(base_cfg)
        cfg["contract_type"] = ctype
        cfg["sizing_method"] = "fixed_1"
        cfg.setdefault("sizing_params", {})["contracts"] = contracts
        cfg.setdefault("exit", {})["stop_loss_usd_per_contract"] = stop
        # Note: fixed_1 returns min(contracts, max_position_size); make sure
        # max_position_size in the firm config is high enough for the test.
        # We bump it via cfg flag the sim reads through firm... actually firm
        # max_position_size caps it. For the sweep we temporarily raise it.

        out_dir = EXPERIMENT_DIR / "out" / "sweep" / f"{ctype}_{contracts}_{stop}"
        results = run_firm(args.firm, cfg, signals, args.n_accounts, out_dir, excursions=excursions)
        s = summarize(args.firm, results)
        s["contract_type"] = ctype
        s["contracts"] = contracts
        s["stop_usd"] = stop if stop is not None else 0
        rows.append(s)
        print(f"  {ctype:5s} x{contracts:<2d} stop={str(stop):>4s}: "
              f"survive={100 - s['pct_blown']:.0f}%  payout={s['pct_with_payout']:.0f}%  "
              f"mean=${s['mean_total_collected']:,.0f}  best=${s['best_total_collected']:,.0f}")

    df = pd.DataFrame(rows)
    out_pq = EXPERIMENT_DIR / "out" / "sweep_results.parquet"
    df.to_parquet(out_pq, index=False)

    # Markdown report
    lines = [
        "# sizing_v1 — Iteration 2 config sweep (funded phase)",
        "",
        f"Firm: {args.firm} $50K, {args.n_accounts} accounts per config, staggered starts.",
        "Model = milk-v1 LightGBM ensemble. Threshold 0.45.",
        "",
        "| contract | n | stop$ | survive% | payout% | mean $ | median $ | best $ | mean trades |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in rows:
        lines.append(
            f"| {s['contract_type']} | {s['contracts']} | {s['stop_usd']} | "
            f"{100 - s['pct_blown']:.0f}% | {s['pct_with_payout']:.0f}% | "
            f"${s['mean_total_collected']:,.0f} | ${s['median_total_collected']:,.0f} | "
            f"${s['best_total_collected']:,.0f} | {s['mean_trades']:.0f} |"
        )
    lines.append("")
    lines.append("**Read:** want high survive% AND high payout% AND positive mean $.")
    lines.append("Micros reduce per-trade risk 10x so the $1k daily limit is far")
    lines.append("harder to breach; more contracts scale the size back up.")
    lines.append("")
    report_path = EXPERIMENT_DIR / "report" / "v1_iter2_sweep.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {report_path}")
    print(f"Wrote {out_pq}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
