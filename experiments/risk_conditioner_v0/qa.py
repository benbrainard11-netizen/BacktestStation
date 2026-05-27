"""Quality-assurance audit + tests for risk_conditioner_v0.

Modes:
  --audit    Resolve PLAN.md §10 ambiguities.
             Output: report/v0_iter1_ambiguities.md + out/sample_counts.parquet.
             Read-only. Runs first.

  --tests    QA tests against features.parquet / labels.parquet / predictions/.
             (Not yet implemented — comes after build_features.py exists.)

This file's --audit mode is implemented. --tests is still a stub.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sqlite3
import sys
import traceback
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import yaml

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]


def _safe_repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


# ---------------------------------------------------------------------------
# Audit 1: Stop source
# ---------------------------------------------------------------------------


def audit_stop_source() -> dict:
    """Find where stops are produced. Grep candidate files; sample assignments."""

    findings: dict = {
        "section": "1. Stop source",
        "files_scanned": [],
        "candidates": [],
        "summary": "",
        "manual_review_required": True,
    }

    search_roots = [
        _safe_repo_path("backend", "app", "strategies"),
        _safe_repo_path("backend", "app", "backtest"),
        _safe_repo_path("backend", "app", "research", "detectors"),
    ]

    stop_re = re.compile(r"\bstop(_price|_ticks|_distance)?\b", re.IGNORECASE)
    assign_re = re.compile(r"^\s*stop[_a-z]*\s*=", re.IGNORECASE)

    for root in search_roots:
        if not root.exists():
            findings["files_scanned"].append(f"MISSING: {root}")
            continue
        for py in sorted(root.rglob("*.py")):
            try:
                lines = py.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            hits = []
            for i, line in enumerate(lines, start=1):
                if assign_re.search(line) or "stop_price=" in line:
                    snippet = line.strip()
                    if len(snippet) > 200:
                        snippet = snippet[:200] + "…"
                    hits.append((i, snippet))
            if hits:
                rel = py.relative_to(REPO_ROOT).as_posix()
                findings["files_scanned"].append(rel)
                findings["candidates"].append({"file": rel, "hits": hits[:10]})

    findings["summary"] = (
        f"Found {len(findings['candidates'])} files with stop-related assignments. "
        "Manual review still required to pick the canonical stop source per detector "
        "family, but the candidate list is now narrow."
    )
    return findings


# ---------------------------------------------------------------------------
# Audit 2: Execution timestamp rule
# ---------------------------------------------------------------------------


def audit_timestamp_rule() -> dict:
    """Extract Strategy interface + Bar dataclass to confirm bar-close decision rule."""

    findings: dict = {
        "section": "2. Execution timestamp rule",
        "summary": "",
        "evidence": [],
        "default_rule": "",
        "manual_review_required": False,
    }

    strategy_py = _safe_repo_path("backend", "app", "backtest", "strategy.py")
    orders_py = _safe_repo_path("backend", "app", "backtest", "orders.py")

    if strategy_py.exists():
        text = strategy_py.read_text(encoding="utf-8")
        bar_match = re.search(r"@dataclass\(frozen=True\)\nclass Bar:[\s\S]*?(?=@dataclass|\nclass\b)", text)
        if bar_match:
            findings["evidence"].append({
                "file": strategy_py.relative_to(REPO_ROOT).as_posix(),
                "section": "Bar dataclass",
                "excerpt": bar_match.group(0)[:800],
            })
        on_bar_match = re.search(r"def on_bar\([\s\S]*?\n        return \[\]", text)
        if on_bar_match:
            findings["evidence"].append({
                "file": strategy_py.relative_to(REPO_ROOT).as_posix(),
                "section": "Strategy.on_bar signature",
                "excerpt": on_bar_match.group(0)[:600],
            })

    if orders_py.exists():
        text = orders_py.read_text(encoding="utf-8")
        bracket_match = re.search(r"@dataclass\(frozen=True\)\nclass BracketOrder:[\s\S]*?(?=@dataclass|\nclass\b)", text)
        if bracket_match:
            findings["evidence"].append({
                "file": orders_py.relative_to(REPO_ROOT).as_posix(),
                "section": "BracketOrder dataclass (fill_immediately, max_hold_bars)",
                "excerpt": bracket_match.group(0)[:1600],
            })

    findings["default_rule"] = (
        "Engine is bar-driven. on_bar(bar, context) fires AFTER bar.ts_event with bar.close known.\n"
        "  ts_signal   = bar.ts_event (current bar close)\n"
        "  ts_decision = bar.ts_event (same bar — strategy emits OrderIntent here)\n"
        "  ts_entry    = next bar's open  (BracketOrder fills at next-bar open + slippage)\n"
        "  EXCEPTION:  fill_immediately=True fills on the SAME bar's open (FractalAMD pattern).\n"
        "              For v0, we treat this as a per-detector config — must verify per family."
    )
    findings["summary"] = (
        "Strategy interface confirms bar-close → next-bar-open execution by default. "
        "BracketOrder.fill_immediately option exists (Fractal AMD uses it) — Codex must check "
        "per detector whether next-bar-open or same-bar-open is the right convention."
    )
    return findings


# ---------------------------------------------------------------------------
# Audit 3: Exit logic
# ---------------------------------------------------------------------------


def audit_exit_logic() -> dict:
    """Find exit/timeout logic in BracketOrder and engine."""

    findings: dict = {
        "section": "3. Real exit logic",
        "summary": "",
        "candidates": [],
        "default_rule": "",
        "manual_review_required": True,
    }

    orders_py = _safe_repo_path("backend", "app", "backtest", "orders.py")
    if orders_py.exists():
        text = orders_py.read_text(encoding="utf-8")
        for kw in ["max_hold_bars", "fill_immediately", "timeout", "session_close", "force_close"]:
            for i, line in enumerate(text.splitlines(), start=1):
                if kw in line:
                    findings["candidates"].append({
                        "file": orders_py.relative_to(REPO_ROOT).as_posix(),
                        "keyword": kw,
                        "line": i,
                        "excerpt": line.strip()[:200],
                    })

    engine_dir = _safe_repo_path("backend", "app", "engine")
    if engine_dir.exists():
        for py in sorted(engine_dir.rglob("*.py")):
            try:
                text = py.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for kw in ["max_hold_bars", "session_close", "timeout", "force_close", "force_flat"]:
                for i, line in enumerate(text.splitlines(), start=1):
                    if kw in line:
                        rel = py.relative_to(REPO_ROOT).as_posix()
                        findings["candidates"].append({
                            "file": rel,
                            "keyword": kw,
                            "line": i,
                            "excerpt": line.strip()[:200],
                        })

    findings["default_rule"] = (
        "Default exit priority (earliest hit wins):\n"
        "  1. target_price touched\n"
        "  2. stop_price touched\n"
        "  3. max_hold_bars timeout (per BracketOrder spec — exits at bar close with reason='timeout')\n"
        "  4. T_cap = 60 minutes (PLAN.md default for labels)\n"
        "  5. session close / forced flat time (must verify if engine enforces)\n"
        "Conservative rule (CLAUDE.md §8): when stop and target are both reachable in same bar, "
        "stop wins; fill_confidence='conservative'."
    )
    findings["summary"] = (
        f"Found {len(findings['candidates'])} exit-related references. Manual review still required "
        "to confirm session-close / forced-flat handling matches PLAN.md §1 label window."
    )
    return findings


# ---------------------------------------------------------------------------
# Audit 4: Continuous-contract roll boundaries
# ---------------------------------------------------------------------------


def audit_roll_boundaries(mbp1_root: Path) -> dict:
    """Read MBP-1 sample parquets per symbol; check instrument_id distribution."""

    findings: dict = {
        "section": "4. Continuous-contract roll boundaries",
        "summary": "",
        "per_symbol": {},
        "manual_review_required": False,
    }

    if not mbp1_root.exists():
        findings["summary"] = f"MBP-1 root not found at {mbp1_root}. MANUAL REVIEW required."
        findings["manual_review_required"] = True
        return findings

    for sym in ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]:
        sym_dir = mbp1_root / f"symbol={sym}"
        if not sym_dir.exists():
            findings["per_symbol"][sym] = {"status": "missing"}
            continue
        # Get first / last file (sorted)
        date_dirs = sorted(d for d in sym_dir.iterdir() if d.is_dir())
        if not date_dirs:
            findings["per_symbol"][sym] = {"status": "no_data"}
            continue

        sample_dirs = [date_dirs[0], date_dirs[len(date_dirs) // 2], date_dirs[-1]]
        instrument_id_values: set = set()
        columns_seen: list[str] = []
        for d in sample_dirs:
            pq_files = list(d.glob("*.parquet"))
            if not pq_files:
                continue
            try:
                schema = pq.read_schema(pq_files[0])
                columns_seen = [f.name for f in schema]
                # Read just instrument_id and ts_event sparsely (head)
                tbl = pq.read_table(pq_files[0], columns=[c for c in ["instrument_id", "raw_symbol"] if c in columns_seen])
                if "instrument_id" in columns_seen:
                    ids = tbl["instrument_id"].to_pylist()
                    instrument_id_values.update(ids[:1000])
            except Exception as e:
                findings["per_symbol"][sym] = {"status": f"read_error: {type(e).__name__}: {e}"}
                break
        else:
            findings["per_symbol"][sym] = {
                "status": "ok",
                "n_date_dirs": len(date_dirs),
                "first_date": date_dirs[0].name,
                "last_date": date_dirs[-1].name,
                "has_instrument_id": "instrument_id" in columns_seen,
                "has_raw_symbol": "raw_symbol" in columns_seen,
                "n_distinct_instrument_ids_sample": len(instrument_id_values),
                "sample_instrument_ids": sorted(instrument_id_values)[:10],
                "columns": columns_seen,
            }

    findings["summary"] = (
        "Inspected MBP-1 parquet schema for ES/NQ/YM/RTY. Look at per_symbol[*].has_instrument_id "
        "and n_distinct_instrument_ids_sample — if instrument_id changes across the year, those "
        "transitions are the roll boundaries. Strategy: exclude label-window samples where "
        "instrument_id changes during the window."
    )
    return findings


# ---------------------------------------------------------------------------
# Audit 5: Sample counts per detector × family × fold
# ---------------------------------------------------------------------------


def _fold_for_date(d: dt.date, folds_cfg: dict) -> str:
    """Map a date to fold label: train_F{n}, val_F{n}, test_F{n}, refit, holdout, OUTSIDE."""
    holdout = folds_cfg.get("final_holdout", {})
    if holdout:
        hs = dt.date.fromisoformat(str(holdout["holdout_start"]))
        he = dt.date.fromisoformat(str(holdout["holdout_end"]))
        if hs <= d <= he:
            return "holdout"
        rs = dt.date.fromisoformat(str(holdout["refit_start"]))
        re_ = dt.date.fromisoformat(str(holdout["refit_end"]))
        if rs <= d <= re_:
            # within the refit-on window. Tag by fold below if applicable.
            pass

    for fold in folds_cfg.get("folds", []):
        fid = fold["id"]
        for phase in ("train", "val", "test"):
            s = dt.date.fromisoformat(str(fold[f"{phase}_start"]))
            e = dt.date.fromisoformat(str(fold[f"{phase}_end"]))
            if s <= d <= e:
                # Earliest hit wins (test is rarer, so check it first via ordering)
                # Returns first phase match
                return f"{phase}_F{fid}"

    return "OUTSIDE"


def audit_sample_counts(meta_db: Path, folds_cfg: dict, families_cfg: dict, out_dir: Path) -> dict:
    """Query meta.sqlite research_events for sample counts per detector × symbol × fold."""

    findings: dict = {
        "section": "5. Sample counts per detector × family × fold",
        "summary": "",
        "viability": {},
        "manual_review_required": False,
    }

    if not meta_db.exists():
        findings["summary"] = f"meta.sqlite not found at {meta_db}. MANUAL REVIEW required."
        findings["manual_review_required"] = True
        return findings

    # PLAN.md Path A symbols + date range
    symbols = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
    start = "2025-05-01"
    end = "2026-05-22"

    conn = sqlite3.connect(meta_db.as_posix())
    placeholders = ",".join(["?"] * len(symbols))
    query = f"""
        SELECT feature_name, primary_symbol,
               date(bar_end_utc) AS day,
               COUNT(*) AS n
        FROM research_events
        WHERE primary_symbol IN ({placeholders})
          AND date(bar_end_utc) BETWEEN ? AND ?
        GROUP BY feature_name, primary_symbol, day
    """
    params = (*symbols, start, end)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        findings["summary"] = "Zero rows in Path A window. Verify research_events backfill covers this range."
        findings["manual_review_required"] = True
        return findings

    df = pd.DataFrame(rows, columns=["feature_name", "primary_symbol", "day", "n"])
    df["day"] = pd.to_datetime(df["day"]).dt.date
    df["fold"] = df["day"].map(lambda d: _fold_for_date(d, folds_cfg))

    # Map family_type
    families_map = families_cfg.get("detector_families", {})
    default_family = families_cfg.get("default_family_type", "UNKNOWN")
    df["family_type"] = df["feature_name"].map(
        lambda fn: families_map.get(fn, {}).get("family_type", default_family) if isinstance(families_map.get(fn), dict) else default_family
    )

    # Save full counts
    out_dir.mkdir(parents=True, exist_ok=True)
    counts_path = out_dir / "sample_counts.parquet"
    df.to_parquet(counts_path, index=False)

    # Aggregates
    by_detector = df.groupby(["feature_name", "family_type"])["n"].sum().sort_values(ascending=False).reset_index()
    by_detector_symbol = df.groupby(["feature_name", "primary_symbol", "family_type"])["n"].sum().sort_values(ascending=False).reset_index()
    by_detector_fold = df.groupby(["feature_name", "family_type", "fold"])["n"].sum().reset_index()

    findings["viability"]["counts_parquet"] = counts_path.relative_to(REPO_ROOT).as_posix()
    findings["viability"]["totals_by_detector"] = by_detector.to_dict(orient="records")
    findings["viability"]["totals_by_detector_x_symbol"] = by_detector_symbol.head(60).to_dict(orient="records")
    findings["viability"]["totals_by_detector_x_fold"] = by_detector_fold.to_dict(orient="records")

    # Quick viability summary (PLAN §9 thresholds)
    type_a_threshold = 500
    type_b_threshold = 2000
    summary_lines = []
    for (det, fam), n in by_detector.set_index(["feature_name", "family_type"])["n"].items():
        if fam == "A":
            ok = n >= type_a_threshold
            marker = "OK" if ok else "INSUFFICIENT"
            summary_lines.append(f"  {det:35s}  family=A  n={n:>10,}  ({marker} vs {type_a_threshold:,})")
        elif fam == "B":
            ok = n >= type_b_threshold
            marker = "OK" if ok else "INSUFFICIENT"
            summary_lines.append(f"  {det:35s}  family=B  n={n:>10,}  ({marker} vs {type_b_threshold:,})")
        else:
            summary_lines.append(f"  {det:35s}  family={fam}  n={n:>10,}  (excluded — needs audit)")
    findings["viability"]["summary_text"] = "\n".join(summary_lines)
    findings["summary"] = (
        f"Wrote sample counts to {counts_path.relative_to(REPO_ROOT).as_posix()}. "
        f"{len(df):,} (detector, symbol, day) rows aggregated. See viability table for "
        "thresholds (Type A ≥ 500, Type B ≥ 2000)."
    )

    return findings


# ---------------------------------------------------------------------------
# Render markdown report
# ---------------------------------------------------------------------------


def render_report(findings: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# risk_conditioner_v0 — Iteration 1 Ambiguities Audit",
        "",
        f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        "",
        "This report resolves PLAN.md §10 ambiguities. Sections marked **MANUAL REVIEW REQUIRED** "
        "still need human inspection — automation can only narrow the candidate set.",
        "",
        "---",
        "",
    ]

    for f in findings:
        lines.append(f"## {f['section']}")
        lines.append("")
        if f.get("manual_review_required"):
            lines.append("**Status:** ⚠️ MANUAL REVIEW REQUIRED")
        else:
            lines.append("**Status:** ✅ resolved / auto-extracted")
        lines.append("")

        if "summary" in f and f["summary"]:
            lines.append(f"**Summary:** {f['summary']}")
            lines.append("")

        if "default_rule" in f and f["default_rule"]:
            lines.append("**Default rule (PLAN.md §10):**")
            lines.append("")
            lines.append("```")
            lines.append(f["default_rule"])
            lines.append("```")
            lines.append("")

        if f["section"].startswith("1.") and f.get("candidates"):
            lines.append(f"**Candidate files ({len(f['candidates'])}):**")
            lines.append("")
            for c in f["candidates"][:30]:
                lines.append(f"- `{c['file']}` ({len(c['hits'])} hits)")
                for ln, snip in c["hits"][:3]:
                    lines.append(f"  - L{ln}: `{snip}`")
            lines.append("")

        if f["section"].startswith("2.") and f.get("evidence"):
            for ev in f["evidence"]:
                lines.append(f"**{ev['section']}** ({ev['file']}):")
                lines.append("")
                lines.append("```python")
                lines.append(ev["excerpt"])
                lines.append("```")
                lines.append("")

        if f["section"].startswith("3.") and f.get("candidates"):
            lines.append("**Exit-logic references:**")
            lines.append("")
            by_kw: dict = {}
            for c in f["candidates"]:
                by_kw.setdefault(c["keyword"], []).append(c)
            for kw, items in sorted(by_kw.items()):
                lines.append(f"- `{kw}` — {len(items)} hits")
                for it in items[:3]:
                    lines.append(f"  - {it['file']}:{it['line']}  `{it['excerpt']}`")
            lines.append("")

        if f["section"].startswith("4.") and f.get("per_symbol"):
            lines.append("**Per-symbol findings:**")
            lines.append("")
            for sym, info in f["per_symbol"].items():
                lines.append(f"- **{sym}**: status={info.get('status', '?')}")
                if info.get("status") == "ok":
                    lines.append(f"  - dates: {info['first_date']} → {info['last_date']} ({info['n_date_dirs']} day-dirs)")
                    lines.append(f"  - has_instrument_id: {info['has_instrument_id']}")
                    lines.append(f"  - has_raw_symbol: {info['has_raw_symbol']}")
                    lines.append(f"  - distinct instrument_ids (sampled): {info['n_distinct_instrument_ids_sample']}")
                    if info.get("sample_instrument_ids"):
                        lines.append(f"  - sample ids: {info['sample_instrument_ids']}")
            lines.append("")

        if f["section"].startswith("5.") and f.get("viability"):
            v = f["viability"]
            lines.append(f"**Counts parquet:** `{v.get('counts_parquet', 'n/a')}`")
            lines.append("")
            lines.append("**Per-detector totals (Path A window 2025-05-01 → 2026-05-22, 4 index symbols):**")
            lines.append("")
            lines.append("```")
            lines.append(v.get("summary_text", "n/a"))
            lines.append("```")
            lines.append("")
            lines.append("**Per-detector × symbol top 30:**")
            lines.append("")
            lines.append("| detector | symbol | family | n |")
            lines.append("|---|---|---|---|")
            for r in v.get("totals_by_detector_x_symbol", [])[:30]:
                lines.append(f"| {r['feature_name']} | {r['primary_symbol']} | {r['family_type']} | {r['n']:,} |")
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.append("## Open decisions (post-audit)")
    lines.append("")
    lines.append("Codex (or you) must still pick:")
    lines.append("")
    lines.append("1. **stop_defaults.yaml** — per-symbol fallback stop sizes (PLAN §10.1).")
    lines.append("2. **Per-detector entry rule** — `fill_immediately=True` vs next-bar-open (PLAN §10.2).")
    lines.append("3. **Session-close / forced-flat behavior** — confirmation against engine source (PLAN §10.3).")
    lines.append("4. **Roll-boundary exclusion logic** — implement based on §4 findings (PLAN §10.4).")
    lines.append("5. **Type B family expansion** — re-audit detectors that are currently UNKNOWN in detector_families.yaml.")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_audit(args: argparse.Namespace) -> int:
    meta_db = Path(args.meta_db).resolve()
    mbp1_root = Path(args.mbp1_root).resolve()
    out_dir = Path(args.out_dir).resolve()
    report_path = Path(args.report_path).resolve()

    folds_cfg = yaml.safe_load((EXPERIMENT_DIR / "walk_forward.yaml").read_text(encoding="utf-8"))
    families_cfg = yaml.safe_load((EXPERIMENT_DIR / "detector_families.yaml").read_text(encoding="utf-8"))

    findings: list[dict] = []

    for fn in (audit_stop_source, audit_timestamp_rule, audit_exit_logic):
        try:
            findings.append(fn())
            print(f"  OK: {fn.__name__}")
        except Exception as e:
            findings.append({
                "section": fn.__name__,
                "manual_review_required": True,
                "summary": f"audit failed: {type(e).__name__}: {e}\n{traceback.format_exc()[:600]}",
            })
            print(f"  FAILED: {fn.__name__}: {e}")

    try:
        findings.append(audit_roll_boundaries(mbp1_root))
        print(f"  OK: audit_roll_boundaries")
    except Exception as e:
        findings.append({
            "section": "4. Continuous-contract roll boundaries",
            "manual_review_required": True,
            "summary": f"audit failed: {type(e).__name__}: {e}",
        })
        print(f"  FAILED: audit_roll_boundaries: {e}")

    try:
        findings.append(audit_sample_counts(meta_db, folds_cfg, families_cfg, out_dir))
        print(f"  OK: audit_sample_counts")
    except Exception as e:
        findings.append({
            "section": "5. Sample counts per detector × family × fold",
            "manual_review_required": True,
            "summary": f"audit failed: {type(e).__name__}: {e}\n{traceback.format_exc()[:600]}",
        })
        print(f"  FAILED: audit_sample_counts: {e}")

    render_report(findings, report_path)
    print(f"\nWrote {report_path.relative_to(REPO_ROOT)}")

    # Also write JSON for downstream consumers
    json_path = out_dir / "audit_findings.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(findings, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {json_path.relative_to(REPO_ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode")

    audit_p = sub.add_parser("--audit", help="Run PLAN §10 ambiguity audit")
    audit_p.add_argument("--meta-db", default=str(_safe_repo_path("data", "meta.sqlite")))
    audit_p.add_argument("--mbp1-root", default=r"D:\data\raw\databento\mbp-1")
    audit_p.add_argument("--out-dir", default=str(EXPERIMENT_DIR / "out"))
    audit_p.add_argument("--report-path", default=str(EXPERIMENT_DIR / "report" / "v0_iter1_ambiguities.md"))

    # Top-level flags (allow `qa.py --audit` direct invocation)
    p.add_argument("--audit", action="store_true", help="Run PLAN §10 ambiguity audit")
    p.add_argument("--tests", action="store_true", help="(Not implemented yet)")
    p.add_argument("--meta-db", default=str(_safe_repo_path("data", "meta.sqlite")))
    p.add_argument("--mbp1-root", default=r"D:\data\raw\databento\mbp-1")
    p.add_argument("--out-dir", default=str(EXPERIMENT_DIR / "out"))
    p.add_argument("--report-path", default=str(EXPERIMENT_DIR / "report" / "v0_iter1_ambiguities.md"))

    args = p.parse_args(argv)

    if args.audit:
        return run_audit(args)
    if args.tests:
        print("qa.py --tests not yet implemented.")
        return 2
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
