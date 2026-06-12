# ES day-flat model v0 — 52 features, 2551 OOS days

control IC +0.018 | REAL mean-fold IC +0.036 | pre-gex era +0.019 | GEX era (2025-05+) +0.133

decile trades n=512: mean net R -0.033, week-block p5 -0.101
by era:
         count   mean
gex_era              
False      456 -0.063
True        56  0.211
by side:
       count   mean
side               
long     256  0.049
short    256 -0.115

GEX feature importances (full fit, descriptive):
gx_width_chg5         23
gx_dist_call          22
gx_dist_put           21
gx_width              13
gx_pos_chg1           13
gx_pos_in_range       12
gx_zero_gamma_dist    12
gx_total_z20           4

GEX block spans 2025-05+ only; its incremental value = gex-era IC/trades
vs pre-gex era on the same model. Multi-year walls rerun when regen lands.