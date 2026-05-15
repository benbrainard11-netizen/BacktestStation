"""Asset-universe coverage and per-feature profiling runner.

This is the next layer above ``asset_feature_profiler.py``. It keeps a
target futures universe in view, checks what the current strategy-lab export
actually contains, runs individual feature profiling for available symbols,
and writes portable-feature candidates by asset group.

It does not create raw market data. Missing symbols in the coverage report
mean the warehouse/export builder still needs to generate those matrices.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

import asset_feature_profiler


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXPORT_ROOT = ROOT / "data" / "strategy_lab_downloads" / "strategy_lab_core_2026_05_13_gapctx"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "strategy_lab_analysis" / "asset_feature_profiles" / "asset_universe_current"
DEFAULT_UNIVERSE_SOURCE = ROOT / "backend" / "app" / "ingest" / "cost_estimator.py"

CORRELATED_CLUSTERS: dict[str, list[str]] = {
    # Main SMT cluster. RTY is included as the small-cap index check, but the
    # first prop-firm basket should still compare NQ/ES/YM separately.
    "index_triads": ["NQ.c.0", "ES.c.0", "YM.c.0", "RTY.c.0"],
    # FX futures are all USD crosses, but behavior splits by region/risk beta.
    "fx_europe": ["6E.c.0", "6B.c.0", "6S.c.0"],
    "fx_commodity": ["6A.c.0", "6C.c.0", "6N.c.0"],
    "fx_yen": ["6J.c.0"],
    # Metals: GC/SI are the cleanest correlated pair; HG/PL/PA are useful, but
    # their industrial supply-demand behavior can diverge.
    "precious_metals": ["GC.c.0", "SI.c.0"],
    "industrial_metals": ["HG.c.0", "PL.c.0", "PA.c.0"],
    # Crude and products are one complex. NG is energy, but not the same SMT set.
    "oil_products": ["CL.c.0", "BZ.c.0", "RB.c.0", "HO.c.0"],
    "natural_gas": ["NG.c.0"],
    # Rate futures should be treated as a curve cluster.
    "rates_curve": ["ZT.c.0", "ZF.c.0", "ZN.c.0", "ZB.c.0"],
    "grains": ["ZC.c.0", "ZS.c.0", "ZW.c.0"],
}

FALLBACK_UNIVERSE: dict[str, list[str]] = CORRELATED_CLUSTERS


def load_manifest(export_root: Path) -> dict[str, Any]:
    return json.loads((export_root / "MANIFEST.json").read_text(encoding="utf-8"))


def load_universe(source: Path, *, use_cost_estimator_groups: bool) -> dict[str, list[str]]:
    """Load UNIVERSE from cost_estimator.py without importing databento."""

    if not use_cost_estimator_groups:
        return CORRELATED_CLUSTERS

    try:
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if any(isinstance(target, ast.Name) and target.id == "UNIVERSE" for target in node.targets):
                value = ast.literal_eval(node.value)
                if isinstance(value, dict):
                    return {str(k): [str(item) for item in v] for k, v in value.items()}
    except Exception:
        pass
    return FALLBACK_UNIVERSE


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def find_symbol_col(columns: list[str]) -> str | None:
    return asset_feature_profiler.find_symbol_col(columns)


def dataset_symbol_counts(export_root: Path, dataset_info: dict[str, Any]) -> dict[str, int]:
    schema_path = export_root / dataset_info["schema"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    columns = list(schema.get("columns", []))
    symbol_col = find_symbol_col(columns)
    if symbol_col is None:
        columns = list(dict.fromkeys(schema.get("feature_columns", []) + schema.get("label_columns", [])))
        symbol_col = find_symbol_col(columns)
    if symbol_col is None:
        return {}

    matrix_path = export_root / dataset_info["matrix"]
    try:
        df = pd.read_parquet(matrix_path, columns=[symbol_col])
    except Exception as exc:
        print(f"coverage warning dataset={dataset_info['name']} symbol_col={symbol_col}: {exc}")
        return {}
    counts = df[symbol_col].dropna().astype(str).value_counts()
    return {str(symbol): int(count) for symbol, count in counts.items()}


def build_coverage(
    export_root: Path,
    universe: dict[str, list[str]],
    dataset_names: list[str],
) -> tuple[pd.DataFrame, dict[str, dict[str, int]]]:
    manifest = load_manifest(export_root)
    datasets = [
        item for item in manifest["datasets"]
        if not dataset_names or item["name"] in set(dataset_names)
    ]
    counts_by_dataset = {
        item["name"]: dataset_symbol_counts(export_root, item)
        for item in datasets
    }

    target_symbols = ordered_unique([symbol for symbols in universe.values() for symbol in symbols])
    rows: list[dict[str, Any]] = []
    for group, symbols in universe.items():
        for symbol in symbols:
            row: dict[str, Any] = {
                "asset_cluster": group,
                "symbol": symbol,
            }
            total = 0
            covered = 0
            for dataset in counts_by_dataset:
                n = counts_by_dataset[dataset].get(symbol, 0)
                row[f"{dataset}_rows"] = n
                total += n
                covered += int(n > 0)
            row["total_rows"] = total
            row["covered_datasets"] = covered
            row["profile_ready"] = total > 0
            rows.append(row)

    all_seen = sorted({symbol for counts in counts_by_dataset.values() for symbol in counts})
    for symbol in all_seen:
        if symbol in target_symbols:
            continue
        row = {
            "asset_cluster": "unmapped_present",
            "symbol": symbol,
        }
        total = 0
        covered = 0
        for dataset in counts_by_dataset:
            n = counts_by_dataset[dataset].get(symbol, 0)
            row[f"{dataset}_rows"] = n
            total += n
            covered += int(n > 0)
        row["total_rows"] = total
        row["covered_datasets"] = covered
        row["profile_ready"] = total > 0
        rows.append(row)

    return pd.DataFrame(rows), counts_by_dataset


def md_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return lines


def write_coverage_report(
    output_dir: Path,
    coverage: pd.DataFrame,
    counts_by_dataset: dict[str, dict[str, int]],
    universe: dict[str, list[str]],
    export_root: Path,
) -> Path:
    report = output_dir / "asset_universe_coverage.md"
    ready = coverage[coverage["profile_ready"]].copy()
    missing = coverage[(coverage["asset_cluster"] != "unmapped_present") & (~coverage["profile_ready"])].copy()

    lines = [
        "# Asset Universe Coverage",
        "",
        f"Export root: `{export_root}`",
        "",
        "This report checks the target futures universe against the current strategy-lab export.",
        "A missing symbol here means the current export has no rows for it yet.",
        "",
        "## Target Universe",
        "",
    ]
    lines.extend(md_table(
        ["asset_cluster", "symbols"],
        [[group, ", ".join(symbols)] for group, symbols in universe.items()],
    ))

    lines.extend(["", "## Dataset Symbol Counts", ""])
    rows = []
    for dataset, counts in counts_by_dataset.items():
        rows.append([dataset, len(counts), sum(counts.values()), ", ".join(sorted(counts)) or "-"])
    lines.extend(md_table(["dataset", "symbols", "rows", "present_symbols"], rows))

    lines.extend(["", "## Profile-Ready Symbols", ""])
    if ready.empty:
        lines.append("No target symbols are present in the current export.")
    else:
        rows = [
            [
                row["asset_cluster"],
                row["symbol"],
                int(row["total_rows"]),
                int(row["covered_datasets"]),
            ]
            for _, row in ready.sort_values(["asset_cluster", "symbol"]).iterrows()
        ]
        lines.extend(md_table(["asset_cluster", "symbol", "total_rows", "covered_datasets"], rows))

    lines.extend(["", "## Missing Target Symbols", ""])
    if missing.empty:
        lines.append("All target symbols are present in at least one dataset.")
    else:
        rows = [
            [row["asset_cluster"], row["symbol"]]
            for _, row in missing.sort_values(["asset_cluster", "symbol"]).iterrows()
        ]
        lines.extend(md_table(["asset_cluster", "symbol"], rows))

    lines.extend([
        "",
        "## Next Data Step",
        "",
        "Build or sync strategy-lab matrices for the missing symbols, then rerun this script.",
        "The same per-feature profiler will automatically include the new assets once they appear in the export.",
        "",
    ])
    report.write_text("\n".join(lines), encoding="utf-8")
    return report


def group_map_from_coverage(coverage: pd.DataFrame) -> dict[str, str]:
    out: dict[str, str] = {}
    for _, row in coverage.iterrows():
        if bool(row.get("profile_ready")):
            out[str(row["symbol"])] = str(row["asset_cluster"])
    return out


def aggregate_portable(grouped: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, part in grouped.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(group_cols, key))
        symbols = sorted(part["symbol"].astype(str).unique())
        row.update(
            {
                "symbol_count": len(symbols),
                "symbols": ",".join(symbols),
                "total_n": int(part["n"].sum()),
                "min_n": int(part["n"].min()),
                "mean_rate": float(part["rate"].mean()),
                "mean_base_rate": float(part["base_rate"].mean()),
                "mean_lift_abs": float(part["lift_abs"].mean()),
                "min_lift_abs": float(part["lift_abs"].min()),
                "mean_lift_ratio": float(part["lift_ratio"].replace([float("inf"), -float("inf")], pd.NA).dropna().mean()),
                "score": float(part["score"].sum()),
            }
        )
        rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(
        ["symbol_count", "min_lift_abs", "mean_lift_abs", "total_n"],
        ascending=[False, False, False, False],
    )


def write_portability_outputs(
    output_dir: Path,
    profile_csv: Path,
    coverage: pd.DataFrame,
    *,
    min_symbols: int,
    top_n: int,
) -> dict[str, Path]:
    portable_csv = output_dir / "portable_feature_candidates.csv"
    portable_report = output_dir / "portable_feature_candidates.md"
    if not profile_csv.exists():
        pd.DataFrame().to_csv(portable_csv, index=False)
        portable_report.write_text("# Portable Feature Candidates\n\nNo profile CSV found.\n", encoding="utf-8")
        return {"portable_csv": portable_csv, "portable_report": portable_report}

    profiles = pd.read_csv(profile_csv)
    if profiles.empty:
        profiles.to_csv(portable_csv, index=False)
        portable_report.write_text("# Portable Feature Candidates\n\nNo profile rows met thresholds.\n", encoding="utf-8")
        return {"portable_csv": portable_csv, "portable_report": portable_report}

    symbol_to_group = group_map_from_coverage(coverage)
    profiles = profiles[profiles["symbol"].astype(str) != "all"].copy()
    profiles["asset_cluster"] = profiles["symbol"].astype(str).map(symbol_to_group).fillna("unmapped_present")
    profiles = profiles[(profiles["n"] > 0) & (profiles["lift_abs"] > 0)].copy()
    if profiles.empty:
        profiles.to_csv(portable_csv, index=False)
        portable_report.write_text("# Portable Feature Candidates\n\nNo positive-lift rows were found.\n", encoding="utf-8")
        return {"portable_csv": portable_csv, "portable_report": portable_report}

    base_cols = ["dataset", "label", "feature", "test"]
    by_group = aggregate_portable(profiles, ["asset_cluster", *base_cols])
    frames = [by_group]
    concrete_groups = {
        group for group in profiles["asset_cluster"].astype(str).unique()
        if group != "unmapped_present"
    }
    if len(concrete_groups) > 1:
        frames.append(
            aggregate_portable(
                profiles.assign(asset_cluster="all_profiled_assets"),
                ["asset_cluster", *base_cols],
            )
        )
    portable = pd.concat(frames, ignore_index=True)
    portable = portable[
        (portable["symbol_count"] >= min_symbols)
        & (portable["min_lift_abs"] > 0)
        & portable["mean_lift_ratio"].map(lambda value: math.isfinite(float(value)) if pd.notna(value) else False)
    ].copy()
    portable = portable.sort_values(
        ["symbol_count", "min_lift_abs", "mean_lift_abs", "score"],
        ascending=[False, False, False, False],
    )
    portable.to_csv(portable_csv, index=False)

    lines = [
        "# Portable Feature Candidates",
        "",
        "These rows are still univariate, but they survived across multiple profiled symbols.",
        f"Minimum symbols: `{min_symbols}`",
        "",
    ]
    if portable.empty:
        lines.append("No portable candidates met the thresholds.")
    else:
        top = portable.head(top_n)
        rows = []
        for _, row in top.iterrows():
            rows.append(
                [
                    row["asset_cluster"],
                    row["symbol_count"],
                    row["symbols"],
                    row["dataset"],
                    f"`{row['label']}`",
                    f"`{row['feature']}`",
                    f"`{row['test']}`",
                    f"{100.0 * float(row['mean_rate']):.1f}%",
                    f"{100.0 * float(row['mean_base_rate']):.1f}%",
                    f"{100.0 * float(row['mean_lift_abs']):.1f}%",
                    f"{100.0 * float(row['min_lift_abs']):.1f}%",
                ]
            )
        lines.extend(md_table(
            [
                "asset_cluster",
                "symbols_n",
                "symbols",
                "dataset",
                "label",
                "feature",
                "test",
                "mean_rate",
                "mean_base",
                "mean_lift",
                "min_lift",
            ],
            rows,
        ))
    lines.extend([
        "",
        "Use `portable_feature_candidates.csv` for the full table.",
        "A row here is a research lead, not a final model.",
        "",
    ])
    portable_report.write_text("\n".join(lines), encoding="utf-8")
    return {"portable_csv": portable_csv, "portable_report": portable_report}


def run_feature_profiler(
    args: argparse.Namespace,
    symbols: list[str],
    output_dir: Path,
) -> dict[str, Path]:
    profiler_args = argparse.Namespace(
        export_root=args.export_root,
        output_dir=output_dir,
        dataset=args.dataset,
        symbol=symbols,
        label=args.label,
        label_token=args.label_token,
        max_labels_per_dataset=args.max_labels_per_dataset,
        min_n=args.min_n,
        quantile=args.quantile,
        top_n=args.top_n,
    )
    return asset_feature_profiler.run(profiler_args)


def run(args: argparse.Namespace) -> dict[str, Path]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    universe = load_universe(
        args.universe_source,
        use_cost_estimator_groups=args.use_cost_estimator_groups,
    )
    coverage, counts_by_dataset = build_coverage(args.export_root, universe, args.dataset)
    coverage_csv = output_dir / "asset_universe_coverage.csv"
    coverage.to_csv(coverage_csv, index=False)
    coverage_report = write_coverage_report(output_dir, coverage, counts_by_dataset, universe, args.export_root)

    paths: dict[str, Path] = {
        "coverage_csv": coverage_csv,
        "coverage_report": coverage_report,
    }

    if args.coverage_only:
        return paths

    available_symbols = sorted(
        coverage.loc[coverage["profile_ready"], "symbol"].astype(str).unique().tolist()
    )
    symbols = args.symbol or available_symbols
    if not symbols:
        print("no available symbols to profile")
        return paths

    print(f"profile symbols={','.join(symbols)}")
    profile_paths = run_feature_profiler(args, symbols, output_dir)
    paths.update(profile_paths)
    paths.update(write_portability_outputs(
        output_dir,
        profile_paths["all_csv"],
        coverage,
        min_symbols=args.min_symbols,
        top_n=args.top_n,
    ))
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--universe-source", type=Path, default=DEFAULT_UNIVERSE_SOURCE)
    parser.add_argument(
        "--use-cost-estimator-groups",
        action="store_true",
        help="Use broad ingest groups from cost_estimator.py instead of correlated strategy clusters.",
    )
    parser.add_argument("--dataset", action="append", default=[])
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--label", action="append", default=[])
    parser.add_argument("--label-token", action="append", default=[])
    parser.add_argument("--max-labels-per-dataset", type=int, default=8)
    parser.add_argument("--min-n", type=int, default=75)
    parser.add_argument("--min-symbols", type=int, default=2)
    parser.add_argument("--quantile", type=float, default=0.2)
    parser.add_argument("--top-n", type=int, default=40)
    parser.add_argument("--coverage-only", action="store_true")
    args = parser.parse_args()

    paths = run(args)
    for name, path in paths.items():
        print(f"{name}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
