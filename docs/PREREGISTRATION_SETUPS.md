# Pre-registration — Setup Discovery (Experiment 3), 15M

**Status: DRAFT v1 FOR REVIEW. NOT LOCKED.** Nothing here has been run, sampled, charted, sent to any model, or
computed. Nothing is frozen until you approve this text and a design lock is written (section 13). Companion to
`docs/SETUP_DISCOVERY_DESIGN.md` (architecture, approved with the changes recorded in section 14) and the permanent
`docs/REAL_FILLS_POLICY.md`. Experiments 1 (1H) and 2 (5M) are closed and untouched; MIB Trader, Hunt, S1, S2 and
all live code are out of scope.

## 0. The question

Freeze the market at time T. Can AI, seeing only what a trader could see live at T, independently recognise a recurring
**setup** — context → location → development → **presence** → **trigger** → invalidation — that can be turned into a
deterministic rule, shows direction-signed favourable behaviour out of sample, and could eventually be executed with
provable fills?

This experiment answers only "is there information in a codeable setup?". It does **not** show tradability or profit.

## 1. Canonical dataset (fixed)

| | |
|---|---|
| File | `data/research_binance.db` (**the canonical dataset for the Setup Discovery experiment**) |
| Bytes | 71,098,368 |
| SHA-256 | `1535c5352c56096f5e50c6ac6522715048d19c6c887548c6f5dc5f0576c27e9f` |
| Symbol | BTC/USDT; timeframes in the file: 1m, 5m, 15m, 30m, 1h, 4h, 1d |
| Coverage report | `docs/setups/COVERAGE_RESEARCH_BINANCE_REPORT.json` (commit `24babaa`) |
| Signal series | 15m: 37,728 rows, 2025-09-01 00:00 → 2026-09-28 23:45 UTC; 0 gaps / duplicates / off-grid / invalid OHLC; 37,727 usable after the loader drops the last stored candle |
| Fill-resolution series | 5m (113,184 rows) and 1m (565,920 rows), same range, 0 gaps; every 15m candle has all 3 five-minute and all 15 one-minute children, and its OHLC equals their aggregate exactly |
| Conventions | epoch seconds, UTC, `ts` = candle **open** time (verified) |

`market_Data_Clean.db` is **not** used for this experiment, and no number from the earlier audit of that file is used.
Every pipeline step recomputes the database SHA-256 and refuses to run on any other file or any change.

## 2. Periods

* **Discovery:** 15m candles with open time **< 2026-06-01T00:00:00Z** (26,208 usable candles; 26,089 positions with a
  full 96-candle lookback and a complete 24-candle forward path inside the period).
* **Hold-out:** open time **≥ 2026-06-01T00:00:00Z** to the end of the data (last usable candle 2026-09-28 23:30 UTC;
  11,519 usable candles ≈ 120 days; 11,495 positions with a full lookback and forward path). Earlier candles may serve as
  lookback for a hold-out trigger; no threshold is refitted. Hold-out candles are physically removed before any discovery
  step reads data, are never charted, never shown to a model, and are first read by the single hold-out run (section 12).
* No forward path may cross the end of its period.

## 3. Definitions

* **Setup:** a frozen, deterministic definition with nine parts: context, location, development, **presence rule**,
  **trigger**, direction (`up` / `down` / `undetermined`), invalidation, required information, expected behaviour
  (descriptive; never evidence).
* **Presence vs trigger are different timestamps.** A setup can exist without being tradable yet:
  `presence_ts` = close time of the first candle on which every presence condition is knowable;
  `trigger_ts` = close time of the first later (or same) candle on which the trigger event is knowable;
  `signal_ts` = `trigger_ts`. A setup that is PRESENT but not TRIGGERED is not an occurrence.
* **Occurrence:** one trigger found by the deterministic recognizer. It is the statistical unit.
* **Causality:** only completed candles ≤ the stamped candle; any structure that needs later candles to be confirmed
  (swing points, ranges) is stamped at its confirmation candle; a condition that needs a future candle moves the trigger.
* **Analytical reference price:** the **open of the candle after the trigger candle**. It is a measurement reference, not
  an execution price. The close of the trigger candle is also reported for continuity with Experiments 1–2.
* **NOT CODEABLE:** needs subjective judgement, a future candle, or a term the frozen text does not pin down. Reported;
  never repaired, never traded.
* **Undetermined direction:** tested only as a movement-size hypothesis; it can never proceed to a directional trade.

## 4. Chart (what the model sees)

96 closed 15m candles ending at T (rows ≤ T only). Candles only: no volume, indicators, annotations, symbol or timeframe
names, dates or clock times. Price axis in percent relative to the close at T; vertical range fits the visible window
(no window is excluded); relative time axis (T-95 … T); PNG metadata scrubbed; style parameters hashed
(`chart_style_sha256`) and identical for every chart. A test must show a chart is unchanged when later candles change.

## 5. Stage A — sample and open discovery

**Sample (outcome-blind, deterministic).** Candidates = discovery positions with a full lookback and a forward path
inside discovery (existence checked from timestamps only). Chart-only features of the 96-candle window:
efficiency `eff` and net move `net_pct` (as in `src/discovery/audit.py`), range expansion `RE` = range of the last 24
candles ÷ range of the preceding 72, and `sharp` = largest 5-candle |close change| ÷ close_T. Tercile cut-points are
taken over all candidates (the whole discovery period; disclosed hindsight about the *distribution of chart features*,
never about outcomes). Six strata, processed in this order, **100 windows each**, a window belonging to the first
stratum that accepts it:

| # | stratum | eligible when |
|---|---|---|
| S1 | directional | `eff` in top tercile **and** `|net_pct|` in top tercile |
| S2 | sideways | `eff` in bottom tercile **and** `|net_pct|` in bottom tercile |
| S3 | expansion | `RE` in top tercile |
| S4 | compression | `RE` in bottom tercile |
| S5 | sharp | `sharp` in top tercile |
| S6 | slow | `sharp` in bottom tercile |

Within a stratum: visiting order = evenly spaced grid, then denser, then all (as in the 5M sampler); accept unless within
**32 candles** of an already accepted window. A shortfall in a stratum is reported and **not** back-filled. The 600
charts are shuffled with a fixed seed (`SEED_ORDER = 777`) before sending; filenames and prompts carry no chronology.

**Calls.** One call per chart, model `gpt-5.4-mini`, no `temperature` set, one pass. Prompt text: Appendix A. Output
fields: `status` (`ACTIONABLE_NOW` / `DEVELOPING` / `NONE`), `visible_summary`, `context`, `location`, `development`,
`trigger`, `direction`, `invalidation`, `expected_behavior`, `information_required`. **"None" is a valid, expected
answer.** Raw responses, image hash and prompt hash are stored; nothing is edited.

**Lints.** *Prompt lint (strict, whole-word, case-insensitive):* the prompts must contain none of: breakout, BOS, CHoCH, liquidity, sweep, FVG,
fair value gap, support, resistance, order block, trend, continuation, reversal, momentum, mean reversion, pattern,
candlestick, bullish, bearish, indicator, volume. *Output lint:* a response is rejected (error row, no retry loop) if it
contains performance or promise language: profit, profitable, win, wins, winning, works, edge, probability, likely,
guaranteed, target, take profit, stop loss, backtest. Technical words the model chooses itself are allowed; we never
supply them.

## 6. Stage B — consolidation

Input: Stage A **text only** (status ≠ `NONE`), no charts, no outcomes. Chunks of **120** descriptions (fixed seed),
one call per chunk, then **one final consolidation call** over the chunk candidates. Each candidate has: `name`,
`context_definition`, `conditions_sequence` (ordered), `presence_rule`, `trigger` (an event on a completed candle),
`direction`, `invalidation`, `information_required`, `supporting_ids`. Prompt text: Appendix B.

Validation (Python): valid JSON and schema; `direction` in the enum; every `supporting_id` exists; **at most 8**
candidates; **at least 15 distinct supporting descriptions** per candidate (otherwise dropped on count alone); output
lint; no performance language. Up to 3 attempts per call, reasons appended, **never edited by hand**; if all fail the
stage stops and is reported. If fewer than one candidate survives, the finding is "no recurring setup recognised".

## 7. Freeze and translation

**F1 — setup-definition freeze:** the Stage B output verbatim (names, definitions, presence rules, triggers, direction,
invalidation, required information) plus all raw Stage A/B responses. After F1 there is no AI step. No merging, splitting,
renaming, trigger changes, lookback changes or removal of bad examples.

**Recognizer.** Written from the frozen text only. Every qualitative term is mapped to one explicit numeric rule in a
**parameter table**, shown to you **before** any scan, each number with its non-outcome derivation. Preferred form: causal
and relative (multiples of the trailing 96-candle range, etc.). A global constant is allowed only if derived from
discovery-period **price statistics** (never outcomes) and then frozen. One primary parameterization; any pre-declared
sensitivity variants are all reported and none is selected. No sweeps, no tuning on outcomes. Interface:
`recognize(candles_up_to_t) → (presence, trigger, invalidation) | none`.

**Tests (all must pass before F2):** determinism; **prefix invariance** (the result at candle t is identical if all later
candles are removed or replaced by noise); synthetic positive and negative cases built from the definition text; no
read of rows > t.

**Frequency sanity (no outcomes):** a recognizer that triggers on < 0.2 % or > 10 % of discovery candles is classified
NOT CODEABLE / NOT SELECTIVE.

**Fidelity audit (outcome-blind, within the AI budget).**
*Precision.* A sample of up to 100 recognizer trigger cases and 100 non-trigger cases (stratified like the Stage A
sample) is shown to the model with the frozen definition text and asked whether the setup is present at the right edge.
Precision = share of the audited recognizer trigger cases judged present. Gate: **precision ≥ 70 %**, evaluated
**only if at least 10 recognizer trigger cases were audited**. If fewer than 10 trigger cases are available, the
candidate is classified **insufficient evidence → NOT CODEABLE FAITHFULLY**; a tiny sample can never pass.
*Recall (mechanical, candidate-specific).* For a candidate *K*, let **E_K** = the Stage A charts with
`status = ACTIONABLE_NOW` whose chart id is in *K*'s `supporting_ids` (the "eligible supporting charts").
`numerator` = the charts in E_K on which the **frozen recognizer of K** is PRESENT, or has TRIGGERED within the last 2
candles, at the chart's end T (evaluated on candles ≤ T only); `denominator` = |E_K|; recall = numerator ÷ denominator.
Gate: **recall ≥ 50 %**, evaluated **only if |E_K| ≥ 10**. If |E_K| < 10 the recall gate is **not** evaluated and fidelity
is classified **insufficient evidence → NOT CODEABLE FAITHFULLY**; a tiny denominator can never pass. The 70 % / 50 %
thresholds are unchanged. Fidelity is not profitability.

**F2 — recognizer freeze:** recognizer code, parameter table, tests, fidelity result, frequency result. The recognizer
author never sees outcomes: the recognizer is frozen **before** the outcome dataset is exposed.

## 8. Occurrences and measurements (descriptive only)

The recognizer scans **every** discovery candle and records **every** trigger, whatever happened next. A **lockout**
(from the trigger until the later of the invalidation event and 24 candles after the trigger) keeps counted occurrences
non-overlapping; triggers inside a lockout are logged, not counted.

Per occurrence: setup id; `presence_ts`; `trigger_ts`; `signal_ts`; direction; analytical reference price; invalidation
level and `invalidation_ts` (first closed candle on which the invalidation rule holds); for horizons **H ∈ {1, 3, 6, 12,
24}** 15m candles: forward return from the reference price to the close of candle `trigger+H`, future high, future low,
MFE, MAE (all % from the reference price), MFE/MAE **before** invalidation, time to a favourable excursion of +F (see
section 9) and time to invalidation, whichever occurs. Excursions in the invalidation candle itself, and any candle
containing both a favourable and an invalidating level, are resolved with the **5-minute** candles; if the 5-minute
order is still undeterminable (and 1-minute data cannot settle it) the event is **AMBIGUOUS**: counted adversely in the
primary result and reported separately with its count. Forward return, future high/low, MFE and MAE are **not fills**.

**Required statement (every report and `summary.json`; Experiment 3 wording, recorded verbatim in policy sections 0
and 11):**

> Forward return, future high, future low, MFE and MAE are descriptive statistics of the historical price series,
> measured from the analytical reference price (the open of the candle after the trigger candle). They are not trade
> fills, they were not shown to be executable prices, and they must not be read as realized trades.

## 9. Statistics (discovery)

Direction-signed outcome for an occurrence *i* of a directional setup: `y_i,H = d_i · r_i,H` with `d = +1` (up) or
`−1` (down) and `r` the raw forward return from the reference price. The hypotheses are only the frozen setups ×
5 horizons (**at most 8 × 5 = 40 cells**).

* **Raw forward return of a candle.** For every 15m candle *c* that is **eligible** (its full 24-candle forward path
  lies inside the same period), `r_{c,H} = 100 · (close[c+H] / open[c+1] − 1)`, H ∈ {1, 3, 6, 12, 24}: the return from the
  analytical reference price of a trigger at *c*. An occurrence's `r_{i,H}` is this value at its trigger candle.
* **Local baseline (stratum).** The stratum of a candle = (UTC calendar week of its open time) × (tercile of the trailing
  96-candle high-low range ending at that candle, as % of its close; cut-points = terciles over eligible discovery
  candles, frozen, and reused unchanged for the hold-out). `m_{k,H}` = mean of `r_{c,H}` over **all** eligible candles of
  stratum *k*. Discovery spans exactly 39 whole UTC weeks (Mon 2025-09-01 → Sun 2026-05-31).
* **Estimand:** `D_{s,H} = mean_i d_i · (r_{i,H} − m_{k(i),H})`. It is the direction-signed advantage of the setup's
  occurrences over a local, volatility-matched baseline; it removes drift and regime clustering.
* **Baseline status (explicit).** The baseline `m` is computed from the **completed** discovery-period history (it uses
  returns that occur after each occurrence, within its week) and is therefore an **ex-post analytical benchmark**. It is
  **not** information available to the AI, **not** information available to the recognizer, **not** part of trigger
  determination, **not** part of execution, and **not** a parameter selected using outcomes. It cannot be computed live
  and must never be read as a tradable signal or a rule. The same applies, on its own data, to the hold-out baseline.
* **Inference.**
  (a) **95 % day-clustered bootstrap** CI of `D`: 10,000 resamples of occurrences by UTC day (all occurrences of a
  sampled day move together), the baseline `m` held fixed, `numpy.random.default_rng(20240601)`.
  (b) **Day-block permutation null (preserves serial dependence; no individual 15m row is ever permuted).** The unit is
  one **UTC day = 96 consecutive 15m candles**, kept intact with all five horizons together. In each draw, within every
  UTC calendar week, the **complete days** (every candle eligible) are permuted: **Monday–Friday among themselves and
  Saturday–Sunday among themselves**; days containing any ineligible candle stay in place. The candle in slot *k* of day *q*
  receives the return rows of slot *k* of the day assigned to *q*. Occurrence times, directions, strata and `d_i` stay
  fixed; each draw recomputes the stratum means `m*` from the permuted rows and then `D*_{s,H}` for **every setup and
  horizon** with the same function used for the observed `D`. **10,000 draws**, `numpy.random.default_rng(12345)`.
  The null assumed is: *the timing of occurrences within a week and day-type carries no information about subsequent
  returns.*
  (c) **maxT.** For each cell, `s_cell` = standard deviation of `D*_cell` over the draws and `Z_cell = D_cell / s_cell`,
  `Z*_{b,cell} = D*_{b,cell} / s_cell`. The two-sided adjusted p of a cell is
  `(1 + #{b : max over all cells |Z*_{b,·}| ≥ |Z_cell|}) / (10,000 + 1)`. All setups × horizons use the **same** draws, so
  their dependence is preserved. Hold-out: the same procedure on hold-out weeks for the single frozen cell
  (`s_cell` from its own draws), with α = 0.05 ÷ (number of G2 PASSes).
  (d) **Control regression** (HC3, analytic, no permutation): `y` on the occurrence dummy, `d·(trailing 24-candle net
  move)`, trailing 96-candle range and efficiency, over the occurrences plus 5 seeded controls per occurrence drawn from
  the same stratum (`default_rng(12345)`).
* **MDE:** the archived `stats.mde` formula (z-based, `m_cells` = cells actually tested, power 0.80) on the
  occurrence/control samples.
* **Code reuse.** Archived helpers (`src/outcomes/stats.py`: `mde`, `ols_hc3`, `welch`, `cohens_d`) are imported unchanged
  behind a new frozen wrapper; their 1H freeze record stays valid. The day-block permutation and maxT above are **new**
  code in `src/setups/`, because the archived permutation shuffles individual rows, which this experiment does not do.

**Research effect-size floor F = 0.15 percentage points** of `D` at the frozen horizon. **F is a research effect-size
screen. It is not assumed net trading profit and is not proof of economic viability.** Execution cost is handled only
by the separate, later gates (section 12).

## 10. Gates, categories and the experiment outcome

* **G0 — codeable and faithful:** recognizer + tests + fidelity (≥ 70 % / ≥ 50 %) + frequency bounds. Else
  **NOT CODEABLE**.
* **G1 — enough occurrences:** **≥ 100** counted discovery occurrences; else **INCONCLUSIVE / LOW FREQUENCY**.
* **G2 — predictive information (discovery), at a horizon, all required:** maxT-adjusted p < 0.05; bootstrap CI of `D`
  excludes 0; control-regression p < 0.05 with the same sign as `D`; `D ≥ F` (direction-favourable); the same result when
  the reference price is the trigger-candle close; and the **robustness** conditions: same sign of `D` in ≥ 80 % of
  discovery months, `D` keeps its sign when the single best month is removed and when the best 5 % of occurrences are
  removed.
* **DOES NOT PASS:** CI within ±MDE at every horizon (not "no edge"). **INCONCLUSIVE / LOW POWER:** otherwise.
  The frozen horizon of a G2 PASS is the one with the smallest adjusted p (ties: shorter).
* **Co-occurrence diagnostics** between candidates are reported (no outcomes used); candidates are never merged or split.
* **G3 — hold-out:** applied once to each G2-PASS setup at its frozen direction and horizon, with
  α = 0.05 ÷ (number of G2 PASSes), ≥ **50** counted hold-out occurrences, same sign, CI excluding 0, `D ≥ F`.
  Fewer than 50 → INCONCLUSIVE, never a lowered bar. Hold-out stats use the same estimand, strata and procedure.
* **Outcome:** a **candidate trading setup** exists only if G0–G3 all pass. Otherwise the report states: "No recurring
  setup that is codeable, statistically favourable and robust out of sample was established."
* **Not part of this experiment:** the execution-aware backtest and paper trading (section 12).

## 11. Budget (hard stop) and cost log

| Stage | Cap |
|---|---|
| Stage A (~600 vision calls) | $3.00 |
| Stage B (text) | $0.50 |
| Fidelity audit (~200 vision calls) | $1.00 |
| **Total — hard ceiling** | **$4.50** |

The run **stops** when estimated or actual cumulative cost reaches the cap (a call is not started if cumulative + its
estimate would exceed it). There is **no automatic continuation**; any further spend needs a new written decision. Every
call logs: model, step, call number, input tokens, output tokens, estimated cost, cumulative cost. A token-based estimate
is shown and approved before each stage. The hold-out costs no AI calls.

## 12. Real fills (policy section references)

* Nothing in this experiment is a fill; all outcomes are descriptive statistics (required statement, section 8).
* Any trading backtest needs a **separate execution specification, frozen before it runs** (policy section 8). It may
  not begin until a setup has passed G0–G3, and it reports every pre-registered execution model, including the
  unfavourable ones.
* **Fill-resolution data hierarchy:** recorded exchange fills > deterministic simulation on 1-minute/5-minute data > UNKNOWN.
  The canonical database holds complete 5m and 1m series equal to the 15m aggregates (section 1), so intrabar order can
  be resolved at 1-minute resolution; where 1-minute data still cannot prove the order, the event is **AMBIGUOUS**, never
  a fill. A resting limit order cannot be proven filled from OHLC alone. The analytical reference price is **not** the
  execution price; a live entry may need finer confirmation and must be modelled separately.
* Every simulated trade must answer the seven audit questions of policy section 10 or it is invalid.
* The only tier-1 evidence is **paper trading with real exchange fills**, a required gate before any integration.

## 13. Freezes and run-once

All freezes are sha256 records (CRLF normalised to LF), written once, each committed before the next step.

| Freeze | Content | Before |
|---|---|---|
| **F0 design lock** | this pre-registration, the coverage report, dataset hash, parameters, prompts (hashed), the sampler and Stage A/B/audit code, the cost logger | sampling |
| **F1** | Stage B output + raw responses (section 7) | any recognizer work |
| **F2** | recognizer, parameter table, tests, fidelity and frequency results | any outcome |
| **F3** | outcome/statistics wrapper and thresholds | the discovery outcome run |
| **F4** | frozen setups/directions/horizons; run-once marker | the hold-out run |

The discovery outcome run and the hold-out run each complete **once** (run-once marker; re-run only with identical
code). The workflow is Discovery → freeze → hold-out → final report; once the hold-out is opened the setup is finished,
and nothing is re-examined to "understand why". Planned new package: `src/setups/` (separate from the archived
`src/outcomes/`, which is never edited and gets no new files); `src/setups/` is added to the policy tripwire's protected
directories before any code beyond the coverage audit exists. Discovery/recognition modules may not import the outcome
module (test-enforced).

## 14. Decisions on record

Approved by the project owner: 15M as the discovery timeframe; 600-chart concept, 96-candle chart; two-stage discovery;
at most 8 candidates, ≥ 15 supporting descriptions; deterministic recognizers; five freezes; outcome firewall; ≥ 100
discovery and ≥ 50 hold-out occurrences; hold-out from 2026-06-01, applied once; fidelity ≥ 70 % / ≥ 50 %; $4.50 hard
budget with cost logging; separate real-fills execution stage; UNKNOWN/ambiguous treated conservatively; paper trading as
the final gate. Modified: the 0.15 % floor is a research effect-size screen only, not net profit. Required: presence and
trigger are separate timestamps; the next-candle open is the *analytical reference price*, not an execution price; the
recognizer is frozen before the outcome dataset is exposed. Dataset replaced by `data/research_binance.db`. Revision requested before F0: day-block permutation null (no row-level permutation); explicit ex-post status of the local baseline; mechanical, candidate-specific recall with a minimum of 10 eligible supporting charts; Experiment 3 analytical-reference-price sentence added to the policy; design doc section 12 corrected.

## 15. Disclosures and limitations

* The 5M experiment's discovery period (Oct 2025 – May 2026) already had descriptive outcome tables for visual families
  computed and read by us; no setup concept was involved, but the period is not virgin for the researchers. The
  hold-out (≥ 2026-06-01) has never been charted, shown to a model or measured by any experiment.
* The model may know historical market episodes; relative axes, no dates and no symbol reduce, not remove, this.
* The day-block null assumes days of the same type (Mon–Fri / Sat–Sun) within a UTC week are exchangeable under
  "no information"; volatility differences among days can make it imperfect, which is why the baseline also matches on
  volatility and why the robustness gates exist. Days with ineligible candles (period ends) are not permuted.
* Candidates are not independent; the maxT correction handles dependence among cells, and co-occurrence is reported.
* The hold-out is ≈ 120 days; low frequency can make G3 INCONCLUSIVE. Data after 2026-09-28 is not in this dataset;
  later data can become a second, forward hold-out and the paper-trading period.
* `docs/SETUP_DISCOVERY_DESIGN.md` §12 reasoned from the earlier database about timeframes and finer data; the 15M
  decision stands as approved and the facts in section 1 above supersede that reasoning.
* The strata, features and thresholds in sections 5–10 are choices made before any outcome exists; none will change
  after F0.

---

## Appendix A — Stage A prompts (proposed text)

**System.**
```
You are a careful, disciplined observer of price charts. You are shown a single chart made of candles. Treat it as a LIVE chart: the right edge is the present moment and nothing after it exists. Use only what is visible in the image. Do not use outside knowledge about what happened. Do not guess what happens after the right edge. Respond with one JSON object only.
```

**User.**
```
Imagine you are looking at this chart live, right now, at the right edge.

Is there a recognisable, potentially actionable trading situation developing or present at the right edge? If there is, describe exactly what you see and what would make it actionable. If there is not, say so. "none" is a perfectly good answer; do not force a situation that is not clearly there.

Return a JSON object with exactly these keys:
- "status": "ACTIONABLE_NOW" if the event that makes it actionable has already happened on or before the last candle; "DEVELOPING" if a situation is forming but that event has not happened yet; "NONE" if there is no recognisable situation.
- "visible_summary": 1-2 sentences describing the price path left to right (appearance only).
- "context": what price was doing before the situation developed ("" if NONE).
- "location": what observable price relationship, visible on this chart, makes the current situation interesting ("" if NONE).
- "development": the sequence of price behaviour immediately before the potential trade, in order ("" if NONE).
- "trigger": the exact observable event, on a completed candle, that makes the situation actionable ("" if NONE).
- "direction": "up", "down", or "undetermined" (use "undetermined" if the direction cannot be determined from the chart, and for NONE).
- "invalidation": the observable event that would show the situation has failed ("" if NONE).
- "expected_behavior": the kind of later price behaviour that would make it successful, described in words, without promising any outcome ("" if NONE).
- "information_required": a list of the specific chart elements (candles, levels, ranges) needed to recognise this situation ([] if NONE).

Describe only what is visible. Do not say or imply that the situation will work or is likely to succeed.
```

## Appendix B — Stage B prompts (proposed text)

**System.**
```
You are a careful analyst who consolidates written descriptions of chart situations. You see only text descriptions, each with an id. You have no information about what happened after any chart, so you must never say or imply that any situation works, wins, or is reliable. Use only what is in the descriptions; do not add conditions that are not in them. Respond with one JSON object only.
```

**User (chunk call).**
```
Below are descriptions of situations observed on live price charts. Each has an id.

Group descriptions that describe the same recurring situation. Return at most 8 distinct candidate situations, and only candidates whose actionable event is an observable event on a completed candle. Merge near-duplicates now; prefer fewer, genuinely distinct candidates.

Return {"candidates": [ ... ]} where each candidate has exactly these keys:
- "name": a short descriptive snake_case name of the situation
- "context_definition": what price was doing before the situation
- "conditions_sequence": an ordered list of observable conditions that must hold, in order
- "presence_rule": when the situation counts as PRESENT, before it is actionable
- "trigger": the exact observable event, on a completed candle, that makes it actionable
- "direction": "up", "down" or "undetermined"
- "invalidation": the observable event that shows it has failed
- "information_required": a list of the chart elements needed to recognise it
- "supporting_ids": the ids of the descriptions it was derived from

Descriptions:
{DESCRIPTIONS}
```

**User (final consolidation call)** — same rules and keys, input = the chunk candidates (each with its
`supporting_ids`); the output `supporting_ids` must be the union of the merged candidates' ids.

Retry suffix (appended on a failed attempt): the validation problems, verbatim, followed by "Return the corrected JSON
object only."
