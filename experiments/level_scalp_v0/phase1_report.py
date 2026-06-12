"""Phase 1 verdict — aggregate the Mode A confirmation run per the PINNED decision rule.

Manifest rule (committed 908c3882, BEFORE the confirmation read): PASS iff
  (a) pooled joint-calendar-day-block p5 of net EV per fill > 0, AND
  (b) >=2 of 4 cells individually positive at day-block p25.
Fills = proof-grade only (behind-you MBO rule OR trade-through; both sufficient).
Net EV = ev_s1 (1-tick stop stress) - commission ticks; s2/s4 reported as stress.
P7 applies its pinned defend_sz_norm >= 2 filter (measured at first touch onset).
Adverse selection = E[reaction (8,8) | touched, not filled] vs realized E[net | filled].

Run: backend/.venv/Scripts/python.exe experiments/level_scalp_v0/phase1_report.py
Artifact: report/phase1_mode_a.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec import MODULE, OUT  # noqa: E402
from atlas_report import block_boot, comm_ticks, md_table  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

MANIFEST = json.loads((MODULE / "phase1_manifest.json").read_text(encoding="utf-8"))


def main() -> int:
    rows, pooled = [], []
    for cfg in MANIFEST["cells"]:
        cid, sym = cfg["id"], cfg["symbol"]
        df = pd.read_parquet(OUT / f"phase1_mode_a_{cid}.parquet")
        ct = comm_ticks(sym)
        if cfg["extra"] and "defend" in cfg["extra"]:
            df = df[df["defend_sz_norm"].fillna(0) >= 2.0]  # pinned P7 condition
        fills = df[df["filled"] == True].copy()  # noqa: E712
        tnf = df[(df["touched"] == True) & (df["filled"] == False)]  # noqa: E712
        r = {
            "cell": cid,
            "placements": len(df),
            "touched": int(df["touched"].sum()),
            "fills": len(fills),
            "fill/touch": round(len(fills) / max(int(df["touched"].sum()), 1), 2),
            "by_behind": (
                int((fills["fill_rule"] == "behind").sum()) if len(fills) else 0
            ),
            "exit_mix": fills["exit"].value_counts().to_dict() if len(fills) else {},
        }
        if len(fills):
            for s in (1, 2, 4):
                r[f"net_s{s}"] = round(float(fills[f"ev_s{s}"].mean() - ct), 2)
            days = fills["trading_day"].astype(str).to_numpy()
            net1 = (fills["ev_s1"].to_numpy(float) - ct)[:, None]
            means, _ = block_boot(net1, days)
            r["p25"] = round(float(np.percentile(means, 25)), 2)
            r["p5"] = round(float(np.percentile(means, 5)), 2)
            r["cell_pos_p25"] = r["p25"] > 0
            fills["net"] = net1[:, 0]
            pooled.append(fills[["trading_day", "net", "cell"]])
        # adverse-selection split (reaction units, gross ticks, (8,8) outcome)
        r["E[react|touch,nofill]"] = (
            round(float(tnf["touch_ev88"].mean()), 2) if len(tnf) else np.nan
        )
        r["E[react|filled]"] = (
            round(float(fills["touch_ev88"].mean()), 2)
            if len(fills) and fills["touch_ev88"].notna().any()
            else np.nan
        )
        rows.append(r)

    cells = pd.DataFrame(rows)
    pool = pd.concat(pooled, ignore_index=True)
    days = pool["trading_day"].astype(str).to_numpy()
    means, _ = block_boot(pool["net"].to_numpy(float)[:, None], days)
    pooled_mean = float(pool["net"].mean())
    pooled_p5 = float(np.percentile(means, 5))
    n_pos = int(cells["cell_pos_p25"].fillna(False).sum())
    verdict = pooled_p5 > 0 and n_pos >= 2

    lines = [
        "# Phase 1 Mode A — CONFIRMATION verdict (pinned rule, manifest 908c3882)",
        "",
        md_table(cells),
        "",
        f"**Pooled fills: n={len(pool)} over {pool['trading_day'].nunique()} days; "
        f"mean net {pooled_mean:+.2f} ticks/fill; joint day-block p5 {pooled_p5:+.2f}.**",
        f"**Cells positive at p25: {n_pos}/4.**",
        "",
        f"## VERDICT: {'PASS — maker edge survives honest fills' if verdict else 'FAIL — adverse selection eats the atlas edge (module rule: NULL unless re-examined per PLAN)'}",
        "",
        "Notes: fills are proof-grade (behind-you OR trade-through) — a conservative",
        "UNDER-estimate of fill frequency (real fills also happen without later proof);",
        "net EV is per-fill, 1-tick stop stress, commission included, maker entry at the",
        "level with zero entry slippage. The adverse-selection columns compare the (8,8)",
        "reaction after touches that did NOT yield a proof-fill vs those that did.",
    ]
    report = "\n".join(lines)
    (MODULE / "report" / "phase1_mode_a.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
