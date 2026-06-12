# Pooled multi-symbol model (champion features + symbol one-hots)

control -0.011
per-symbol FULL IC:  {'ES': 0.001, 'NQ': -0.009, 'RTY': -0.008, 'YM': 0.005}
per-symbol ERA IC:   {'ES': -0.005, 'NQ': -0.006, 'RTY': -0.017, 'YM': -0.011}
solo-model era reference: ES 0.108 / NQ 0.083 (RTY/YM solo era ~0.02/0.07 from replication)