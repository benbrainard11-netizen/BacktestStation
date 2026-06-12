# Defense-break continuation — pre-stated (8,8)@30m taker

| population       |   n_breaks |   break_rate |   PRIM(8,8)_net |   PRIM(8,8)_p5 |   PRIM(8,8)_win% |   sec(12,8)_net |   sec(12,8)_p5 |   sec(12,8)_win% |   sec(16,8)_net |   sec(16,8)_p5 |   sec(16,8)_win% |   sec(6,6)_net |   sec(6,6)_p5 |   sec(6,6)_win% |   med_break_latency_s |
|:-----------------|-----------:|-------------:|----------------:|---------------:|-----------------:|----------------:|---------------:|-----------------:|----------------:|---------------:|-----------------:|---------------:|--------------:|----------------:|----------------------:|
| NQ+RTY (PRIMARY) |        251 |         0.91 |           -0.09 |          -0.9  |             0.57 |           -0.02 |          -1.07 |             0.46 |           -0.13 |          -1.15 |             0.37 |          -1.14 |         -1.81 |            0.51 |                    11 |
| ES (secondary)   |        288 |         0.93 |           -0.6  |          -1.44 |             0.49 |           -0.6  |          -1.54 |             0.38 |           -1.03 |          -2.03 |             0.28 |          -0.77 |         -1.44 |            0.49 |                     2 |

Events that broke within 60m of detection: 543/590 (92%).
Entry at touched-side quote at break detection (spread inside); net of
commission + 1 tick stop slip; horizon 30m; stop wins ties.