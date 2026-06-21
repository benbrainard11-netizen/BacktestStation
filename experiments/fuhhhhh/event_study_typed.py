"""Typed event study: slice sweeps by what/where/how-far/how-confirmed.

Answers Ben's questions directly: which swept-level TYPE and TIMEFRAME reaches the
wall, whether proximity matters, whether 5m/15m confirmation matters, and which candle
SMT works on. Descriptive (not a gate); R is net of costs, grossR adds cost back.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

OUT = Path(__file__).resolve().parent / "out"
pd.set_option("display.width", 200)


def row(df: pd.DataFrame, label: str) -> dict:
    if len(df) < 25:
        return {"slice": label, "n": len(df), "note": "thin"}
    prior = df["stop_dist_pts"] / (df["target_dist_pts"] + df["stop_dist_pts"])
    bymo = df.groupby(df["date"].str.slice(0, 7))["r_signed"].mean()
    return {"slice": label, "n": len(df),
            "reach%": round(df["reached"].mean() * 100, 1),
            "edge": round((df["reached"].mean() - prior.mean()) * 100, 1),
            "meanR": round(df["r_signed"].mean(), 3),
            "grossR": round((df["r_signed"] + C.COST_PTS / df["stop_dist_pts"]).mean(), 3),
            "R_d1": round(df["r_signed_d1"].dropna().mean(), 3) if df["r_signed_d1"].notna().any() else np.nan,
            "mo+": f"{int((bymo > 0).sum())}/{len(bymo)}"}


def block(title: str, rows: list[dict]) -> str:
    rep = pd.DataFrame(rows).set_index("slice")
    print(f"\n### {title}")
    print(rep.to_string())
    return f"\n### {title}\n{rep.to_string()}\n"


def main() -> int:
    df = pd.read_parquet(OUT / "events_v3t.parquet")
    sw = df[df["fired_sweep"]].copy()
    out = ["# typed event study (v3t)\n"]

    out.append(block("Triggers overall", [
        row(df, "ALL"), row(df[df.dir == 1], "  UP"), row(df[df.dir == -1], "  DOWN"),
        row(df[df.fired_sweep], "sweep (any)"), row(df[df.fired_smt], "smt (any)"),
        row(df[df.fired_flow], "flow (any)"),
        row(df[df.fired_sweep & (df.confluence == 1)], "sweep solo"),
        row(df[df.fired_sweep & (df.confluence == 1) & (df.dir == -1)], "sweep solo SHORT"),
    ]))

    out.append(block("SWEEP by swept timeframe (solo)", [
        row(sw[(sw.swept_tf == tf) & (sw.confluence == 1)], f"tf={tf}")
        for tf in ["5m", "15m", "60m", "OR", "ON", "1D"]]))
    out.append(block("SWEEP by swept timeframe — SHORT solo", [
        row(sw[(sw.swept_tf == tf) & (sw.confluence == 1) & (sw.dir == -1)], f"tf={tf} SHORT")
        for tf in ["5m", "15m", "60m", "OR", "ON", "1D"]]))

    out.append(block("SWEEP by swept type (solo)", [
        row(sw[(sw.swept_type == ty) & (sw.confluence == 1)], f"type={ty}")
        for ty in ["swingLo", "swingHi", "pdh", "pdl", "onh", "onl", "orh", "orl"]]))

    sw["prox_b"] = pd.cut(sw["swept_dist_atr"], [0, 0.25, 0.5, 1.0, 2.0],
                          labels=["0-.25ATR", ".25-.5", ".5-1", "1-2"])
    out.append(block("SWEEP by proximity (how far the level was, solo)", [
        row(sw[(sw.prox_b == b) & (sw.confluence == 1)], f"dist={b}")
        for b in ["0-.25ATR", ".25-.5", ".5-1", "1-2"]]))

    sw["over_b"] = pd.cut(sw["overshoot_tk"], [0, 2, 4, 8, 1e9],
                          labels=["<=2tk", "2-4tk", "4-8tk", ">8tk"])
    out.append(block("SWEEP by overshoot (exact extreme vs deep poke, solo)", [
        row(sw[(sw.over_b == b) & (sw.confluence == 1)], f"over={b}")
        for b in ["<=2tk", "2-4tk", "4-8tk", ">8tk"]]))

    out.append(block("SWEEP by confirmation (solo SHORT)", [
        row(sw[(sw.confluence == 1) & (sw.dir == -1) & sw[col]], f"{col}=T")
        for col in ["confirm_5m", "confirm_15m"]] + [
        row(sw[(sw.confluence == 1) & (sw.dir == -1) & ~sw["confirm_5m"]], "confirm_5m=F"),
        row(sw[(sw.confluence == 1) & (sw.dir == -1) & ~sw["confirm_15m"]], "confirm_15m=F")]))

    out.append(block("SMT by timeframe (solo)", [
        row(df[df.fired_smt & (df.confluence == 1) & (df.smt_tf == tf)], f"smt={tf}")
        for tf in ["5m", "15m", "60m"]] + [
        row(df[df.fired_smt & (df.confluence == 1) & (df.smt_tf == tf) & (df.dir == -1)], f"smt={tf} SHORT")
        for tf in ["5m", "15m", "60m"]]))

    (OUT / "report_v3t_eventstudy.md").write_text("\n".join(out), encoding="utf-8")
    print(f"\nreport -> {OUT / 'report_v3t_eventstudy.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
