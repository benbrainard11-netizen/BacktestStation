"""Paper-trade Gate 2 — block bootstrap on daily P&L.

QUESTION: is the observed cum_R robust to *which specific days* were
lucky? Or is the positive R an artifact of a handful of big days?

CONTEXT: A standard IID bootstrap (resample individual trades or days)
destroys time-series structure. Block bootstrap preserves serial
correlation by resampling consecutive blocks of days. We test multiple
block sizes:

  - 1 day  (IID)         — strictest, no autocorrelation preserved
  - 5 days (1 trade week) — preserves intra-week structure
  - 20 days (~1 month)    — preserves intra-month regime structure

METHOD:
  - Build per-trading-day total pnl_r per family
  - For each block size, B=10,000 resamples:
      * Sample (n_days / block_size) blocks with replacement
      * Concatenate; sum pnl_r → bootstrap cum_R
  - Pro-rate to "annual R" = cum_R * (252 / n_days)
  - Report: mean / median / 5th / 95th percentile / P(negative)

PASS THRESHOLD (pre-registered):
  - P(annual_R <= 0) <= 5%  for BOTH families across all 3 block sizes
  - 5th percentile of annual_R > 0 for at least 1 block size
  - Median annual_R within 50%-200% of observed annual_R

Why these: a strategy whose 5th percentile of resampled annual R is
above zero is bootstrap-robust to day shuffling. P(neg) <= 5% is a
reasonable significance bar for "the positive R wasn't luck."

OUTPUT:
  experiments/paper_trade_gates_2026_05_17/results/v23_block_bootstrap.json
  experiments/paper_trade_gates_2026_05_17/results/v23_block_bootstrap.md
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
V20_DIR = REPO_ROOT / "experiments" / "locked_walkforward_2026_05_17" / "results"
OUT_DIR = REPO_ROOT / "experiments" / "paper_trade_gates_2026_05_17" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)


FAMILY_FILES = {
    "OB strict": [
        "trades_locked_holdout_1_OB_strict_primary_2tick.csv",
        "trades_locked_holdout_2_OB_strict_primary_2tick.csv",
    ],
    "Sweep reversed (filtered)": [
        "trades_locked_holdout_1_Sweep_reversed_filtered_primary_2tick.csv",
        "trades_locked_holdout_2_Sweep_reversed_filtered_primary_2tick.csv",
    ],
}


N_RESAMPLES = 10_000
BLOCK_SIZES = (1, 5, 20)
TRADING_DAYS_PER_YEAR = 252


def load_daily_pnl(filenames: list[str]) -> pd.DataFrame:
    """Aggregate per-trading-day total pnl_r."""
    frames = []
    for fn in filenames:
        df = pd.read_csv(V20_DIR / fn)
        df = df.dropna(subset=["pnl_r", "exit_ts"]).copy()
        df["exit_ts"] = pd.to_datetime(df["exit_ts"], utc=True)
        df["trade_date"] = df["exit_ts"].dt.date
        frames.append(df[["trade_date", "pnl_r"]])
    combined = pd.concat(frames, ignore_index=True)
    daily = (
        combined.groupby("trade_date")["pnl_r"]
        .sum()
        .reset_index()
        .sort_values("trade_date")
        .reset_index(drop=True)
    )
    return daily


def block_bootstrap(
    daily_pnl: np.ndarray,
    *,
    block_size: int,
    n_resamples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Standard non-overlapping block bootstrap. Returns array of
    bootstrap cum_R sums (length = n_resamples).

    Resample (n_days // block_size) blocks with replacement, concatenate,
    and sum. Tail days (n_days % block_size) ignored when block_size > 1;
    impact is small for our sizes.
    """
    n_days = len(daily_pnl)
    n_blocks_full = n_days // block_size
    usable = n_blocks_full * block_size
    if n_blocks_full == 0:
        # block_size > n_days -- fall back to IID
        block_size = 1
        n_blocks_full = n_days
        usable = n_days

    # All possible block starting indexes (non-overlapping, but we can
    # also support overlapping starts; for our small-day windows
    # overlapping gives more sampling variety).
    block_starts = np.arange(0, n_days - block_size + 1)

    sums = np.empty(n_resamples, dtype=np.float64)
    for i in range(n_resamples):
        chosen = rng.choice(block_starts, size=n_blocks_full, replace=True)
        # Vectorize the gather: build index matrix
        idx_matrix = chosen[:, None] + np.arange(block_size)[None, :]
        sums[i] = daily_pnl[idx_matrix].sum()
    return sums


def analyze_family(name: str, daily: pd.DataFrame) -> dict:
    if daily.empty:
        return {"family": name, "passed": False, "error": "no trade days"}

    pnl = daily["pnl_r"].to_numpy(dtype=np.float64)
    n_days = len(pnl)
    observed_cum_r = float(pnl.sum())
    observed_annual_r = observed_cum_r * (TRADING_DAYS_PER_YEAR / n_days)

    by_block: dict[str, dict] = {}
    rng = np.random.default_rng(seed=42)
    for block_size in BLOCK_SIZES:
        sums = block_bootstrap(
            pnl, block_size=block_size, n_resamples=N_RESAMPLES, rng=rng
        )
        annuals = sums * (TRADING_DAYS_PER_YEAR / n_days)
        by_block[f"block_{block_size}d"] = {
            "n_resamples": N_RESAMPLES,
            "annual_r_mean": float(annuals.mean()),
            "annual_r_median": float(np.median(annuals)),
            "annual_r_5th": float(np.quantile(annuals, 0.05)),
            "annual_r_95th": float(np.quantile(annuals, 0.95)),
            "p_negative_annual_r": float((annuals <= 0).mean()),
        }

    # Pass checks
    all_p_neg_ok = all(
        b["p_negative_annual_r"] <= 0.05 for b in by_block.values()
    )
    any_5th_positive = any(b["annual_r_5th"] > 0 for b in by_block.values())
    medians = [b["annual_r_median"] for b in by_block.values()]
    median_within = all(
        0.5 * observed_annual_r <= m <= 2.0 * observed_annual_r
        for m in medians
    )
    passed = bool(all_p_neg_ok and any_5th_positive and median_within)

    return {
        "family": name,
        "n_trade_days": int(n_days),
        "observed_cum_r": round(observed_cum_r, 2),
        "observed_annual_r": round(observed_annual_r, 2),
        "by_block": {k: {kk: round(vv, 4) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in by_block.items()},
        "checks": {
            "p_negative_le_5pct_all_blocks": bool(all_p_neg_ok),
            "5th_percentile_positive_any_block": bool(any_5th_positive),
            "median_within_0.5_to_2x_observed": bool(median_within),
        },
        "passed": passed,
    }


def write_md(results: list[dict]) -> str:
    lines: list[str] = []
    lines.append("# v23 — Block Bootstrap (Paper-Trade Gate 2)")
    lines.append("")
    lines.append(f"_Generated {datetime.utcnow().isoformat()}Z_")
    lines.append("")
    lines.append(
        f"Tests whether the v20 OB strict + Sweep reversed cum_R is robust to "
        f"resampling daily P&L blocks. {N_RESAMPLES:,} resamples per block size."
    )
    lines.append("")
    overall = all(r.get("passed", False) for r in results)
    lines.append(f"## Verdict: {'PASS' if overall else 'FAIL'}")
    lines.append("")
    for r in results:
        lines.append(f"### {r['family']}")
        lines.append("")
        lines.append(f"- Trade days: {r['n_trade_days']:,}")
        lines.append(f"- Observed cum_R: {r['observed_cum_r']:.2f}")
        lines.append(f"- Observed annual R (pro-rated to 252 trading days): {r['observed_annual_r']:.2f}")
        lines.append("")
        lines.append("| Block | Mean | Median | 5th | 95th | P(neg) |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for block_name, b in r["by_block"].items():
            lines.append(
                f"| {block_name} | {b['annual_r_mean']:.2f} | {b['annual_r_median']:.2f} | "
                f"{b['annual_r_5th']:.2f} | {b['annual_r_95th']:.2f} | "
                f"{b['p_negative_annual_r']*100:.2f}% |"
            )
        lines.append("")
        c = r["checks"]
        lines.append(f"- P(annual_R ≤ 0) ≤ 5% on all blocks: **{c['p_negative_le_5pct_all_blocks']}**")
        lines.append(f"- 5th percentile > 0 on at least one block: **{c['5th_percentile_positive_any_block']}**")
        lines.append(f"- Median within [0.5x, 2x] observed: **{c['median_within_0.5_to_2x_observed']}**")
        lines.append(f"- **{'PASS' if r['passed'] else 'FAIL'}**")
        lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- P(annual_R ≤ 0) is the bootstrap p-value of the null \"no edge.\"")
    lines.append("- Block sizes 1d / 5d / 20d test sensitivity to autocorrelation. If results hold under 20d blocks (which preserve month-scale regime), edge isn't just intra-day noise.")
    lines.append("- The Sweep family had only ~95 day-2-holdout days plus ~500 holdout-1 days; small samples will have wider intervals.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    print(f"v23 block bootstrap — {N_RESAMPLES:,} resamples × {len(BLOCK_SIZES)} block sizes")

    results: list[dict] = []
    for family, files in FAMILY_FILES.items():
        daily = load_daily_pnl(files)
        print(f"  {family}: {len(daily)} trade days, cum_R={daily['pnl_r'].sum():.2f}")
        results.append(analyze_family(family, daily))

    payload = {
        "generator": "v23_block_bootstrap",
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "n_resamples_per_block": N_RESAMPLES,
        "block_sizes_days": list(BLOCK_SIZES),
        "trading_days_per_year": TRADING_DAYS_PER_YEAR,
        "results": results,
        "overall_pass": all(r.get("passed", False) for r in results),
    }
    out_json = OUT_DIR / "v23_block_bootstrap.json"
    out_md = OUT_DIR / "v23_block_bootstrap.md"
    out_json.write_text(json.dumps(payload, indent=2))
    out_md.write_text(write_md(results), encoding="utf-8")

    print(f"  wrote: {out_json.relative_to(REPO_ROOT)}")
    print(f"  wrote: {out_md.relative_to(REPO_ROOT)}")
    print()
    for r in results:
        verdict = "PASS" if r.get("passed") else "FAIL"
        if "error" in r:
            print(f"  {r['family']:<32} ERROR: {r['error']}")
            continue
        print(f"  {r['family']:<32} {verdict}")
        for bn, b in r["by_block"].items():
            print(
                f"    {bn:<10}  mean={b['annual_r_mean']:.1f}  "
                f"median={b['annual_r_median']:.1f}  "
                f"5th={b['annual_r_5th']:.1f}  P(neg)={b['p_negative_annual_r']*100:.1f}%"
            )
    print()
    overall = "PASS" if payload["overall_pass"] else "FAIL"
    print(f"OVERALL: {overall}")
    return 0 if payload["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
