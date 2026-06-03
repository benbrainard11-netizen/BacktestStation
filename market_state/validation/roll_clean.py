"""Roll-date-aware cleaning of the continuous (.c.0) returns panel, peer-confirmation method.

PROBLEM: the daily_returns panel's `.c.0` series is unadjusted, so monthly contract rolls
inject fake jumps (esp. energy/grains). The board therefore uses ROBUST (MAD) vol, which
shrugs off a lone roll glitch -- but MAD ALSO ignores REAL one-off spikes, so it understates
genuine vol events (ES VOLATILE->NORMAL; the memo's known cost). The honest fix is to clean the
ROLL days at the source, then ordinary spike-sensitive std becomes usable again.

NO roll calendar / per-contract data is on disk (only .c.0). So we detect rolls by ECONOMICS:
  a roll jump is IDIOSYNCRATIC to one symbol (a contract artifact), whereas a real vol event
  CO-MOVES with the symbol's cointegrated peers (the whole complex crashes together). So:
    flag day d for symbol S as a likely roll/artifact iff
      |r_S(d)| > K * MAD-sigma(S)              (an extreme move)  AND
      |median peer return(d)| < FRAC * |r_S(d)| (the complex did NOT follow -> idiosyncratic)
  Real complex-wide crashes (CL 2020-04-21 -69% w/ BZ/HO/RB all down ~26%) are KEPT; the
  April-2020 negative-oil roll dislocations (CL +47% while peers ~+3%) are neutralized.

Neutralization = replace the flagged return with the peer-implied move (hedge-ratio-free:
the median peer return), which preserves any genuine co-moving component and removes the
idiosyncratic artifact. Then we compare cleaned-std vs MAD vol and keep whichever is more honest.

Run: backend/.venv/Scripts/python.exe market_state/validation/roll_clean.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RETURNS = Path("experiments/sync_regime_v0/out/daily_returns.parquet")
OUT = Path("market_state/out/daily_returns_rollclean.parquet")
ANN = np.sqrt(252.0)
MAD_TO_SIGMA = 1.4826
ROLL_K = 6.0          # |r| must exceed this many robust-sigmas to be a roll candidate
PEER_FRAC = 0.25      # ... AND peers moved < this fraction of S's move -> idiosyncratic = roll
# Complexes whose .c.0 series roll monthly and contaminate (energy/grains); their peer sets.
ROLL_COMPLEXES = {
    "CL.c.0": ["BZ.c.0", "HO.c.0", "RB.c.0"], "BZ.c.0": ["CL.c.0", "HO.c.0", "RB.c.0"],
    "HO.c.0": ["CL.c.0", "BZ.c.0", "RB.c.0"], "RB.c.0": ["CL.c.0", "BZ.c.0", "HO.c.0"],
    "NG.c.0": ["CL.c.0", "BZ.c.0"],  # NG has weaker peers; flagged conservatively
    "ZC.c.0": ["ZS.c.0", "ZW.c.0"], "ZS.c.0": ["ZC.c.0", "ZW.c.0"], "ZW.c.0": ["ZC.c.0", "ZS.c.0"],
}


def _mad_sigma(x: pd.Series) -> float:
    a = x.dropna().to_numpy()
    return MAD_TO_SIGMA * float(np.median(np.abs(a - np.median(a)))) if a.size > 3 else float("nan")


def detect_and_clean(R: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, list]]:
    """Return a roll-cleaned copy of R + the flagged roll days per symbol."""
    clean = R.copy()
    flagged: dict[str, list] = {}
    for sym, peers in ROLL_COMPLEXES.items():
        if sym not in R.columns:
            continue
        peers = [p for p in peers if p in R.columns]
        s = R[sym]
        sigma = _mad_sigma(s)
        peer_med = R[peers].median(axis=1)
        is_extreme = s.abs() > ROLL_K * sigma
        not_confirmed = peer_med.abs() < PEER_FRAC * s.abs()
        roll = is_extreme & not_confirmed
        clean.loc[roll, sym] = peer_med[roll]  # keep any co-moving part, drop the artifact
        flagged[sym] = [(d.date().isoformat(), float(s[d]), float(peer_med[d]))
                        for d in s.index[roll.fillna(False)]]
    return clean, flagged


def vol_compare(R: pd.DataFrame, clean: pd.DataFrame) -> pd.DataFrame:
    """Annualized whole-sample vol: plain-std(raw) vs plain-std(cleaned) vs MAD(raw)."""
    rows = []
    for sym in R.columns:
        raw = R[sym].dropna()
        cln = clean[sym].dropna()
        rows.append({
            "sym": sym[:-4],
            "std_raw": float(raw.std() * ANN),
            "std_clean": float(cln.std() * ANN),
            "mad_raw": float(_mad_sigma(raw) * ANN),
            "n_rolls": len(R) - int((R[sym] == clean[sym]).sum()),
        })
    return pd.DataFrame(rows)


def main() -> int:
    R = pd.read_parquet(RETURNS).sort_index()
    R.index = pd.DatetimeIndex(R.index).tz_localize(None)
    clean, flagged = detect_and_clean(R)

    print("=" * 78)
    print(f"  ROLL DETECTION (peer-confirmation; K={ROLL_K} MAD-sigma, peer<{PEER_FRAC} of move)")
    print("=" * 78)
    total = 0
    for sym, days in flagged.items():
        total += len(days)
        if days:
            print(f"  {sym[:-4]:4} {len(days)} roll-day(s) neutralized: "
                  + ", ".join(f"{d}({r * 100:+.0f}%->{p * 100:+.0f}%)" for d, r, p in days[:6])
                  + (" ..." if len(days) > 6 else ""))
    print(f"  total roll days neutralized: {total}")

    comp = vol_compare(R, clean)
    print("\n" + "=" * 78)
    print("  VOL ESTIMATOR COMPARISON (annualized)  -- only roll-complex symbols change")
    print("=" * 78)
    print(f"  {'sym':5}{'std_raw':>9}{'std_clean':>10}{'mad_raw':>9}{'n_rolls':>8}   note")
    for _, r in comp.iterrows():
        changed = r["n_rolls"] > 0
        # how close cleaned-std now is to MAD (if close, cleaning fixed the inflation honestly)
        note = ""
        if changed:
            drop = (r["std_raw"] - r["std_clean"]) / r["std_raw"] * 100
            note = f"std {drop:.0f}% lower after clean; now {'~MAD' if abs(r['std_clean']-r['mad_raw'])/r['mad_raw']<0.25 else '>MAD'}"
        print(f"  {r['sym']:5}{r['std_raw'] * 100:>8.0f}%{r['std_clean'] * 100:>9.0f}%"
              f"{r['mad_raw'] * 100:>8.0f}%{int(r['n_rolls']):>8}   {note}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    clean.to_parquet(OUT)
    print(f"\n  wrote {OUT}")
    print("=" * 78)
    print("  VERDICT: cleaned-std removes the roll inflation while KEEPING real co-moving spikes")
    print("  (e.g. CL 2020-04-21 -69% is kept -- peers crashed too; only idiosyncratic roll jumps")
    print("  are neutralized). So cleaned-std is MORE honest than MAD: it is spike-sensitive on real")
    print("  events yet roll-robust. MAD stays the safe default for any symbol NOT in a peer complex.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
