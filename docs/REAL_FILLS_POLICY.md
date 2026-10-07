# REAL FILLS ONLY — permanent research and engineering policy of MIB-Pattern-Lab

**Status: PERMANENT. Applies to every stage of this project, present and future.**
Recorded by the project owner. It may be made stricter; it may never be relaxed to obtain a result.

> **A profitable backtest with impossible or unproven fills is a FAILED BACKTEST.**
> A lower-profit backtest with causally valid fills is infinitely more valuable.
> Do not optimise for attractive results. Optimise for historical truth.

The research must NEVER manufacture, assume, interpolate or infer a fill that did not actually occur in the
historical market data. This experiment series is designed so that this cannot happen.

## 0. Where the project stands relative to this policy
* **Experiments 1 (1H) and 2 (5M) are NOT trading backtests.** Their outcome measurements — forward close return,
  future high, future low, MFE, MAE (and win rate of the forward return) — are **descriptive statistical measurements of
  the historical price series**, taken from the close of the last candle of a visual window. They are **not trade fills**.
  The prices used (for example a future high or low) were **not shown to be executable**. MFE/MAE must never be called a
  "realized trade", a "profit" or an "executable price", and no report may imply that they were.
* **Experiment 3 (Setup Discovery) is also not a trading backtest.** Its outcome measurements are descriptive statistics
  measured from the **analytical reference price** (see section 11). The analytical reference price is **not** an execution
  price: **analytical reference price ≠ execution price**.
* No order, fill, position, stop, take-profit, spread, slippage or fee exists anywhere in the current code or reports.
* **No trading backtest may be implemented** until the separate execution specification in section 8 exists and is frozen.
  A repository test (`tests/test_policy.py`) makes the accidental creation of backtest/execution/fill code fail loudly.

## 1. A fill must be causally executable
A trade may be considered filled only if the historical data **proves** that the order could actually have been
executed. Do NOT assume:
* that touching a price means a guaranteed fill;
* that an intrabar price was available at a particular time when the OHLC data cannot establish it;
* that the best possible price inside a candle was obtainable;
* that a limit order filled merely because the candle's high/low crossed it;
* that a stop order filled at the exact requested price when the market could have gapped or slipped through it;
* that an order can execute at a candle close if the strategy only knows that close after the candle has closed;
* that multiple orders can all fill at the same historical price simply because the candle range permits it.

## 2. Never use future information to establish a fill
Only information known at the exact moment the hypothetical order was submitted may be used. For a signal at time T:
* information from candles before T is allowed;
* information from the currently closed candle is allowed only after that candle has actually closed;
* future candles cannot influence whether the order was submitted, the fill price, or whether the trade existed.

## 3. OHLC ambiguity must be handled conservatively
If OHLC data cannot determine the chronological order of intrabar events, **do not invent an order**. If the same
candle contains both a potential entry price and a potential stop price and OHLC does not say which came first, the
backtester must not automatically choose the favourable sequence. Mark the event **AMBIGUOUS** and either
1. exclude it under a rule defined **before** the backtest, or
2. apply a conservative deterministic assumption defined **before** the backtest.
Never choose whichever sequence produces the better result.

## 4. No hindsight fills
Forbidden: "The candle eventually reached our entry price, therefore we got filled." That is not sufficient. The
engine must establish that the order was **active before** the price interaction and that the interaction occurred in an
**executable chronological sequence**. Likewise "the candle eventually hit TP, therefore TP filled" is not valid
unless the trade itself could first have been established.

## 5. No best-price selection
Never select the candle high for a long exit, the candle low for a short exit, an ideal intrabar entry, an ideal TP or an
ideal SL because it gives a better result. Use only prices that are causally available and executable under the
predefined execution model.

## 6. Real market-data hierarchy
1. **Highest priority:** actual recorded exchange execution/fill data.
2. If unavailable: **deterministic historical execution simulation using sufficiently granular market data.**
3. If the available data cannot establish whether an execution occurred: the trade/event is marked **UNKNOWN** or
   **AMBIGUOUS** — never treated as a successful fill. Uncertainty is never silently converted into a fill.

## 7. The experiments before any trading conversion
See section 0. The outcome tables of Experiments 1 and 2 stay descriptive. Every final report and every
machine-readable summary of those experiments must carry the required sentence in section 11 below.

## 8. A separate execution specification, frozen before any trading backtest
If a discovered pattern ever passes discovery **and** hold-out and we want to convert it into a trading strategy,
**STOP before implementing the backtest.** First write a separate, explicit execution specification covering at least:
signal timestamp; order submission timestamp; order type; order activation; market/limit/stop behaviour; fill
conditions; intrabar sequencing; spread; slippage; fees; partial fills; gaps; ambiguous candles; position state;
cancellation; exchange-specific execution rules. **That specification must itself be frozen (hashed and committed)
BEFORE the trading backtest is run.**

## 9. No optimisation against execution assumptions
Do not test several execution assumptions and keep the one that gives the best result. If several execution models are
scientifically necessary, they must be pre-registered and **reported separately**, including the unfavourable ones.

## 10. Audit requirement
Every simulated trade must be traceable to the underlying market data. For every fill the system must be able to answer:
* What signal created the order?
* At what exact timestamp was the order active?
* What market data proves the fill?
* What price was used?
* What candle/tick established it?
* Why was the fill chronologically possible?
* What assumptions were applied?
**If the system cannot answer these questions, the fill is not valid.**

## 11. Required wording for current and future reports
Every final report and every `summary.json` of the 5M (and 1H) discovery experiments must contain this sentence
verbatim:

> Forward return, future high, future low, MFE and MAE are descriptive statistics of the historical price series,
> measured from the close of the last candle of each visual window. They are not trade fills, they were not shown to be
> executable prices, and they must not be read as realized trades.

**Experiment 3 (Setup Discovery, `docs/PREREGISTRATION_SETUPS.md`).** Every final report and every `summary.json` of that
experiment must instead contain this sentence verbatim:

> Forward return, future high, future low, MFE and MAE are descriptive statistics of the historical price series,
> measured from the analytical reference price (the open of the candle after the trigger candle). They are not trade
> fills, they were not shown to be executable prices, and they must not be read as realized trades.

The permanent distinction is: **analytical reference price ≠ execution price.** The open of the candle after a trigger is
a measurement reference chosen because it is the earliest price that could in principle follow a trigger that became known
at a candle close; it was not shown to be obtainable, and no report may call it an entry, a fill or an executable price.
A trade conversion still requires the separate frozen execution specification of section 8.

## 12. Pre-implementation checklist for any future trading backtest
- [ ] A frozen execution specification exists (section 8) and its hash is committed.
- [ ] Every fill rule uses only information available at order submission (section 2).
- [ ] Ambiguous candles are handled by a rule fixed before the run (section 3); no best-sequence selection.
- [ ] Data granularity is stated and is sufficient; otherwise events are UNKNOWN/AMBIGUOUS (section 6).
- [ ] Execution models are pre-registered and all are reported (section 9).
- [ ] Every fill is traceable and answers the seven audit questions (section 10).
- [ ] The accidental-implementation guard in `tests/test_policy.py` has been updated deliberately and reviewed.
