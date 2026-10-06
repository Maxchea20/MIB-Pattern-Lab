# Setup Discovery (Experiment 3) — design proposal

**Status: DRAFT FOR REVIEW. Nothing in this document is locked, run, sampled, called or computed.**
No OpenAI call, no chart, no outcome, no code for this experiment exists. Experiments 1 (1H) and 2 (5M) are closed and
untouched; MIB Trader, Hunt, S1, S2 and all live code are out of scope. The permanent policy `docs/REAL_FILLS_POLICY.md`
applies to everything below.

**Question.** Freeze the market at time T. Can AI, seeing only what a trader could see live at T, independently
recognise a recurring *trading setup* (context → location → development → trigger → invalidation) that can be turned
into a deterministic rule, shows favourable behaviour out of sample, and could eventually be executed with provable fills?

## 0. What I inspected, and what it teaches

* Repository: archived 1H and 5M pipelines (`src/discovery`, `src/charts`, `src/data`, `src/validation`, `src/outcomes`,
  `src/exp5m`), their locks/freezes, the real-fills policy and its AST tripwire (`tests/policy_guard.py`), config.
* **Visual families are not setups.** Both closed experiments labelled a *shape of the whole window*. A setup needs an
  event (trigger) at a knowable moment and a failure condition. Neither experiment could produce that by construction.
* **Effect sizes were small.** The best 5M cell was ~0.17 percentage points over two hours (adjusted p = 0.063, not a
  pass). Fees and slippage on a liquid perpetual are plausibly of that order. A statistically detectable effect that is
  smaller than realistic round-trip cost is not a trading setup, so this design adds an effect-size floor (§15).
* **Many cells, little power.** 25 cells with correction left little room. Here the unit is the *occurrence* and the
  number of hypotheses is kept small and fixed before any outcome.
* **Overlapping observations.** A condition that stays true for several candles creates correlated "occurrences". The
  design counts only non-overlapping occurrences (§10, §15).
* **Disclosure (contamination).** The 5M discovery period (Oct 2025 – May 2026) already had descriptive outcome tables
  for *visual families* computed and read by us. No setup concept was involved, but the period is not virgin for the
  researchers. The hold-out proposed in §16 (from 2026-06-01) has never been charted, shown to AI, or measured by any
  experiment.

## 1. What exactly is a "setup"?

A setup is a **pre-declared, frozen, deterministic event definition** with these parts. A candidate that lacks any part
is not a setup and is dropped (not repaired).

| Part | Meaning | Must be |
|---|---|---|
| Context | what price was doing before | visible in candles up to T |
| Location | the price relationship that makes the situation interesting | expressible from prior completed candles |
| Development | the sequence immediately before the possible trade | ordered, finite, observable |
| **Trigger** | the single observable event that makes it actionable | an event on a *closed* candle |
| Direction | up / down / **undetermined** | stated, never inferred from outcomes |
| Invalidation | an observable event proving the setup failed | a price level or event on closed candles |
| Required information | exactly which completed candles/derived values are needed | subset of OHLC history ≤ T |
| Presence rule | what counts as "setup present" | codeable without discretion |
| Expected behaviour | descriptive only; never evidence | not used in any test |

**Occurrence** = one trigger event found by the deterministic recognizer. The central statistical unit is the
occurrence, not the chart and not a family label.

A candidate is **NOT CODEABLE** if turning it into code needs a subjective judgement, a future candle, or a term the
frozen text does not pin down. NOT CODEABLE candidates are reported and never traded or "rescued".

**Undetermined-direction setups** (the AI says direction cannot be known) are tested only as *movement-size* hypotheses.
They can never proceed to a directional trade; they are reported separately.

## 2. What chart information will AI see?

* One clean candle chart ending at a **closed** candle T (only rows ≤ T are ever passed to the renderer).
* Price axis in **percent relative to the close at T** (magnitude is visible, absolute price is not). The vertical range
  fits the visible window (not the 4.3% fixed span of 5M), so no window is excluded (the 5M excluded-window limitation does not arise).
* Relative time axis only (T-N … T). No dates, clock times, symbol or timeframe names, no volume, no indicators,
  no annotations. PNG metadata scrubbed. OHLC only; a volume-aware study would be a later, separate experiment.
* **Lookback: 96 candles** (long enough to show a prior range/extreme and the build-up to a trigger).

## 3. What is hidden from AI?

Everything after T: future candles, highs/lows, returns, volatility; any outcome or label; whether the setup "won";
timestamps and sample order that reveal chronology; hold-out data; any backtest or statistic; the other charts' answers.
Model prior knowledge of historical BTC episodes cannot be removed, only reduced (relative axes, no dates, no symbol);
this is disclosed as a limitation.

## 4. Stage A — open discovery

* Sample: **600 charts** from the discovery period, chosen **outcome-blind** and stratified by chart-only features of
  the 96-candle window (equal quotas): directional (high efficiency, large net move), sideways (low efficiency, small net
  move), expansion vs compression (recent range vs prior range), sharp vs slow (largest 5-candle move). These cover the
  user's list without looking at any future price. Minimum spacing 32 candles; shuffled with a fixed seed before sending.
* One call per chart, free text/JSON, no vocabulary supplied and **no setup names or technical-analysis terms in the
  prompt** (strict prompt lint, as before). The prompt asks, in plain words, whether a recognisable, actionable
  situation is developing at the right edge and, if so, for the fields in §1 (context, location, development, trigger,
  direction or "cannot be determined", invalidation, expected behaviour, information required) plus a status:
  `ACTIONABLE_NOW` / `DEVELOPING` / `NONE`. **"No setup here" is a valid and expected answer.**
* One pass (there is no tag set to stabilise). Raw responses are stored; nothing is edited. The exact prompt text will be
  shown to you for review before any lock, as with 5M.
* **Output lint** (new, because trigger/invalidation/direction words are now required): reject responses that make
  performance claims or promises (profitable, wins, works, edge, high-probability, guaranteed, target, take-profit,
  stop-loss *distances*). Words such as trigger, direction, invalidation, and any technical vocabulary the model chooses
  on its own are allowed; they are never supplied by us.

## 5. Stage B — setup consolidation

* Input: the Stage A **text descriptions only** (no charts, no outcomes). Done map-reduce (chunks of ~150 descriptions →
  candidate setups per chunk → one final consolidation call) with fixed seeds and chunking.
* Output: **at most 8** candidate setups, each with name, context/location/development, trigger, direction,
  invalidation, required information, and a presence rule, plus the **ids of the Stage A descriptions it was derived
  from**. Python validates the schema, that cited ids exist, and that each candidate cites **at least 15 distinct
  descriptions** (recurrence), else it is dropped on count alone.
* The model must not state or imply that a setup works. Validation and lint as in D2: up to 3 attempts, reasons appended,
  never edited by hand; if all fail the stage stops and is reported.
* **Overlap diagnostics are computed later without outcomes** (co-occurrence of recognizers). No merging or splitting
  after the freeze: near-duplicate candidates are tested separately and the report says so.

## 6. How outcome leakage is prevented

1. Separate code path: the new package (planned `src/setups/`) is split into *discovery/recognition* modules and one
   *outcome* module. The first group may not import the outcome module or any forward-looking helper (test-enforced,
   like the existing `forward.py` firewall). `src/setups/` is added to the policy tripwire's protected directories.
2. The renderer receives `df[df.ts <= T]` only; a test shows the PNG is unchanged when future candles are altered.
3. No outcome column is ever written next to charts, descriptions, tags or definitions that the model or the
   recognizer author can read.
4. Recognizer development uses only price structure, synthetic test cases, frequency statistics and the fidelity audit
   (§8) — never outcome files. The first outcome computation happens after the recognizer freeze.
5. Chart order randomised with a fixed seed; filenames and prompts carry no chronology.
6. Everything the model returned and every hash is recorded (`prompt`, `image`, `response`, `model`).
7. No peeking at hold-out data by anyone for any purpose until its single run (§16).

## 7. How candidate setups are frozen

Freezes are sha256 records (CRLF-normalised, as in 1H/5M), written once, each committed before the next step:

| Freeze | Contents | Before |
|---|---|---|
| F0 design lock | this design as pre-registration v1, parameters, prompts, discovery code, coverage report | sampling |
| F1 setup-definition freeze | Stage B output verbatim: names, definitions, required information, trigger, direction, invalidation, plus raw A/B responses | any recognizer work |
| F2 recognizer freeze | recognizer code, the parameter table (each number with its non-outcome derivation), tests, fidelity-audit result, frequency check | any outcome |
| F3 outcome-code freeze | outcome/statistics code, matched-baseline rule, thresholds | the outcome run |
| F4 hold-out run-once | frozen setup/recognizer/horizon/direction, run-once marker | hold-out |

After F1 there is no AI step. No renaming, merging, splitting, trigger changes, lookback changes or removal of bad
examples. A failed candidate is reported as failed; an ambiguous one is reported as ambiguous.

## 8. How each setup becomes deterministic Python

The translation is the highest-risk step because it is where discretion hides.

* The recognizer is written **from the frozen text only**; every qualitative term ("approaches", "temporary
  penetration", "extreme", "range") is mapped to one explicit numeric rule in a **parameter table** that is shown to
  you **before** any scan. Preferred form: causal, rolling and relative (e.g. a multiple of the trailing 96-candle range),
  not a global constant. A global constant is allowed only if derived from discovery-period *price statistics*
  (never outcomes) and then frozen. **No sweeps, no tuning on outcomes.** Sensitivity variants may be pre-declared; if
  so all are reported and none is selected.
* Interface: `recognize(candles_up_to_t) -> trigger | none`. Same data → same answer, no AI at scan time.
* Tests: determinism; **prefix invariance** (the answer at candle t is identical if all later candles are removed or
  replaced with noise); synthetic constructed positive/negative cases from the definition text; no use of rows > t.
* **Fidelity audit** (outcome-blind): a stratified sample of charts where the recognizer fires and where it does not is
  shown to the model with the frozen definition text and asked "is this setup present at the right edge?". Report
  agreement. This checks the translation, not profitability. Proposed gate: the recognizer's precision against the
  model's reading ≥ 70% and recall of `ACTIONABLE_NOW` Stage A cases ≥ 50%; otherwise **NOT CODEABLE FAITHFULLY**.
* Frequency sanity (no outcomes): a recognizer that fires on < 0.2% or > 10% of candles is not a setup; classify as
  NOT CODEABLE / NOT SELECTIVE.

## 9. How trigger timing is established causally

* The trigger is stamped at the **close time of the first candle on which every condition is knowable**.
* Swing highs/lows and any structure that needs later candles to be confirmed are **stamped at the confirmation
  candle**, never at the pivot candle. A condition that needs a future candle moves the trigger to that candle.
* `signal_ts` = close of the trigger candle. No order can exist before it.
* Outcome reference price (descriptive only): the **open of the next candle**, the earliest price that could in
  principle be traded after the trigger became known. The close of the trigger candle is also reported for continuity
  with 1H/5M but is not the primary reference. These are descriptive measurements, not fills.

## 10. How unsuccessful occurrences are found

The recognizer scans **every** candle of the discovery series and records **every** trigger, regardless of what
happened next; AI-chosen examples are never used as the statistical sample. Per occurrence: setup id, trigger and
signal timestamps, direction, reference price, invalidation level, highs/lows over each horizon, signed forward returns,
MFE/MAE, MFE/MAE before invalidation, time to favourable move, time to invalidation. A **lockout** (from the trigger
until the invalidation or 24 candles, whichever is later) makes counted occurrences non-overlapping; triggers inside a
lockout are logged but not counted. Distributions (including losers and ambiguous cases) are reported in full.

## 11. How real fills will eventually be proven

Nothing in this experiment is a fill; outcomes are descriptive statistics (the required policy sentence appears in
every report and `summary.json`). Before any trading backtest a separate **execution specification** (policy §8) is
frozen first. The data hierarchy is: recorded exchange fills > deterministic simulation on finer data > UNKNOWN.

* The data in hand is OHLC. A resting-limit fill cannot be proven from OHLC, so such fills are **UNKNOWN** unless a
  conservative rule fixed in advance applies. The default model is a marketable order at the next candle's open with
  pessimistic, pre-declared spread and slippage; stops fill at the worse of the stop and the next available price.
* Intrabar order is resolved with the **finer series (5-minute candles, if present for the whole period)**; if a candle
  still contains both a stop and a favourable level, the event is **AMBIGUOUS**, counted adversely in the primary
  result and also reported separately.
* Every simulated trade must answer the seven audit questions in the policy, or it is invalid.
* The only tier-1 evidence is **paper trading with real exchange fills**, which is a required gate before any integration.

## 12. Which timeframe first?

**Recommendation: 15-minute signals, with 5-minute candles reserved for later execution-resolution.**

* 5M moves are small relative to realistic costs (§0), and its candle noise dominated the last experiment.
* 1H has six years of history, but only the ~13-month window has finer candles for resolving fills, and the 1H hold-out
  (≥ 2024-06-01) was reserved for the archived experiment: using it here would consume it.
* 15M keeps the whole pipeline (discovery → hold-out → fill resolution) inside the same ~13-month period that has 5M
  data. Cost: a short history (~38k candles). **Precondition:** a read-only coverage report for 15M (gaps, duplicates,
  timestamp convention, whether 1M data exists), like `COVERAGE_REPORT.json` for 5M. Not run yet.

## 13. How many discovery charts are needed?

**600 for Stage A** (same scale as 5M, ~100 per stratum across six chart-only strata), as a cap rather than a promise.
The real quantity that matters is the number of **occurrences found by the recognizer**; Stage A only needs enough
variety for candidate definitions to recur (≥ 15 citing descriptions). If fewer than 15 distinct descriptions support any
candidate, the finding is "no recurring setup recognised", which is a valid result.

## 14. OpenAI budget

Proposal (hard caps, enforced by the existing cost module; a token-based estimate is shown and approved before any spend):

| Stage | Cap |
|---|---|
| Stage A (≈600 vision calls, longer outputs than D1) | $3.00 |
| Stage B (text only, map-reduce) | $0.50 |
| Fidelity audit (vision, ≈200 calls) | $1.00 |
| **Total** | **$4.50** |

These are estimates; real per-call cost has not been measured for these prompts. The hold-out costs nothing in AI calls
because it is mechanical Python.

## 15. What conditions make a setup PASS or FAIL?

Each frozen candidate is classified at the discovery stage by **fixed gates** (all declared before F1):

* **G0 Codeable and faithful:** deterministic recognizer, prefix-invariance tests pass, fidelity gate (§8), frequency
  bounds. Else **NOT CODEABLE**.
* **G1 Enough occurrences:** ≥ **100** counted (non-overlapping) discovery occurrences. Else **INCONCLUSIVE / LOW FREQUENCY**.
* **G2 Predictive information (discovery):** unit = occurrence; outcome = **direction-signed** forward return at 1, 3,
  6, 12, 24 candles from the next-candle open, compared with a **matched baseline** (non-occurrence times in the same
  volatility/trailing-move strata, same direction sign), with day-clustered bootstrap CIs, stratified permutation test, a
  control regression (as in 5M), and **maxT correction across setups × horizons**. **PASS** at a horizon requires all of:
  adjusted p < 0.05; CI of the difference excludes 0; control regression p < 0.05 with the same sign; the effect also
  holds measured from the next-open reference; and a **cost-aware floor**: mean signed return ≥ *F* (see decisions).
  Statistics reuse the archived 1H/5M code (imported, not copied) behind a new frozen wrapper.
* **DOES NOT PASS:** CI within ±MDE at every horizon. **INCONCLUSIVE / LOW POWER:** otherwise. (Neither means "no edge".)
* **Robustness (pre-declared, all must hold for a PASS to count):** same sign in at least 80% of months, no single
  month or the top 5% of trades drives the result (leave-one-month-out, trimmed mean), and the result is not an artefact of
  a single other candidate (co-occurrence check).
* **G3 Hold-out (§16):** the frozen setup, direction and horizon, mechanically applied once, with α = 0.05 ÷ (number of
  discovery PASSes), ≥ 50 counted occurrences, same sign, CI excluding 0, and the same floor *F*.
* **Experiment outcome.** A *candidate trading setup* exists only if G0–G3 all pass. If none does, the report says: "No
  recurring setup that is codeable, statistically favourable and robust out of sample was established." Later gates —
  execution-aware backtest under a separate frozen spec (all pre-registered execution models reported, adverse
  ambiguity), then paper trading with real fills — are **outside this experiment**.

## 16. How will the chronological hold-out work?

* **Discovery:** candles before **2026-06-01** (Stage A charts, Stage B, recognizer design).
* **Hold-out:** **2026-06-01 up to the data end (~2026-10-06, ≈ 4 months)**. Never charted, never shown to AI, never
  measured by any experiment so far. Recognizers may use earlier candles as lookback; no thresholds are refit.
* Occurrences whose forward window would cross the end of discovery are excluded from discovery counts.
* Applied **once**, mechanically, with a run-once marker; no AI, no vocabulary change, no tuning, no reclassification.
* Limit: ≈ 4 months may yield too few occurrences; then the result is INCONCLUSIVE rather than a lowered bar. New data
  that arrives after the freeze becomes a **second, forward hold-out** (and the paper-trading stage).

## Planned order (after your approval)

F0 design lock → 15M coverage report → sampler dry-run (no API) → Stage A → Stage B → **F1** → recognizer + parameter
table (reviewed by you) → fidelity audit → **F2** → **F3** → discovery outcome run (once) → hold-out only for G2 PASSes
(once) → report. Every step runs on your machine where the data and key live; I stop after each.

## Decisions I need from you before F0

1. **Timeframe:** 15M (recommended) or another?
2. **Floor *F*** (minimum mean signed return per occurrence to count as a pass, before any execution model). The 5M
   effects were ≤ 0.17 pp; a floor near realistic round-trip cost (proposal: **0.15%**) would have failed all of them,
   which is the point. Which value do you want?
3. **Budget:** approve the $4.50 cap structure?
4. **Hold-out:** use 2026-06-01 onward for the hold-out as proposed?
5. **Thresholds** in §8/§15 (fidelity ≥ 70%/50%, ≥ 100 discovery and ≥ 50 hold-out occurrences, ≥ 15 supporting
   descriptions, ≤ 8 candidates): accept or change before they are frozen.

## Honest expectations and the main failure modes

* AI will often "see" setups in noise. The defence is structural: outcome-blind discovery, deterministic recurrence
  counts, a matched baseline, a cost-aware floor and an untouched hold-out.
* Many AI-described triggers will turn out **NOT CODEABLE**; that is an acceptable, informative result.
* Two closed experiments found nothing predictive; a third negative result is plausible, and the design is built to
  report it cleanly. If the data cannot prove the fill, the trade does not exist.
