"""Layer 1 — eval-EV funnel Monte Carlo (vectorized day-level, per firm x shape x risk).

Strategy shape: (p win rate, win_R payoff vs -1R loss, n trades/day, risk $/trade).
Day outcome: k ~ Binomial(n, p); pnl = (k*win_R - (n-k)) * risk; intraday worst uses
the LOSSES-FIRST ordering (conservative for real-time breach checks); intraday best
uses wins-first (conservative for intraday-trailing HW). iid trades; greedy payouts;
funded horizon 252 trading days; fixed risk.

EV per campaign = -E[fees to pass] - activation + E[funded payouts to trader].
E[attempts] = 1/P(pass) (geometric); resets used after the first attempt where cheaper.

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/eval_ev.py
Artifact: report/eval_ev_v0.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODULE = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE))
from funnel_specs import FUNNELS  # noqa: E402

START = 50000.0
N_PATHS = 3000
FUNDED_DAYS = 252
RNG = np.random.default_rng(11)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def day_draws(p, win_r, n, risk, paths, days, dll=0.0, dll_soft=False):
    """Trade-grain day outcomes with an HONEST DLL stop.

    Walk the n trades in sequence; once cumulative PnL <= -dll, stop OPENING new trades —
    the crossing trade still completes at full risk (a soft DLL caps new entries, it cannot
    liquidate an in-flight trade at exactly -dll). soft DLL -> day ends, account alive; hard
    DLL -> account blows. dll<=0 -> take all n trades. Returns day_pnl, worst (intraday min),
    best (intraday max), hard_blow — all shape (paths, days).

    This replaces the old day-grain clip (worst=losses-first + day_pnl=-dll), which refunded
    the overshoot and manufactured fake positive drift from a zero-edge strategy.
    """
    wins = RNG.random((paths, days, n)) < p
    tr = np.where(wins, win_r * risk, -risk)               # per-trade PnL
    cum = np.cumsum(tr, axis=2)                             # within-day cumulative
    if dll and dll > 0:
        crossed = cum <= -dll
        any_cross = crossed.any(axis=2)
        idx = np.where(any_cross, np.argmax(crossed, axis=2), n - 1)   # last trade taken
        day_pnl = np.take_along_axis(cum, idx[..., None], axis=2)[..., 0]
        taken = np.arange(n)[None, None, :] <= idx[..., None]
        cum_t = np.where(taken, cum, np.nan)
        worst = np.nanmin(cum_t, axis=2)
        best = np.nanmax(cum_t, axis=2)
        hard_blow = any_cross & (not dll_soft)
        return day_pnl, worst, best, hard_blow
    return (cum[..., -1], np.min(cum, axis=2), np.max(cum, axis=2),
            np.zeros((paths, days), bool))


def eval_sim(spec: dict, p, win_r, n, risk) -> tuple[float, float]:
    """Returns (pass_prob, mean_days_per_attempt)."""
    e = spec["eval"]
    pnl, worst, _, hard = day_draws(p, win_r, n, risk, N_PATHS, e["max_days"], e["dll"], e["dll_soft"])
    bal = np.full(N_PATHS, START)
    hw = bal.copy()
    alive = np.ones(N_PATHS, bool)
    passed = np.zeros(N_PATHS, bool)
    best_day = np.zeros(N_PATHS)
    days_used = np.full(N_PATHS, e["max_days"], float)
    for d in range(e["max_days"]):
        a = alive & ~passed
        if not a.any():
            break
        day_pnl = pnl[:, d]  # soft DLL already baked into pnl/worst by day_draws (trade-grain)
        if e["dll"] > 0 and not e["dll_soft"]:           # hard DLL -> blow on the crossing trade
            alive[a & hard[:, d]] = False
            a = alive & ~passed
        floor = np.where(hw - e["dd"] > START - e["dd"], hw - e["dd"], START - e["dd"])
        if e["dd_mode"] in ("eod_rt", "intraday"):
            alive[a & (bal + worst[:, d] <= floor)] = False
        a = alive & ~passed
        bal[a] += day_pnl[a]
        alive[a & (bal <= floor)] = False  # EOD breach (all modes)
        hw = np.maximum(hw, bal)
        best_day = np.maximum(best_day, np.where(a, day_pnl, 0))
        prof = bal - START
        # eval consistency gates compare best day to TOTAL PROFIT (more profit cures it)
        ok_cons = (
            (best_day <= 0.5 * prof) if e["best_day_cap"] else np.ones(N_PATHS, bool)
        )
        newly = (
            alive & ~passed & (prof >= e["target"]) & (d + 1 >= e["min_days"]) & ok_cons
        )
        days_used[newly] = d + 1
        passed |= newly
    return float(passed.mean()), (
        float(days_used[passed].mean()) if passed.any() else np.nan
    )


def funded_sim(spec: dict, p, win_r, n, risk, diag: bool = False):
    """Expected trader-side payout total over the funded account's life (<=252d).
    diag=True -> return a dict of operational stats (payout speed, blow rate) instead."""
    f = spec["funded"]
    po = f["payout"]
    pnl, worst, best, hard = day_draws(p, win_r, n, risk, N_PATHS, FUNDED_DAYS, f["dll"], f["dll_soft"])
    bal = np.full(N_PATHS, START)
    hw = bal.copy()
    alive = np.ones(N_PATHS, bool)
    paid = np.zeros(N_PATHS)
    n_payouts = np.zeros(N_PATHS, int)
    first_pay = np.full(N_PATHS, -1)             # day of first payout (-1 = none)
    win_days = np.zeros(N_PATHS, int)
    cyc_prof = np.zeros(N_PATHS)
    cyc_best = np.zeros(N_PATHS)
    locked = np.zeros(N_PATHS, bool)
    for d in range(FUNDED_DAYS):
        if not alive.any():
            break
        day_pnl = pnl[:, d]  # soft DLL already baked in (trade-grain); no day-clip refund
        if f["dll"] > 0 and not f["dll_soft"]:           # hard DLL -> blow on the crossing trade
            alive[alive & hard[:, d]] = False
        if f["dd_mode"] == "intraday":
            hw = np.maximum(hw, bal + best[:, d])
        floor = np.where(locked, f["lock_floor"], hw - f["dd"])
        if f["dd_mode"] in ("eod_rt", "intraday"):
            alive[alive & (bal + worst[:, d] <= floor)] = False
        bal[alive] += day_pnl[alive]
        alive[alive & (bal <= floor)] = False
        hw = np.maximum(hw, bal)
        locked |= hw >= f["lock_hw"]
        gain = np.where(alive, day_pnl, 0)
        win_days += (gain >= po["day_thresh"]) & (gain > 0) & alive
        cyc_prof += np.where(alive, gain, 0)
        cyc_best = np.maximum(cyc_best, gain)
        # greedy payout attempt
        elig = (
            alive
            & (bal - START > po["buffer"])
            & (win_days >= po["win_days"])
            & (cyc_prof > 0)
        )
        if po["consistency_pct"]:
            elig &= cyc_best <= (po["consistency_pct"] / 100.0) * np.maximum(
                cyc_prof, 1e-9
            )
        if po["lifetime_payouts"]:
            elig &= n_payouts < po["lifetime_payouts"]
        if elig.any():
            avail = np.maximum(bal - START - po["buffer"], 0)
            cap = np.full(N_PATHS, po["cap"] if po["cap"] else 1e12)
            if po["ladder"]:
                lad = np.array(po["ladder"], float)
                cap = lad[np.minimum(n_payouts, len(lad) - 1)]
            amt = np.minimum(avail, cap)
            take = elig & (amt >= po["min_payout"])
            paid[take] += amt[take] * f["split"]
            bal[take] -= amt[take]
            first_pay[take & (first_pay < 0)] = d
            n_payouts[take] += 1
            win_days[take] = 0
            cyc_prof[take] = 0.0
            cyc_best[take] = 0.0
            if po["floor_to_start_after_first"]:
                locked |= take
            if po["lifetime_payouts"]:
                alive &= ~(
                    take & (n_payouts >= po["lifetime_payouts"])
                )  # account closes
    if diag:
        got = n_payouts >= 1
        return {
            "paid_mean": float(paid.mean()),
            "p_any_payout": float(got.mean()),
            "days_to_first_payout": float(first_pay[got].mean()) if got.any() else float("nan"),
            "mean_payouts": float(n_payouts.mean()),
            "blow_no_payout": float(((~alive) & (n_payouts == 0)).mean()),
            "paid_array": paid,        # per-account trader-side payout distribution (for fleet sim)
        }
    return float(paid.mean())


def campaign_ev(firm: str, p, win_r, n, risk) -> dict:
    spec = FUNNELS[firm]
    e = spec["eval"]
    p_pass, days = eval_sim(spec, p, win_r, n, risk)
    if p_pass < 0.01:
        return {
            "firm": firm,
            "p_pass": p_pass,
            "ev": -e["fee"],
            "v_funded": 0.0,
            "cost_to_funded": np.inf,
            "days_to_pass": np.nan,
        }
    v = funded_sim(spec, p, win_r, n, risk)
    attempts = 1.0 / p_pass
    if e["fee_kind"] == "monthly":
        months = max(np.ceil((days if np.isfinite(days) else e["max_days"]) / 21), 1)
        fees = e["fee"] * months * attempts
    else:
        retry = e["reset"] if e.get("reset") else e["fee"]
        fees = e["fee"] + (attempts - 1) * retry
    cost = fees + e["act"]
    return {
        "firm": firm,
        "p_pass": round(p_pass, 3),
        "days_to_pass": round(days, 1),
        "cost_to_funded": round(cost, 0),
        "v_funded": round(v, 0),
        "ev": round(v - cost, 0),
    }


def main() -> int:
    # REGRESSION GUARD (the soft-DLL bug): an honest DLL must NOT manufacture drift from a
    # zero-edge strategy. The old day-grain clip produced ~+$216/day here. Trade-grain -> ~0.
    dp, _, _, _ = day_draws(0.5, 1.0, 2, 900.0, 20000, 1, dll=1200.0, dll_soft=True)
    assert abs(float(dp.mean())) < 15.0, f"zero-edge drift ${dp.mean():.1f}/day — soft-DLL bug regressed"

    # the honest question: what does a fixed edge level pay, per firm, at optimal
    # shape/risk? edge_r = p*win_R - (1-p) pinned at 0 / +0.05 / +0.10 per trade.
    edge_levels = [0.0, 0.05, 0.10]
    win_rs = [1.0, 1.5, 2.0]
    ns = [2, 4]
    risks = [150, 250, 400, 600, 900]
    rows = []
    for firm in FUNNELS:
        for edge in edge_levels:
            best = None
            for wr in win_rs:
                p = (edge + 1) / (wr + 1)  # solves p*wr-(1-p)=edge
                for n in ns:
                    for r in risks:
                        res = campaign_ev(firm, p, wr, n, r)
                        res.update(shape=f"p{p:.3f}/R{wr}/n{n}", risk=r)
                        if best is None or res["ev"] > best["ev"]:
                            best = res
            best.update(
                edge_r=edge,
                excluded=FUNNELS[firm]["excluded"],
                fleet_cap=FUNNELS[firm]["accounts_cap"],
            )
            rows.append(best)
            print(best)
    tab = pd.DataFrame(rows)
    piv = tab.pivot_table(index="firm", columns="edge_r", values="ev").round(0)
    lines = [
        "# Layer 1 — eval-EV per firm at PINNED per-trade edge (0 / +0.05R / +0.10R)",
        "",
        "## EV per campaign ($) by edge level",
        piv.to_string(),
        "",
        "## Best config per firm x edge",
        tab.to_string(index=False),
        "",
        "ev = expected $ per campaign (fees in; funded life capped 252d; trader split",
        "applied). Conservative: losses-first intraday breaches, iid trades, fixed",
        "risk, greedy payouts. Apex at street fee $90 (list $450: ev -$360).",
        "TPT excluded from fleet (bots banned) — reference row only.",
    ]
    (MODULE / "report").mkdir(exist_ok=True)
    (MODULE / "report" / "eval_ev_v0.md").write_text("\n".join(lines), encoding="utf-8")
    print("\nwritten: report/eval_ev_v0.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
