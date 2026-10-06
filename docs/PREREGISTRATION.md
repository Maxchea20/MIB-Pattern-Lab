# Pre-registration — MIB Pattern Lab (1h BTC/USDT)

**Version: v2 DRAFT.** Supersedes the earlier "outcome test plan v1" (see git history).
**Status: no forward-return / outcome data has been examined.** Only chart shapes, AI tags and window-only geometry
(`src/discovery/audit.py`) have been looked at. This document must be approved (and the OPEN ITEMS in section 12
answered) before any outcome is computed. After the first outcome is computed, nothing here may change.

The scientific question: **do recurring visual shapes in clean price history contain information about subsequent
price movement?** This is not a trading-rule project. No interpretation of shapes, no technical-analysis renaming,
no entry/exit/TP/SL logic is part of this experiment.

## 1. Data split (fixed)
| timeframe | discovery period | hold-out (locked) |
|---|---|---|
| 1h (the only timeframe tested here) | 2020-06-05 up to 2024-06-01 (exclusive) | 2024-06-01 onward |

* Enforced in code: `config.discovery_end(tf)` -> `discover.discovery_candles()` removes later candles before any
  window is built; sampling asserts every window ends before the cutoff.
* The hold-out is tagged and evaluated **once**, at the end (section 9). No tuning after seeing it.
* The first 1h pilot (`tagset_v1_1h`, 100 windows, ~20 after 2024-06-01) is not reused. Only tags were looked at.

## 2. Frozen tagging setup (unchanged; also used, unchanged, for the hold-out)
* Model `gpt-5.4-mini`; prompt `retag-v1`; vocabulary `vocab-v1`.
  * vocab sha256 `3eab422efbf6279fa7efe991230c7b493699e35c8bff3e7b89d649b439805d54`
  * system prompt sha256 `5ac0b75fd36689bd3994c3a35bdc195e858fd41b27ee423a0fe9cf15d2c93690`
  * user prompt (pass 1) sha256 `4b478c2d878a98a1259a834b6b7482b42d9a4f04f8f4f8e38633d35b111a40cb`
  * user prompt (pass 2, vocabulary reversed) sha256 `7e6d3f8d72fdd94fc8d549ea9f1eacd13fd0ee2dbe2aa9c9fb8030c9005715d9`
* Two passes; a window's **stable tags** = tags present in BOTH passes. Invalid tags are errors, never repaired.
* Charts: 60 closed 1h candles ending at T; fixed vertical span (computed once from the discovery period, **25.2%**,
  then frozen and reused unchanged for the hold-out); axes anonymised (% vs close at T, T-50..T).
* **No outcome information is available during tagging**: the model sees only the PNG and the fixed prompt, and the
  tagging code cannot import the outcome module (test-enforced).

## 3. Discovery sample (option C: fill the remaining capacity)
* Start: 431 non-overlapping windows (`tagset_v1_1h_cut20240601`, stratified by window range).
* Top-up: `python -m src.discovery.tagset --timeframe 1h --topup 999` adds the remaining non-overlapping
  discovery-period windows (target ~580 total), same chart style (hash-checked), same frozen tagging setup. Windows
  never overlap each other or the originals and never touch hold-out data.
* The final `windows.jsonl` sha256 is recorded in the analysis output; the discovery sample is **frozen** when
  tagging finishes and the hash is recorded.
* The sample is stratified by window range (a feature of the chart itself, not an outcome). Baselines and nulls are
  computed on this same sample, and range is a control covariate (section 6).

## 4. Outcome measures (only `src/outcomes/` may read candles after T)
Entry reference = **close of T**. For each window and each horizon H in {1, 3, 6, 12, 24} one-hour candles (hours):
* `ret_H` = 100 * (close[T+H] / close[T] - 1)
* `fut_high_H` = max(high[T+1..T+H]);  `fut_low_H` = min(low[T+1..T+H])  (prices)
* `MFE_H` = 100 * (fut_high_H / close[T] - 1)   (max favorable excursion, >= 0 on the long side by construction)
* `MAE_H` = 100 * (fut_low_H / close[T] - 1)    (max adverse excursion, <= 0)
No TP/SL, no costs in these measures. Signs are not flipped for any family (no assumed direction).

Exclusions (counted and reported): the 24 candles after T must exist, be gap-free and be **before the cutoff**
(a discovery window whose forward path reaches into the hold-out period is excluded, so no hold-out data influences
discovery outcomes).

## 5. Families
**Primary (confirmatory) families:**
| family | definition (stable tags) |
|---|---|
| sideways_range | `sideways_range` |
| drift_up | `drift_up` |
| drift_down | `drift_down` |
| impulse_up | **see OPEN ITEM 1** |

**Exploratory families (reported separately, descriptive, no claims, no multiplicity budget):**
`stair_step_up`, `sharp_rally`, `range_breakout_up` (kept **separate**, not merged), plus `sharp_drop`, `rounded_top`,
`rounded_bottom`, `terminal_spike_up`, `terminal_spike_down`, `choppy_volatile`, `tight_compression`, `v_reversal`,
`spike_and_retrace`. Never observed in discovery (dropped): `stair_step_down`, `inverted_v`, `range_breakdown`, `none`.
A window may belong to several families. Windows with no stable tag stay in the non-family population.
A family is analysed only if it has >= 30 windows with valid outcomes (otherwise reported as "too few").

## 6. Statistics (reported for every family and every horizon)
For each family vs. the **non-family population** (all other discovery windows):
* N; mean and median `ret_H`; win % (`ret_H` > 0); mean and median MFE_H and MAE_H;
* effect size: mean difference (percentage points) and Cohen's d;
* 95% confidence interval for the mean difference (bootstrap, 10,000 resamples, fixed seed 20240601);
* unadjusted significance: Welch t-test p-value and permutation p-value;
* control regression (supplementary): `ret_H ~ net_pct + range_pct + eff + family_dummy`, HC3 robust errors, where
  net_pct/range_pct/eff are window-only features (`audit.py`). It tests whether the family adds information
  **beyond simple measurable features**.

## 7. Null / permutation test
* Fixed seed 12345, **10,000 permutations**. Each permutation shuffles the outcome rows (all horizons, MFE and MAE
  jointly) against the family-membership matrix across the discovery observations, which preserves the outcome
  distribution and the dependence between horizons and between families.
* Statistic per (family, horizon): Welch t of `ret_H`, family vs non-family. The real value is compared with its
  null distribution (reported: observed statistic, null 2.5/50/97.5 percentiles, unadjusted two-sided p).
* **Family-wise correction:** Westfall–Young **maxT** over all primary (family x horizon) cells (3 or 4 families x 5
  horizons), giving adjusted p-values. MFE/MAE use the same permutations but are secondary/unadjusted (they scale
  with volatility).

## 8. Discovery decision rule (no single test decides)
A primary family **survives discovery at horizon H** only if, with N >= 30:
1. maxT-adjusted permutation p-value for `ret_H` < 0.05, **and**
2. the 95% bootstrap CI for the mean difference excludes 0, **and**
3. the control regression's family dummy has the same sign and p < 0.05.
Everything else (medians, win %, MFE/MAE, effect sizes, all other cells) is reported in full. If several horizons
qualify, the one with the smallest adjusted p is the family's frozen hold-out horizon (ties: shorter horizon).
If nothing survives, the conclusion is "no detectable effect at this power", and nothing is re-tuned on this data.

## 9. Freeze, then hold-out (exactly once)
Order is fixed:
1. Discovery tagging (incl. top-up) complete.
2. Discovery outcome analysis complete and reported.
3. **Freeze**: tagging setup (section 2), family definitions (section 5), analysis code and decisions (sections 6-8),
   the discovery `windows.jsonl` hash. Recorded as a git tag `prereg-frozen`.
4. Tag the hold-out with the frozen setup. Hold-out windows lie **entirely** inside the hold-out period
   (window start >= 2024-06-01), are non-overlapping, use the **discovery 25.2% span** (not recomputed; wider windows
   excluded), and need 24 forward candles inside the available data. Same stratified, fill-capacity procedure.
5. Run the outcome evaluation **once** (code writes a lock file and refuses to run twice).
6. Report everything, good or bad. Nothing is modified based on hold-out results.

Hold-out verdict, only for families that survived discovery, at their frozen horizon: same sign as discovery, one-sided
permutation p < 0.05, control-regression dummy same sign, and mean difference >= 50% of the discovery estimate.
Non-surviving and exploratory families are shown on the hold-out descriptively and carry no verdict.

## 10. Power (stated up front)
With ~580 windows (drift families ~90 each), 80% power and ~15 maxT cells, the minimum detectable effect is
about 0.43 x the standard deviation of `ret_H`. Assuming BTC 1h-candle std of roughly 0.6%, 1.1%, 1.5%, 2.1%, 3.0%
at 1/3/6/12/24 h (to be checked against the data), that is ~0.26 / 0.46 / 0.65 / 0.9 / 1.3 percentage points.
Plausible true effects are smaller, so "no result" means **inconclusive for small effects**, not proof of no edge.

## 11. Constraints
* No trading rules, entry/exit logic, TP/SL or position sizing anywhere in this experiment.
* No interpretation or technical-analysis renaming of shapes before the hold-out result exists.
* Any conversion of a surviving pattern into a trading setup is a separate, later discussion.

## 12. OPEN ITEMS (must be answered before anything runs)
1. **impulse_up.** Your instruction says to keep `impulse_up` as a primary family AND not to merge
   `stair_step_up`, `sharp_rally`, `range_breakout_up` yet. Both cannot hold literally. Default written here
   (**option A**): the three primary families are sideways_range, drift_up, drift_down (3 x 5 = 15 maxT cells);
   the three impulse shapes stay separate and exploratory; `impulse_up` is only a reserved name. Option B: keep
   `impulse_up` = union of the three as a 4th primary family (20 cells) while ALSO reporting the three separately.
2. **Hold-out scope.** Default written here: evaluate every frozen family once on the hold-out, but give verdicts
   only to families that survived discovery. Alternative: evaluate only the survivors.
3. **Discovery decision rule** (section 8) and the 0.05 thresholds: confirm or change.
