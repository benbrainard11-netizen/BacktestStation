# Per-firm strategy-profile + sizing engine — what actually beats prop firms

Built on the existing `sizing_v1` Account state machine (real trailing-DD, daily-loss, payout, consistency-rule
logic). Feeds each firm synthetic trade streams from a family of return-distribution profiles spanning
**smooth/high-win-rate → fat-tail/home-run**, all at *matched* per-trade edge (E≈+0.40R), so we isolate
DISTRIBUTION SHAPE, not edge size. Then a risk-size sweep on the winner. Metric = **net $ pocketed per account**
(payouts net of fees) + **blow-up rate**. Tool: `profile_per_firm.py`. **Firm numbers are PLACEHOLDERS — swap in
real ones and re-run.**

## Finding 1 — the original "home runs for uncapped firms" idea is WRONG
A balanced/moderate profile won on **every** firm; fat-tail/home-run lost everywhere:

| firm | best profile | home-run blow rate |
|---|---|---|
| TPT (uncapped, no consistency) | **balanced p58/1.4R** (smooth ~tied) | 46–97% |
| Apex / MFFU / Topstep / Tradeify / Lucid | **balanced p58/1.4R** | 22–72% |

**Why:** the **trailing drawdown** is the dominant constraint, and it punishes *variance*. Home-run profiles
(low win rate, big wins) have long losing streaks between the rare wins → they hit the trailing-DD floor and
**blow up** (even at TPT with no consistency rule). And ultra-smooth (tiny wins) struggles to clear the
winning-day $ threshold → fewer winning days → slower payouts. **The sweet spot is the middle: ~58% win rate,
~1.4R payoff.** It's *not* "different profile per firm" — moderate variance wins universally because every firm
has a trailing DD. That's the counterintuitive, money-saving lesson: **for prop accounts, don't chase home
runs — variance blows you up.**

## Finding 2 — sizing is where the firm differences are HUGE (the real lever)
Risk-size sweep on the balanced profile (net $/acct : blow%):

| firm | $150 risk | $300 risk | $400 risk | binding constraint |
|---|---|---|---|---|
| **Apex** (no daily-loss limit) | 14.3k / 1% | 28.4k / 3% | **37.2k / 5%** | only trailing DD → size UP safely |
| MFFU (no daily-loss) | 15.1k / 8% | 28.8k / 14% | 36.4k / 19% | trailing DD |
| TPT | 15.5k / 24% | 24.6k / 51% | 30.5k / 55% | trailing DD (high blow) |
| Topstep (daily $1k) | 14.8k / 8% | 27.0k / 14% | **3.1k / 100%** | **daily-loss limit caps risk** |
| Tradeify (daily $1k) | 15.5k / 2% | 24.9k / 5% | **2.1k / 100%** | daily-loss limit |
| Lucid (daily $1.1k, cap $2k) | 14.1k / 2% | 15.6k / 5% | 1.6k / 100% | daily-loss + **payout cap plateaus it** |

**The three levers, ranked:**
1. **Daily-loss limit = the risk ceiling.** Max risk ≈ daily_loss_limit ÷ trades_per_day; size past it and you
   blow ~100% on a bad day. **Firms with NO daily-loss limit (Apex, MFFU) let you size up massively → ~40% more
   payout** ($37k vs ~$27k) at *low* blow rate. This is the single biggest edge in firm selection.
2. **Trailing DD = the blow-rate curve.** Bigger DD tolerates more risk before blowing.
3. **Payout cap = the extraction ceiling.** Lucid's $2k cap plateaus net at ~$15.5k no matter how big you size.

## The actual "beat props most" play
**Moderate-variance profile (~58% win / ~1.4R)** + **size up to each firm's daily-loss/DD ceiling** + **favor
firms with no daily-loss limit and uncapped payouts (Apex-type)**. That combo dominates — *not* home runs, *not*
a different strategy per firm.

## Honest caveats (this is a demo of the engine, not the final answer)
1. **Firm numbers are placeholders** — especially "no daily-loss limit" for Apex/MFFU. Plug in the REAL rules.
2. **Matched-edge assumption** — if a let-winners-run (fat-tail) exit captures *more total edge* than a
   quick-target one, the calculus shifts; here all profiles have equal edge by construction.
3. **Trade-close-only accounting** (Account v1 limitation) — intraday heat isn't tracked, so real blow rates at
   high risk are *understated*. Bar-level MTM would raise them.
4. **SINGLE-account sim** — the #1 gap for your milk plan: running one strategy across 80 accounts means a bad
   day blows **many at once (correlated)**. That correlation is the real milk risk and is NOT modeled here.
5. Fixed 3 trades/day; winning-day threshold $200 (placeholder) drives the smooth-fails result.

## Next (in priority for the milk plan)
1. **Real firm numbers** — drop in exact DD/daily-loss/consistency/cap/min-days for the firms you actually use.
2. **Correlated multi-account sim** — the milk math: N accounts, same strategy, correlated daily P&L → how many
   blow together, expected portfolio payout, optimal account count. *This is the real "beat props" question.*
3. **Plug Mira's real return distribution** (measured win-rate/payoff/trades-per-day) instead of synthetic
   profiles → what Mira *actually* nets per firm + the size to run it at.
