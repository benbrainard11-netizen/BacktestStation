# Atlas v0 — UNBLINDED (spec frozen at this run)

## Primary cells (sole gating authority; fixed (k,j); maker wall = commission only)

| cell                    |   n |   days |   comm_ticks |   taker_extra_ticks | kj    |   ev_gross |   ev_net_maker |   ev_net_taker |   p5_maker |   p95_maker | pass_maker   |
|:------------------------|----:|-------:|-------------:|--------------------:|:------|-----------:|---------------:|---------------:|-----------:|------------:|:-------------|
| P1 gap_pdc ES open      |  77 |     59 |         0.3  |                3.3  | 8/8   |   1.55844  |       1.25444  |       -1.74556 |  -0.400505 |    2.78933  | False        |
| P2 premarket NQ open    | 212 |    140 |         0.76 |                3.76 | 12/12 |  -2.03774  |      -2.79774  |       -5.79774 |  -4.16299  |   -1.52061  | False        |
| P3 pdc ES on+pre        | 565 |    119 |         0.3  |                3.3  | 8/8   |   1.38761  |       1.08361  |       -1.91639 |   0.475218 |    1.61287  | True         |
| P4 PDH/PDL NQ RTH       | 322 |    103 |         0.76 |                3.76 | 12/12 |  -0.89441  |      -1.65441  |       -4.65441 |  -2.80897  |   -0.518007 | False        |
| P5 round NQ RTH         | 795 |    130 |         0.76 |                3.76 | 12/12 |  -0.588679 |      -1.34868  |       -4.34868 |  -2.04677  |   -0.658042 | False        |
| P6 round ES RTH         | 686 |    135 |         0.3  |                3.3  | 8/8   |   1.22449  |       0.92049  |       -2.07951 |   0.29145  |    1.51722  | True         |
| P7 wall-extremes ES RTH | 530 |    137 |         0.3  |                3.3  | 8/8   |   1.82264  |       1.51864  |       -1.48136 |   0.897548 |    2.14622  | True         |
| P8 round RTY RTH        | 952 |    138 |         0.76 |                3.76 | 8/8   |   1.39076  |       0.630756 |       -2.36924 |   0.174648 |    1.06143  | True         |

**Primary verdict: 4/8 cells clear the maker wall at p5 (day-block AND level-block, wider CI).**

## Retest / overshoot table (stop-offset evidence; lit gap we now own)

| symbol   |   n_rejected8 |   p_retest_2t |   overshoot_med |   overshoot_p75 |   overshoot_p90 |
|:---------|--------------:|--------------:|----------------:|----------------:|----------------:|
| ES.c.0   |          6551 |         0.77  |             2.5 |             8.5 |            19.5 |
| NQ.c.0   |          7681 |         0.943 |             5.5 |            18   |            48   |
| YM.c.0   |          7826 |         0.856 |             3   |            11.5 |            27   |
| RTY.c.0  |          7027 |         0.815 |             3   |            11   |            24.5 |

## Exploratory cells (selection-aware p5; NO gating power — rule C19/C20)

| symbol   | family   | sess   |   n |   days |   comm_ticks |   taker_extra_ticks | kj           |   ev_net_maker |   ev_net_taker |   p5_maker | pass_maker   |
|:---------|:---------|:-------|----:|-------:|-------------:|--------------------:|:-------------|---------------:|---------------:|-----------:|:-------------|
| ES.c.0   | ash      | rth    | 261 |     93 |         0.3  |                3.3  | 16/16 (best) |        3.50826 |       0.508261 |    2.35963 | False        |
| ES.c.0   | asl      | rth    | 221 |     81 |         0.3  |                3.3  | 12/8 (best)  |        2.22089 |      -0.779113 |    1.75606 | False        |
| ES.c.0   | onl      | rth    | 204 |     76 |         0.3  |                3.3  | 12/12 (best) |        2.1862  |      -0.813804 |    1.65231 | False        |
| ES.c.0   | lol      | rth    | 261 |     93 |         0.3  |                3.3  | 16/12 (best) |        2.64236 |      -0.35764  |    1.62572 | False        |
| ES.c.0   | ash      | on_pre | 295 |    101 |         0.3  |                3.3  | 2/12 (best)  |        1.60108 |      -1.39892  |    1.49805 | False        |
| ES.c.0   | pdc      | rth    | 268 |     93 |         0.3  |                3.3  | 8/12 (best)  |        1.6251  |      -1.3749   |    1.4715  | False        |
| ES.c.0   | pml      | rth    | 294 |    101 |         0.3  |                3.3  | 2/12 (best)  |        1.55314 |      -1.44686  |    1.46259 | False        |
| ES.c.0   | onh      | rth    | 248 |     97 |         0.3  |                3.3  | 6/16 (best)  |        2.01052 |      -0.989484 |    1.45286 | False        |
| ES.c.0   | rth_open | rth    | 394 |    136 |         0.3  |                3.3  | 2/16 (best)  |        1.55894 |      -1.44106  |    1.44184 | False        |
| ES.c.0   | pd_mid   | rth    | 219 |     77 |         0.3  |                2.3  | 2/16 (best)  |        1.53162 |      -0.468384 |    1.44063 | False        |
| ES.c.0   | loh      | rth    | 293 |    111 |         0.3  |                3.3  | 6/16 (best)  |        1.80522 |      -1.19478  |    1.42106 | False        |
| ES.c.0   | gap_pdc  | rth    | 272 |     94 |         0.3  |                3.3  | 8/12 (best)  |        1.56732 |      -1.43268  |    1.40674 | False        |
| ES.c.0   | pmh      | rth    | 317 |    116 |         0.3  |                3.3  | 6/16 (best)  |        1.82218 |      -1.17782  |    1.38123 | False        |
| ES.c.0   | round    | rth    | 686 |    135 |         0.3  |                3.3  | 2/16 (best)  |        1.46568 |      -1.53432  |    1.38007 | False        |
| RTY.c.0  | pd_mid   | rth    | 229 |     79 |         0.76 |                2.76 | 16/12 (best) |        2.37537 |       0.375371 |    1.35851 | False        |

(83 gated-in exploratory cells; full table in out/atlas_cells.parquet. An exploratory cell is promotable only by replicating on CONFIRMATION.)

## Interpretation (appended post-run — honest caveats)

1. **4/8 primaries clear, and the pattern is mechanism-coherent, not random**: every ES
   cell is positive (pdc on/pre +1.08, round +0.92, wall-extremes +1.52, plus unpowered
   gap_pdc +1.25), every NQ cell is decisively NEGATIVE (p95 < 0 on all three). ES fades
   levels; NQ breaks them. This matches the repo prior (ES chops, NQ expands) and the
   external research (round-number bifurcation). RTY passes small (+0.63, p5 +0.17).
2. **P1 (gap_pdc ES open) is UNPOWERED, not killed**: n=77 < the 200 gate — a
   registration error (the session-restricted cut was never power-checked; the RTH-wide
   version n=272 sits in the exploratory table at p5 +1.41). Verdict: insufficient n.
3. **The maker wall here is the BEST CASE, not an estimate**: EV assumes a fill AT the
   level with zero adverse selection and zero spread. Taker EV is negative everywhere
   except deep-target ES asia cells. The entire surviving edge therefore lives or dies
   on Phase 1's queue model — E[move|filled] vs E[move|touched] is the tax, and the
   documented direction is against us.
4. **The P7 tension**: a big defending stack predicts the bounce AND sits ahead of you
   in the queue — the very wall that makes the level good makes your fill unlikely or
   adverse (you fill when the wall is being eaten). Phase 1 must test posting 1 tick
   inside the wall vs joining it.
5. **Retest table is the keeper stat**: after an 8-tick rejection, price retests the
   level within 2 ticks 77% (ES) to 94% (NQ) of the time; median overshoot through the
   level before rejection = 2.5 ticks (ES) / 5.5 (NQ), p75 = 8.5 / 18. Implications:
   (a) a 2–4 tick stop buffer gets swept on ~half of eventually-successful rejections —
   stops must be wider or entries later; (b) "you get a second chance at the level"
   is true 8-9 times out of 10 — patience over chasing.
6. **Module ADVANCES to Phase 1** (PLAN gate: >=1 primary cleared). Phase 1 = honest
   fills on the 4 surviving cells: Mode A queue-model maker on the 2026 MBO window;
   Mode B is near-pre-killed by the taker wall (only deep-target ES asia cells clear it).
