# Approach model — last pullback before the hit

         n       hit    mean_r      dist
tt                                      
cw    3853  0.093693 -0.180989  1.665254
pcl   4296  0.192272 -0.412316  1.322507
pdh  16632  0.103054 -0.304835  1.675092
pdl  16305  0.107758 -0.438370  1.456301
pw    4047  0.096368 -0.358759  1.619200

all events: n=45133, mean net R -0.358
control (shuffled y, full feats): -0.012
geometry IC +0.129 | full IC +0.041 | value-add -0.088 | full era pooled +0.117
top-quintile by geometry: n=8028, mean net R -0.239, wk p5 -0.330 | era n=1934 mean +0.125
top-quintile by full    : n=8028, mean net R -0.308, wk p5 -0.409 | era n=1949 mean +0.049

## Post-run adversarial review (2026-06-14) — numbers above are an UPPER BOUND

A 12-agent review confirmed 8 defects, all biased OPTIMISTIC; the null verdict
strengthens under every fix. Material ones (quantified by reviewers):
- Stop fills booked at the stop price though detection is on closes already past
  it; close-only triggers also can't see intrabar wick-outs (rule-8 violation).
  Honest all-events mean: ~-0.46R vs -0.358 booked (+0.104R forgiveness; era
  +0.098 — LARGER than the only positive cells above).
- Top-quintile threshold uses the test fold's own prediction quantile — not
  implementable live.
- 43% of events are same-minute duplicates across same-side targets (chains avg
  7.1/day-target); effective n is ~5-7x smaller than printed.
- y_r is vol-rankable by construction on the 67.5% stop mass (-1 - 2/risk);
  vol proxies differ between baseline and full sets, muddying value-add (which
  was negative anyway).
- mins_left used realized session length; x_* daily columns carried the UTC
  panel leak (1.8% of events) — the leak whose champion-scale consequence is in
  report/leak_audit.md.
VERDICT UNCHANGED: construction null; harness not worth perfecting unless the
event definition is revisited.