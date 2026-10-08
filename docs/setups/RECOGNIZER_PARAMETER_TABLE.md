# Recognizer parameter table — DRAFT v2 (user decisions applied)

**Status: DRAFT. Not frozen (no F2). No recognizer code, no historical setup scan, no outcome, no AI call exists for this step.**

**Review decisions applied in v2.** J-1, J-2, J-3, J-4, J-6, J-7, J-8, J-10, J-11, J-12, J-13 approved. **J-5 NOT approved: C5 stays NOT CODEABLE** (not dead forever; a missing rule is not invented to save it, and the other seven do not depend on it). **J-9 stays flagged**: `c_t < c_{t−3}` is *our* numerical translation of "bearish candles push / pressure lower"; the frozen AI description does **not** say "three candles", and no report may present it as if it did (see the *Transparency* lines in C3 and C8). The 33/67 values are still **not** frozen: the derivation output is reviewed first (section 4).
It translates the eight setup definitions frozen in F1 (`docs/setups/SETUP_CANDIDATES.json`, file hash `2864bee7…`) into explicit
numeric rules on completed 15-minute candles. The English is not edited, merged, split or renamed; this document only decides what
it means mathematically, as the pre-registration (section 7) requires, and says where it **cannot** be decided objectively.

## 0. Rules this translation obeys

| # | Rule |
|---|---|
| P1 | **Translate, do not tighten.** A difficult definition is never made stricter to make it easier to code. |
| P2 | **No new trading logic.** Nothing is added that the frozen text does not say; nothing the text says is silently dropped. Every clause is coded, or listed in the judgment ledger (section 8) as *not coded* with the reason. |
| P3 | **No outcomes.** No return, excursion, win/loss or R value was used or is used to choose any rule or tolerance. Numbers are derived from discovery-period **price** statistics only, by a procedure fixed here (section 4), then frozen. |
| P4 | **One uniform convention** for all eight candidates (section 2). No per-candidate tuning. |
| P5 | **Causality.** Every quantity at decision candle *t* uses completed candles ≤ *t* only. A structure that needs later candles to be confirmed is stamped at its confirmation candle. |
| P6 | **NOT CODEABLE is a valid, expected verdict** when a term has no objective referent. It is reported and never repaired. |
| P7 | **Fixed before values exist.** This table fixes the *definitions and the derivation rule*. The threshold *values* are computed once by the derivation procedure (section 4) after you approve this text, and are frozen with the recognizer at F2. |

## 1. What stays invariant across every candidate

* Evidence base: the 96-candle window the model saw (chart ending at the decision candle), measured in units of its own range.
* Direction is as frozen (`up` / `down`); no candidate is `undetermined`.
* Every trigger is a **completed-candle close** beyond a level. An intrabar touch is never a trigger.
* **Presence and trigger are different timestamps** (pre-registration section 3).
* Overlapping candidates stay separate. Their overlap is measured (section 7), never merged.

## 2. Common conventions (apply to all candidates)

**G1 Window and zones** (decision candle *t*; requires 96 gap-free completed candles, otherwise not evaluated)
* `W` = candles *t*−95 … *t* (the chart). `R` = max high − min low over `W` (`R = 0` → not evaluated). All distances are in `R` units.
* `E` (right edge) = last 24 candles *t*−23 … *t*. `P` (prior) = *t*−95 … *t*−24 (the same 24/72 split as the sampler's range-expansion feature).
* "Recent" = within the last 48 candles *t*−47 … *t*. "Prior" / "context" = earlier than the structure it precedes.
* `ZoneHigh` = max high over `E`; `ZoneLow` = min low over `E`; `pos_E(x) = (x − ZoneLow)/(ZoneHigh − ZoneLow)`.
  "Upper part of the range" ≡ `pos_E ≥ 2/3`; "lower part" ≡ `pos_E ≤ 1/3`. `c_t` = close of candle *t*.

**G2 Confirmed swing points (causal).** With `K = 3`: a swing high at candle *j* needs `high_j ≥` the highs of the 3 candles before and `> ` the highs of the 3 after; a swing low is symmetric (`≤` before, `<` after). It is **known only at candle *j*+3** and may not be used earlier. `SH*` = (index `jH`, price `hH`) = the most recent confirmed swing high in `W`; `SL*` = (`jL`, `lL`) the most recent confirmed swing low. `lB` = low of the latest confirmed swing low with index `< jH` (start of the up-leg ending at `SH*`); `hB` = high of the latest confirmed swing high with index `< jL` (start of the down-leg ending at `SL*`).

**G3 Magnitude words → three bands.** Every measured quantity `m` (section 3) has two thresholds `q33(m)`, `q67(m)` = its 33rd and 67th percentile over the discovery period (section 4).
| Word in the frozen text | Rule |
|---|---|
| small, tight, shallow, slight, near, close, compressing | `m ≤ q33(m)` |
| sharp, strong, impulsive, large, steep | `m ≥ q67(m)` |
| unqualified existence of a leg, rebound, pullback, retracement ("a prior upward leg", "retrace part", "rebound visible") | `m > q33(m)` (i.e. not small) |

**G4 Timestamps and the presence → trigger machine.**
* `Presence_t` = the conjunction of the candidate's presence conditions evaluated at *t* (all conditions use data ≤ *t*).
* **Trigger** happens at the first candle *t′* such that `Presence_{t′−1}` is true **and** `c_{t′}` is beyond `Level_{t′−1}` (above for `up`, below for `down`). `Level` is candidate-specific and is computed from data ≤ *t′*−1 only.
* `presence_ts` = close time of the first candle of the unbroken run of `Presence` that ends at *t′*−1 (the run length is recorded); `trigger_ts` = close time of *t′*; `signal_ts = trigger_ts`.
* **Invalidation** (candidate-specific): the level is frozen at the trigger from data ≤ *t′*−1; `invalidation_ts` = close time of the first later completed candle whose close breaches it. A breach before the trigger ends nothing (presence is simply re-evaluated each candle).
* Occurrence de-duplication: the lockout of the pre-registration (until the later of the invalidation and 24 candles after the trigger).

**G5 Chart-axis artifacts are not market concepts.** The chart's price axis is "% versus the close at T", so "the zero line", "0.00%" and "flat" mean *the close at the decision candle* by construction, which is always where price is. They cannot define a condition. They are **not coded** (ledger J-3). Where the frozen *presence rule* (the operative definition) does not contain them, nothing is lost.

**G6 Level named by the presence rule.** Where the text offers several words for a level ("support, pullback low, range floor"), the **operative level is the one the candidate's own presence rule names**; the others are recorded as synonyms or as *not coded* (ledger J-4). No automatic min/max across alternatives is introduced.

**G7 Sensitivity variants (pre-declared; all reported; none ever selected).** Primary: bands 33/67, `K = 3`. Variants: bands 25/75 and 40/60; `K = 2` and `K = 5`. They are reported next to the primary result and play no role in any gate.

**G8 No loosening, no tuning.** The frequency rule of the pre-registration (a recognizer that triggers on < 0.2 % or > 10 % of discovery candles is NOT SELECTIVE / NOT CODEABLE) is applied to the primary parameterization. If a candidate fails it, thresholds are **not** loosened to rescue it.

## 3. Measured quantities

All are functions of the window at *t*, in `R` units unless stated. Percentiles are over discovery positions where the quantity is defined.

| id | definition | defined when |
|---|---|---|
| `ZR` | (ZoneHigh − ZoneLow) / R — width of the right-edge zone | always |
| `EFF` | \|c_t − c_{t−23}\| / Σ_{k=t−22..t} \|c_k − c_{k−1}\| — 0 if the sum is 0; low = sideways/choppy | always |
| `UP` | (hH − lB) / R — the up-leg ending at the latest swing high | `SH*`, `lB` exist |
| `DN` | (hB − lL) / R — the down-leg ending at the latest swing low | `SL*`, `hB` exist |
| `PBL` | min low over [jH … t] — the pullback low since the latest swing high | `SH*` exists |
| `RET` | (hH − PBL) / (hH − lB) — retracement fraction of the up-leg | `UP` defined |
| `RH` | max high over [jL … t] — the rebound high since the latest swing low | `SL*` exists |
| `REB` | (RH − lL) / R — rebound size | `SL*` exists |
| `DT(L)` | (L − c_t) / R for a level `L ≥ c_t` — distance below a resistance | level defined |
| `DF(L)` | (c_t − L) / R for a level `L ≤ c_t` — distance above a support | level defined |

`DT` / `DF` have one percentile pair **per candidate level** (the level differs by candidate), named `DT_C1`, `DF_C3`, … below.

## 4. How the numbers are derived (once, price-only, then frozen)

1. A small deterministic script (`src/setups/derive_params.py`; it contains no outcome, forward-return or future-price code) computes every quantity of section 3 at every discovery position *t* (open time < 2026-06-01) that has 96 gap-free candles. The run reported 26,113 positions (26,208 candles before the cutoff), the same count as the sampler's; my earlier expectation that this script's count would be larger was wrong. Each position is computed from its own 96-candle window only (a function that receives nothing else). `DT_Cn` / `DF_Cn` are measured where their level exists: C1 `Res1` (needs `SH*`); C2 `RH` (needs `SL*`); C3 `ZoneLow`; C4 `LL*` (D1 holds, `LL*` exists, `c_t ≥ LL*`); C6 `PBL` (needs `SH*`); C7 `ZoneHigh`; C8 `lL` (needs `SL*`, `c_t ≥ lL`). C5 is excluded. `UP` is defined only when `hH > lB`, `DN` only when `hB > lL`. It does not look for setups, trigger anything or read any hold-out candle.
2. Output: for each quantity (and `DT_Cn` / `DF_Cn`) the 25th, 33rd, 40th, 60th, 67th and 75th percentiles, and the number of positions defined. These tables are hashed into the F2 record. The primary run uses 33/67; the others serve the pre-declared variants.
3. The script runs once. The hold-out never contributes to any threshold and is not refitted.
4. The disclosed limitation (as for the sampler's terciles): the thresholds use the whole discovery period of **price** data, not an expanding window. They contain no outcome information.

## 5. The eight candidates

Common to every candidate below: a window of 96 gap-free candles; `R > 0`; evaluation at each completed candle *t*; the trigger is the **very next** completed candle that closes beyond the level while the setup was present on the previous candle.

### C1 `bullish_breakout_from_right_edge_consolidation` (up, 20 supporting descriptions)
Frozen idea: after an upward leg, a small consolidation near the right edge approaches the top of its range or the prior swing high; it becomes actionable on a close above it.

| | Rule |
|---|---|
| Conditions | **A1** `SH*` recent (`jH ≥ t−47`), `UP > q33(UP)` ("a prior upward leg … in place"). **A2** `ZR ≤ q33(ZR)` ("small consolidation, pause or pullback near the right edge"). **A3** with `Res1 = ZoneHigh` if `hH` is not in `E` or `hH < c_t`, else `min(ZoneHigh, hH)`: `DT(Res1) ≤ q33(DT_C1)` ("approaches the top of that local range or prior swing high"). |
| Presence | A1 ∧ A2 ∧ A3 (and `c_t ≤ Res1` holds by construction: not yet beyond the resistance). |
| Trigger | first *t′* with `Presence_{t′−1}` and `c_{t′} > Res1_{t′−1}`. |
| Invalidation | the first of **(a)** close `< PBL` (the pullback low, frozen at the trigger) and **(b)** after the trigger, a close `≤ Res1` (back inside the prior range after the breakout attempt). |
| Invariant | an up-leg precedes; the right edge is a compression; price is at the top of the compression; the break is a completed close above the resistance. |
| Allowed variation | leg size anywhere above the "small" band; compression anywhere inside the "small" band (≤ q33 of the zone width); distance to the top anywhere inside the "near" band; duration of the presence run unrestricted. |
| Forbidden variation | no preceding up-leg (that is a different concept); a wide, trending zone (not a consolidation); price far below the resistance; a trigger by an intrabar poke. |
| Numeric tolerance | `UP > q33`, `ZR ≤ q33`, `DT_C1 ≤ q33`. |
| Not coded (ledger) | J-4: the choice between the swing high and the consolidation high is made by the min rule above (the earliest-reached level, the literal "or"). |
| **Verdict** | **CODEABLE** |

### C2 `bullish_rebound_breakout_after_drop` (up, 22)
Frozen idea: a sharp decline, a base/rebound above the low, price pressing into the rebound high; actionable on a close above it.

| | Rule |
|---|---|
| Conditions | **B1** `SL*` recent (`jL ≥ t−47`), `DN ≥ q67(DN)` ("sharp decline … swing low"). **B2** `c_t > lL` and `REB > q33(REB)` ("base, bounce or recovery forms above that low"; "rebound is visible"). **B3** `Res2 = RH`; `DT(Res2) ≤ q33(DT_C2)` ("pressing into the rebound high or local resistance"). |
| Presence | B1 ∧ B2 ∧ B3. |
| Trigger | `c_{t′} > RH_{t′−1}` after `Presence_{t′−1}`. |
| Invalidation | the first close `< lL` ("a new lower low below … the selloff trough"). |
| Invariant | a sharp down-leg into a swing low; a rebound above that low; price at the rebound high. |
| Allowed variation | decline size ≥ the "large" band; rebound size above the "small" band; proximity inside the "near" band. |
| Forbidden variation | a mild decline; no rebound; price far below the rebound high; a close below the low (that is invalidation). |
| Numeric tolerance | `DN ≥ q67`, `REB > q33`, `DT_C2 ≤ q33`. |
| Not coded (ledger) | J-3: "or the zero line" in condition 3 (and "nearby_zero_line" in the information list) is a chart-axis artifact; the presence rule, which is the operative definition, does not contain it. J-10: "small" in "small base/bounce" has no stated reference size. J-4: "recent rebound base" as an alternative invalidation level is not separately defined; only the trough `lL` is coded (this makes invalidation later, not earlier). |
| **Verdict** | **CODEABLE** (with J-3, J-4, J-10) |

### C3 `bearish_breakdown_from_right_edge_range` (down, 21)
Frozen idea: a sideways/choppy range at the right edge rolls over from its upper part and presses into its lower part; actionable on a close below the range floor.

| | Rule |
|---|---|
| Conditions | **C3a** `EFF ≤ q33(EFF)` ("sideways or choppy range"). **C3b** `SH*` in `E` with `pos_E(hH) ≥ 2/3` ("turns down from the upper part … or a local rebound high"). **C3c** `pos_E(c_t) ≤ 1/3` and `c_t < c_{t−3}` ("bearish candles push into the lower part of the range"). **C3d** `DF(ZoneLow) ≤ q33(DF_C3)` ("pressing against the lower edge"). |
| Presence | C3a ∧ C3b ∧ C3c ∧ C3d. |
| Trigger | `c_{t′} < ZoneLow_{t′−1}` after `Presence_{t′−1}`. |
| Invalidation | the first close `> hH` ("recent local highs"). |
| Invariant | a range; a roll-over from its upper part; price in its lower part; a close below the floor. |
| Allowed variation | any efficiency inside the "small" band; roll-over high anywhere in the upper third; distance to the floor inside the "near" band. |
| Forbidden variation | a trending (high-efficiency) zone; price still in the middle/upper range; a floor break that has already happened. |
| Numeric tolerance | `EFF ≤ q33`, `pos_E ≥ 2/3` (high) and `≤ 1/3` (close), `DF_C3 ≤ q33`. |
| Not coded (ledger) | J-4: "local support, pullback low, range floor" are treated as one level, the range floor `ZoneLow` (named by the presence rule: "lower edge of the local range"). J-9: "bearish candles push" := `c_t < c_{t−3}`. |
| Transparency (J-9) | `c_t < c_{t−3}` is **our translation**, a judgment choice. The frozen AI description says only that bearish candles push into the lower part; it specifies no number of candles. Reports must say so. |
| **Verdict** | **CODEABLE** |

### C4 `bearish_continuation_below_broken_support` (down, 16)
Frozen idea: a support is already broken; price stays below it, makes lower highs/lows, and a close below the latest minor low continues the move.

| | Rule |
|---|---|
| Conditions | **D1** a confirmed swing low `(jS, lS)` in `W` and a candle `b > jS` with `c_b < lS`; of all such broken swing lows take the one with the most recent first break `b` (ties: the higher `lS`) ("a prior support area or range floor is broken"). **D2** `c_t < lS` ("remains below that broken level"). **D3** after `b`: at least two confirmed swing highs with the latest lower than the previous (lower high) **or** at least two confirmed swing lows with the latest lower than the previous (lower low). **D4** `LL* =` the most recent confirmed swing low with index `> b`; `c_t ≥ LL*` and `DF(LL*) ≤ q33(DF_C4)` ("another push through the latest minor low"). |
| Presence | D1 ∧ D2 ∧ D3 ∧ D4. |
| Trigger | `c_{t′} < LL*_{t′−1}`. |
| Invalidation | the first close `> min(lS, hLH)`, where `hLH` = high of the most recent confirmed swing high with index `> b` (`lS` if none). |
| Invariant | an earlier broken swing low; price below it; a descending structure after the break; price near its latest low. |
| Allowed variation | which swing low was broken; lower highs *or* lower lows; any distance inside the "near" band. |
| Forbidden variation | support not yet broken; price back above the broken level; no descending structure (a single pivot); a continuation close already printed. |
| Numeric tolerance | `DF_C4 ≤ q33` (the structure itself is categorical). |
| Not coded (ledger) | J-4: "support shelf" and "pullback low" as alternative trigger levels have no separate objective definition beyond a swing low; only the latest swing low is coded. |
| **Verdict** | **CODEABLE — FLAGGED**: depends on pivot chains (needs ≥ 2 pivots after the break); the frequency gate may remove it. |

### C5 `bullish_continuation_after_spike_and_pullback` (up, 17)
Frozen idea: an impulsive rally to a spike high; a shallow pullback or tight consolidation that holds above the *prior breakout zone*; actionable on a close above the spike high.

| | Rule |
|---|---|
| Conditions | **E1** `SH*` recent, `UP ≥ q67(UP)` ("sharp upward impulse creates a spike high"). **E2** `RET ≤ q33(RET)` **or** `ZR ≤ q33(ZR)`, and no high above `hH` since `jH` ("shallow pullback or tight consolidation just below that high"). **E3** "**holds above the prior breakout zone**": *see below*. **E4** `DT(hH) ≤ q33(DT_C5)` ("compressing near the high"). |
| Presence | E1 ∧ E2 ∧ E3 ∧ E4. |
| Trigger | `c_{t′} > hH_{t′−1}`. |
| Invalidation | close below the operative base: the "breakout base, pullback low or prior consolidation top". |
| The problem | "Prior breakout zone", "breakout base" and "prior consolidation top" (condition 3, presence rule, invalidation) have **no objective referent** in the frozen text: which earlier structure the impulse "broke out" of is a subjective choice. |
| Proposed J-5 (**DECLINED by the reviewer**) | `B5` = the high of the latest confirmed swing high before the up-leg's start low `lB`. This was an interpretation, not something the frozen text forces, so it is **not adopted** and nothing downstream may use it. Kept here only as a record of what was proposed and refused. |
| Invariant | an impulsive rally; a shallow/tight hold below the spike high; price held above the structure the impulse started from; a close above the spike high. |
| Allowed variation | pullback depth or consolidation width inside the "small" band; proximity inside the "near" band. |
| Forbidden variation | a mild rally; a pullback that breaks the base; a new high already printed. |
| Numeric tolerance | `UP ≥ q67`, `RET ≤ q33` or `ZR ≤ q33`, `DT_C5 ≤ q33`. |
| **Verdict** | **NOT CODEABLE** (decision recorded). "Prior breakout zone" has no objective referent. Dropping E3 is not allowed: it would make the recognizer looser than the frozen definition (P1/P2). C5 is excluded from derivation, recognition and every later gate; it can be revisited only by a new, explicit, separately recorded decision. |

### C6 `bearish_rejection_from_recent_high` (down, 18)
Frozen idea: price reaches a recent high/upper range, fails to continue, retraces part of the prior rise; actionable on a close below the pullback low.

| | Rule |
|---|---|
| Conditions | **F1** `SH*` recent (`jH ≥ t−47`) with `(hH − min low over W)/R ≥ 2/3` ("recent high or upper range"). **F2** no close above `hH` since `jH` ("failed to continue higher"); `c_t < hH`. **F3** `UP > q33(UP)` and `RET > q33(RET)` ("retrace part of the prior rise"). **F4** `DF(PBL) ≤ q33(DF_C6)` ("toward nearby support"). |
| Presence | F1 ∧ F2 ∧ F3 ∧ F4. |
| Trigger | `c_{t′} < PBL_{t′−1}`. |
| Invalidation | the first close `> hH` ("above the recent high or reclaim area of the rejected top"). |
| Invariant | a high in the upper part of the window; no continuation above it; a partial retracement of the prior rise; price near the pullback low. |
| Allowed variation | retracement above the "small" band; proximity inside the "near" band; the high anywhere in the top third of the window. |
| Forbidden variation | a high in the lower/middle window; a close above the high; no retracement; the pullback low already broken. |
| Numeric tolerance | `RET > q33`, `DF_C6 ≤ q33`, high at ≥ 2/3 of the window range. |
| Not coded (ledger) | J-3: "or the zero line". J-4: "nearest short-term support", "pullback low", "consolidation floor" are one level, the pullback low `PBL` (named by "retrace … toward nearby support"). J-10: "rejection" has no separate candle-shape rule beyond F2–F3. |
| **Verdict** | **CODEABLE** (with J-3, J-4, J-10) |

### C7 `bullish_breakout_from_right_edge_range` (up, 47)
Frozen idea: after a decline, a rebound and/or consolidation at the right edge tests the local high area; actionable on a close above the ceiling.

| | Rule |
|---|---|
| Conditions | **H1** `DN > q33(DN)` ("sold off or drifted lower … after a decline or pullback"). **H2** `REB > q33(REB)` **or** `ZR ≤ q33(ZR)` ("a rebound and/or consolidation"). **H3** `Res7 = ZoneHigh`; `DT(Res7) ≤ q33(DT_C7)` ("pushing back toward nearby highs … testing the local high area"). |
| Presence | H1 ∧ H2 ∧ H3. |
| Trigger | `c_{t′} > ZoneHigh_{t′−1}`. |
| Invalidation | the first of **(a)** close `< ZoneLow` (frozen at the trigger; "recent pullback low") and **(b)** after the trigger, a close `≤ ZoneHigh` (back into the prior range). |
| Invariant | a prior decline; a rebound or consolidation after it; price at the ceiling; a completed close above it. |
| Allowed variation | decline above the "small" band; rebound **or** consolidation (either is enough); proximity inside the "near" band. |
| Forbidden variation | no prior decline (that is C1's context); price far below the ceiling; an intrabar poke. |
| Numeric tolerance | `DN > q33`, `REB > q33` or `ZR ≤ q33`, `DT_C7 ≤ q33`. |
| Not coded (ledger) | J-3: "near flat or the 0.00% area" in the context and "0.00% reference" in the information list. J-10: "small pullback or hesitation candles" is texture with no stated rule. |
| **Verdict** | **CODEABLE** (with J-3, J-10). It is the broadest candidate (47 supporting descriptions) and the most likely to overlap C1 and C2. |

### C8 `bearish_breakdown_from_right_edge_support` (down, 15 — the minimum)
Frozen idea: after a rise or bounce, price rolls over from a local high / lower-high structure and presses into a visible support; actionable on a close below it.

| | Rule |
|---|---|
| Conditions | **I1** prior rise or bounce: `UP > q33(UP)` **or** `REB > q33(REB)`. **I2** right-edge structure: a lower-high sequence (the latest two confirmed swing highs in `W`, the latest lower) **or** `EFF ≤ q33(EFF)` **or** `REB > q33(REB)` ("rebound, lower-high sequence, or choppy consolidation"). **I3** `SL*` recent (`jL ≥ t−47`), `c_t ≥ lL`, `DF(lL) ≤ q33(DF_C8)` and `c_t < c_{t−3}` ("pressure lower into that support"). **I4** `SH*` recent with `c_t < hH` ("rolling over from a local high"). |
| Presence | I1 ∧ I2 ∧ I3 ∧ I4. |
| Trigger | `c_{t′} < lL_{t′−1}`. |
| Invalidation | the first of **(a)** close `> hH` and **(b)** after the trigger, a close `≥ lL` (recovers into the broken range). |
| Invariant | a prior rise/bounce; a roll-over from a recent high; a visible swing-low support; price pressing into it; a completed close below it. |
| Allowed variation | which of the I1/I2 alternatives holds; proximity inside the "near" band. |
| Forbidden variation | no recent swing low; price already below it; price far above it; a continuing uptrend with no roll-over. |
| Numeric tolerance | `UP`/`REB` `> q33`, `EFF ≤ q33`, `DF_C8 ≤ q33`. |
| Transparency (J-9) | The "pressure lower" clause `c_t < c_{t−3}` is **our translation** (J-9), not a number in the frozen description. Reports must say so. |
| Not coded (ledger) | J-3: "0.00% or nearby reference". J-4: "support floor or recent swing low" is one level, the swing low `lL`. J-13: the OR-chain in I1/I2 makes I2 weak (`REB > q33` alone satisfies it); it is coded literally and **not** tightened (P1). |
| **Verdict** | **CODEABLE — FLAGGED**: a literal translation of two OR-chains is permissive and will overlap C3; fidelity and the overlap diagnostics decide. |

## 6. Verdict summary

| # | Candidate | Verdict |
|---|---|---|
| C1 | bullish_breakout_from_right_edge_consolidation | CODEABLE |
| C2 | bullish_rebound_breakout_after_drop | CODEABLE (J-3, J-4, J-10) |
| C3 | bearish_breakdown_from_right_edge_range | CODEABLE |
| C4 | bearish_continuation_below_broken_support | CODEABLE — FLAGGED (needs ≥ 2 pivots; may be rare) |
| C5 | bullish_continuation_after_spike_and_pullback | **NOT CODEABLE** (J-5 declined; excluded from all later steps) |
| C6 | bearish_rejection_from_recent_high | CODEABLE (J-3, J-4, J-10) |
| C7 | bullish_breakout_from_right_edge_range | CODEABLE (J-3, J-10) |
| C8 | bearish_breakdown_from_right_edge_support | CODEABLE — FLAGGED (permissive OR-chain) |

"CODEABLE" here means *translatable*. It does not mean the recognizer will pass the later gates: the **fidelity audit** (precision ≥ 70 %, recall ≥ 50 %, ≥ 10 cases each), the **frequency bounds** (0.2 %–10 % of discovery candles) and the occurrence minimum (≥ 100) can still classify any of them NOT CODEABLE FAITHFULLY / NOT SELECTIVE. With conjunctions of several "small / near" conditions, a low trigger frequency is a real risk; if a candidate falls below 0.2 % it is reported, not loosened (G8).

## 7. Overlap diagnostics (planned, outcome-blind)

For every pair of candidates: the number of candles on which both `Presence` conditions hold, the number of identical trigger candles, and the Jaccard index of trigger sets (and of presence sets). Pairs expected to overlap: C1/C7, C3/C8, C4/C8, C2/C7. These are reported before any outcome is computed. Overlapping candidates are **not** merged, split, renamed or dropped because of overlap (F1 and the pre-registration).

## 8. Judgment ledger — the choices I made that the frozen English does not force

Each is made on structural grounds only. Any you reject must be replaced by an alternative you specify, or the candidate that depends on it becomes NOT CODEABLE.

| id | Choice | Alternative | Affects |
|---|---|---|---|
| J-1 | The bands are the 33rd/67th percentiles of each measure's own discovery distribution (the same terciles the sampler used) | quartiles or 40/60 (reported as variants) | all |
| J-2 | An unqualified leg/rebound/retracement means "not small" (`> q33`) | any positive size | C1, C6, C7, C8 |
| J-3 | "zero line", "0.00%", "flat" are chart-axis artifacts and are not coded | code them as "price at the decision close" (always true) — this would add nothing | C2, C6, C7, C8 |
| J-4 | The operative level is the one named by the presence rule; synonyms are one level; objectively undefined alternatives (support shelf, base low, consolidation top) are not coded | "earliest-reached of all alternatives" (min/max rule) | all |
| J-5 | **DECLINED.** (Proposed: `B5` = high of the latest confirmed swing high before the up-leg's start low.) C5 is NOT CODEABLE | — | C5 |
| J-6 | `K = 3` candles for swing confirmation (variants 2 and 5) | other K | C1–C8 |
| J-7 | "Right edge" = last 24 candles; "recent" = last 48; the 24/72 split mirrors the sampler | other windows | C1–C8 |
| J-8 | "Upper/lower part of the range" = top/bottom third | other fractions | C3 |
| J-9 | **Flagged, approved with transparency.** "Bearish candles push / pressure lower" := `c_t < c_{t−3}`. Our numerical translation; the AI text specifies no candle count | any candle-colour count | C3, C8 |
| J-10 | Texture words with no stated rule are not coded: "small base/bounce", "hesitation candles", "rejection" beyond the retracement | add a rule (this would be new logic) | C2, C6, C7 |
| J-11 | The trigger is the very next candle that closes beyond the level while presence held on the previous candle | wait several candles | C1–C8 |
| J-12 | Distances use the 96-candle range at the decision candle | another normaliser | C1–C8 |
| J-13 | OR-chains are coded literally and permissively (C8 I1/I2) | require one specific alternative | C8 |

## 9. Planned tests (to be written with the recognizer; none exists yet)

For **each** candidate, on constructed series (no market data):
1. **Positive case:** a synthetic window built to satisfy every condition at stated geometry; assert presence at the intended candle, trigger exactly at the next closing candle beyond the level, `presence_ts < trigger_ts`, and the invalidation timestamp when a later close breaches the level.
2. **Negative cases:** the same series with **one** condition broken at a time (each yields no presence); price touching but not **closing** beyond the level (no trigger); a close beyond the level two candles after presence (trigger only if presence still held on the previous candle).
3. **Prefix invariance:** the recognizer's output at candle *t* is identical when every later candle is removed, or replaced by noise, or multiplied by a constant. Verified at every *t* of a long random series.
4. **Causality guard:** the series is wrapped so that reading any row after *t* raises an error; pivots are never used before `j + K`; a pivot candidate with fewer than `K` candles after it does not exist at *t*.
5. **Determinism:** two runs on the same data give byte-identical occurrence lists; a window with a gap, `R = 0`, ties at pivot highs/lows, and NaN are handled by "not evaluated".
6. **Firewall:** the recognizer module imports no outcome, forward-return or evaluation code (extending the existing import-firewall test).
7. **Derivation script:** a test that it reads only candles ≤ the cutoff and ≤ the position, that hold-out candles change nothing, and that no outcome field is accessible.

## 10. What this document is not

No recognizer code, no scan of any series, no frequency or outcome number, no AI call, no F2 record. After your review: (1) edits to this text; (2) the derivation script and its one run; (3) the recognizer and its tests; (4) the fidelity audit and frequency check; (5) F2. No candidate definition (F1) changes at any step.
