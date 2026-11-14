# Experiment 5 result: trend + RSI as written. One run on the untouched data (2023-01 to 2025-08, Binance spot BTCUSDT 15m; rules frozen `0f4afa6d…`)

Event study, not a backtest: hypothetical results from the next 15m open, in units of the risk distance (R). No fill was assumed. Costs: 0.04 % per order plus slippage.

| | signals | gross R (mean) | net R at 0.01 % slippage | share positive |
|---|---:|---:|---:|---:|
| all with-trend | 478 (291 long, 187 short) | **+0.007** | **−0.119** | 57 % |
| first half (to 2024-04) | 229 | +0.044 | −0.081 | 58 % |
| second half | 249 | −0.027 | −0.155 | 57 % |
| 2023 / 2024 / 2025 | 169 / 180 / 129 | +0.002 / +0.064 / −0.067 | −0.133 / −0.039 / −0.214 | |
| counter-trend diagnostic (the old bounce long) | 660 | +0.003 | −0.105 | 58 % |

Exits: 285 by RSI, 181 by the risk level, 12 by the time stop. Net result at 0 % slippage: −0.094 R; at 0.03 %: −0.170 R. Excluded signals: 0.

**Stop rule (charter section 6, applied mechanically):** 1 mean net R above zero: **NO**. 2 at least 100 signals: yes. 3 positive in both halves: **NO**. 4 excluded share at most 20 %: yes. **Not met: the method as written is dropped.**

Reading: before costs the written rule has no measurable edge (+0.007 R is zero); costs turn it into a steady loss of about 0.1 R per signal. Winners were taken early by the RSI exit (mean favourable move 0.61 R) while the risk level took 1 R. This tests the written rule only, not the trader's discretion, and only on Binance spot candles with MEXC-style costs.
Next (as agreed in the charter): stop chart/RSI methods and look at funding, open interest and volatility regimes.
