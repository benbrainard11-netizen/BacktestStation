"""MBO-free 2025 OOS gate run — reuses Mira's export pipeline verbatim except it
DROPS the 15 cluster.bookproxy (MBO) features so 2025 has no missing features.

Everything else (v10.make_model, hyperparameters, prev_q75 threshold logic, the
reclaim entry/stop replay) is Mira's own code, imported from the bs-mira-v15
worktree. Reads its cached 2025 combined candidates (read-only); writes entries
only to OUR sizing_v1/out dir. Does not touch Mira's artifacts or meta.sqlite.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

MIRA = Path(r"C:/Users/benbr/bs-mira-v15")
for p in [MIRA, MIRA / "backend", MIRA / "experiments"]:
    sys.path.insert(0, str(p))

OUT = Path(r"C:/Users/benbr/BacktestStation/experiments/sizing_v1/out/mira_oos_mbofree")
OUT.mkdir(parents=True, exist_ok=True)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


exp = load_module("mira_export_oos", MIRA / "experiments/mira_v15_gate_validation/export_2025_oos_entries.py")


def train_mbofree(args):
    """Mira's train_final_model, but drop bookproxy features from structure_smt."""
    data = exp.v10.load_dataset(Path(args.v9), Path(args.v5), limit_candidates=None)
    data["session_date"] = exp.parse_date_series(data["session_date"])
    dev = data[exp.date_mask(data, "session_date", exp.TRAIN_START, exp.TRAIN_END, inclusive_end=True)].copy()
    blocks, _cc = exp.v10.feature_blocks(dev)
    full = list(blocks[exp.MODEL_BLOCK])
    features = [f for f in full if "bookproxy" not in f.lower()]
    dropped = [f for f in full if "bookproxy" in f.lower()]
    print(f"structure_smt features: {len(full)} -> {len(features)} (dropped {len(dropped)} bookproxy)", flush=True)

    train = dev[dev[exp.TARGET_COL].notna()].copy()
    train[exp.TARGET_COL] = pd.to_numeric(train[exp.TARGET_COL], errors="coerce")
    train = train[train[exp.TARGET_COL].notna()].copy()
    y = train[exp.TARGET_COL].astype(int)

    hp = exp.training_args()
    x_train, fmeta = exp.prepare_train_matrix(train, features, max_cat_levels=hp.max_cat_levels)
    model = exp.v10.make_model(hp)
    model.fit(x_train, y)
    scores = pd.Series(model.predict_proba(x_train)[:, 1], index=train.index)
    off0 = pd.to_numeric(train["decision_offset_sec"], errors="coerce").eq(exp.DECISION_OFFSET_SEC)
    threshold = float(scores.loc[off0].quantile(0.75))
    print(f"trained on {len(train)} rows ({train['candidate_row_id'].nunique()} candidates), "
          f"pos_rate={y.mean():.3f}, prev_q75 threshold={threshold:.6f}", flush=True)

    return {
        "model": model,
        "threshold": threshold,
        "raw_features": fmeta["raw_features"],
        "kept_raw_features": fmeta["kept_raw_features"],
        "dropped_raw_features": fmeta["dropped_raw_features"],
        "encoded_columns": fmeta["encoded_columns"],
        "n_features": len(features),
        "dropped_bookproxy": dropped,
    }


def main() -> int:
    args = SimpleNamespace(
        v9=str(exp.DEFAULT_V9), v5=str(exp.DEFAULT_V5), meta_db=str(exp.DEFAULT_META_DB),
        symbols="ES.c.0,NQ.c.0,YM.c.0,RTY.c.0",
        oos_start=exp.OOS_START, oos_end=exp.OOS_END, data_root=None, reuse_oos_combined=True,
    )
    bundle = train_mbofree(args)
    combined = exp.build_oos_combined(args)  # cached -> returns path, no rebuild
    gated = exp.load_and_score_oos(combined, bundle, args)
    scored = int(gated.attrs.get("scored_rows", 0))
    print(f"2025 OOS: scored={scored}, gated(before 1/opp)={int(gated.attrs.get('gated_before_one_per_opportunity', 0))}, "
          f"gated(after)={len(gated)}", flush=True)
    if gated.empty:
        print("STILL 0 gated entries even MBO-free — that would be a real signal, not an artifact.", flush=True)
        (OUT / "result_summary.json").write_text(json.dumps(
            {"n_features": bundle["n_features"], "threshold": bundle["threshold"],
             "scored": scored, "gated": 0, "entries": 0}, indent=2), encoding="utf-8")
        return 0

    entries, summary = exp.export_entries(gated)
    entries.to_parquet(OUT / "mira_2025_oos_mbofree_entries.parquet", index=False)
    entries.to_csv(OUT / "mira_2025_oos_mbofree_entries.csv", index=False)
    summary.update(n_features=bundle["n_features"], threshold=bundle["threshold"], scored=scored)
    (OUT / "result_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\nENTRIES EXPORTED: {len(entries)}", flush=True)
    print(json.dumps(summary, indent=2, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
