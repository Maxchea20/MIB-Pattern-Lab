# Hand-check of FIREs (independent recomputation from the raw Binance candles)

**270/270 checks agree; 0 MISMATCH.**
Every check re-derives the previous-candle state with `src/brain/explain.py`, which is written separately from the detectors. MISMATCH would mean a bug.

## S1 bullish_breakout_from_right_edge_consolidation

### S1-231-up 2025-09-03T10:00:00+00:00 up level 111221.00 (presence 2 / recomputed 2, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-09-03T08:30:00+00:00 | 111073.10 | 111085.40 | 110953.30 | 111013.60 |
| 2025-09-03T08:45:00+00:00 | 111013.60 | 111029.60 | 110923.00 | 110974.90 |
| 2025-09-03T09:00:00+00:00 | 110974.80 | 111026.70 | 110843.00 | 110866.90 |
| 2025-09-03T09:15:00+00:00 | 110866.90 | 111238.00 | 110866.90 | 111080.10 |
| 2025-09-03T09:30:00+00:00 | 111080.00 | 111200.00 | 111055.00 | 111150.40 |
| 2025-09-03T09:45:00+00:00 | 111150.60 | 111283.60 | 111092.40 | 111261.20 |

| previous-candle condition | ok | detail |
|---|---|---|
| A1 recent swing high and up-leg > q33 | ok | swing high idx 90 (recent from 48), UP 0.2153 vs q33 0.1889 |
| A2 compact right edge ZR <= q33 | ok | ZR 0.2203 vs q33 0.3754 |
| A3 close near the top DT <= q33 | ok | DT 0.0207 vs q33 0.0890 (level 111221.00) |


### S1-8887-up 2025-12-02T14:00:00+00:00 up level 87576.50 (presence 2 / recomputed 2, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-12-02T12:30:00+00:00 | 87405.70 | 87516.00 | 87130.30 | 87286.00 |
| 2025-12-02T12:45:00+00:00 | 87286.10 | 87320.20 | 87163.50 | 87225.60 |
| 2025-12-02T13:00:00+00:00 | 87225.60 | 87284.70 | 87005.00 | 87124.10 |
| 2025-12-02T13:15:00+00:00 | 87124.10 | 87399.20 | 87124.10 | 87278.00 |
| 2025-12-02T13:30:00+00:00 | 87278.10 | 87536.00 | 87268.00 | 87433.60 |
| 2025-12-02T13:45:00+00:00 | 87433.70 | 87870.20 | 87424.80 | 87691.30 |

| previous-candle condition | ok | detail |
|---|---|---|
| A1 recent swing high and up-leg > q33 | ok | swing high idx 88 (recent from 48), UP 0.3258 vs q33 0.1889 |
| A2 compact right edge ZR <= q33 | ok | ZR 0.3422 vs q33 0.3754 |
| A3 close near the top DT <= q33 | ok | DT 0.0371 vs q33 0.0890 (level 87576.50) |


### S1-18562-up 2026-03-13T08:45:00+00:00 up level 71616.00 (presence 6 / recomputed 6, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-03-13T07:15:00+00:00 | 71394.90 | 71559.50 | 71371.30 | 71479.90 |
| 2026-03-13T07:30:00+00:00 | 71479.90 | 71561.70 | 71348.00 | 71542.00 |
| 2026-03-13T07:45:00+00:00 | 71542.10 | 71649.70 | 71492.20 | 71585.30 |
| 2026-03-13T08:00:00+00:00 | 71585.20 | 71618.00 | 71347.10 | 71440.40 |
| 2026-03-13T08:15:00+00:00 | 71440.30 | 71569.60 | 71400.70 | 71543.90 |
| 2026-03-13T08:30:00+00:00 | 71543.80 | 72156.40 | 71537.70 | 71890.00 |

| previous-candle condition | ok | detail |
|---|---|---|
| A1 recent swing high and up-leg > q33 | ok | swing high idx 85 (recent from 48), UP 0.2601 vs q33 0.1889 |
| A2 compact right edge ZR <= q33 | ok | ZR 0.2727 vs q33 0.3754 |
| A3 close near the top DT <= q33 | ok | DT 0.0269 vs q33 0.0890 (level 71616.00) |


### S1-29172-up 2026-07-01T21:15:00+00:00 up level 60332.80 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-07-01T19:45:00+00:00 | 60185.90 | 60185.90 | 59952.30 | 60000.00 |
| 2026-07-01T20:00:00+00:00 | 60000.00 | 60030.10 | 59875.20 | 59969.30 |
| 2026-07-01T20:15:00+00:00 | 59969.30 | 59997.00 | 59844.50 | 59948.10 |
| 2026-07-01T20:30:00+00:00 | 59948.10 | 60049.10 | 59930.00 | 60010.50 |
| 2026-07-01T20:45:00+00:00 | 60010.50 | 60170.30 | 60003.50 | 60100.30 |
| 2026-07-01T21:00:00+00:00 | 60100.30 | 60443.70 | 60092.70 | 60427.10 |

| previous-candle condition | ok | detail |
|---|---|---|
| A1 recent swing high and up-leg > q33 | ok | swing high idx 89 (recent from 48), UP 0.2065 vs q33 0.1889 |
| A2 compact right edge ZR <= q33 | ok | ZR 0.3705 vs q33 0.3754 |
| A3 close near the top DT <= q33 | ok | DT 0.0842 vs q33 0.0890 (level 60332.80) |


### S1-37683-up 2026-09-28T13:00:00+00:00 up level 83477.70 (presence 5 / recomputed 5, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-09-28T11:30:00+00:00 | 82992.00 | 83081.60 | 82953.10 | 83045.80 |
| 2026-09-28T11:45:00+00:00 | 83045.90 | 83060.20 | 82953.00 | 83054.50 |
| 2026-09-28T12:00:00+00:00 | 83054.50 | 83477.70 | 82979.90 | 83346.70 |
| 2026-09-28T12:15:00+00:00 | 83346.60 | 83437.50 | 83241.70 | 83331.10 |
| 2026-09-28T12:30:00+00:00 | 83331.10 | 83399.30 | 83232.60 | 83312.10 |
| 2026-09-28T12:45:00+00:00 | 83312.10 | 83609.40 | 83312.00 | 83546.50 |

| previous-candle condition | ok | detail |
|---|---|---|
| A1 recent swing high and up-leg > q33 | ok | swing high idx 73 (recent from 48), UP 0.2436 vs q33 0.1889 |
| A2 compact right edge ZR <= q33 | ok | ZR 0.3569 vs q33 0.3754 |
| A3 close near the top DT <= q33 | ok | DT 0.0638 vs q33 0.0890 (level 83477.70) |

## S2 bullish_rebound_breakout_after_drop

### S2-151-up 2025-09-02T14:00:00+00:00 up level 110507.50 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-09-02T12:30:00+00:00 | 109389.50 | 109437.80 | 108612.10 | 108708.10 |
| 2025-09-02T12:45:00+00:00 | 108708.10 | 108800.20 | 108333.00 | 108749.60 |
| 2025-09-02T13:00:00+00:00 | 108749.50 | 109236.90 | 108687.90 | 109136.20 |
| 2025-09-02T13:15:00+00:00 | 109136.20 | 109541.20 | 109132.50 | 109325.20 |
| 2025-09-02T13:30:00+00:00 | 109325.20 | 110507.50 | 108990.70 | 110432.60 |
| 2025-09-02T13:45:00+00:00 | 110432.60 | 111243.90 | 110360.80 | 111113.40 |

| previous-candle condition | ok | detail |
|---|---|---|
| B1 recent swing low and decline >= q67 | ok | swing low idx 92, DN 0.7173 vs q67 0.3316 |
| B2 close above the low and rebound > q33 | ok | close 110432.60 vs low 108333.0, REB 0.6589 vs q33 0.1886 |
| B3 pressing into the rebound high DT <= q33 | ok | DT 0.0227 vs q33 0.0618 |


### S2-8326-up 2025-11-26T17:45:00+00:00 up level 88784.70 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-11-26T16:15:00+00:00 | 87514.10 | 87811.20 | 87514.00 | 87538.10 |
| 2025-11-26T16:30:00+00:00 | 87538.10 | 87939.30 | 87454.10 | 87579.10 |
| 2025-11-26T16:45:00+00:00 | 87579.20 | 87816.00 | 87455.00 | 87778.90 |
| 2025-11-26T17:00:00+00:00 | 87778.90 | 87948.00 | 87703.30 | 87813.00 |
| 2025-11-26T17:15:00+00:00 | 87813.00 | 88784.70 | 87663.40 | 88621.00 |
| 2025-11-26T17:30:00+00:00 | 88620.90 | 89479.30 | 88520.00 | 89473.20 |

| previous-candle condition | ok | detail |
|---|---|---|
| B1 recent swing low and decline >= q67 | ok | swing low idx 89, DN 0.3960 vs q67 0.3316 |
| B2 close above the low and rebound > q33 | ok | close 88621.00 vs low 86596.6, REB 0.8251 vs q33 0.1886 |
| B3 pressing into the rebound high DT <= q33 | ok | DT 0.0617 vs q33 0.0618 |


### S2-17886-up 2026-03-06T07:45:00+00:00 up level 70854.60 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-03-06T06:15:00+00:00 | 70269.90 | 70490.10 | 70265.40 | 70389.10 |
| 2026-03-06T06:30:00+00:00 | 70389.10 | 70647.30 | 70342.40 | 70626.80 |
| 2026-03-06T06:45:00+00:00 | 70626.80 | 70830.90 | 70555.00 | 70565.50 |
| 2026-03-06T07:00:00+00:00 | 70565.50 | 70776.60 | 70430.70 | 70514.60 |
| 2026-03-06T07:15:00+00:00 | 70514.60 | 70854.60 | 70510.00 | 70827.80 |
| 2026-03-06T07:30:00+00:00 | 70827.80 | 71046.30 | 70827.80 | 71033.60 |

| previous-candle condition | ok | detail |
|---|---|---|
| B1 recent swing low and decline >= q67 | ok | swing low idx 89, DN 0.3744 vs q67 0.3316 |
| B2 close above the low and rebound > q33 | ok | close 70827.80 vs low 70100.0, REB 0.2194 vs q33 0.1886 |
| B3 pressing into the rebound high DT <= q33 | ok | DT 0.0078 vs q33 0.0618 |


### S2-26911-up 2026-06-08T08:00:00+00:00 up level 63248.60 (presence 6 / recomputed 6, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-06-08T06:30:00+00:00 | 63040.10 | 63073.60 | 62868.70 | 63002.90 |
| 2026-06-08T06:45:00+00:00 | 63003.00 | 63015.90 | 62900.00 | 62958.80 |
| 2026-06-08T07:00:00+00:00 | 62958.90 | 63178.00 | 62779.00 | 63058.60 |
| 2026-06-08T07:15:00+00:00 | 63058.60 | 63223.10 | 62944.50 | 63152.00 |
| 2026-06-08T07:30:00+00:00 | 63152.10 | 63248.60 | 63052.10 | 63084.60 |
| 2026-06-08T07:45:00+00:00 | 63084.50 | 63320.90 | 63072.60 | 63259.90 |

| previous-candle condition | ok | detail |
|---|---|---|
| B1 recent swing low and decline >= q67 | ok | swing low idx 87, DN 0.3423 vs q67 0.3316 |
| B2 close above the low and rebound > q33 | ok | close 63084.60 vs low 62377.0, REB 0.2812 vs q33 0.1886 |
| B3 pressing into the rebound high DT <= q33 | ok | DT 0.0529 vs q33 0.0618 |


### S2-37696-up 2026-09-28T16:15:00+00:00 up level 83369.40 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-09-28T14:45:00+00:00 | 82907.80 | 83029.50 | 82500.10 | 82990.50 |
| 2026-09-28T15:00:00+00:00 | 82990.60 | 83233.10 | 82881.40 | 82915.10 |
| 2026-09-28T15:15:00+00:00 | 82915.00 | 83099.10 | 82755.10 | 83035.20 |
| 2026-09-28T15:30:00+00:00 | 83035.30 | 83337.30 | 82973.30 | 83170.60 |
| 2026-09-28T15:45:00+00:00 | 83170.60 | 83369.40 | 83169.40 | 83328.40 |
| 2026-09-28T16:00:00+00:00 | 83328.40 | 83444.10 | 83205.30 | 83382.90 |

| previous-candle condition | ok | detail |
|---|---|---|
| B1 recent swing low and decline >= q67 | ok | swing low idx 91, DN 0.5249 vs q67 0.3316 |
| B2 close above the low and rebound > q33 | ok | close 83328.40 vs low 82500.1, REB 0.3524 vs q33 0.1886 |
| B3 pressing into the rebound high DT <= q33 | ok | DT 0.0166 vs q33 0.0618 |

## S3 bearish_breakdown_from_right_edge_range

### S3-141-down 2025-09-02T11:30:00+00:00 down level 109932.40 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-09-02T10:00:00+00:00 | 110408.00 | 110435.70 | 110278.80 | 110396.60 |
| 2025-09-02T10:15:00+00:00 | 110396.70 | 110422.80 | 110193.80 | 110196.00 |
| 2025-09-02T10:30:00+00:00 | 110196.00 | 110300.00 | 110131.10 | 110198.90 |
| 2025-09-02T10:45:00+00:00 | 110198.90 | 110224.00 | 110082.60 | 110202.70 |
| 2025-09-02T11:00:00+00:00 | 110202.70 | 110211.00 | 110013.20 | 110027.70 |
| 2025-09-02T11:15:00+00:00 | 110027.70 | 110132.00 | 109845.00 | 109852.90 |

| previous-candle condition | ok | detail |
|---|---|---|
| C3a sideways/choppy EFF <= q33 | ok | EFF 0.0313 vs q33 0.1079 |
| C3b roll-over high in the upper third of the right edge | ok | swing high idx 86 (edge from 72), position 1.0000 |
| C3c close in the lower third and below 3 candles ago | ok | position 0.1242, close 110027.70 vs 110196.00 |
| C3d near the floor DF <= q33 | ok | DF 0.0289 vs q33 0.1397 |


### S3-8167-down 2025-11-25T02:00:00+00:00 down level 87825.00 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-11-25T00:30:00+00:00 | 87846.30 | 88234.90 | 87828.50 | 88147.30 |
| 2025-11-25T00:45:00+00:00 | 88147.20 | 88208.10 | 87913.30 | 88057.90 |
| 2025-11-25T01:00:00+00:00 | 88058.00 | 88146.90 | 87856.40 | 88089.60 |
| 2025-11-25T01:15:00+00:00 | 88089.50 | 88172.60 | 87880.90 | 88006.70 |
| 2025-11-25T01:30:00+00:00 | 88006.60 | 88052.80 | 87868.00 | 87933.40 |
| 2025-11-25T01:45:00+00:00 | 87933.50 | 87933.50 | 87666.00 | 87687.50 |

| previous-candle condition | ok | detail |
|---|---|---|
| C3a sideways/choppy EFF <= q33 | ok | EFF 0.1019 vs q33 0.1079 |
| C3b roll-over high in the upper third of the right edge | ok | swing high idx 76 (edge from 72), position 1.0000 |
| C3c close in the lower third and below 3 candles ago | ok | position 0.0802, close 87933.40 vs 88057.90 |
| C3d near the floor DF <= q33 | ok | DF 0.0274 vs q33 0.1397 |


### S3-18930-down 2026-03-17T04:45:00+00:00 down level 74201.10 (presence 4 / recomputed 4, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-03-17T03:15:00+00:00 | 74904.90 | 74970.70 | 74700.30 | 74796.20 |
| 2026-03-17T03:30:00+00:00 | 74796.20 | 74807.00 | 74292.30 | 74392.10 |
| 2026-03-17T03:45:00+00:00 | 74392.10 | 74525.20 | 74231.60 | 74424.90 |
| 2026-03-17T04:00:00+00:00 | 74424.90 | 74644.90 | 74389.20 | 74642.00 |
| 2026-03-17T04:15:00+00:00 | 74642.00 | 74652.20 | 74250.00 | 74390.60 |
| 2026-03-17T04:30:00+00:00 | 74390.60 | 74473.40 | 73943.30 | 74019.50 |

| previous-candle condition | ok | detail |
|---|---|---|
| C3a sideways/choppy EFF <= q33 | ok | EFF 0.0642 vs q33 0.1079 |
| C3b roll-over high in the upper third of the right edge | ok | swing high idx 84 (edge from 72), position 1.0000 |
| C3c close in the lower third and below 3 candles ago | ok | position 0.1054, close 74390.60 vs 74392.10 |
| C3d near the floor DF <= q33 | ok | DF 0.0600 vs q33 0.1397 |


### S3-28650-down 2026-06-26T10:45:00+00:00 down level 59544.70 (presence 3 / recomputed 3, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-06-26T09:15:00+00:00 | 60141.10 | 60152.00 | 60052.30 | 60096.50 |
| 2026-06-26T09:30:00+00:00 | 60096.50 | 60104.30 | 59918.60 | 59974.70 |
| 2026-06-26T09:45:00+00:00 | 59974.80 | 60004.40 | 59544.70 | 59709.30 |
| 2026-06-26T10:00:00+00:00 | 59709.30 | 59799.50 | 59625.20 | 59717.90 |
| 2026-06-26T10:15:00+00:00 | 59717.90 | 59834.20 | 59688.80 | 59701.30 |
| 2026-06-26T10:30:00+00:00 | 59701.40 | 59787.90 | 59427.40 | 59532.00 |

| previous-candle condition | ok | detail |
|---|---|---|
| C3a sideways/choppy EFF <= q33 | ok | EFF 0.0992 vs q33 0.1079 |
| C3b roll-over high in the upper third of the right edge | ok | swing high idx 84 (edge from 72), position 1.0000 |
| C3c close in the lower third and below 3 candles ago | ok | position 0.1317, close 59701.30 vs 59974.70 |
| C3d near the floor DF <= q33 | ok | DF 0.0422 vs q33 0.1397 |


### S3-37595-down 2026-09-27T15:00:00+00:00 down level 84550.00 (presence 2 / recomputed 2, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-09-27T13:30:00+00:00 | 84894.80 | 85146.40 | 84741.50 | 84751.90 |
| 2026-09-27T13:45:00+00:00 | 84752.00 | 85052.30 | 84694.30 | 84991.80 |
| 2026-09-27T14:00:00+00:00 | 84991.80 | 85015.70 | 84870.10 | 84956.60 |
| 2026-09-27T14:15:00+00:00 | 84956.50 | 84987.90 | 84644.30 | 84663.40 |
| 2026-09-27T14:30:00+00:00 | 84663.30 | 84756.30 | 84626.10 | 84682.80 |
| 2026-09-27T14:45:00+00:00 | 84682.70 | 84700.00 | 84390.60 | 84488.00 |

| previous-candle condition | ok | detail |
|---|---|---|
| C3a sideways/choppy EFF <= q33 | ok | EFF 0.0302 vs q33 0.1079 |
| C3b roll-over high in the upper third of the right edge | ok | swing high idx 91 (edge from 72), position 1.0000 |
| C3c close in the lower third and below 3 candles ago | ok | position 0.2227, close 84682.80 vs 84991.80 |
| C3d near the floor DF <= q33 | ok | DF 0.0971 vs q33 0.1397 |

## S4 bearish_continuation_below_broken_support

### S4-213-down 2025-09-03T05:30:00+00:00 down level 110783.60 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-09-03T04:00:00+00:00 | 110991.80 | 111117.50 | 110855.70 | 110855.70 |
| 2025-09-03T04:15:00+00:00 | 110855.70 | 111055.60 | 110783.60 | 110965.80 |
| 2025-09-03T04:30:00+00:00 | 110965.80 | 111044.90 | 110923.10 | 110977.70 |
| 2025-09-03T04:45:00+00:00 | 110977.70 | 111048.40 | 110915.00 | 110966.70 |
| 2025-09-03T05:00:00+00:00 | 110966.70 | 111022.70 | 110811.30 | 110858.30 |
| 2025-09-03T05:15:00+00:00 | 110858.40 | 110874.70 | 110644.00 | 110730.70 |

| previous-candle condition | ok | detail |
|---|---|---|
| D1 a swing low was broken by a close | ok | break idx/level (80, 110958.5) |
| D2 close still below the broken level | ok | close 110858.30 vs broken level 110958.50 |
| D3 lower high or lower low after the break | ok | swing highs after break 1, lows 2; lower_high=False lower_low=True |
| D4 above the latest minor low and near it DF <= q33 | ok | minor low 110783.60, DF 0.0219 vs q33 0.1162 |


### S4-7784-down 2025-11-21T02:15:00+00:00 down level 86522.40 (presence 3 / recomputed 3, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-11-21T00:45:00+00:00 | 87187.10 | 87400.00 | 87155.00 | 87249.90 |
| 2025-11-21T01:00:00+00:00 | 87249.90 | 87438.00 | 87054.20 | 87117.80 |
| 2025-11-21T01:15:00+00:00 | 87117.70 | 87370.50 | 86800.00 | 87249.30 |
| 2025-11-21T01:30:00+00:00 | 87249.20 | 87299.00 | 86880.00 | 87203.60 |
| 2025-11-21T01:45:00+00:00 | 87203.60 | 87300.00 | 86959.60 | 87017.40 |
| 2025-11-21T02:00:00+00:00 | 87017.40 | 87038.00 | 86367.30 | 86405.30 |

| previous-candle condition | ok | detail |
|---|---|---|
| D1 a swing low was broken by a close | ok | break idx/level (52, 90400.0) |
| D2 close still below the broken level | ok | close 87017.40 vs broken level 90400.00 |
| D3 lower high or lower low after the break | ok | swing highs after break 4, lows 4; lower_high=True lower_low=False |
| D4 above the latest minor low and near it DF <= q33 | ok | minor low 86522.40, DF 0.0699 vs q33 0.1162 |


### S4-17118-down 2026-02-26T07:45:00+00:00 down level 68080.00 (presence 3 / recomputed 3, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-02-26T06:15:00+00:00 | 68424.80 | 68424.80 | 68201.10 | 68213.70 |
| 2026-02-26T06:30:00+00:00 | 68213.60 | 68222.00 | 68082.20 | 68090.00 |
| 2026-02-26T06:45:00+00:00 | 68090.00 | 68196.00 | 68025.50 | 68146.10 |
| 2026-02-26T07:00:00+00:00 | 68146.10 | 68235.30 | 68128.00 | 68198.50 |
| 2026-02-26T07:15:00+00:00 | 68198.60 | 68269.90 | 68065.00 | 68146.00 |
| 2026-02-26T07:30:00+00:00 | 68146.00 | 68165.70 | 67958.30 | 67964.50 |

| previous-candle condition | ok | detail |
|---|---|---|
| D1 a swing low was broken by a close | ok | break idx/level (60, 68720.0) |
| D2 close still below the broken level | ok | close 68146.00 vs broken level 68720.00 |
| D3 lower high or lower low after the break | ok | swing highs after break 4, lows 3; lower_high=True lower_low=False |
| D4 above the latest minor low and near it DF <= q33 | ok | minor low 68080.00, DF 0.0127 vs q33 0.1162 |


### S4-26527-down 2026-06-04T08:00:00+00:00 down level 63607.40 (presence 3 / recomputed 3, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-06-04T06:30:00+00:00 | 64228.10 | 64417.90 | 64039.30 | 64309.50 |
| 2026-06-04T06:45:00+00:00 | 64309.40 | 64309.40 | 63943.10 | 64007.20 |
| 2026-06-04T07:00:00+00:00 | 64007.40 | 64041.80 | 63678.30 | 63785.10 |
| 2026-06-04T07:15:00+00:00 | 63785.20 | 63800.00 | 63450.00 | 63664.20 |
| 2026-06-04T07:30:00+00:00 | 63664.10 | 64014.00 | 63660.00 | 63892.80 |
| 2026-06-04T07:45:00+00:00 | 63892.90 | 63917.50 | 63560.60 | 63561.70 |

| previous-candle condition | ok | detail |
|---|---|---|
| D1 a swing low was broken by a close | ok | break idx/level (61, 64711.1) |
| D2 close still below the broken level | ok | close 63892.80 vs broken level 64711.10 |
| D3 lower high or lower low after the break | ok | swing highs after break 2, lows 2; lower_high=True lower_low=False |
| D4 above the latest minor low and near it DF <= q33 | ok | minor low 63607.40, DF 0.0468 vs q33 0.1162 |


### S4-36438-down 2026-09-15T13:45:00+00:00 down level 76807.20 (presence 5 / recomputed 5, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-09-15T12:15:00+00:00 | 76892.40 | 76958.00 | 76865.80 | 76911.60 |
| 2026-09-15T12:30:00+00:00 | 76911.70 | 76940.60 | 76818.00 | 76909.60 |
| 2026-09-15T12:45:00+00:00 | 76909.60 | 77099.90 | 76840.00 | 76916.10 |
| 2026-09-15T13:00:00+00:00 | 76916.00 | 77111.90 | 76916.00 | 76957.90 |
| 2026-09-15T13:15:00+00:00 | 76958.00 | 76977.40 | 76873.50 | 76913.30 |
| 2026-09-15T13:30:00+00:00 | 76913.30 | 76913.30 | 76065.00 | 76398.20 |

| previous-candle condition | ok | detail |
|---|---|---|
| D1 a swing low was broken by a close | ok | break idx/level (69, 77265.8) |
| D2 close still below the broken level | ok | close 76913.30 vs broken level 77265.80 |
| D3 lower high or lower low after the break | ok | swing highs after break 2, lows 3; lower_high=False lower_low=True |
| D4 above the latest minor low and near it DF <= q33 | ok | minor low 76807.20, DF 0.0365 vs q33 0.1162 |

## S5 bullish_continuation_after_spike_and_pullback

### S5-404-up 2025-09-05T05:15:00+00:00 up level 111444.10 (presence 3 / recomputed 3, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-09-05T03:45:00+00:00 | 111137.40 | 111279.60 | 111124.40 | 111266.90 |
| 2025-09-05T04:00:00+00:00 | 111267.00 | 111311.00 | 111114.30 | 111123.30 |
| 2025-09-05T04:15:00+00:00 | 111123.30 | 111254.40 | 111086.20 | 111213.50 |
| 2025-09-05T04:30:00+00:00 | 111213.50 | 111375.00 | 111213.50 | 111357.30 |
| 2025-09-05T04:45:00+00:00 | 111357.30 | 111429.10 | 111306.00 | 111396.70 |
| 2025-09-05T05:00:00+00:00 | 111396.80 | 111519.50 | 111361.10 | 111519.40 |

| previous-candle condition | ok | detail |
|---|---|---|
| E0 two confirmed swing highs | ok | 9 confirmed swing highs |
| E1 recent spike high above the previous swing high, up-leg >= q67 | ok | spike idx 87, spike high 111444.10, previous swing high 110893.50, UP 0.4243 vs q67 0.3250 |
| E2 shallow pullback or tight range, no higher high since | ok | RET 0.3844 vs q33 0.6908; ZR 0.5454 vs q33 0.3754; max high since 111429.10 |
| E3 broke above the previous swing high (a close) and held above it | ok | first close above 110893.50: idx 82; lowest close since: 111079.9 |
| E4 near the spike high DT <= q33 | ok | DT 0.0192 vs q33 0.1015 |


### S5-8287-up 2025-11-26T08:00:00+00:00 up level 87857.30 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-11-26T06:30:00+00:00 | 87581.00 | 87658.30 | 87422.40 | 87636.80 |
| 2025-11-26T06:45:00+00:00 | 87636.70 | 87857.30 | 87562.30 | 87762.40 |
| 2025-11-26T07:00:00+00:00 | 87762.40 | 87832.80 | 87661.00 | 87789.30 |
| 2025-11-26T07:15:00+00:00 | 87789.40 | 87855.00 | 87687.90 | 87770.00 |
| 2025-11-26T07:30:00+00:00 | 87770.00 | 87770.00 | 87670.50 | 87750.20 |
| 2025-11-26T07:45:00+00:00 | 87750.20 | 87947.00 | 87701.70 | 87896.20 |

| previous-candle condition | ok | detail |
|---|---|---|
| E0 two confirmed swing highs | ok | 9 confirmed swing highs |
| E1 recent spike high above the previous swing high, up-leg >= q67 | ok | spike idx 92, spike high 87857.30, previous swing high 87711.10, UP 0.4704 vs q67 0.3250 |
| E2 shallow pullback or tight range, no higher high since | ok | RET 0.2932 vs q33 0.6908; ZR 0.5660 vs q33 0.3754; max high since 87855.00 |
| E3 broke above the previous swing high (a close) and held above it | ok | first close above 87711.10: idx 92; lowest close since: 87750.2 |
| E4 near the spike high DT <= q33 | ok | DT 0.0501 vs q33 0.1015 |


### S5-21700-up 2026-04-15T01:15:00+00:00 up level 74635.00 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-04-14T23:45:00+00:00 | 74103.30 | 74200.10 | 74000.00 | 74106.90 |
| 2026-04-15T00:00:00+00:00 | 74106.90 | 74635.00 | 74085.00 | 74499.60 |
| 2026-04-15T00:15:00+00:00 | 74499.70 | 74600.20 | 74346.80 | 74538.50 |
| 2026-04-15T00:30:00+00:00 | 74538.50 | 74560.00 | 74391.90 | 74505.30 |
| 2026-04-15T00:45:00+00:00 | 74505.30 | 74551.70 | 74385.50 | 74520.30 |
| 2026-04-15T01:00:00+00:00 | 74520.30 | 74715.60 | 74461.00 | 74701.20 |

| previous-candle condition | ok | detail |
|---|---|---|
| E0 two confirmed swing highs | ok | 11 confirmed swing highs |
| E1 recent spike high above the previous swing high, up-leg >= q67 | ok | spike idx 92, spike high 74635.00, previous swing high 74339.40, UP 0.3872 vs q67 0.3250 |
| E2 shallow pullback or tight range, no higher high since | ok | RET 0.6335 vs q33 0.6908; ZR 0.3872 vs q33 0.3754; max high since 74600.20 |
| E3 broke above the previous swing high (a close) and held above it | ok | first close above 74339.40: idx 92; lowest close since: 74505.3 |
| E4 near the spike high DT <= q33 | ok | DT 0.0512 vs q33 0.1015 |


### S5-29149-up 2026-07-01T15:30:00+00:00 up level 60067.90 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-07-01T14:00:00+00:00 | 59463.00 | 59966.00 | 59239.90 | 59948.60 |
| 2026-07-01T14:15:00+00:00 | 59948.80 | 60067.90 | 59753.10 | 59756.40 |
| 2026-07-01T14:30:00+00:00 | 59756.50 | 59794.20 | 59510.10 | 59583.00 |
| 2026-07-01T14:45:00+00:00 | 59582.90 | 59746.10 | 59392.80 | 59523.80 |
| 2026-07-01T15:00:00+00:00 | 59523.70 | 59971.70 | 59496.90 | 59895.00 |
| 2026-07-01T15:15:00+00:00 | 59895.00 | 60520.00 | 59822.20 | 60288.40 |

| previous-candle condition | ok | detail |
|---|---|---|
| E0 two confirmed swing highs | ok | 9 confirmed swing highs |
| E1 recent spike high above the previous swing high, up-leg >= q67 | ok | spike idx 92, spike high 60067.90, previous swing high 58733.50, UP 0.7681 vs q67 0.3250 |
| E2 shallow pullback or tight range, no higher high since | ok | RET 0.3806 vs q33 0.6908; ZR 0.7681 vs q33 0.3754; max high since 59971.70 |
| E3 broke above the previous swing high (a close) and held above it | ok | first close above 58733.50: idx 88; lowest close since: 58989.1 |
| E4 near the spike high DT <= q33 | ok | DT 0.0749 vs q33 0.1015 |


### S5-36369-up 2026-09-14T20:30:00+00:00 up level 79298.30 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-09-14T19:00:00+00:00 | 79184.80 | 79184.80 | 78970.50 | 79040.10 |
| 2026-09-14T19:15:00+00:00 | 79040.10 | 79208.10 | 79040.00 | 79101.00 |
| 2026-09-14T19:30:00+00:00 | 79101.00 | 79156.70 | 78914.80 | 79099.00 |
| 2026-09-14T19:45:00+00:00 | 79099.00 | 79120.70 | 78935.40 | 78952.10 |
| 2026-09-14T20:00:00+00:00 | 78952.00 | 79198.90 | 78936.70 | 79142.90 |
| 2026-09-14T20:15:00+00:00 | 79142.90 | 79570.90 | 79142.80 | 79405.60 |

| previous-candle condition | ok | detail |
|---|---|---|
| E0 two confirmed swing highs | ok | 10 confirmed swing highs |
| E1 recent spike high above the previous swing high, up-leg >= q67 | ok | spike idx 90, spike high 79298.30, previous swing high 78666.10, UP 0.6298 vs q67 0.3250 |
| E2 shallow pullback or tight range, no higher high since | ok | RET 0.2065 vs q33 0.6908; ZR 0.3848 vs q33 0.3754; max high since 79208.10 |
| E3 broke above the previous swing high (a close) and held above it | ok | first close above 78666.10: idx 82; lowest close since: 78786.7 |
| E4 near the spike high DT <= q33 | ok | DT 0.0527 vs q33 0.1015 |

## S6 bearish_rejection_from_recent_high

### S6-140-down 2025-09-02T11:15:00+00:00 down level 110082.60 (presence 2 / recomputed 2, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-09-02T09:45:00+00:00 | 110337.70 | 110408.10 | 110246.30 | 110408.00 |
| 2025-09-02T10:00:00+00:00 | 110408.00 | 110435.70 | 110278.80 | 110396.60 |
| 2025-09-02T10:15:00+00:00 | 110396.70 | 110422.80 | 110193.80 | 110196.00 |
| 2025-09-02T10:30:00+00:00 | 110196.00 | 110300.00 | 110131.10 | 110198.90 |
| 2025-09-02T10:45:00+00:00 | 110198.90 | 110224.00 | 110082.60 | 110202.70 |
| 2025-09-02T11:00:00+00:00 | 110202.70 | 110211.00 | 110013.20 | 110027.70 |

| previous-candle condition | ok | detail |
|---|---|---|
| F1 recent swing high in the top third of the window | ok | swing high idx 87, height 1.0000 |
| F2 no close above the high since, close below it | ok | close 110202.70 vs high 110700.0 |
| F3 up-leg > q33 and retracement in (q33, 1.0] | ok | UP 0.2326 vs q33 0.1889; RET 0.8043 vs q33 0.6908 |
| F4 near the pullback low DF <= q33 | ok | DF 0.0364 vs q33 0.0651 |


### S6-8189-down 2025-11-25T07:30:00+00:00 down level 87757.80 (presence 3 / recomputed 3, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-11-25T06:00:00+00:00 | 88078.30 | 88110.10 | 87988.10 | 88041.00 |
| 2025-11-25T06:15:00+00:00 | 88041.00 | 88081.00 | 87879.80 | 87899.80 |
| 2025-11-25T06:30:00+00:00 | 87899.90 | 87948.70 | 87784.50 | 87835.50 |
| 2025-11-25T06:45:00+00:00 | 87835.60 | 88024.80 | 87757.80 | 87963.80 |
| 2025-11-25T07:00:00+00:00 | 87963.80 | 88022.20 | 87814.50 | 87976.40 |
| 2025-11-25T07:15:00+00:00 | 87976.40 | 87976.40 | 87651.90 | 87667.00 |

| previous-candle condition | ok | detail |
|---|---|---|
| F1 recent swing high in the top third of the window | ok | swing high idx 86, height 0.8229 |
| F2 no close above the high since, close below it | ok | close 87976.40 vs high 88477.6 |
| F3 up-leg > q33 and retracement in (q33, 1.0] | ok | UP 0.2474 vs q33 0.1889; RET 0.7363 vs q33 0.6908 |
| F4 near the pullback low DF <= q33 | ok | DF 0.0553 vs q33 0.0651 |


### S6-22573-down 2026-04-24T03:30:00+00:00 down level 77986.00 (presence 2 / recomputed 2, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-04-24T02:00:00+00:00 | 78369.80 | 78546.00 | 78250.00 | 78349.90 |
| 2026-04-24T02:15:00+00:00 | 78349.90 | 78357.30 | 78192.30 | 78215.70 |
| 2026-04-24T02:30:00+00:00 | 78215.70 | 78365.90 | 78206.70 | 78365.90 |
| 2026-04-24T02:45:00+00:00 | 78365.90 | 78395.30 | 77986.00 | 78074.00 |
| 2026-04-24T03:00:00+00:00 | 78074.00 | 78134.00 | 78023.50 | 78090.90 |
| 2026-04-24T03:15:00+00:00 | 78090.80 | 78090.80 | 77591.40 | 77697.00 |

| previous-candle condition | ok | detail |
|---|---|---|
| F1 recent swing high in the top third of the window | ok | swing high idx 91, height 0.9524 |
| F2 no close above the high since, close below it | ok | close 78090.90 vs high 78546.0 |
| F3 up-leg > q33 and retracement in (q33, 1.0] | ok | UP 0.3009 vs q33 0.1889; RET 0.8682 vs q33 0.6908 |
| F4 near the pullback low DF <= q33 | ok | DF 0.0489 vs q33 0.0651 |


### S6-29130-down 2026-07-01T10:45:00+00:00 down level 58634.00 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-07-01T09:15:00+00:00 | 58930.00 | 58976.00 | 58841.30 | 58869.40 |
| 2026-07-01T09:30:00+00:00 | 58869.30 | 58920.70 | 58792.80 | 58859.60 |
| 2026-07-01T09:45:00+00:00 | 58859.70 | 58950.00 | 58818.10 | 58921.40 |
| 2026-07-01T10:00:00+00:00 | 58921.40 | 58923.30 | 58724.20 | 58733.70 |
| 2026-07-01T10:15:00+00:00 | 58733.70 | 58768.50 | 58634.00 | 58715.40 |
| 2026-07-01T10:30:00+00:00 | 58715.50 | 58730.60 | 58590.90 | 58593.60 |

| previous-candle condition | ok | detail |
|---|---|---|
| F1 recent swing high in the top third of the window | ok | swing high idx 90, height 0.7777 |
| F2 no close above the high since, close below it | ok | close 58715.40 vs high 59069.7 |
| F3 up-leg > q33 and retracement in (q33, 1.0] | ok | UP 0.3672 vs q33 0.1889; RET 0.7039 vs q33 0.6908 |
| F4 near the pullback low DF <= q33 | ok | DF 0.0483 vs q33 0.0651 |


### S6-37595-down 2026-09-27T15:00:00+00:00 down level 84626.10 (presence 2 / recomputed 2, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-09-27T13:30:00+00:00 | 84894.80 | 85146.40 | 84741.50 | 84751.90 |
| 2026-09-27T13:45:00+00:00 | 84752.00 | 85052.30 | 84694.30 | 84991.80 |
| 2026-09-27T14:00:00+00:00 | 84991.80 | 85015.70 | 84870.10 | 84956.60 |
| 2026-09-27T14:15:00+00:00 | 84956.50 | 84987.90 | 84644.30 | 84663.40 |
| 2026-09-27T14:30:00+00:00 | 84663.30 | 84756.30 | 84626.10 | 84682.80 |
| 2026-09-27T14:45:00+00:00 | 84682.70 | 84700.00 | 84390.60 | 84488.00 |

| previous-candle condition | ok | detail |
|---|---|---|
| F1 recent swing high in the top third of the window | ok | swing high idx 91, height 1.0000 |
| F2 no close above the high since, close below it | ok | close 84682.80 vs high 85146.4 |
| F3 up-leg > q33 and retracement in (q33, 1.0] | ok | UP 0.4082 vs q33 0.1889; RET 0.9318 vs q33 0.6908 |
| F4 near the pullback low DF <= q33 | ok | DF 0.0414 vs q33 0.0651 |

## S7 bullish_breakout_from_right_edge_range

### S7-102-up 2025-09-02T01:45:00+00:00 up level 109410.50 (presence 2 / recomputed 2, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-09-02T00:15:00+00:00 | 109045.20 | 109298.90 | 108975.60 | 108975.60 |
| 2025-09-02T00:30:00+00:00 | 108975.60 | 109063.90 | 108834.90 | 108834.90 |
| 2025-09-02T00:45:00+00:00 | 108834.90 | 109076.90 | 108834.90 | 108985.30 |
| 2025-09-02T01:00:00+00:00 | 108985.40 | 109202.60 | 108970.30 | 109151.00 |
| 2025-09-02T01:15:00+00:00 | 109151.00 | 109219.40 | 109003.40 | 109157.70 |
| 2025-09-02T01:30:00+00:00 | 109157.60 | 109499.00 | 108924.80 | 109439.30 |

| previous-candle condition | ok | detail |
|---|---|---|
| H1 a decline preceded: DN > q33 | ok | DN 0.7129 vs q33 0.1845 |
| H2 rebound > q33 or compact edge | ok | REB 0.7549 vs q33 0.1886; ZR 0.7549 vs q33 0.3754 |
| H3 near the local high DT <= q33 | ok | DT 0.0949 vs q33 0.1307 |


### S7-8693-up 2025-11-30T13:30:00+00:00 up level 91580.00 (presence 3 / recomputed 3, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-11-30T12:00:00+00:00 | 91000.90 | 91218.50 | 90960.00 | 91197.90 |
| 2025-11-30T12:15:00+00:00 | 91197.90 | 91333.10 | 91197.80 | 91218.50 |
| 2025-11-30T12:30:00+00:00 | 91218.60 | 91441.00 | 91164.70 | 91400.10 |
| 2025-11-30T12:45:00+00:00 | 91400.20 | 91495.70 | 91350.20 | 91432.40 |
| 2025-11-30T13:00:00+00:00 | 91432.30 | 91480.00 | 91356.80 | 91419.10 |
| 2025-11-30T13:15:00+00:00 | 91419.00 | 91934.40 | 91419.00 | 91808.90 |

| previous-candle condition | ok | detail |
|---|---|---|
| H1 a decline preceded: DN > q33 | ok | DN 0.2832 vs q33 0.1845 |
| H2 rebound > q33 or compact edge | ok | REB 0.3828 vs q33 0.1886; ZR 0.4843 vs q33 0.3754 |
| H3 near the local high DT <= q33 | ok | DT 0.1082 vs q33 0.1307 |


### S7-20377-up 2026-04-01T06:30:00+00:00 up level 68732.50 (presence 10 / recomputed 10, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-04-01T05:00:00+00:00 | 68272.30 | 68401.00 | 68114.50 | 68366.30 |
| 2026-04-01T05:15:00+00:00 | 68366.40 | 68732.50 | 68318.90 | 68552.90 |
| 2026-04-01T05:30:00+00:00 | 68552.90 | 68630.50 | 68440.40 | 68470.10 |
| 2026-04-01T05:45:00+00:00 | 68470.10 | 68528.50 | 68404.00 | 68418.20 |
| 2026-04-01T06:00:00+00:00 | 68418.30 | 68671.70 | 68418.20 | 68616.60 |
| 2026-04-01T06:15:00+00:00 | 68616.60 | 68860.00 | 68578.20 | 68826.00 |

| previous-candle condition | ok | detail |
|---|---|---|
| H1 a decline preceded: DN > q33 | ok | DN 0.2845 vs q33 0.1845 |
| H2 rebound > q33 or compact edge | ok | REB 0.4286 vs q33 0.1886; ZR 0.4286 vs q33 0.3754 |
| H3 near the local high DT <= q33 | ok | DT 0.0415 vs q33 0.1307 |


### S7-29503-up 2026-07-05T08:00:00+00:00 up level 62928.00 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-07-05T06:30:00+00:00 | 62772.00 | 62800.00 | 62718.00 | 62729.80 |
| 2026-07-05T06:45:00+00:00 | 62729.80 | 62774.80 | 62718.00 | 62749.90 |
| 2026-07-05T07:00:00+00:00 | 62749.80 | 62774.20 | 62728.30 | 62728.70 |
| 2026-07-05T07:15:00+00:00 | 62728.60 | 62808.70 | 62690.50 | 62726.40 |
| 2026-07-05T07:30:00+00:00 | 62726.40 | 62920.10 | 62726.30 | 62895.10 |
| 2026-07-05T07:45:00+00:00 | 62895.10 | 63039.30 | 62868.00 | 62995.10 |

| previous-candle condition | ok | detail |
|---|---|---|
| H1 a decline preceded: DN > q33 | ok | DN 0.2820 vs q33 0.1845 |
| H2 rebound > q33 or compact edge | ok | REB 0.2746 vs q33 0.1886; ZR 0.3557 vs q33 0.3754 |
| H3 near the local high DT <= q33 | ok | DT 0.0309 vs q33 0.1307 |


### S7-37686-up 2026-09-28T13:45:00+00:00 up level 83609.40 (presence 9 / recomputed 9, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-09-28T12:15:00+00:00 | 83346.60 | 83437.50 | 83241.70 | 83331.10 |
| 2026-09-28T12:30:00+00:00 | 83331.10 | 83399.30 | 83232.60 | 83312.10 |
| 2026-09-28T12:45:00+00:00 | 83312.10 | 83609.40 | 83312.00 | 83546.50 |
| 2026-09-28T13:00:00+00:00 | 83546.40 | 83546.50 | 83270.00 | 83372.90 |
| 2026-09-28T13:15:00+00:00 | 83372.90 | 83525.00 | 83315.00 | 83524.90 |
| 2026-09-28T13:30:00+00:00 | 83525.00 | 83793.60 | 83349.40 | 83710.70 |

| previous-candle condition | ok | detail |
|---|---|---|
| H1 a decline preceded: DN > q33 | ok | DN 0.2692 vs q33 0.1845 |
| H2 rebound > q33 or compact edge | ok | REB 0.4077 vs q33 0.1886; ZR 0.4077 vs q33 0.3754 |
| H3 near the local high DT <= q33 | ok | DT 0.0326 vs q33 0.1307 |

## S8 bearish_breakdown_from_right_edge_support

### S8-141-down 2025-09-02T11:30:00+00:00 down level 109932.40 (presence 4 / recomputed 4, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-09-02T10:00:00+00:00 | 110408.00 | 110435.70 | 110278.80 | 110396.60 |
| 2025-09-02T10:15:00+00:00 | 110396.70 | 110422.80 | 110193.80 | 110196.00 |
| 2025-09-02T10:30:00+00:00 | 110196.00 | 110300.00 | 110131.10 | 110198.90 |
| 2025-09-02T10:45:00+00:00 | 110198.90 | 110224.00 | 110082.60 | 110202.70 |
| 2025-09-02T11:00:00+00:00 | 110202.70 | 110211.00 | 110013.20 | 110027.70 |
| 2025-09-02T11:15:00+00:00 | 110027.70 | 110132.00 | 109845.00 | 109852.90 |

| previous-candle condition | ok | detail |
|---|---|---|
| I1 prior rise or bounce | ok | UP 0.2326, REB 0.2326 vs q33 0.1889/0.1886 |
| I2 lower-high sequence, choppy edge or rebound | ok | lower_high=False, EFF 0.0313 vs q33 0.1079, REB 0.2326 |
| I3 recent swing low, above it, near it, pressing lower | ok | swing low idx 82, DF 0.0289 vs q33 0.1072, close 110027.70 vs 3 ago 110196.00 |
| I4 rolling over from a recent high | ok | swing high idx 86, high 110700.0 |


### S8-9046-down 2025-12-04T05:45:00+00:00 down level 93072.80 (presence 4 / recomputed 4, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-12-04T04:15:00+00:00 | 93422.20 | 93479.70 | 93275.10 | 93358.20 |
| 2025-12-04T04:30:00+00:00 | 93358.20 | 93480.00 | 93255.60 | 93336.30 |
| 2025-12-04T04:45:00+00:00 | 93336.30 | 93343.00 | 93170.00 | 93317.80 |
| 2025-12-04T05:00:00+00:00 | 93317.80 | 93339.70 | 92985.00 | 93152.90 |
| 2025-12-04T05:15:00+00:00 | 93153.00 | 93232.70 | 92950.00 | 93168.50 |
| 2025-12-04T05:30:00+00:00 | 93168.50 | 93181.30 | 92910.20 | 92917.60 |

| previous-candle condition | ok | detail |
|---|---|---|
| I1 prior rise or bounce | ok | UP 0.3797, REB 0.3797 vs q33 0.1889/0.1886 |
| I2 lower-high sequence, choppy edge or rebound | ok | lower_high=False, EFF 0.0776 vs q33 0.1079, REB 0.3797 |
| I3 recent swing low, above it, near it, pressing lower | ok | swing low idx 82, DF 0.0376 vs q33 0.1072, close 93168.50 vs 3 ago 93336.30 |
| I4 rolling over from a recent high | ok | swing high idx 83, high 94040.0 |


### S8-18930-down 2026-03-17T04:45:00+00:00 down level 74201.10 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-03-17T03:15:00+00:00 | 74904.90 | 74970.70 | 74700.30 | 74796.20 |
| 2026-03-17T03:30:00+00:00 | 74796.20 | 74807.00 | 74292.30 | 74392.10 |
| 2026-03-17T03:45:00+00:00 | 74392.10 | 74525.20 | 74231.60 | 74424.90 |
| 2026-03-17T04:00:00+00:00 | 74424.90 | 74644.90 | 74389.20 | 74642.00 |
| 2026-03-17T04:15:00+00:00 | 74642.00 | 74652.20 | 74250.00 | 74390.60 |
| 2026-03-17T04:30:00+00:00 | 74390.60 | 74473.40 | 73943.30 | 74019.50 |

| previous-candle condition | ok | detail |
|---|---|---|
| I1 prior rise or bounce | ok | UP 0.5695, REB 0.5695 vs q33 0.1889/0.1886 |
| I2 lower-high sequence, choppy edge or rebound | ok | lower_high=False, EFF 0.0642 vs q33 0.1079, REB 0.5695 |
| I3 recent swing low, above it, near it, pressing lower | ok | swing low idx 74, DF 0.0600 vs q33 0.1072, close 74390.60 vs 3 ago 74392.10 |
| I4 rolling over from a recent high | ok | swing high idx 84, high 75998.9 |


### S8-27694-down 2026-06-16T11:45:00+00:00 down level 66440.10 (presence 3 / recomputed 3, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-06-16T10:15:00+00:00 | 66509.80 | 66755.50 | 66509.80 | 66633.40 |
| 2026-06-16T10:30:00+00:00 | 66633.40 | 66637.50 | 66539.20 | 66579.90 |
| 2026-06-16T10:45:00+00:00 | 66579.90 | 66592.40 | 66451.10 | 66476.10 |
| 2026-06-16T11:00:00+00:00 | 66476.10 | 66619.30 | 66402.40 | 66484.00 |
| 2026-06-16T11:15:00+00:00 | 66484.10 | 66556.80 | 66359.40 | 66445.10 |
| 2026-06-16T11:30:00+00:00 | 66445.00 | 66452.60 | 66325.40 | 66376.90 |

| previous-candle condition | ok | detail |
|---|---|---|
| I1 prior rise or bounce | ok | UP 0.1913, REB 0.1913 vs q33 0.1889/0.1886 |
| I2 lower-high sequence, choppy edge or rebound | ok | lower_high=True, EFF 0.1901 vs q33 0.1079, REB 0.1913 |
| I3 recent swing low, above it, near it, pressing lower | ok | swing low idx 89, DF 0.0030 vs q33 0.1072, close 66445.10 vs 3 ago 66579.90 |
| I4 rolling over from a recent high | ok | swing high idx 91, high 66755.5 |


### S8-37670-down 2026-09-28T09:45:00+00:00 down level 82617.80 (presence 1 / recomputed 1, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-09-28T08:15:00+00:00 | 82990.20 | 83015.60 | 82775.00 | 82809.70 |
| 2026-09-28T08:30:00+00:00 | 82809.80 | 82934.50 | 82725.50 | 82888.80 |
| 2026-09-28T08:45:00+00:00 | 82888.90 | 82994.70 | 82865.30 | 82931.10 |
| 2026-09-28T09:00:00+00:00 | 82931.00 | 82979.40 | 82551.60 | 82853.10 |
| 2026-09-28T09:15:00+00:00 | 82853.00 | 82942.60 | 82729.20 | 82796.30 |
| 2026-09-28T09:30:00+00:00 | 82796.20 | 82828.50 | 82552.50 | 82603.50 |

| previous-candle condition | ok | detail |
|---|---|---|
| I1 prior rise or bounce | ok | UP 0.2436, REB 0.2456 vs q33 0.1889/0.1886 |
| I2 lower-high sequence, choppy edge or rebound | ok | lower_high=True, EFF 0.3179 vs q33 0.1079, REB 0.2456 |
| I3 recent swing low, above it, near it, pressing lower | ok | swing low idx 80, DF 0.0688 vs q33 0.1072, close 82796.30 vs 3 ago 82888.80 |
| I4 rolling over from a recent high | ok | swing high idx 86, high 83250.0 |

## S9 tight_range_breakout_both_directions

### S9-141-down 2025-09-02T11:30:00+00:00 down level 109932.40 (presence 12 / recomputed 12, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-09-02T10:00:00+00:00 | 110408.00 | 110435.70 | 110278.80 | 110396.60 |
| 2025-09-02T10:15:00+00:00 | 110396.70 | 110422.80 | 110193.80 | 110196.00 |
| 2025-09-02T10:30:00+00:00 | 110196.00 | 110300.00 | 110131.10 | 110198.90 |
| 2025-09-02T10:45:00+00:00 | 110198.90 | 110224.00 | 110082.60 | 110202.70 |
| 2025-09-02T11:00:00+00:00 | 110202.70 | 110211.00 | 110013.20 | 110027.70 |
| 2025-09-02T11:15:00+00:00 | 110027.70 | 110132.00 | 109845.00 | 109852.90 |

| previous-candle condition | ok | detail |
|---|---|---|
| compact range ZR <= q33 | ok | ZR 0.2326 vs q33 0.3754 |
| a prior move exists | ok | UP 0.2326, DN 0.1938 |
| close inside the range | ok | close 110027.70 in [109932.40, 110700.00] |


### S9-8218-down 2025-11-25T14:45:00+00:00 down level 86628.40 (presence 11 / recomputed 11, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2025-11-25T13:15:00+00:00 | 87550.00 | 87675.00 | 87421.80 | 87568.40 |
| 2025-11-25T13:30:00+00:00 | 87568.40 | 87647.40 | 86953.80 | 86984.90 |
| 2025-11-25T13:45:00+00:00 | 86984.90 | 87091.50 | 86806.20 | 87027.80 |
| 2025-11-25T14:00:00+00:00 | 87027.80 | 87261.30 | 86778.00 | 86951.90 |
| 2025-11-25T14:15:00+00:00 | 86951.90 | 87197.30 | 86830.00 | 87135.10 |
| 2025-11-25T14:30:00+00:00 | 87135.00 | 87194.80 | 86498.10 | 86562.10 |

| previous-candle condition | ok | detail |
|---|---|---|
| compact range ZR <= q33 | ok | ZR 0.2795 vs q33 0.3754 |
| a prior move exists | ok | UP 0.2795, DN 0.4680 |
| close inside the range | ok | close 87135.10 in [86628.40, 87732.70] |


### S9-19439-down 2026-03-22T12:00:00+00:00 down level 68240.10 (presence 11 / recomputed 11, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-03-22T10:30:00+00:00 | 68688.90 | 68730.20 | 68543.00 | 68574.70 |
| 2026-03-22T10:45:00+00:00 | 68574.70 | 68644.20 | 68539.50 | 68601.10 |
| 2026-03-22T11:00:00+00:00 | 68601.10 | 68650.00 | 68520.40 | 68614.30 |
| 2026-03-22T11:15:00+00:00 | 68614.40 | 68640.00 | 68339.00 | 68374.10 |
| 2026-03-22T11:30:00+00:00 | 68374.10 | 68475.60 | 68240.10 | 68365.00 |
| 2026-03-22T11:45:00+00:00 | 68365.00 | 68383.40 | 68030.00 | 68177.00 |

| previous-candle condition | ok | detail |
|---|---|---|
| compact range ZR <= q33 | ok | ZR 0.3392 vs q33 0.3754 |
| a prior move exists | ok | UP 0.1253, DN 0.2490 |
| close inside the range | ok | close 68365.00 in [68240.10, 69220.00] |


### S9-27656-down 2026-06-16T02:15:00+00:00 down level 66065.10 (presence 3 / recomputed 3, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-06-16T00:45:00+00:00 | 66374.80 | 66400.00 | 66201.10 | 66216.90 |
| 2026-06-16T01:00:00+00:00 | 66216.80 | 66331.90 | 66206.60 | 66247.10 |
| 2026-06-16T01:15:00+00:00 | 66247.10 | 66345.90 | 66220.00 | 66335.00 |
| 2026-06-16T01:30:00+00:00 | 66335.00 | 66378.60 | 66313.00 | 66325.80 |
| 2026-06-16T01:45:00+00:00 | 66325.70 | 66388.80 | 66284.90 | 66309.90 |
| 2026-06-16T02:00:00+00:00 | 66309.90 | 66331.80 | 66014.20 | 66028.20 |

| previous-candle condition | ok | detail |
|---|---|---|
| compact range ZR <= q33 | ok | ZR 0.3169 vs q33 0.3754 |
| a prior move exists | ok | UP 0.1818, DN 0.6244 |
| close inside the range | ok | close 66309.90 in [66065.10, 66658.20] |


### S9-37683-up 2026-09-28T13:00:00+00:00 up level 83477.70 (presence 17 / recomputed 17, streak 0)

| check | result |
|---|---|
| trigger candle in the DB equals the FIRE's candle | ok |
| setup was PRESENT on the previous candle (all conditions) | ok |
| operative level recomputed independently equals the FIRE's level | ok |
| trigger candle closed beyond that level | ok |
| no earlier fire in the run (first valid candle) == streak_position 0 | ok |
| presence run length recomputed equals the FIRE's | ok |

| candle open | open | high | low | close |
|---|---:|---:|---:|---:|
| 2026-09-28T11:30:00+00:00 | 82992.00 | 83081.60 | 82953.10 | 83045.80 |
| 2026-09-28T11:45:00+00:00 | 83045.90 | 83060.20 | 82953.00 | 83054.50 |
| 2026-09-28T12:00:00+00:00 | 83054.50 | 83477.70 | 82979.90 | 83346.70 |
| 2026-09-28T12:15:00+00:00 | 83346.60 | 83437.50 | 83241.70 | 83331.10 |
| 2026-09-28T12:30:00+00:00 | 83331.10 | 83399.30 | 83232.60 | 83312.10 |
| 2026-09-28T12:45:00+00:00 | 83312.10 | 83609.40 | 83312.00 | 83546.50 |

| previous-candle condition | ok | detail |
|---|---|---|
| compact range ZR <= q33 | ok | ZR 0.3569 vs q33 0.3754 |
| a prior move exists | ok | UP 0.2436, DN 0.2692 |
| close inside the range | ok | close 83312.10 in [82551.60, 83477.70] |

