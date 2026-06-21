from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


PHOENIX = timezone(timedelta(hours=-7))


@dataclass(frozen=True)
class SummaryRow:
    start: datetime | None
    end: datetime | None
    file: str
    state_tags: str
    entries: list[list[object]]


@dataclass(frozen=True)
class ReconnectGap:
    start: datetime
    end: datetime
    file: str


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_json_list(value: str | None) -> list[list[object]]:
    if not value:
        return []
    text = value.strip()
    if not text or text == "[]":
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def load_summary(path: Path) -> list[SummaryRow]:
    rows: list[SummaryRow] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(
                SummaryRow(
                    start=parse_dt(row.get("start_utc_approx")),
                    end=parse_dt(row.get("end_utc_approx")),
                    file=row.get("file", ""),
                    state_tags=row.get("state_tags", ""),
                    entries=parse_json_list(row.get("entries")),
                )
            )
    return rows


def load_live_symbol_filter(config_path: Path) -> tuple[set[str], bool]:
    symbols: set[str] = set()
    no_ym = False
    if not config_path.exists():
        return symbols, no_ym
    for raw in config_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line.startswith("symbols:") and "[" in line and not symbols:
            inside = line.split("[", 1)[1].split("]", 1)[0]
            symbols = {part.strip() for part in inside.split(",") if part.strip()}
        elif line.startswith("filter:"):
            no_ym = "no_ym" in line
    return symbols, no_ym


def row_covers(row: SummaryRow, ts: datetime) -> bool:
    if row.start is None or row.end is None:
        return False
    return row.start <= ts <= row.end


def parse_reconnect_gaps(log_dir: Path) -> list[ReconnectGap]:
    gaps: list[ReconnectGap] = []
    ts_re = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}),(\d{3})")
    open_gap: tuple[datetime, str] | None = None
    for path in sorted(log_dir.glob("*.log")):
        try:
            fh = path.open("r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if (
                    "WebSocket connection closed unexpectedly" not in line
                    and "Reconnection successful" not in line
                ):
                    continue
                match = ts_re.match(line)
                if not match:
                    continue
                local = datetime.strptime(
                    f"{match.group(1)} {match.group(2)}.{match.group(3)}",
                    "%Y-%m-%d %H:%M:%S.%f",
                ).replace(tzinfo=PHOENIX)
                ts = local.astimezone(timezone.utc)
                if "WebSocket connection closed unexpectedly" in line:
                    open_gap = (ts, str(path))
                elif open_gap is not None:
                    gaps.append(ReconnectGap(open_gap[0], ts, open_gap[1]))
                    open_gap = None
    return gaps


def entry_matches(rows: list[SummaryRow], ts: datetime, symbol: str, direction: str) -> tuple[bool, str, str]:
    direction = direction.lower()
    for row in rows:
        if not row_covers(row, ts):
            continue
        for entry in row.entries:
            if len(entry) < 3:
                continue
            line_no, entry_symbol, entry_direction = entry[:3]
            if str(entry_symbol) == symbol and str(entry_direction).lower() == direction:
                return True, row.file, f"entry_line={line_no}; interval={row.start.isoformat()}..{row.end.isoformat()}"
    return False, "", ""


def classify(
    ts: datetime,
    symbol: str,
    direction: str,
    summary_rows: list[SummaryRow],
    reconnect_gaps: list[ReconnectGap],
    live_symbols: set[str],
    live_no_ym: bool,
) -> dict[str, str]:
    if (live_symbols and symbol not in live_symbols) or (live_no_ym and symbol.startswith("YM.")):
        return {
            "live_state": "filtered_by_live_config",
            "live_detected": "false",
            "live_gate_score": "",
            "live_armed": "false",
            "live_entered": "false",
            "miss_category": "not_expected_live_symbol_filtered",
            "evidence_log_file": str(Path("metadata_logs") / "config.yaml"),
            "evidence_line_or_time": f"symbols={sorted(live_symbols)}; filter=no_ym={live_no_ym}",
        }

    covered = [r for r in summary_rows if row_covers(r, ts)]
    runtime = [r for r in covered if r.state_tags != "no_runtime_marker"]
    connected = [r for r in runtime if "connected" in r.state_tags]
    lockout = [r for r in runtime if "rpCode13_lockout" in r.state_tags]
    exact_gap = [g for g in reconnect_gaps if g.start <= ts <= g.end]
    live_entered, entry_file, entry_evidence = entry_matches(runtime, ts, symbol, direction)

    if live_entered:
        return {
            "live_state": "connected",
            "live_detected": "unknown",
            "live_gate_score": "",
            "live_armed": "true",
            "live_entered": "true",
            "miss_category": "matched_live_entry",
            "evidence_log_file": entry_file,
            "evidence_line_or_time": entry_evidence,
        }

    if exact_gap:
        gap = exact_gap[0]
        return {
            "live_state": "reconnecting_blind",
            "live_detected": "false",
            "live_gate_score": "",
            "live_armed": "false",
            "live_entered": "false",
            "miss_category": "operational_reconnect_gap",
            "evidence_log_file": gap.file,
            "evidence_line_or_time": f"{gap.start.isoformat()}..{gap.end.isoformat()}",
        }

    if lockout and not connected:
        row = lockout[0]
        return {
            "live_state": "locked_out_rpCode13",
            "live_detected": "false",
            "live_gate_score": "",
            "live_armed": "false",
            "live_entered": "false",
            "miss_category": "operational_locked_out",
            "evidence_log_file": row.file,
            "evidence_line_or_time": f"{row.start.isoformat()}..{row.end.isoformat()}",
        }

    if connected:
        row = connected[0]
        state = "connected_reconnect_storm" if "reconnecting_blindness" in row.state_tags else "connected"
        return {
            "live_state": state,
            "live_detected": "unknown",
            "live_gate_score": "",
            "live_armed": "unknown",
            "live_entered": "false",
            "miss_category": "bot_up_no_live_entry_no_candidate_telemetry",
            "evidence_log_file": row.file,
            "evidence_line_or_time": f"{row.start.isoformat()}..{row.end.isoformat()}; state_tags={row.state_tags}",
        }

    if runtime:
        row = runtime[0]
        return {
            "live_state": row.state_tags or "runtime_unknown",
            "live_detected": "unknown",
            "live_gate_score": "",
            "live_armed": "unknown",
            "live_entered": "false",
            "miss_category": "runtime_state_not_connected",
            "evidence_log_file": row.file,
            "evidence_line_or_time": f"{row.start.isoformat()}..{row.end.isoformat()}; state_tags={row.state_tags}",
        }

    if covered:
        row = covered[0]
        return {
            "live_state": "no_runtime_marker",
            "live_detected": "false",
            "live_gate_score": "",
            "live_armed": "false",
            "live_entered": "false",
            "miss_category": "no_runtime_marker",
            "evidence_log_file": row.file,
            "evidence_line_or_time": f"{row.start.isoformat()}..{row.end.isoformat()}",
        }

    return {
        "live_state": "no_live_log_coverage",
        "live_detected": "false",
        "live_gate_score": "",
        "live_armed": "false",
        "live_entered": "false",
        "miss_category": "no_live_log_coverage",
        "evidence_log_file": "",
        "evidence_line_or_time": "",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transfer-dir",
        type=Path,
        default=Path.home() / "Downloads" / "mira_live_transfer_20260605_110402",
    )
    parser.add_argument(
        "--xref",
        type=Path,
        default=Path(r"C:\Users\benbr\BacktestStation\experiments\sizing_v1\out\mira_short_revalidation\recent_live_replay_armed_for_live_xref.csv"),
    )
    args = parser.parse_args()

    metadata = args.transfer_dir / "metadata_logs"
    summary_rows = load_summary(metadata / "live_log_event_summary.csv")
    reconnect_gaps = parse_reconnect_gaps(metadata / "logs")
    live_symbols, live_no_ym = load_live_symbol_filter(metadata / "config.yaml")

    out_rows: list[dict[str, str]] = []
    with args.xref.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            ts = parse_dt(row["trigger_ts_utc"])
            if ts is None:
                continue
            classified = classify(
                ts,
                row["symbol"],
                row["direction"],
                summary_rows,
                reconnect_gaps,
                live_symbols,
                live_no_ym,
            )
            out_rows.append(
                {
                    "trigger_ts_utc": row["trigger_ts_utc"],
                    "symbol": row["symbol"],
                    "direction": row["direction"],
                    "offline_gate_score": row["gate_score"],
                    "offline_marginal": row["marginal"],
                    "offline_armed": row["armed"],
                    "offline_entered": row["entered"],
                    **classified,
                }
            )

    output = metadata / "live_xref_result_from_replay.csv"
    fields = [
        "trigger_ts_utc",
        "symbol",
        "direction",
        "offline_gate_score",
        "offline_marginal",
        "offline_armed",
        "offline_entered",
        "live_state",
        "live_detected",
        "live_gate_score",
        "live_armed",
        "live_entered",
        "miss_category",
        "evidence_log_file",
        "evidence_line_or_time",
    ]
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)

    counts: dict[str, int] = {}
    for row in out_rows:
        counts[row["miss_category"]] = counts.get(row["miss_category"], 0) + 1

    summary_output = metadata / "live_xref_summary_from_replay.csv"
    with summary_output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["miss_category", "count"])
        writer.writeheader()
        for key, value in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            writer.writerow({"miss_category": key, "count": value})

    print(f"wrote {output}")
    print(f"wrote {summary_output}")
    for key, value in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
