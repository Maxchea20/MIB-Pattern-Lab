# S1 v2 result (one scan; detectors frozen `a0c84c8b…`; v1 `5199bd9a…` untouched). Descriptive; no fill, no trade; nothing patched.

**Integrity.** Replay == batch: True. Imported detectors S2-S4, S6-S8 == Experiment 3 raw triggers: True. S2-S9 fires identical to v1: True (636/191/101/55/284/703/668/574 as before).

**Fires.** S1 v1 305 (213 in-sample, 92 unseen); v2 1205 (833, 372). Same candle 144, v1-only 161, v2-only 1061, Jaccard 0.105. v2 streak positions 0/1/2/3/4: 874/250/64/13/3; median presence 2 candles. 61-125 fires per month.

**The 12 cited charts at T..T-6 (consistency check, not a recall target; v1 recognised 0).** v2 fired within T..T-6 on S0013, S0159, S0201, S0347 (S0201's fire was at T-2, i.e. the break happened before the chart ended); present but no fire on S0472.
Not recognised: S0036, S0120, S0500, S0535 (spike/pullback then pause; the A2 condition fails at T), S0181 (A1), S0163, S0176 (reversal candles, correctly not S1).
Open observation, not diagnosed and not patched: the spike-then-pause family (S0120, S0036, S0535, S0500) was **not** fixed by corrections 1-3; at T both `ZR` and `RET` fail A2. `RET` still uses the last confirmed swing low as the leg's base (kept as approved); whether that is why is unchecked.

**Ten unseen-period fires (evenly spaced), read against S1's definition (my reading).**

| # | fire | structure | reading |
|---|---|---|---|
| 1 | 2026-06-04 14:15 | 7-candle bounce inside a downtrend, break of the bounce's minor high, presence 1 candle | **bad / weak**: no pause, not a leg-then-consolidation |
| 2 | 2026-06-14 01:15 | rise, spike at -14, ~13 tight candles under it, close above the pause high | good |
| 3 | 2026-06-27 14:15 | gradual rise, ~7-candle pause, close above its high | good |
| 4 | 2026-07-11 20:45 | range-bound, small pause under the range top, a tiny close above it, failed at once | borderline (range break, weak leg) |
| 5 | 2026-07-25 13:45 | rebound into prior resistance, small pause, break, continued up | plausible / good |
| 6 | 2026-08-06 05:15 | pullback then ~10 tight candles under 64,700, break | good |
| 7 | 2026-08-17 23:15 | rise, 20-candle pause under 64,500, close above the pause high (below the leg's earlier peak) | plausible |
| 8 | 2026-08-26 23:30 | rebound after a drop, small pause, break of a minor high, presence 1 candle | borderline (rebound) |
| 9 | 2026-09-13 21:30 | long flat range, V-shaped dip and recovery, close just above the range top, then a 700 drop | borderline |
| 10 | 2026-09-27 12:15 | steady rise, pause, close above the pause high, failed quickly | good |

4 good, 2 plausible, 3 borderline, 1 weak. No reversal-candle or pure-momentum recognitions among the ten. Nothing was changed because of this.

**Forward descriptive numbers (direction-signed % from the next candle open; the unconditional baseline is every candle measured the same way; NOT fills; no significance test; fires overlap so the s.e. is optimistic).**

| | n | h1 mean (base) | h6 mean (base) | h24 mean (base) | h6 share>0 | invalidated within 24 | median candles to invalidation |
|---|---:|---|---|---|---|---:|---:|
| v1 in-sample | 213 | -0.006 (-0.001) | -0.035 (-0.007) | +0.207 (-0.030) s.e. 0.077 | 0.44 | 164/213 | 4 |
| v1 unseen | 92 | +0.011 (+0.001) | +0.085 (+0.008) | -0.058 (+0.031) s.e. 0.101 | 0.39 | 76/92 | 3 |
| v2 in-sample | 833 | -0.011 (-0.001) | -0.024 (-0.007) | +0.027 (-0.030) s.e. 0.043 | 0.43 | 663/833 | 3 |
| v2 unseen | 372 | +0.003 (+0.001) | -0.032 (+0.008) | -0.003 (+0.031) s.e. 0.054 | 0.38 | 315/372 | 3 |

Reading: no sign of directional follow-through in either version or period; about 80-85 % of fires are invalidated (a close back inside) within 24 candles, typically after 3. v1's one nominally large number (in-sample h24 +0.207) did not recur in v1's unseen period or in v2.
This does not show that no trading edge exists anywhere; it says this reading of S1 shows none descriptively on this data.

**Answer for S1.** The translation was partly too strict (v2 recognises part of the structure v1 missed, and v2 produces visibly S1-like fires), and about half of the cited charts were never S1 (the AI was loose). Making the translation more faithful did not change the descriptive picture.
