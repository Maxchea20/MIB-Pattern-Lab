## SETUP BRAIN RESULT

Detector version `5199bd9a484ba2881c4d704403bf5bbce7eaef5a5cc00c2397e8180ab59ad5d3`. A FIRE is a signal, not a trade or a fill.

| Setup | Fires | Long | Short | In-sample | Unseen |
|---|---:|---:|---:|---:|---:|
| S1 | 305 | 305 | 0 | 213 | 92 |
| S2 | 636 | 636 | 0 | 451 | 185 |
| S3 | 191 | 0 | 191 | 129 | 62 |
| S4 | 101 | 0 | 101 | 74 | 27 |
| S5 | 55 | 55 | 0 | 35 | 20 |
| S6 | 284 | 0 | 284 | 183 | 101 |
| S7 | 703 | 703 | 0 | 478 | 225 |
| S8 | 668 | 0 | 668 | 461 | 207 |
| S9 | 574 | 271 | 303 | 403 | 171 |

Total fires: **3517** (invalidation events: 3447). Replay == batch scan: **True**. Imported detectors identical to the Experiment 3 recognizer's raw triggers: **True**.

### Earliest / latest fire

| Setup | Earliest | Latest |
|---|---|---|
| S1 | 2025-09-03T10:00:00+00:00 | 2026-09-28T13:00:00+00:00 |
| S2 | 2025-09-02T14:00:00+00:00 | 2026-09-28T16:30:00+00:00 |
| S3 | 2025-09-02T11:30:00+00:00 | 2026-09-27T15:00:00+00:00 |
| S4 | 2025-09-03T05:30:00+00:00 | 2026-09-15T13:45:00+00:00 |
| S5 | 2025-09-05T05:15:00+00:00 | 2026-09-14T20:30:00+00:00 |
| S6 | 2025-09-02T11:15:00+00:00 | 2026-09-27T15:00:00+00:00 |
| S7 | 2025-09-02T01:45:00+00:00 | 2026-09-28T13:45:00+00:00 |
| S8 | 2025-09-02T11:30:00+00:00 | 2026-09-28T09:45:00+00:00 |
| S9 | 2025-09-02T11:30:00+00:00 | 2026-09-28T13:00:00+00:00 |

### Overlap (same-candle fires | presence Jaccard)

| pair | same-candle fires | fire Jaccard | presence both | presence Jaccard |
|---|---:|---:|---:|---:|
| S1/S2 | 4 | 0.004 | 66 | 0.015 |
| S1/S3 | 0 | 0.000 | 1 | 0.000 |
| S1/S4 | 0 | 0.000 | 17 | 0.006 |
| S1/S5 | 7 | 0.020 | 59 | 0.024 |
| S1/S6 | 0 | 0.000 | 9 | 0.003 |
| S1/S7 | 87 | 0.094 | 765 | 0.115 |
| S1/S8 | 0 | 0.000 | 80 | 0.015 |
| S1/S9 | 198 | 0.291 | 2039 | 0.289 |
| S2/S5 | 7 | 0.010 | 25 | 0.008 |
| S2/S7 | 159 | 0.135 | 791 | 0.111 |
| S2/S9 | 4 | 0.003 | 162 | 0.017 |
| S3/S4 | 7 | 0.025 | 51 | 0.025 |
| S3/S6 | 31 | 0.070 | 207 | 0.091 |
| S3/S7 | 0 | 0.000 | 2 | 0.000 |
| S3/S8 | 69 | 0.087 | 510 | 0.116 |
| S3/S9 | 72 | 0.104 | 507 | 0.064 |
| S4/S6 | 8 | 0.021 | 32 | 0.019 |
| S4/S7 | 0 | 0.000 | 13 | 0.002 |
| S4/S8 | 45 | 0.062 | 192 | 0.048 |
| S4/S9 | 12 | 0.018 | 171 | 0.023 |
| S5/S7 | 32 | 0.044 | 236 | 0.042 |
| S5/S8 | 0 | 0.000 | 3 | 0.001 |
| S5/S9 | 7 | 0.011 | 65 | 0.009 |
| S6/S7 | 0 | 0.000 | 7 | 0.001 |
| S6/S8 | 111 | 0.132 | 667 | 0.172 |
| S6/S9 | 32 | 0.039 | 375 | 0.048 |
| S7/S8 | 0 | 0.000 | 22 | 0.002 |
| S7/S9 | 140 | 0.123 | 1785 | 0.168 |
| S8/S9 | 90 | 0.078 | 1078 | 0.114 |

### Forward descriptive statistics (direction-signed % from the analytical reference price = next candle open; NOT fills)

| Setup | Period | Rows | mean ret h1 | mean ret h6 | mean ret h24 | median MFE | median MAE | share ret h6 > 0 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| S1 | IN_SAMPLE | 213 | -0.006 | -0.035 | 0.207 | 0.619 | 0.529 | 0.441 |
| S1 | UNSEEN | 92 | 0.011 | 0.085 | -0.058 | 0.506 | 0.471 | 0.391 |
| S2 | IN_SAMPLE | 451 | -0.039 | -0.030 | -0.065 | 0.475 | 0.640 | 0.435 |
| S2 | UNSEEN | 185 | -0.004 | 0.023 | -0.068 | 0.564 | 0.547 | 0.486 |
| S3 | IN_SAMPLE | 129 | -0.012 | -0.066 | -0.057 | 0.518 | 0.682 | 0.411 |
| S3 | UNSEEN | 62 | -0.062 | -0.119 | -0.230 | 0.565 | 0.629 | 0.403 |
| S4 | IN_SAMPLE | 74 | -0.026 | -0.045 | 0.049 | 0.600 | 0.599 | 0.500 |
| S4 | UNSEEN | 27 | 0.075 | 0.155 | -0.062 | 0.813 | 0.647 | 0.667 |
| S5 | IN_SAMPLE | 35 | -0.027 | -0.094 | -0.017 | 0.517 | 0.677 | 0.371 |
| S5 | UNSEEN | 20 | -0.052 | -0.327 | -0.537 | 0.188 | 0.853 | 0.100 |
| S6 | IN_SAMPLE | 183 | 0.001 | -0.008 | -0.003 | 0.597 | 0.506 | 0.464 |
| S6 | UNSEEN | 101 | 0.004 | -0.028 | -0.084 | 0.390 | 0.599 | 0.446 |
| S7 | IN_SAMPLE | 477 | -0.006 | 0.013 | -0.099 | 0.532 | 0.652 | 0.468 |
| S7 | UNSEEN | 225 | 0.014 | 0.036 | -0.136 | 0.466 | 0.659 | 0.409 |
| S8 | IN_SAMPLE | 461 | -0.002 | 0.016 | 0.038 | 0.616 | 0.559 | 0.447 |
| S8 | UNSEEN | 207 | -0.010 | -0.082 | -0.152 | 0.519 | 0.636 | 0.454 |
| S9 | IN_SAMPLE | 403 | -0.016 | -0.034 | 0.053 | 0.555 | 0.629 | 0.429 |
| S9 | UNSEEN | 171 | 0.030 | 0.021 | -0.106 | 0.483 | 0.604 | 0.409 |

### Consecutive fires and invalidation

| Setup | fires | first-in-streak | max streak position | invalidated within 24 | never invalidated by data end | median candles to invalidation |
|---|---:|---:|---:|---:|---:|---:|
| S1 | 305 | 254 | 2 | 240 | 2 | 4.0 |
| S2 | 636 | 495 | 4 | 141 | 21 | 68.0 |
| S3 | 191 | 180 | 2 | 39 | 9 | 78.5 |
| S4 | 101 | 101 | 0 | 48 | 4 | 25.0 |
| S5 | 55 | 55 | 0 | 19 | 1 | 51.0 |
| S6 | 284 | 241 | 4 | 66 | 16 | 59.0 |
| S7 | 703 | 524 | 4 | 548 | 9 | 3.0 |
| S8 | 668 | 668 | 0 | 529 | 6 | 4.0 |
| S9 | 574 | 494 | 3 | 463 | 2 | 3.0 |

### Rediscovery check (descriptive): charts the AI cited for the setup and rated ACTIONABLE_NOW

| Setup | cited charts | PRESENT at end | FIRED on last 2 candles | either |
|---|---:|---:|---:|---:|
| S1 | 12 | 0 | 0 | 0 |
| S2 | 1 | 0 | 0 | 0 |
| S3 | 15 | 1 | 2 | 2 |
| S4 | 16 | 0 | 0 | 0 |
| S5 | 2 | 0 | 0 | 0 |
| S6 | 4 | 0 | 1 | 1 |
| S7 | 12 | 3 | 1 | 3 |
| S8 | 5 | 0 | 1 | 1 |
| S9 | 2 | 0 | 0 | 0 |

### Examples (charts in `examples/`)

* **S1 #1** `S1_1.png` - 2025-09-03T10:00:00+00:00 (IN_SAMPLE). S1 (bullish_breakout_from_right_edge_consolidation) was PRESENT for 2 completed candle(s) up to the previous candle; the trigger candle closed at 111261.20, above the operative level 111221.00, so the brain fired UP on that close. Invalidation rules at the fire: close lt 110843.00, close le 111221.00. After: {"analytical_reference_price": 111261.2, "fwd_return_pct_h1": 0.029120663807336022, "fwd_return_pct_h6": 0.17238713945202377, "fwd_return_pct_h24": 0.8155583437892133, "mfe_pct": 1.0869018130309493, "mae_pct": 0.264602574841899, "candles_to_invalidation": 11}
* **S1 #2** `S1_2.png` - 2025-12-02T14:00:00+00:00 (IN_SAMPLE). S1 (bullish_breakout_from_right_edge_consolidation) was PRESENT for 2 completed candle(s) up to the previous candle; the trigger candle closed at 87691.30, above the operative level 87576.50, so the brain fired UP on that close. Invalidation rules at the fire: close lt 87005.00, close le 87576.50. After: {"analytical_reference_price": 87691.2, "fwd_return_pct_h1": 0.6916315434159825, "fwd_return_pct_h6": 2.7920703559764393, "fwd_return_pct_h24": 4.742437097451058, "mfe_pct": 5.2251537212399946, "mae_pct": 0.14961592497307885, "candles_to_invalidation": 1253}
* **S1 #3** `S1_3.png` - 2026-03-13T08:45:00+00:00 (IN_SAMPLE). S1 (bullish_breakout_from_right_edge_consolidation) was PRESENT for 6 completed candle(s) up to the previous candle; the trigger candle closed at 71890.00, above the operative level 71616.00, so the brain fired UP on that close. Invalidation rules at the fire: close lt 71150.00, close le 71616.00. After: {"analytical_reference_price": 71890.0, "fwd_return_pct_h1": -0.1391014049241912, "fwd_return_pct_h6": 0.4595910418695226, "fwd_return_pct_h24": 1.4047850883293744, "mfe_pct": 2.754207817498955, "mae_pct": 0.47308387814717356, "candles_to_invalidation": 31}
* **S1 #4** `S1_4.png` - 2026-07-01T21:15:00+00:00 (UNSEEN). S1 (bullish_breakout_from_right_edge_consolidation) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 60427.10, above the operative level 60332.80, so the brain fired UP on that close. Invalidation rules at the fire: close lt 59844.50, close le 60332.80. After: {"analytical_reference_price": 60427.1, "fwd_return_pct_h1": 0.1280882253161364, "fwd_return_pct_h6": 0.06933974988043712, "fwd_return_pct_h24": 0.037896903872591814, "mfe_pct": 1.4809580469689942, "mae_pct": 1.4432266317595865, "candles_to_invalidation": 8}
* **S1 #5** `S1_5.png` - 2026-09-28T13:00:00+00:00 (UNSEEN). S1 (bullish_breakout_from_right_edge_consolidation) was PRESENT for 5 completed candle(s) up to the previous candle; the trigger candle closed at 83546.50, above the operative level 83477.70, so the brain fired UP on that close. Invalidation rules at the fire: close lt 82551.60, close le 83477.70. After: {"analytical_reference_price": 83546.4, "fwd_return_pct_h1": -0.2076690318194463, "fwd_return_pct_h6": -0.4209636800628136, "fwd_return_pct_h24": 0.5430515258586954, "mfe_pct": 0.961860714525109, "mae_pct": 1.2523579711393729, "candles_to_invalidation": 1}
* **S2 #1** `S2_1.png` - 2025-09-02T14:00:00+00:00 (IN_SAMPLE). S2 (bullish_rebound_breakout_after_drop) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 111113.40, above the operative level 110507.50, so the brain fired UP on that close. Invalidation rules at the fire: close lt 108333.00. After: {"analytical_reference_price": 111113.4, "fwd_return_pct_h1": -0.12284746934213553, "fwd_return_pct_h6": 0.08684821092685979, "fwd_return_pct_h24": -0.33344313107149803, "mfe_pct": 0.5658183441421105, "mae_pct": 0.8953915549339664, "candles_to_invalidation": 4234}
* **S2 #2** `S2_2.png` - 2025-11-26T17:45:00+00:00 (IN_SAMPLE). S2 (bullish_rebound_breakout_after_drop) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 89473.20, above the operative level 88784.70, so the brain fired UP on that close. Invalidation rules at the fire: close lt 86596.60. After: {"analytical_reference_price": 89473.2, "fwd_return_pct_h1": 0.3568666371606355, "fwd_return_pct_h6": 0.35396073908164905, "fwd_return_pct_h24": 0.9960524492250267, "mfe_pct": 1.3212895034490746, "mae_pct": 0.022911888699628236, "candles_to_invalidation": 422}
* **S2 #3** `S2_3.png` - 2026-03-06T07:45:00+00:00 (IN_SAMPLE). S2 (bullish_rebound_breakout_after_drop) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 71033.60, above the operative level 70854.60, so the brain fired UP on that close. Invalidation rules at the fire: close lt 70100.00. After: {"analytical_reference_price": 71033.6, "fwd_return_pct_h1": -0.009713712947123643, "fwd_return_pct_h6": -0.6948824218398153, "fwd_return_pct_h24": -1.3762501126227678, "mfe_pct": 0.18920623479592447, "mae_pct": 1.9942675015767297, "candles_to_invalidation": 18}
* **S2 #4** `S2_4.png` - 2026-06-08T08:00:00+00:00 (UNSEEN). S2 (bullish_rebound_breakout_after_drop) was PRESENT for 6 completed candle(s) up to the previous candle; the trigger candle closed at 63259.90, above the operative level 63248.60, so the brain fired UP on that close. Invalidation rules at the fire: close lt 62377.00. After: {"analytical_reference_price": 63259.9, "fwd_return_pct_h1": -0.15823610217531314, "fwd_return_pct_h6": 0.15049027899189937, "fwd_return_pct_h24": 0.7282654572643876, "mfe_pct": 1.0880510402324406, "mae_pct": 0.9508393152692252, "candles_to_invalidation": 118}
* **S2 #5** `S2_5.png` - 2026-09-28T16:15:00+00:00 (UNSEEN). S2 (bullish_rebound_breakout_after_drop) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 83382.90, above the operative level 83369.40, so the brain fired UP on that close. Invalidation rules at the fire: close lt 82500.10. After: {"analytical_reference_price": 83383.0, "fwd_return_pct_h1": 0.716692851060774, "fwd_return_pct_h6": 0.7122554957245342, "fwd_return_pct_h24": -0.29058681026108424, "mfe_pct": 1.1597088135471223, "mae_pct": 0.39096698367773186, "candles_to_invalidation": null}
* **S3 #1** `S3_1.png` - 2025-09-02T11:30:00+00:00 (IN_SAMPLE). S3 (bearish_breakdown_from_right_edge_range) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 109852.90, below the operative level 109932.40, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 110700.00. After: {"analytical_reference_price": 109853.0, "fwd_return_pct_h1": -0.011742965599470523, "fwd_return_pct_h6": 1.0044331970906484, "fwd_return_pct_h24": -0.8883690022120527, "mfe_pct": 1.3836672644351955, "mae_pct": 1.719661729766142, "candles_to_invalidation": 10}
* **S3 #2** `S3_2.png` - 2025-11-25T02:00:00+00:00 (IN_SAMPLE). S3 (bearish_breakdown_from_right_edge_range) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 87687.50, below the operative level 87825.00, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 89177.30. After: {"analytical_reference_price": 87687.6, "fwd_return_pct_h1": -0.0726442507264391, "fwd_return_pct_h6": -0.2405129117457827, "fwd_return_pct_h24": 0.3710900971174991, "mfe_pct": 0.5104484556539446, "mae_pct": 0.9009255584597975, "candles_to_invalidation": 159}
* **S3 #3** `S3_3.png` - 2026-03-17T04:45:00+00:00 (IN_SAMPLE). S3 (bearish_breakdown_from_right_edge_range) was PRESENT for 4 completed candle(s) up to the previous candle; the trigger candle closed at 74019.50, below the operative level 74201.10, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 75998.90. After: {"analytical_reference_price": 74019.4, "fwd_return_pct_h1": -0.24844837974911105, "fwd_return_pct_h6": -0.11875265133196589, "fwd_return_pct_h24": 0.41786342499396945, "mfe_pct": 0.6854959645714476, "mae_pct": 0.5529631420951864, "candles_to_invalidation": 2995}
* **S3 #4** `S3_4.png` - 2026-06-26T10:45:00+00:00 (UNSEEN). S3 (bearish_breakdown_from_right_edge_range) was PRESENT for 3 completed candle(s) up to the previous candle; the trigger candle closed at 59532.00, below the operative level 59544.70, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 60734.00. After: {"analytical_reference_price": 59532.1, "fwd_return_pct_h1": 0.40667135881313765, "fwd_return_pct_h6": 0.16024968042451793, "fwd_return_pct_h24": -0.8534891260345345, "mfe_pct": 1.9218203288645985, "mae_pct": 1.7602268356063488, "candles_to_invalidation": 114}
* **S3 #5** `S3_5.png` - 2026-09-27T15:00:00+00:00 (UNSEEN). S3 (bearish_breakdown_from_right_edge_range) was PRESENT for 2 completed candle(s) up to the previous candle; the trigger candle closed at 84488.00, below the operative level 84550.00, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 85146.40. After: {"analytical_reference_price": 84488.1, "fwd_return_pct_h1": 0.02343525301196081, "fwd_return_pct_h6": -0.05065802166219768, "fwd_return_pct_h24": -0.023435253011938606, "mfe_pct": 0.2628772572705551, "mae_pct": 0.3819472801495083, "candles_to_invalidation": null}
* **S4 #1** `S4_1.png` - 2025-09-03T05:30:00+00:00 (IN_SAMPLE). S4 (bearish_continuation_below_broken_support) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 110730.70, below the operative level 110783.60, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 110958.50. After: {"analytical_reference_price": 110730.7, "fwd_return_pct_h1": 0.0012643286821045763, "fwd_return_pct_h6": 0.048857272644342586, "fwd_return_pct_h24": -0.6523032907766346, "mfe_pct": 0.2201738090701122, "mae_pct": 0.8482742365035101, "candles_to_invalidation": 10}
* **S4 #2** `S4_2.png` - 2025-11-21T02:15:00+00:00 (IN_SAMPLE). S4 (bearish_continuation_below_broken_support) was PRESENT for 3 completed candle(s) up to the previous candle; the trigger candle closed at 86405.30, below the operative level 86522.40, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 87465.40. After: {"analytical_reference_price": 86405.3, "fwd_return_pct_h1": -0.05740388610420144, "fwd_return_pct_h6": 0.4416395753501279, "fwd_return_pct_h24": 2.2546070669276164, "mfe_pct": 6.127286173417601, "mae_pct": 0.4149051042007912, "candles_to_invalidation": 262}
* **S4 #3** `S4_3.png` - 2026-02-26T07:45:00+00:00 (IN_SAMPLE). S4 (bearish_continuation_below_broken_support) was PRESENT for 3 completed candle(s) up to the previous candle; the trigger candle closed at 67964.50, below the operative level 68080.00, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 68487.80. After: {"analytical_reference_price": 67964.5, "fwd_return_pct_h1": 0.24203812284354642, "fwd_return_pct_h6": -0.4805449903994008, "fwd_return_pct_h24": -0.1305093100074206, "mfe_pct": 0.315605941337016, "mae_pct": 1.0670276394294076, "candles_to_invalidation": 9}
* **S4 #4** `S4_4.png` - 2026-06-04T08:00:00+00:00 (UNSEEN). S4 (bearish_continuation_below_broken_support) was PRESENT for 3 completed candle(s) up to the previous candle; the trigger candle closed at 63561.70, below the operative level 63607.40, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 64480.00. After: {"analytical_reference_price": 63561.8, "fwd_return_pct_h1": 0.3815184592003362, "fwd_return_pct_h6": 1.148173903193428, "fwd_return_pct_h24": -1.008310022686576, "mfe_pct": 2.219886787347114, "mae_pct": 1.040404771419312, "candles_to_invalidation": 919}
* **S4 #5** `S4_5.png` - 2026-09-15T13:45:00+00:00 (UNSEEN). S4 (bearish_continuation_below_broken_support) was PRESENT for 5 completed candle(s) up to the previous candle; the trigger candle closed at 76398.20, below the operative level 76807.20, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 77188.00. After: {"analytical_reference_price": 76398.1, "fwd_return_pct_h1": -0.24908996427919217, "fwd_return_pct_h6": 0.534437374751473, "fwd_return_pct_h24": 0.7081327938783799, "mfe_pct": 1.9486086695873484, "mae_pct": 1.2114175614315048, "candles_to_invalidation": 246}
* **S5 #1** `S5_1.png` - 2025-09-05T05:15:00+00:00 (IN_SAMPLE). S5 (bullish_continuation_after_spike_and_pullback) was PRESENT for 3 completed candle(s) up to the previous candle; the trigger candle closed at 111519.40, above the operative level 111444.10, so the brain fired UP on that close. Invalidation rules at the fire: close lt 110893.50. After: {"analytical_reference_price": 111519.4, "fwd_return_pct_h1": -0.03138467387736599, "fwd_return_pct_h6": 0.08025509462927793, "fwd_return_pct_h24": 0.5425961760913367, "mfe_pct": 1.2819294221454003, "mae_pct": 0.06366605272266623, "candles_to_invalidation": 38}
* **S5 #2** `S5_2.png` - 2025-11-26T08:00:00+00:00 (IN_SAMPLE). S5 (bullish_continuation_after_spike_and_pullback) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 87896.20, above the operative level 87857.30, so the brain fired UP on that close. Invalidation rules at the fire: close lt 87711.10. After: {"analytical_reference_price": 87896.2, "fwd_return_pct_h1": -0.35473660977380916, "fwd_return_pct_h6": -0.933601225081393, "fwd_return_pct_h24": -0.9263199091655849, "mfe_pct": 0.014790172954004532, "mae_pct": 1.8604899870529157, "candles_to_invalidation": 1}
* **S5 #3** `S5_3.png` - 2026-04-15T01:15:00+00:00 (IN_SAMPLE). S5 (bullish_continuation_after_spike_and_pullback) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 74701.20, above the operative level 74635.00, so the brain fired UP on that close. Invalidation rules at the fire: close lt 74339.40. After: {"analytical_reference_price": 74701.2, "fwd_return_pct_h1": -0.08728106108067957, "fwd_return_pct_h6": -0.6171252938373173, "fwd_return_pct_h24": -1.109620728984262, "mfe_pct": 0.05086933007769634, "mae_pct": 1.2224703217618926, "candles_to_invalidation": 5}
* **S5 #4** `S5_4.png` - 2026-07-01T15:30:00+00:00 (UNSEEN). S5 (bullish_continuation_after_spike_and_pullback) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 60288.40, above the operative level 60067.90, so the brain fired UP on that close. Invalidation rules at the fire: close lt 58733.50. After: {"analytical_reference_price": 60288.4, "fwd_return_pct_h1": -0.1584052653578416, "fwd_return_pct_h6": -0.6395923593925157, "fwd_return_pct_h24": 0.3584437470558255, "mfe_pct": 0.5085555430232036, "mae_pct": 0.8721412411011098, "candles_to_invalidation": null}
* **S5 #5** `S5_5.png` - 2026-09-14T20:30:00+00:00 (UNSEEN). S5 (bullish_continuation_after_spike_and_pullback) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 79405.60, above the operative level 79298.30, so the brain fired UP on that close. Invalidation rules at the fire: close lt 78666.10. After: {"analytical_reference_price": 79405.6, "fwd_return_pct_h1": -0.1329881015948553, "fwd_return_pct_h6": -0.8530884471624312, "fwd_return_pct_h24": -1.8719082785093377, "mfe_pct": 0.07253896450627462, "mae_pct": 2.1357435747604847, "candles_to_invalidation": 8}
* **S6 #1** `S6_1.png` - 2025-09-02T11:15:00+00:00 (IN_SAMPLE). S6 (bearish_rejection_from_recent_high) was PRESENT for 2 completed candle(s) up to the previous candle; the trigger candle closed at 110027.70, below the operative level 110082.60, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 110700.00. After: {"analytical_reference_price": 110027.7, "fwd_return_pct_h1": 0.15886908478501827, "fwd_return_pct_h6": 1.1993343494410835, "fwd_return_pct_h24": -0.536046831843251, "mfe_pct": 1.5402485010592715, "mae_pct": 1.5581530832690316, "candles_to_invalidation": 11}
* **S6 #2** `S6_2.png` - 2025-11-25T07:30:00+00:00 (IN_SAMPLE). S6 (bearish_rejection_from_recent_high) was PRESENT for 3 completed candle(s) up to the previous candle; the trigger candle closed at 87667.00, below the operative level 87757.80, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 88477.60. After: {"analytical_reference_price": 87667.1, "fwd_return_pct_h1": 0.002965764808016136, "fwd_return_pct_h6": 0.7853573347356035, "fwd_return_pct_h24": 0.11258499482703632, "mfe_pct": 1.184823040798666, "mae_pct": 0.09787023866421052, "candles_to_invalidation": 136}
* **S6 #3** `S6_3.png` - 2026-04-24T03:30:00+00:00 (IN_SAMPLE). S6 (bearish_rejection_from_recent_high) was PRESENT for 2 completed candle(s) up to the previous candle; the trigger candle closed at 77697.00, below the operative level 77986.00, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 78546.00. After: {"analytical_reference_price": 77697.0, "fwd_return_pct_h1": 0.12432912467663648, "fwd_return_pct_h6": 0.09845939997683573, "fwd_return_pct_h24": 0.3076051842413441, "mfe_pct": 0.4391417944064724, "mae_pct": 0.41468782578477636, "candles_to_invalidation": 273}
* **S6 #4** `S6_4.png` - 2026-07-01T10:45:00+00:00 (UNSEEN). S6 (bearish_rejection_from_recent_high) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 58593.60, below the operative level 58634.00, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 59069.70. After: {"analytical_reference_price": 58593.6, "fwd_return_pct_h1": -0.0648534993582972, "fwd_return_pct_h6": 0.29132874580158896, "fwd_return_pct_h24": -2.5028330739193416, "mfe_pct": 0.5111479752054837, "mae_pct": 3.2877310832582385, "candles_to_invalidation": 13}
* **S6 #5** `S6_5.png` - 2026-09-27T15:00:00+00:00 (UNSEEN). S6 (bearish_rejection_from_recent_high) was PRESENT for 2 completed candle(s) up to the previous candle; the trigger candle closed at 84488.00, below the operative level 84626.10, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 85146.40. After: {"analytical_reference_price": 84488.1, "fwd_return_pct_h1": 0.02343525301196081, "fwd_return_pct_h6": -0.05065802166219768, "fwd_return_pct_h24": -0.023435253011938606, "mfe_pct": 0.2628772572705551, "mae_pct": 0.3819472801495083, "candles_to_invalidation": null}
* **S7 #1** `S7_1.png` - 2025-09-02T01:45:00+00:00 (IN_SAMPLE). S7 (bullish_breakout_from_right_edge_range) was PRESENT for 2 completed candle(s) up to the previous candle; the trigger candle closed at 109439.30, above the operative level 109410.50, so the brain fired UP on that close. Invalidation rules at the fire: close lt 107400.00, close le 109410.50. After: {"analytical_reference_price": 109439.3, "fwd_return_pct_h1": -0.1617334906199197, "fwd_return_pct_h6": 0.8130534460655481, "fwd_return_pct_h24": 0.718571847590388, "mfe_pct": 1.0586690521595, "mae_pct": 0.29075478370200747, "candles_to_invalidation": 1}
* **S7 #2** `S7_2.png` - 2025-11-30T13:30:00+00:00 (IN_SAMPLE). S7 (bullish_breakout_from_right_edge_range) was PRESENT for 3 completed candle(s) up to the previous candle; the trigger candle closed at 91808.90, above the operative level 91580.00, so the brain fired UP on that close. Invalidation rules at the fire: close lt 90859.70, close le 91580.00. After: {"analytical_reference_price": 91809.0, "fwd_return_pct_h1": -0.17329455717849385, "fwd_return_pct_h6": -0.3804637889531559, "fwd_return_pct_h24": -0.5439553856375623, "mfe_pct": 0.04868803712054781, "mae_pct": 0.7852171355749338, "candles_to_invalidation": 4}
* **S7 #3** `S7_3.png` - 2026-04-01T06:30:00+00:00 (IN_SAMPLE). S7 (bullish_breakout_from_right_edge_range) was PRESENT for 10 completed candle(s) up to the previous candle; the trigger candle closed at 68826.00, above the operative level 68732.50, so the brain fired UP on that close. Invalidation rules at the fire: close lt 67534.90, close le 68732.50. After: {"analytical_reference_price": 68825.9, "fwd_return_pct_h1": 0.5197171413668489, "fwd_return_pct_h6": -0.25281180485834387, "fwd_return_pct_h24": -0.5019912561986084, "mfe_pct": 0.6714042242818463, "mae_pct": 0.6769254016293247, "candles_to_invalidation": 6}
* **S7 #4** `S7_4.png` - 2026-07-05T08:00:00+00:00 (UNSEEN). S7 (bullish_breakout_from_right_edge_range) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 62995.10, above the operative level 62928.00, so the brain fired UP on that close. Invalidation rules at the fire: close lt 62549.60, close le 62928.00. After: {"analytical_reference_price": 62995.1, "fwd_return_pct_h1": -0.01777916060137219, "fwd_return_pct_h6": -0.4530511103244539, "fwd_return_pct_h24": -0.3574881220920312, "mfe_pct": 0.14112208727345976, "mae_pct": 0.9286436564113765, "candles_to_invalidation": 2}
* **S7 #5** `S7_5.png` - 2026-09-28T13:45:00+00:00 (UNSEEN). S7 (bullish_breakout_from_right_edge_range) was PRESENT for 9 completed candle(s) up to the previous candle; the trigger candle closed at 83710.70, above the operative level 83609.40, so the brain fired UP on that close. Invalidation rules at the fire: close lt 82551.60, close le 83609.40. After: {"analytical_reference_price": 83710.7, "fwd_return_pct_h1": -0.12137038634247865, "fwd_return_pct_h6": -0.9504161355716634, "fwd_return_pct_h24": -0.523588979664491, "mfe_pct": 0.7637016534326024, "mae_pct": 1.446171158525722, "candles_to_invalidation": 1}
* **S8 #1** `S8_1.png` - 2025-09-02T11:30:00+00:00 (IN_SAMPLE). S8 (bearish_breakdown_from_right_edge_support) was PRESENT for 4 completed candle(s) up to the previous candle; the trigger candle closed at 109852.90, below the operative level 109932.40, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 110700.00, close ge 109932.40. After: {"analytical_reference_price": 109853.0, "fwd_return_pct_h1": -0.011742965599470523, "fwd_return_pct_h6": 1.0044331970906484, "fwd_return_pct_h24": -0.8883690022120527, "mfe_pct": 1.3836672644351955, "mae_pct": 1.719661729766142, "candles_to_invalidation": 9}
* **S8 #2** `S8_2.png` - 2025-12-04T05:45:00+00:00 (IN_SAMPLE). S8 (bearish_breakdown_from_right_edge_support) was PRESENT for 4 completed candle(s) up to the previous candle; the trigger candle closed at 92917.60, below the operative level 93072.80, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 94040.00, close ge 93072.80. After: {"analytical_reference_price": 92917.8, "fwd_return_pct_h1": -0.015712812830259715, "fwd_return_pct_h6": -0.10643816362418956, "fwd_return_pct_h24": 0.12247384247151549, "mfe_pct": 0.2708845883135358, "mae_pct": 0.7341973227949827, "candles_to_invalidation": 3}
* **S8 #3** `S8_3.png` - 2026-03-17T04:45:00+00:00 (IN_SAMPLE). S8 (bearish_breakdown_from_right_edge_support) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 74019.50, below the operative level 74201.10, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 75998.90, close ge 74201.10. After: {"analytical_reference_price": 74019.4, "fwd_return_pct_h1": -0.24844837974911105, "fwd_return_pct_h6": -0.11875265133196589, "fwd_return_pct_h24": 0.41786342499396945, "mfe_pct": 0.6854959645714476, "mae_pct": 0.5529631420951864, "candles_to_invalidation": 1}
* **S8 #4** `S8_4.png` - 2026-06-16T11:45:00+00:00 (UNSEEN). S8 (bearish_breakdown_from_right_edge_support) was PRESENT for 3 completed candle(s) up to the previous candle; the trigger candle closed at 66376.90, below the operative level 66440.10, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 66755.50, close ge 66440.10. After: {"analytical_reference_price": 66376.9, "fwd_return_pct_h1": -0.11916796355360137, "fwd_return_pct_h6": 0.30582928699592893, "fwd_return_pct_h24": 0.9803109214199468, "mfe_pct": 1.5790131807902896, "mae_pct": 0.6179860764814471, "candles_to_invalidation": 1}
* **S8 #5** `S8_5.png` - 2026-09-28T09:45:00+00:00 (UNSEEN). S8 (bearish_breakdown_from_right_edge_support) was PRESENT for 1 completed candle(s) up to the previous candle; the trigger candle closed at 82603.50, below the operative level 82617.80, so the brain fired DOWN on that close. Invalidation rules at the fire: close gt 83250.00, close ge 82617.80. After: {"analytical_reference_price": 82603.6, "fwd_return_pct_h1": -0.044065876063514864, "fwd_return_pct_h6": -0.42976335171833746, "fwd_return_pct_h24": -0.6864107617585713, "mfe_pct": 0.12529720254322863, "mae_pct": 1.4421889602874272, "candles_to_invalidation": 1}
* **S9 #1** `S9_1.png` - 2025-09-02T11:30:00+00:00 (IN_SAMPLE). S9 (tight_range_breakout_both_directions) was PRESENT for 12 completed candle(s) up to the previous candle; the trigger candle closed at 109852.90, below the operative level 109932.40, so the brain fired DOWN on that close. Invalidation rules at the fire: close ge 109932.40. After: {"analytical_reference_price": 109853.0, "fwd_return_pct_h1": -0.011742965599470523, "fwd_return_pct_h6": 1.0044331970906484, "fwd_return_pct_h24": -0.8883690022120527, "mfe_pct": 1.3836672644351955, "mae_pct": 1.719661729766142, "candles_to_invalidation": 9}
* **S9 #2** `S9_2.png` - 2025-11-25T14:45:00+00:00 (IN_SAMPLE). S9 (tight_range_breakout_both_directions) was PRESENT for 11 completed candle(s) up to the previous candle; the trigger candle closed at 86562.10, below the operative level 86628.40, so the brain fired DOWN on that close. Invalidation rules at the fire: close ge 86628.40. After: {"analytical_reference_price": 86562.1, "fwd_return_pct_h1": -0.1535313953797246, "fwd_return_pct_h6": -0.27032615890787426, "fwd_return_pct_h24": -0.6730428212808892, "mfe_pct": 0.5787752376617439, "mae_pct": 1.7939721887523463, "candles_to_invalidation": 1}
* **S9 #3** `S9_3.png` - 2026-03-22T12:00:00+00:00 (IN_SAMPLE). S9 (tight_range_breakout_both_directions) was PRESENT for 11 completed candle(s) up to the previous candle; the trigger candle closed at 68177.00, below the operative level 68240.10, so the brain fired DOWN on that close. Invalidation rules at the fire: close ge 68240.10. After: {"analytical_reference_price": 68177.0, "fwd_return_pct_h1": -0.139196503219563, "fwd_return_pct_h6": -0.8612875309855106, "fwd_return_pct_h24": -0.6717808058436026, "mfe_pct": 0.03505581061060692, "mae_pct": 1.2071519720726842, "candles_to_invalidation": 1}
* **S9 #4** `S9_4.png` - 2026-06-16T02:15:00+00:00 (UNSEEN). S9 (tight_range_breakout_both_directions) was PRESENT for 3 completed candle(s) up to the previous candle; the trigger candle closed at 66028.20, below the operative level 66065.10, so the brain fired DOWN on that close. Invalidation rules at the fire: close ge 66065.10. After: {"analytical_reference_price": 66028.2, "fwd_return_pct_h1": 0.44344689087389977, "fwd_return_pct_h6": -0.10162324582527749, "fwd_return_pct_h24": -0.6173119969952401, "mfe_pct": 0.6377578065129619, "mae_pct": 0.7804241218146268, "candles_to_invalidation": 6}
* **S9 #5** `S9_5.png` - 2026-09-28T13:00:00+00:00 (UNSEEN). S9 (tight_range_breakout_both_directions) was PRESENT for 17 completed candle(s) up to the previous candle; the trigger candle closed at 83546.50, above the operative level 83477.70, so the brain fired UP on that close. Invalidation rules at the fire: close le 83477.70. After: {"analytical_reference_price": 83546.4, "fwd_return_pct_h1": -0.2076690318194463, "fwd_return_pct_h6": -0.4209636800628136, "fwd_return_pct_h24": 0.5430515258586954, "mfe_pct": 0.961860714525109, "mae_pct": 1.2523579711393729, "candles_to_invalidation": 1}

### Translation notes and data quality

Dataset: {"rows": 37727, "first_open": "2025-09-01T00:00:00+00:00", "last_open": "2026-09-28T23:30:00+00:00", "gaps": 0, "missing_candles": 0, "duplicate_timestamps": 0, "out_of_order": 0, "invalid_ohlc_rows": 0}.
Incomplete candles refused by the brain: 0; gaps seen: 0.
* S1-S4,S6-S8: Numeric translations of docs/setups/RECOGNIZER_PARAMETER_TABLE.md (judgments J-1..J-14); includes J-9 (c_t < c_{t-3} is OUR translation of 'bearish candles push') and J-14 (C6 RET <= 1.0).
* S5: J-15: the breakout level is the latest confirmed swing high before the spike's swing high; 'the spike breaks above it' = a completed close above it at or before the spike high; 'holds above' = no later completed close below it. Other S5 conditions as in the Experiment 3 table; the q33 of DT(spike high) is derived (price-only) by src/brain/derive_s5.py.
* S9: J-16: range = last 24 candles; compact = ZR <= q33(ZR); a prior move exists = UP or DN defined and > q33; direction is decided only at the trigger. 'Repeated tests' and 'waiting near one side' are not coded. The presence condition 'close inside the range' is true by construction (the range includes the decision candle).

No pass/fail is stated: nothing here is gated. Forward return, future high/low, MFE and MAE are descriptive statistics of the price series and are not trading results; where the order of two events inside one 15m candle is unknown it is flagged, never assumed.
