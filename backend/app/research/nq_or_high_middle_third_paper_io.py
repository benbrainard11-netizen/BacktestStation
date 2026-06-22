"""File outputs for the OR-high shadow paper monitor."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from app.research.nq_opening_range_mbp_execution_stats import json_safe
from app.research.nq_or_high_middle_third_paper_types import (
    CLOSED_TRADES_JSONL,
    POSITIONS_FILE,
    SIGNALS_JSONL,
    SNAPSHOT_FILE,
    SNAPSHOTS_JSONL,
    PaperMonitorConfig,
)


def write_outputs(snapshot: dict[str, object], cfg: PaperMonitorConfig) -> None:
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    (cfg.output_dir / SNAPSHOT_FILE).write_text(
        json.dumps(json_safe(snapshot), indent=2),
        encoding="utf-8",
    )
    pd.DataFrame(snapshot["positions"]).to_csv(cfg.output_dir / POSITIONS_FILE, index=False)
    append_unique_jsonl(cfg.output_dir / SNAPSHOTS_JSONL, [snapshot], "snapshot_id")
    append_unique_jsonl(cfg.output_dir / SIGNALS_JSONL, snapshot.get("signals", []), "signal_id")
    closed = [row for row in snapshot["positions"] if row.get("status") == "closed"]
    append_unique_jsonl(cfg.output_dir / CLOSED_TRADES_JSONL, closed, "paper_trade_id")
    write_live_status(snapshot, cfg.live_status_path)


def write_live_status(snapshot: dict[str, object], path: Path) -> None:
    account = dict(snapshot["paper_account"])
    payload = {
        "strategy_status": "running" if not str(snapshot["state"]).startswith("error") else "error",
        "last_heartbeat": snapshot["last_heartbeat"],
        "current_symbol": snapshot["symbol"],
        "current_session": f"OR-high paper | {snapshot['state']}",
        "today_pnl": account["today_pnl"],
        "today_r": account["today_r"],
        "trades_today": account["trades_today"],
        "last_signal": snapshot.get("last_signal"),
        "last_error": snapshot.get("last_error"),
        "raw": snapshot,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2), encoding="utf-8")


def append_unique_jsonl(path: Path, rows: list[dict[str, object]], id_key: str) -> None:
    if not rows:
        return
    seen = existing_ids(path, id_key)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            row = row | {"snapshot_id": snapshot_id(row)}
            identity = str(row.get(id_key))
            if identity and identity not in seen:
                handle.write(json.dumps(json_safe(row)) + "\n")
                seen.add(identity)


def existing_ids(path: Path, id_key: str) -> set[str]:
    if not path.exists():
        return set()
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            existing = json.loads(line)
        except json.JSONDecodeError:
            continue
        if id_key in existing:
            seen.add(str(existing[id_key]))
    return seen


def config_json(cfg: PaperMonitorConfig) -> dict[str, object]:
    return {
        "symbol": cfg.symbol,
        "primary_entry_style": cfg.primary_entry_style,
        "execution": asdict(cfg.execution),
    }


def snapshot_id(row: dict[str, object]) -> str:
    return f"{row.get('session_date')}:{row.get('last_heartbeat')}:{row.get('state')}"
