# Experiment 5 — Trend + RSI, as the trader actually trades it. CHARTER (approved by the trader: "Go ahead"). Rules are implemented in `src/trendrsi/` and frozen by `docs/trend_rsi/FREEZE.json` before the untouched data is analysed.

**Purpose.** Write the trader's discretionary method down as rules, test the *written* version once on data nobody has looked at, and stop if it does not survive costs.
It cannot test the trader's "gut"; it tests only what can be written down. A negative result is a result.

## 1. What the trader does (from their own words and their MEXC export, Oct 15 – Nov 13 2026; 57 closed trades)
* Reads trend and RSI on 1H, 4H, 1D; enters on 15m (5m/1m possible) after a pullback and a change of character (CHoCH) in the direction of the trend.
* Counter-trend bounce longs inside a bear trend were tried and "failed miserably" (export: 38 such longs, net −49.40; all longs −112.28; shorts +29.49 with the trend).
* Exits "when I feel it will reverse", i.e. RSI almost or already oversold/overbought. In the export the exit 15m RSI was a median 45 for longs; only 19 % exited at 65 or higher. No numbers in mind for "oversold"/"overbought".

## 2. Proposed written rules (for approval; every number is a convention fixed in advance, none is tuned)

| Piece | Proposal |
|---|---|
| RSI | Wilder, length 14, on completed candles only |
| Oversold / overbought | the textbook 30 / 70; "almost" = within 5 points: **35 / 65** |
| Bias (trend) | **Bear:** 4H close < 4H EMA50 *and* EMA50 falling over 6 bars, *and* 1D close < 1D EMA20 with EMA20 falling over 3 days. **Bull:** the mirror. Otherwise: no trade. (My labelling of "I see the trend"; the trader may replace it.) |
| With-trend SHORT (bear bias) | 15m RSI reaches ≥ 65 (the bounce is "almost overbought") → then a 15m CHoCH down: a close below the most recent confirmed 15m swing low (confirmed swing, K = 3, known only 3 candles later). Signal = that close; the reference price is the next 15m open. |
| With-trend LONG (bull bias) | the mirror: 15m RSI ≤ 35, then a close above the most recent confirmed swing high |
| Stop | beyond the extreme of the move that triggered the setup (shorts: the highest high since the RSI ≥ 65 reading; longs: the lowest low since the RSI ≤ 35 reading). Required: no trade without one |
| Exit | 15m RSI ≤ 35 for a short (≥ 65 for a long), the stop, or a time stop at 24 h (96 candles), whichever is first |
| Counter-trend bounce (the trader's old long in a bear trend) | **measured as a diagnostic only, not part of the traded rule** |
| Entry timeframe | 15m. 1m candles are used only as evidence for which level was reached first, never to pick entries |

Free choices: RSI length, the two RSI levels, EMA lengths 50 / 20 and their slope windows, K = 3, the 24-hour time stop, the stop placement. All fixed before the test.

## 3. Costs (from the export; both legs)
* Taker fee 0.02 % per order until Oct 30 and **0.04 % per order from Nov 3** (round trip 0.08 %). The rule is tested at 0.04 %.
* Slippage on market orders cannot be seen in the export: sensitivity at 0 %, 0.01 %, 0.03 % per order.
* Funding on perpetuals is not in the export and is not yet in the data: reported separately once sourced.

## 4. Evidence rules (REAL FILLS ONLY)
* Stage 1 is an event study, not a backtest: for every signal, measure from the analytical reference price (next 15m open) where the stop and the RSI exit would have been reached. It is a description, not a trade.
* When 15m candles cannot say which level came first, the 1m candles decide. If they cannot either, the signal is AMBIGUOUS: excluded and counted, never resolved in the favorable direction.
* Only if Stage 1 is positive after costs: a frozen execution spec with fill evidence, then paper trading, then (only then) small real size.

## 5. Data
* **Untouched test:** Binance BTCUSDT spot, 2023-01 to 2025-08 (32 months), 1m to 1d, downloaded and checksum-verified. Nobody has analysed it. It is run **once**, after the rules are frozen.
* **Development look (no tuning):** 2025-09 to 2026-11, used only to confirm the code does what the rules say and to compare with the trader's real trades.
* Venue note: signals and candles are Binance spot; the costs are MEXC perpetual. That mismatch is stated in every result.

## 6. Stop rule, stated in advance
The idea is dropped, and we move to funding, open interest and volatility regimes, if on the untouched period any of these holds (conservative intrabar resolution, 0.04 % fee, 0.01 % slippage per order):
1. the average result per signal, in units of the stop distance, is not above zero;
2. there are fewer than 100 signals;
3. the average is not above zero in **both** halves of the period (2023-01 to 2024-04 and 2024-05 to 2025-08);
4. more than 20 % of signals are AMBIGUOUS.

## 7. What I need approved
The rules in §2 (or your replacements), the costs in §3, the data split in §5 and the stop rule in §6.
