# S1 review and proposed revision (S1 only). PROPOSAL: nothing is coded, frozen or rescanned.

Scope: `bullish_breakout_from_right_edge_consolidation` only. S2–S9, the v1 freeze (`5199bd9a…`) and the v1 results stay as they are. No forward return,
MFE, MAE or baseline number was used to write this proposal (I had seen S1's aggregate forward means in the first report; they were near zero and are not used).

## 1. The AI definition (frozen, F1)

Context: price recovering/advancing, then paused in a small right-edge consolidation near a nearby resistance. Conditions: (1) a prior upward leg or rebound is in place;
(2) price forms a **small consolidation, pause, or pullback** near the right edge; (3) price approaches the **top of that local range or prior swing high**.
Presence: still inside the small consolidation/pullback, no close beyond the local resistance. Trigger: a close above the most recent **local swing high or consolidation high**.
Invalidation: close back below the pullback low, or back inside the range after the attempt.

## 2. The 12 cited charts, read against the definition (my subjective reading; disagree freely)

| Chart | What the chart shows | Fits S1's structure? | Why v1 said no (condition at T) |
|---|---|---|---|
| S0201 | leg up, ~12 tight candles at −1.0 %, then two strong closes above the range (the break was ~3 candles before T) | **yes** | A1 leg 0.113 < 0.189; A2 ZR 0.44 > 0.375 |
| S0036 | sharp rally, shallow stepped pullback, strong rebound closing above the pullback highs | **yes** (AI trigger: "above the prior pullback high") | A2 ZR 0.73; A3 DT 0.153 |
| S0120 | spike candle, then ~9 tight candles just under it | **yes** (pause under the spike high, trigger pending) | A2 ZR 0.62 (zone contains the spike); A3 DT 0.179 (spike wick) |
| S0159 | rebound, small base, breakout attempt at T | plausible | A1 leg 0.114 |
| S0535 | spike, 2 red pullback candles, last candle near the breakout area | plausible | A2 ZR 0.81 (zone contains the spike); A3 DT 0.276 |
| S0500 | spike, then one pullback candle | plausible | A2 ZR 0.91; A3 DT 0.143 |
| S0013, S0181, S0347, S0472 | stair-step or near-vertical run into the right edge, no real pause at the top | **no** (momentum run) | A2 fails (and the AI calls them breakouts from a consolidation) |
| S0163, S0176 | one huge reversal candle off a low, no prior up-leg | **no** (reversal) | A1 / A2 / A3 fail correctly |

Reading: roughly 3 clear + 3 plausible + 4 momentum runs + 2 reversal candles. A detector that recognised all 12 would have to drop the pause requirement, which is **not** S1.
So "recognise all 12" is not the target; "stop mistranslating the structure the definition does describe" is.

## 3. Which translations are wrong or too strict (and which are not)

1. **A dropped alternative (J-13 applied inconsistently).** The text says "small consolidation, pause, **or pullback**". v1 coded only compactness (`ZR ≤ q33`) and ignored the pullback branch.
   Evidence: 11/12 charts fail A2; 4 miss by A2 alone. Fix: literal OR with the existing quantities, `ZR ≤ q33(ZR)` **or** `RET ≤ q33(RET)` (shallow pullback, as already used for S5). No new threshold.
2. **The "local range top / swing high" level is contaminated by the leg.** v1 measures the pause over a fixed last-24-candle zone; when the leg's top or a spike is inside it, the zone high is the spike wick,
   so "near the top" is measured to a level price is not pausing under. Evidence: S0120, S0535, S0500. Fix: the resistance is the **pause's own high** (highest high since the leg's swing high, at most the last 24 candles),
   i.e. "top of that local range"; level = that high (or the swing high if price is already above the pause high). Because the quantity changes, its q33 is re-derived price-only on the discovery period (like DT_C5).
3. **"Prior upward leg" is defined as the last zig only.** v1's leg = latest confirmed swing low → swing high, which in choppy rises can be tiny relative to the window range (S0201 0.113, S0159 0.114) although price clearly rebounded.
   Fix: "a rebound is in place" = rise from the lowest low **before the swing high** within the window to the swing high, `UPnet = (hH − min low before jH)/R ≥ q33(UPnet)`; q33 re-derived price-only. The `jH` recency rule is unchanged.

Not changed: window 96, `K = 3` confirmed swings, "recent" = last 48, q33 meaning "small/near", presence-then-next-candle trigger, invalidation, no lockout, direction up.
Not coded (as before): "repeated tests", texture words.

## 4. Proposed S1 v2

* A1 `SH*` recent (`jH ≥ t−47`) and `UPnet > q33(UPnet)`.
* A2 `ZR ≤ q33(ZR)` **or** `RET ≤ q33(RET)`.
* A3 level `L` = highest high over `max(jH+1, t−23) … t` (the pause) — or, if `hH < c_t`, the same; presence needs `DT = (L − c_t)/R ≤ q33(DT_S1v2)`.
* Trigger: `c_{t'} > L_{t'−1}` with presence on `t'−1`. Invalidation (information): close `< PBL` (min low since `jH`) before the trigger frozen at the trigger, and after the trigger a close `≤ L`.
* New price-only derivations (discovery period, one run each): `UPnet`, `DT_S1v2` (same procedure as `derive_s5`).

## 5. How it will be judged (stated now, before any run)

* Not by forward returns and not by "all 12 recognised". The 12 charts are now design evidence, so recognising them is a consistency check, not validation.
* Reported: fires per period; what the v2 detector says on the 12 charts at T, T−1…T−6 (descriptive); 10 new v2 fires from the unseen period inspected against the definition; v1 vs v2 same-candle overlap.
* Failure to be reported honestly: if v2 fires on momentum runs or reversal candles that the definition excludes, that is a finding, not something to patch after the scan.

## 6. Process

You approve (or amend) §3–§4 → I implement S1 v2 in **new** files (v1 files are not touched, so the v1 freeze still verifies) with tests (prefix invariance, no look-ahead, independent explanation check) → you run the two price-only derivations →
I freeze v2 (new hash, S2–S9 byte-identical to v1) → you scan once into `results/brain_v2/`.
