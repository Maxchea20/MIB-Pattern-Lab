# Pre-registration — MIB Pattern Lab, Experiment 2: BTC/USDT 5M visual-pattern discovery

**Status: DRAFT v1 — NOT FROZEN.** It becomes the frozen design when `docs/PREREG_5M_DESIGN_LOCK.json` is written
(section 14), which happens after the open decisions in section 13 are answered and the data coverage has been
re-verified. **No 5M outcome has been computed or looked at.** No 5M discovery sample has been generated and no
5M AI discovery call has been made under this design.

## 0. Relationship to the archived 1H experiment
* The 1H experiment is **archived and untouched**: `docs/PREREGISTRATION.md`, `docs/PREREG_LOCK.json`,
  `docs/OUTCOME_CODE_FREEZE.json`, `src/outcomes/*` and the other files in its freeze list. A test and the design lock
  verify that all of them still match their own hashes. 1H conclusion (recorded by the user): the AI discovered
  recurring visual families, but the 1H experiment did not establish a robust predictive edge from them
  (all three primary families INCONCLUSIVE / LOW POWER); no 1H hold-out is run.
* All 5M code lives in `src/exp5m/`; nothing is added to `src/outcomes/`. 5M **imports** the archived statistical
  functions unchanged; it does not copy-and-edit them, so the statistical methodology is identical by construction.
* Nothing from the 1H outcome results is used to tune 5M. The 5M design below was fixed from the project's
  philosophy and from design (not outcome) considerations only.

## 1. Hypothesis (unchanged) and research constraints
Can AI discover recurring visual patterns in clean historical price charts that are followed by unusually favourable
price movement? This is pure research: no conventional technical-analysis strategy, no entry/exit/FIRE/Hunt/S1/S2/
execution/live-trading logic, no TP/SL, fees, leverage or sizing. The models are never told to look for trend,
breakout, BOS, CHoCH, support/resistance, FVG, liquidity, indicators, volume, candlestick names, setups or buy/sell
signals; prompts and the discovered vocabulary are language-linted for these (section 6).

## 2. Data (verified by `python -m src.exp5m.coverage` on the real database)
Source: `market_Data_Clean.db`, table `candles`, `symbol = BTC_USDT`, `timeframe = 5m`. Result of the verification run
(its full JSON is `docs/5m/COVERAGE_REPORT.json`, hash-locked in the design lock):
* 111,068 rows, 111,068 unique timestamps, **0 duplicates**; earliest **2025-09-15 19:05 UTC**, latest
  **2026-10-06 10:40 UTC**; expected on the 5-minute grid 111,068 → **0 missing candles, 0 gaps, 0 off-grid timestamps,
  0 invalid OHLC rows**.
* Timestamps are stored as epoch **seconds** and interpreted as **UTC**; the timestamp is the candle's **open** time
  (verified on 9,255 overlapping 1h candles: `1h.open == 5m.open` at the same timestamp 100.0%, at -55m 0.0%).
* The loader drops the last stored candle (it may have been written mid-candle) → **111,067 usable closed candles**;
  it keeps only closed, valid, de-duplicated candles.
* Coverage is **~13 months, one market regime** (limitation, section 12).

## 3. Visual windows, charts and causal normalisation
* Window = **60 consecutive closed 5M candles** (~5 hours) ending at T; the last candle is T; no candle after T is ever
  in the chart; windows must be gap-free (enforced by `validate_window`).
* Chart (deterministic PNG, fixed style): candles, a price axis and a time axis only. No indicators, moving averages,
  RSI, MACD, ATR, volume, trendlines, support/resistance, labels, pattern names, markers or future candles.
* **Price axis:** `100 * (price / close_T - 1)`, i.e. % relative to the close of the last candle (known at T).
  No absolute BTC price appears. **Time axis:** relative offsets `T-50 … T` (no dates).
* **Causal fixed vertical span.** One span (in %) is used for every chart: the 99th percentile of window ranges
  (`max high − min low`, as % of the close at T) over windows lying entirely inside the **calibration prefix** — the first
  28 days of data — rounded up to a multiple of 0.05%. (Dry-run on the real data: calibration prefix ends 2025-10-13 19:05 UTC; span = **4.3%**.) The span therefore uses **no information from after any
  discovery window's end**; every discovery window starts after the prefix. Windows wider than the span are
  **excluded and counted, never clipped**. No future high/low/volatility enters any normalisation.
  (The archived 1H experiment learned its span from the whole discovery period, which is not strictly causal; it is
  left as it was. 5M fixes this.)

## 4. Discovery period, hold-out and discovery sampling (deterministic, outcome-blind)
* Discovery windows: start after the calibration prefix, end before **2026-06-01 (UTC)**, and have 24 gap-free forward
  candles that also end before 2026-06-01 (existence of candles only; no price value is read for this).
  Hold-out (2026-06-01 onward) is physically removed from the data before sampling and is **not used at all** unless
  section 10 is triggered.
* Candidate windows → split into **4 equal-count strata by window range** (a property of the chart itself) → each
  stratum contributes N/4 windows, **spread evenly over time**, never closer than 60 candles (**no overlaps**).
  Non-overlap plus even time spread is the de-duplication. `N_TARGET = 600` (same order of magnitude as the 1H
  discovery sample of 452). If fewer fit, N is whatever fits and is reported; shortfall is not back-filled.
* Dry-run on the real data (deterministic, so the build reproduces it): 74,363 closed candles before the cutoff → 74,304
  gap-free windows → 66,240 start after the calibration prefix → **1,762 (2.66%) wider than the 4.3% span, excluded**
  → 24 without a complete forward path → **64,454 candidates** → **600 selected (150 per stratum)**, first window end
  2025-10-14 00:00, last 2026-05-31 21:55 (UTC). About 1,100 non-overlapping windows fit in total, so N=600 is not forced.
  The funnel is written to `sample_meta.json`. The selected list is `windows5m.jsonl` (sha256 recorded in the discovery lock).
  Code: `src/exp5m/sampling.py`. Seeds: none needed (the procedure is deterministic).

## 5. AI discovery — outcome-blind, three steps (model `gpt-5.4-mini`; prompts in `src/exp5m/prompts5m.py`)
* **D1 – free description.** Every second window of the time-sorted sample (~300) is sent as an image with prompt D1:
  plain geometric description plus up to five self-chosen snake_case *shape names*. One pass.
* **D2 – vocabulary consolidation (one call).** The model receives the D1 shape names with counts and a seeded sample
  (seed 12345, 40) of D1 summaries, and groups the **recurring** shapes into **6–10 visually distinct families**,
  writing each family's name and one-sentence visual definition (≤25 words). We do not write or rename any family.
  No forbidden-word list is shown to the model up front (that would itself prime it). The output is accepted only if it
  passes validation (6–10 families, snake_case, unique, `none` reserved, ≤25-word definitions) **and the language lint**
  (no forbidden word in any name or definition). On failure the same call is repeated up to 3 times with the reasons
  (including the offending words) appended; every attempt is stored. If all fail, the experiment stops
  and is reported; nothing is fixed by hand.
* **Freeze the vocabulary** (`docs/5m/VOCABULARY_5M.json`, sha256 recorded) **before** step D3 and before any outcome code
  runs. No family is merged, split or renamed afterwards.
* **D3 – classification.** All sampled windows are classified against the frozen vocabulary (families + `none`): 1–3
  names each, **two passes**, the second listing the vocabulary in reversed order; a window's **stable tags** are the
  tags present in **both** passes. Invalid/unknown names are errors, never repaired. Same mechanics as the 1H
  experiment.
* The model sees only the image and the fixed prompt: no timestamp, filename, price level, forward data or outcome.
  The discovery code cannot import the outcome code (test-enforced).

## 6. Language lint (applies to all prompts and to the discovered vocabulary)
Forbidden words include: trend, breakout/breakdown, BOS, CHoCH, support, resistance, FVG, liquidity, sweep, indicator(s),
volume, RSI, MACD, ATR, EMA/SMA, Bollinger, named candlestick patterns (doji, hammer, engulfing, harami, marubozu),
setup, signal, buy, sell, long, short, bullish, bearish, momentum, pullback, retracement, reversal, continuation,
consolidation, accumulation, distribution, impulse, correction, plus outcome words (profit, loss, outcome, forward,
future, predict, forecast, favourable, trade, entry, exit). Names such as `sideways_range`, `drift_up`, `drift_down`
are allowed because they describe appearance only. The full list is in `prompts5m.py` and is hash-locked.

## 7. Families and the confirmatory set
* A family = one frozen vocabulary name. A window may belong to several (stable tags). Windows with no stable tag (or
  only `none`) belong to no family and stay in the non-family population.
* **Confirmatory (primary) families = every frozen family with at least 30 windows that have a complete 24-candle
  forward path** (counted from tags and candle existence only, before any outcome is computed, and recorded in the
  discovery lock). All other families are exploratory/descriptive. No family is dropped, merged or promoted after
  outcomes are seen.
* Number of confirmatory cells = (#confirmatory families) × 5 horizons; the maxT correction and the MDE use it.

## 8. Outcome measurement (after discovery is completely frozen; deterministic Python)
Same definition as the 1H experiment. Entry reference = **close of T** (last candle of the window). For horizons
**H = 1, 3, 6, 12, 24 five-minute candles**: forward close return `100·(close[T+H]/close[T]−1)`, future high and low
`max high / min low over T+1..T+H`, `MFE = 100·(fut_high/close[T]−1)`, `MAE = 100·(fut_low/close[T]−1)`, win rate
(`return > 0`). No TP/SL, fees, leverage, sizing, execution assumption or trading rule. A window is excluded (and
counted) if its 24 following candles do not all exist gap-free before the discovery cutoff.

## 9. Statistical methodology (identical to the archived 1H experiment; decided before any 5M outcome)
Implemented by calling the archived, hash-frozen functions unchanged (`src/outcomes/analyze.analyze` /
`categorize`, `stats`, `forward`). No threshold is loosened or tightened.
* Per confirmatory family and horizon: N, mean, median, win %, MFE, MAE, mean difference vs the non-family population,
  Cohen's d, 95% bootstrap CI (10,000 resamples, seed 20240601), Welch p, permutation p.
* **Permutation test:** 10,000 shuffles (seed 12345) of the outcome rows (all horizons, MFE and MAE jointly) against the
  family-membership matrix; Welch-t statistic per cell; observed vs null percentiles.
* **Family-wise correction:** Westfall–Young **maxT** across all confirmatory cells.
* **Control regression** (HC3): `ret_H ~ net_pct + range_pct + eff + family_dummy` (window-only features).
* **Decision rule (per confirmatory family, N ≥ 30), all three at one horizon:** maxT-adjusted p < 0.05; the 95%
  bootstrap CI excludes 0; the control regression's family dummy has the same sign as the effect and p < 0.05.
  - **PASS:** all criteria hold at some horizon (frozen hold-out horizon = smallest adjusted p; ties → shorter).
  - **DOES NOT PASS:** not PASS, N ≥ 30, and at every horizon the 95% CI lies within ±MDE (effects at least that large
    are not supported). It never means that no edge exists.
  - **INCONCLUSIVE / LOW POWER:** everything else. An underpowered negative result is never described as proof of no edge.
* Reading note: the non-family population contains the other families, so one real effect can appear mirrored in another.
* MFE/MAE comparisons are secondary and unadjusted. Exploratory families are descriptive, with unadjusted p only.

## 10. Hold-out (conditional; not run unless there is a discovery PASS)
The hold-out (2026-06-01 onward, ~4 months) is run **only if** at least one confirmatory family achieves PASS in discovery.
Then, with everything frozen (vocabulary, family definitions, windows rule, analysis code), hold-out windows lying entirely
inside the hold-out and using the **same calibration span** are sampled by the same procedure, tagged with the frozen
setup, and evaluated **exactly once** (lock file). All frozen families are reported; only discovery-PASS families get a
PASS / DOES NOT PASS / INCONCLUSIVE verdict (same-sign, one-sided p < 0.05/(#discovery-PASS families), regression agrees,
effect ≥ 50% of discovery). If nothing passes in discovery, **no hold-out is manufactured**.

## 11. Fixed order of work and freezes
1. Verify coverage (done: see section 2) → commit `docs/5m/COVERAGE_REPORT.json`.
2. Answer the open decisions (section 13); finalise this document.
3. **Design lock** (`python -m src.exp5m.lock5m --write`): hashes of this document, `params.py`, `sampling.py`,
   `prompts5m.py`, `coverage.py`, `io5m.py`, `discover5m.py` (the whole discovery pipeline), the coverage report, all
   parameters, the prompt templates, and proof that the 1H archive is intact. Every later step refuses to run if any
   of it changed.
4. Generate the discovery sample: `sampling --build --confirm-design-sha <12>` → `windows5m.jsonl`, charts, `sample_meta.json`.
5. `discover5m d1` (descriptions) → `discover5m d2` (vocabulary; **frozen**, `docs/5m/VOCABULARY_5M.json`) →
   `discover5m d3` (two-pass classification). All cost-capped and resumable.
6. **Discovery lock** (`lock5m --stage discovery --write` → `docs/PREREG_5M_DISCOVERY_LOCK.json`): sample, vocabulary,
   tags, model/prompt hashes, N per family, the **confirmatory set** (families with N ≥ 30) and exclusions. Tag counts only.
7. Build and freeze the 5M outcome wrapper (its own freeze file); run the outcome analysis **once**; report.
8. Interpretation only after step 7. Hold-out only under section 10.
After a freeze, no change to prompts, vocabulary, families, window rules, thresholds, horizons or code is allowed.

## 12. Limitations (stated up front)
* About 13 months, a single market regime: a result here says nothing about other regimes.
* Power depends on the number of families that reach N ≥ 30 and on their sizes; with many confirmatory cells the
  maxT correction reduces power. INCONCLUSIVE / LOW POWER is a likely and acceptable outcome.
* Excluding windows wider than the span removes the most extreme windows: **2.66% of post-calibration windows (1,762) are
  wider than 4.3% and can never be sampled**, so nothing here speaks about those periods.
* Vocabulary names come from the model; their quality is not guaranteed (but they are frozen before any outcome).

## 13. OPEN DECISIONS (to confirm before the design lock)
1. **Vocabulary source:** induce a new vocabulary via D1→D2 (written here), instead of reusing the 1H `vocab-v1`
   (which contains breakout/reversal-style names).
2. **Causal span via a 28-day calibration prefix** (the first four weeks are not used for discovery windows).
3. **Split:** discovery before 2026-06-01; hold-out only if a PASS occurs.
4. **Size and cost:** N = 600 windows; D1 on ~300; D3 = 600 × 2 passes. Estimated API cost about $2 (to be confirmed
   against the actual account balance).
5. **Confirmatory rule:** every family with ≥ 30 forward-valid windows is confirmatory (cap 6–10 families).
6. **Language lint list** (section 6), including a few words beyond the user's list (reversal, impulse, consolidation, …).

## 14. Audit trail (produced by the pipeline; all hash-recorded)
Database file hash and coverage report; exact window construction and parameters (`params.py`); chart style hash and the
calibration span; the sampling funnel and exclusions; `windows5m.jsonl` hash and number of windows; model name, prompt
template hashes, D1 descriptions, D2 attempts, frozen vocabulary and its hash; D3 tags (two passes); seeds (12345,
20240601; sampling is deterministic); outcome horizons; the statistical tests and B values; analysis-code freeze hash;
final verdicts in `summary.json` and `report.md`.
