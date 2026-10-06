# Pre-registration — MIB Pattern Lab, Experiment 2: BTC/USDT 5M visual-pattern discovery

**Status: DRAFT v3 — all six open decisions are answered and amendments A1–A7 (approved by the user) are applied
(section 13); awaiting the user's final review. NOT FROZEN.** It becomes the frozen design only when `docs/PREREG_5M_DESIGN_LOCK.json` is written (section 11, step 3),
which happens **after** the user has read the final text. **No 5M outcome has been computed or looked at.** No 5M
discovery sample has been generated and no 5M AI discovery call has been made under this design.

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
signals. The prompts are linted so that they never name such concepts, and the discovered vocabulary is linted so that
it cannot prescribe a trade (section 6). The permanent real-fills rule (`docs/REAL_FILLS_POLICY.md`) applies to this
and every later experiment: nothing here is a trading backtest and no fill of any kind is simulated.

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
* **Causal fixed vertical span (frozen calculation).** One span (in %) is used for every chart. It is computed **only**
  from the **calibration prefix** = all candles with timestamp < `first candle + 28 days` (real data: first candle
  2025-09-15 19:05 UTC, prefix ends **2025-10-13 19:05 UTC**; every discovery window must start at or after that instant):
  1. *Windows used:* every gap-free run of 60 consecutive closed candles whose last candle lies inside the prefix
     (`valid_end_indices`, applied to the prefix data only).
  2. *Range of a window:* `range_pct = 100 × (max high over its 60 candles − min low over its 60 candles) / close_T`,
     where `close_T` is the close of its last candle.
  3. *Percentile:* `numpy.quantile(range_pct, 0.99)` with numpy's **default method (linear interpolation between order
     statistics)**, over all those windows.
  4. *Rounding:* `span = ceil(percentile / 0.05) × 0.05` (rounded to 10 decimals), i.e. rounded **up** to a multiple of
     0.05 percentage points. Dry-run on the real data: **span = 4.3%**.
  5. *Y-axis of every chart:* lower limit = `mid − span/2`, upper limit = `mid + span/2`, where
     `mid = (min low + max high) / 2` of **that window** in the normalised % units (both known at T). Every chart therefore
     covers exactly the same vertical extent; only its position follows its own window.
  The span uses **no information from after any discovery window's end**; every discovery window starts after the prefix.
  Windows wider than the span are **excluded and counted, never clipped** (section 12). No future high/low/volatility
  enters any normalisation. (The archived 1H experiment learned its span from the whole discovery period, which is not
  strictly causal; it is left as it was. 5M fixes this.)

## 4. Discovery period, hold-out and discovery sampling (deterministic, outcome-blind)
* Discovery windows: start after the calibration prefix, end before **2026-06-01 (UTC)**, and have 24 gap-free forward
  candles that also end before 2026-06-01 (existence of candles only; no price value is read for this).
  Hold-out (2026-06-01 onward) is physically removed from the data before sampling and is **not used at all** unless
  section 10 is triggered.
* **Why the discovery cutoff is 2026-06-01 (rationale fixed before any 5M outcome existed).** No 5M outcome has ever been
  computed. The date is the project's pre-existing 5m cutoff (`config.DISCOVERY_END`, set in the project's Stage 2 commit
  `3da4718`, before this experiment was designed) and was chosen from the **data coverage dates alone**: it reserves the
  last ~4 months of the 5M series for a possible one-shot hold-out (2026-06-01 → 2026-10-06 10:35 = about 36,700
  usable candles, i.e. about 610 non-overlapping 60-candle windows — enough for one hold-out evaluation) and leaves ~9
  months (2025-09-15 → 2026-05-31) for discovery. It is a calendar-month boundary. It was **not** derived from any outcome,
  price pattern or statistical analysis. *Disclosure:* earlier 5M work only produced charts, tags and window geometry,
  never forward returns — (a) the first-milestone visual-QA set of 20 evenly spaced charts spans the whole series,
  **including hold-out dates**, and was inspected only for chart cleanliness; (b) the 5M tagging pilots drew windows
  only from before the cutoff. No tag or description of any hold-out window exists.
* Candidate windows → split into **4 equal-count strata by window range** (a property of the chart itself) → each
  stratum contributes N/4 windows, **spread evenly over time**, never closer than 60 candles (**no overlaps**).
  Non-overlap plus even time spread is the de-duplication. `N_TARGET = 600` (same order of magnitude as the 1H
  discovery sample of 452). If fewer fit, N is whatever fits and is reported; shortfall is not back-filled.
* **Information used by the sampling (full disclosure).** The selection uses exactly: (i) each window's **own prices up to
  T** (its range, to place it in a stratum); (ii) whether the **24 candle timestamps after T exist, are contiguous and lie
  before the cutoff** (no price after T is read for this); (iii) the three **quartile cut-points of window range, computed
  over the whole discovery-period candidate set**, and the time order of the candidates. Element (iii) is **the one place
  where selection-stage hindsight exists**: a window's stratum label depends on the distribution of ranges of windows that
  end after it. It determines only *which* windows are chosen. It **never enters any chart image, any AI input (D1, D2,
  D3) or any outcome calculation**, and no forward return, forward high/low or any other price after T of any window is used
  anywhere in the sampling. A strictly causal alternative (cut-points taken from the calibration prefix only) was
  considered and rejected because, as volatility changes over the year, the strata would become badly unequal.
* **Exact deterministic selection procedure** (`src/exp5m/sampling.py`; no randomness, no seed):
  1. *Candidates:* gap-free 60-candle windows that start at/after the prefix end, end before the cutoff, have range ≤ the
     span, and have 24 contiguous candles after T before the cutoff. Sorted by end time.
  2. *Strata:* `pd.qcut(rank(range_pct, method="first"), 4)` → equal-count quartiles Q1_quiet, Q2, Q3, Q4_active (ties are
     broken by time order). Stratum quota = `N_TARGET // 4` = **150 each** (any remainder goes to the first strata).
  3. *Visiting order inside a stratum* (candidates in time order): first `quota` evenly spaced positions
     `round(linspace(0, n−1, quota))`, then an evenly spaced grid of `min(n, 4·quota)` positions, then every position in
     order; duplicates removed, first occurrence kept.
  4. *Acceptance:* a candidate is accepted unless its end time is **less than 60 candles (18,000 s)** from any window
     already accepted (in any stratum); strata are processed in the order Q1, Q2, Q3, Q4 (earlier strata take their time
     slots first); a stratum stops when it reaches its quota. Accepted windows therefore never overlap.
  5. *Output:* all accepted windows sorted by end time = the discovery sample (`windows5m.jsonl`).
  6. *D1 subset:* walking the time-sorted sample as i = 1, 2, 3, …, a window is in the description stage iff
     `(i − 1) mod 2 = 0`, i.e. the **1st, 3rd, 5th, … windows** (300 of 600); the flag is stored in `windows5m.jsonl`.
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
  passes validation (6–10 families, snake_case, unique, `none` reserved, ≤25-word definitions) **and the vocabulary lint**
  (section 6: no trade-decision / outcome / non-visible term in any name or definition). On failure the same call is repeated up to 3 times with the reasons
  (including the offending words) appended; every attempt is stored. If all fail, the experiment stops
  and is reported; nothing is fixed by hand.
* **D2 exact inputs.** Taken from the clean D1 rows (time-sorted): (a) every shape name is normalised (lower-case; each run
  of non-alphanumeric characters becomes one underscore; leading/trailing underscores stripped) and counted over all rows;
  the **80 most frequent** names (ties broken alphabetically) are shown as `name: count`; (b) **40 summaries** are drawn
  without replacement with `random.Random(12345).sample` from the time-sorted clean rows, each cut to 300 characters with
  line breaks removed, and shown in time order; (c) the number of described charts; (d) the bounds 6 and 10. A retry appends
  only the reasons the previous answer was rejected.
* **Model randomness and the reproducibility record.** **No `temperature` (or any other sampling parameter) is set
  explicitly in any call**; the model's API defaults apply. Model outputs are therefore **not reproducible by re-running**.
  The **stored raw model responses** — every D1 description, every D2 attempt, every D3 pass, each with the model name and
  prompt hashes — **are the reproducibility record**. Everything downstream (vocabulary file, stable tags, families,
  statistics) is deterministic given those stored responses. Re-running a step in order to obtain different outputs is not
  permitted (section 11).
* **Freeze the vocabulary** (`docs/5m/VOCABULARY_5M.json`, sha256 recorded) **before** step D3 and before any outcome code
  runs. No family is merged, split or renamed afterwards.
* **D3 – classification.** All sampled windows are classified against the frozen vocabulary (families + `none`): 1–3
  names each, **two passes**, the second listing the vocabulary in reversed order; a window's **stable tags** are the
  tags present in **both** passes. Invalid/unknown names are errors, never repaired. Same mechanics as the 1H
  experiment.
* The model sees only the image and the fixed prompt: no timestamp, filename, price level, forward data or outcome.
  The discovery code cannot import the outcome code (test-enforced).

## 6. Language lint (two different rules; both hash-locked in `prompts5m.py`)
The purpose of the lint is to stop visual discovery from turning into explicit trading instructions or outcome
interpretation. It is **not** meant to stop the model from naturally describing visual structure.
* **Prompt rule (unchanged from the original instruction).** The three prompts themselves must not name technical-analysis
  concepts (trend, breakout, support/resistance, indicators, volume, candlestick names, setups, buy/sell signals, ...),
  so that the model is not primed to look for them. Every template is checked against the strict list.
* **Vocabulary rule (user decision 6).** The model-written family names and definitions **may use natural structural words**
  (for example trend, breakout, reversal, impulse, consolidation, pullback, momentum, correction, candlestick-shape
  words). A name or definition is rejected **only** if it contains a word that
  (a) prescribes or implies a **trading decision, an outcome interpretation or a market-sentiment bias**: buy, sell, long,
  short, entry, exit, target, stop loss, take profit, profit/profitable, winning/winner, trade/trading, signal, setup,
  bullish, bearish, bull, bear, outcome, forward, future, predict(ion), forecast, favo(u)rable; or
  (b) refers to something that is **not visually present in a clean chart**: volume, indicator(s), RSI, MACD, ATR, EMA, SMA,
  Bollinger, liquidity, FVG, BOS, CHoCH, support, resistance (inferred levels are not drawn).
  Judgment calls: bullish/bearish stay rejected because they express sentiment rather than geometry; `long` and `short`
  are rejected as listed by the user, even though they could describe a wick or candle size (such a name is rejected
  and the consolidation call is repeated, see section 5). `sideways_range`, `drift_up`, `drift_down` are accepted.
* We never add pattern names or concepts ourselves; the lint only rejects, it never edits.

## 7. Families and the confirmatory set
* A family = one frozen vocabulary name. A window may belong to several (stable tags). Windows with no stable tag (or
  only `none`) belong to no family and stay in the non-family population.
* **Confirmatory (primary) families = every frozen family with at least 30 windows that have a complete 24-candle
  forward path** (counted from tags and candle existence only, before any outcome is computed, and recorded in the
  discovery lock). All other families are exploratory/descriptive. No family is dropped, merged or promoted after
  outcomes are seen.
* By construction (section 4, step 1) **every sampled window already has a complete 24-candle forward path**, so a family's
  count of windows with a complete forward path equals its count of stable tags.
* Number of confirmatory cells = (#confirmatory families) × 5 horizons; the maxT correction and the MDE use it.

## 8. Outcome measurement (after discovery is completely frozen; deterministic Python)
Same definition as the 1H experiment. Entry reference = **close of T** (last candle of the window). For horizons
**H = 1, 3, 6, 12, 24 five-minute candles**: forward close return `100·(close[T+H]/close[T]−1)`, future high and low
`max high / min low over T+1..T+H`, `MFE = 100·(fut_high/close[T]−1)`, `MAE = 100·(fut_low/close[T]−1)`, win rate
(`return > 0`). No TP/SL, fees, leverage, sizing, execution assumption or trading rule. A window is excluded (and
counted) if its 24 following candles do not all exist gap-free before the discovery cutoff.

**These are descriptive statistics, not trade fills** (permanent policy: `docs/REAL_FILLS_POLICY.md`). Forward return,
future high, future low, MFE and MAE are measurements of the historical series from the close of the last window candle.
The prices involved were **not shown to be executable**, and nothing here may be called a realized trade, a profit or an
executable price. No order, fill, spread, slippage or fee is modelled. Any later conversion into a trading rule requires a
separate execution specification, frozen before any trading backtest (policy section 8). The final report and
`summary.json` must contain the exact sentence given in policy section 11.

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

**What is frozen at each stage, and what (if anything) is permitted afterwards**

| Stage | Frozen at this stage | Permitted afterwards |
|---|---|---|
| **Design lock** (before any sample/AI call) | This document; `params.py`; `sampling.py`; `prompts5m.py` (templates + both lint lists); `coverage.py`; `io5m.py`; `discover5m.py`; the coverage report and database hash; all parameters; the 1H-archive hashes | **Only:** (a) re-sending API calls that failed or returned invalid output, with identical prompts (steps are resumable); (b) changing the `--budget-usd` cost cap. **Nothing else.** |
| **Sample generation** | `windows5m.jsonl`, the charts, `sample_meta.json` (incl. the limitation statement); the span and style hash | Nothing. (A rebuild must reproduce identical hashes; it is deterministic.) |
| **D1** (descriptions) | Stored raw descriptions | (a) re-send failed calls with identical prompts |
| **D2** (vocabulary) | `docs/5m/VOCABULARY_5M.json` is written **once** and is immutable; all D2 attempts are kept | Nothing manual. Only the automatic, recorded retries (max 3). No merge/split/rename/edit, ever |
| **D3** (classification) | Raw tags of both passes | (a) re-send failed/invalid calls with identical prompts; (b) cost cap |
| **Discovery lock** | Sample, vocabulary, tags, model/prompt hashes, N per family, the confirmatory set, exclusions | **Nothing** |
| **Outcome wrapper** | The 5M outcome code + its dependencies (own freeze file), built after the discovery lock and before it is run | Nothing |
| **Outcome analysis** | Report and `summary.json` | Nothing; an identical re-run only |
| **Hold-out** (only after a discovery PASS) | Everything above; hold-out windows by the same procedure | Nothing; evaluated exactly once |

**Never permitted after the relevant freeze:** editing prompts, vocabulary, family definitions, window rules, thresholds,
horizons or statistical code; merging, splitting, renaming, dropping or promoting a family; re-running D1–D3 to obtain a
"better" vocabulary or different tags; any change motivated by an outcome.

## 12. Limitations (stated up front; items marked REQUIRED must appear in the final report)
* **REQUIRED — population of inference.** The 4.3% causal-span constraint excludes approximately 1,762 candidate windows
  (2.66% of the candidate population). Therefore, conclusions from the 600-window discovery experiment apply only to the
  sampled population within the causal-span constraint and do not establish behavior for those excluded high-span
  windows. (The pipeline generates this sentence from the real funnel numbers into `sample_meta.json`
  (`limitation_statement`); the final report reproduces it verbatim, **and the machine-readable `summary.json` produced by
  the 5M outcome wrapper must carry the same text in a `limitation_statement` field** — the wrapper refuses to write the
  report or the summary without it.)
* **REQUIRED — what the outcome numbers are.** The final report and `summary.json` contain, verbatim: "Forward return,
  future high, future low, MFE and MAE are descriptive statistics of the historical price series, measured from the close of
  the last candle of each visual window. They are not trade fills, they were not shown to be executable prices, and they
  must not be read as realized trades." (`docs/REAL_FILLS_POLICY.md`, section 11.)
* About 13 months, a single market regime: a result here says nothing about other regimes.
* Power depends on the number of families that reach N ≥ 30 and on their sizes; with many confirmatory cells the
  maxT correction reduces power. INCONCLUSIVE / LOW POWER is a likely and acceptable outcome.
* Vocabulary names come from the model; their quality is not guaranteed (but they are frozen before any outcome).
* The `long`/`short` rejection (section 6) can force a re-run of the consolidation call for purely visual uses of those words.

## 13. Decisions recorded (all confirmed by the user)
1. **New vocabulary: CONFIRMED.** D1 → D2 independently induce the 5M vocabulary; the 1H vocabulary is not reused.
2. **Causal span: CONFIRMED.** The 28-day calibration prefix (2025-09-15 19:05 → 2025-10-13 19:05 UTC) sets the 4.3% span; it
   lies strictly before the discovery period; discovery windows start after it.
3. **Chronology: CONFIRMED.** Discovery data is before 2026-06-01. The hold-out may only be used if a discovery family first
   passes the pre-registered criteria.
4. **Discovery sample: CONFIRMED.** 600 windows, deterministic and stratified as specified, about $2 with the cost cap enforced.
5. **Confirmatory threshold: CONFIRMED.** Every discovered family with at least 30 windows is confirmatory; smaller families
   remain exploratory.
6. **Language lint: CHANGED.** `reversal`, `impulse`, `consolidation` (and the other structural words) are no longer forbidden;
   the vocabulary lint targets trade-prescribing, outcome-interpreting and non-visible terms only (section 6). The
   span-exclusion limitation is preserved (section 12, REQUIRED). Everything else stays as designed.
7. **Amendments A1–A7: APPROVED and applied** as documentation/clarity changes only (no methodology change): A1 sampling
   information disclosure (quartile cut-points as the one selection-stage hindsight element); A2 exact span calculation,
   interpolation, range formula and y-axis centring; A3 cutoff rationale; A4 explicit deterministic selection and D1
   subset; A5 D2 inputs, unset temperature and the raw responses as reproducibility record; A6 freeze/stage table;
   A7 limitation statement also in `summary.json`.
8. **Real-fills policy: ADDED** as permanent project documentation (`docs/REAL_FILLS_POLICY.md`); this experiment's outcome
   measures are descriptive, not trade fills (section 8, section 12 REQUIRED sentence).

## 14. Audit trail (produced by the pipeline; all hash-recorded)
Database file hash and coverage report; the limitation statement; exact window construction and parameters (`params.py`); chart style hash and the
calibration span; the sampling funnel and exclusions; `windows5m.jsonl` hash and number of windows; model name, prompt
template hashes, D1 descriptions, D2 attempts, frozen vocabulary and its hash; D3 tags (two passes); seeds (12345,
20240601; sampling is deterministic); outcome horizons; the statistical tests and B values; analysis-code freeze hash;
final verdicts in `summary.json` and `report.md`.
