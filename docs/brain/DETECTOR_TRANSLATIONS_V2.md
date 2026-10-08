# Setup Brain v2 - detector translations (S1 replaced; S2-S9 unchanged)

v1 (`docs/brain/DETECTOR_TRANSLATIONS.md`, freeze `docs/brain/BRAIN_FREEZE.json`) stays valid and untouched. v2 changes **S1 only**, as approved translation corrections (not performance
optimization); see `docs/brain/S1_REVIEW_AND_PROPOSAL.md` for the evidence (the 12 cited charts) and the criteria for judging it.

## S1 v2 `bullish_breakout_from_right_edge_consolidation`

Window `W` = 96 completed candles ending at `t`; `R` = its range; confirmed swings with `K = 3` (known at `j+3`); `SH*` = latest confirmed swing high (`jH`, `hH`).

* **A1 (J-19, net up-leg):** `SH*` is recent (`jH ≥ t−47`) and `UPnet = (hH − min low before jH in W)/R > q33(UPnet)`.
* **A2 (J-17, literal OR):** `ZR ≤ q33(ZR)` (last 24 candles compact) **or** `RET ≤ q33(RET)` (shallow pullback; `RET` as in v1). If `RET` is undefined that branch is false.
* **A3 (J-18, the pause's own high):** `L` = highest high from `max(jH+1, t−23)` to `t`; `DT = (L − c_t)/R ≤ q33(DT_S1v2)`.
* **Presence** = A1 ∧ A2 ∧ A3. **Trigger:** `c_{t'} > L_{t'−1}` with presence on `t'−1`. **Invalidation (information):** the first later close `< PBL` (min low since `jH`) or `≤ L` (both frozen at the trigger).
* `q33(UPnet)` and `q33(DT_S1v2)` are derived price-only on the discovery period by `src/brain/derive_s1v2.py` (`results/brain_v2/derived_s1v2.json`); `q33(ZR)`, `q33(RET)` are the existing derived values.
* Not changed from v1: window, `K`, "recent", the meaning of q33 as "small/near", presence-then-next-candle trigger, no lockout. Not coded: "repeated tests", texture words.

## S2-S9

Exactly the v1 functions (`src/brain/detectors.py`, `src/setups/recognizer.py`, S5/S9 translations in `DETECTOR_TRANSLATIONS.md`). The v2 scan must reproduce the v1 fires of S2-S9 exactly; any difference aborts the run.
