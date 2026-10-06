# Pre-registration — MIB Pattern Lab (1h BTC/USDT)

**Version: v2, user decisions recorded.** It becomes **LOCKED** when `docs/PREREG_LOCK.json` (section 13) is committed,
which happens after the discovery top-up is tagged and verified and **before any outcome is computed**.
**Status: no forward-return / outcome data has been examined.** Only chart shapes, AI tags and window-only geometry
(`src/discovery/audit.py`) have been looked at. After outcome analysis begins, nothing in this document, the tagging
prompt, the vocabulary, the family definitions, the discovery-window rules or the decision rules may change.

**Scientific question:** do recurring visual shapes in clean price history contain information about subsequent price
movement? This is not a trading-rule project: no interpretation of shapes, no technical-analysis renaming, no
entry/exit/TP/SL logic. Converting a pattern into a trading setup is a separate discussion that happens only if a
pattern survives the hold-out.

## 1. Data split (fixed)
| timeframe | discovery period | hold-out (locked) |
|---|---|---|
| **1h** (the only timeframe of this experiment) | 2020-06-05 up to 2024-06-01 (exclusive) | 2024-06-01 onward |

* Enforced in code: `config.discovery_end(tf)` -> `discover.discovery_candles()` removes later candles before any
  window is built; sampling asserts every window ends before the cutoff.
* The hold-out is tagged and evaluated **once** (section 9). Nothing is modified based on it.
* The first 1h pilot (`tagset_v1_1h`, 100 windows, ~20 after 2024-06-01) is not reused. Only tags were looked at.
* The same methodology may be repeated on 5m **after** this experiment is complete, as a separate pre-registration.
  The experiment is not switched to 5m.

## 2. Frozen tagging setup (unchanged; used unchanged for the hold-out)
* Model `gpt-5.4-mini`; prompt `retag-v1`; vocabulary `vocab-v1`.
  * vocab sha256 `3eab422efbf6279fa7efe991230c7b493699e35c8bff3e7b89d649b439805d54`
  * system prompt sha256 `5ac0b75fd36689bd3994c3a35bdc195e858fd41b27ee423a0fe9cf15d2c93690`
  * user prompt (pass 1) sha256 `4b478c2d878a98a1259a834b6b7482b42d9a4f04f8f4f8e38633d35b111a40cb`
  * user prompt (pass 2, vocabulary reversed) sha256 `7e6d3f8d72fdd94fc8d549ea9f1eacd13fd0ee2dbe2aa9c9fb8030c9005715d9`
* Two passes; a window's **stable tags** = tags present in BOTH passes. Invalid tags are errors, never repaired.
* Charts: 60 closed 1h candles ending at T; fixed vertical span (computed once from the discovery period, **25.2%**,
  then frozen and reused unchanged for the hold-out); anonymised axes (% vs close at T, T-50..T).
* **No outcome information is available during tagging.** The model sees only the PNG and the fixed prompt, and the
  tagging/chart/data code cannot import the outcome module (test-enforced).

## 3. Discovery sample (option C: fill the remaining capacity)
* Start: 431 non-overlapping windows (`tagset_v1_1h_cut20240601`, stratified by window range).
* Top-up: `python -m src.discovery.tagset --timeframe 1h --topup 999` adds every remaining non-overlapping window
  inside the discovery period (target ~580 total), same chart style (hash-checked), same frozen tagging setup.
  New windows never overlap each other or the originals and never use hold-out data.
* Discovery window rules (frozen): 60 closed gap-free 1h candles; window end < 2024-06-01; windows >= 60 candles
  apart; window range <= the fixed span (wider windows are excluded, not clipped).
* The discovery sample is **frozen** when tagging finishes; its `windows.jsonl` sha256 goes into the lock record.
* The sample is stratified by window range (a chart property, not an outcome). Baselines and nulls use this same
  sample; `range_pct` is a control covariate (section 6).

## 4. Outcome measures (only `src/outcomes/` may read candles after T)
Entry reference = **close of T**. For each window and each horizon H in {1, 3, 6, 12, 24} one-hour candles (hours):
* `ret_H` = 100 * (close[T+H] / close[T] - 1)
* `fut_high_H` = max(high[T+1..T+H]);  `fut_low_H` = min(low[T+1..T+H])  (prices)
* `MFE_H` = 100 * (fut_high_H / close[T] - 1)   (max favorable excursion, >= 0)
* `MAE_H` = 100 * (fut_low_H / close[T] - 1)    (max adverse excursion, <= 0)

No TP/SL, no costs, no trading rules. No sign is flipped for any family (no assumed direction).
Exclusions (counted and reported): the 24 candles after T must exist, be gap-free and lie **before the cutoff**
(a discovery window whose forward path reaches into the hold-out is excluded).

## 5. Families (Option A; frozen in `src/discovery/families.py`)
Every vocabulary shape except `none` is its own **single-tag family**. Nothing is merged.
Visually distinct shapes are never combined on the basis of our interpretation.

**Primary (confirmatory) families — exactly three:**
`sideways_range`, `drift_up`, `drift_down`.

**Exploratory families (descriptive; no confirmatory claim; no multiplicity budget):** every other shape,
including `stair_step_up`, `sharp_rally` and `range_breakout_up` (each kept **separate**), `sharp_drop`,
`rounded_top`, `rounded_bottom`, `terminal_spike_up`, `terminal_spike_down`, `choppy_volatile`,
`tight_compression`, `v_reversal`, `spike_and_retrace`, `stair_step_down`, `inverted_v`, `range_breakdown`.

**`impulse_up` is NOT defined and NOT used in this experiment.** The name is reserved for possible future work.
A window may belong to several families. Windows with no stable tag (or only `none`) are in no family and stay in the
non-family population.
A family gets a formal category (section 8) only if it is primary and has N >= 30 windows with valid outcomes;
every family is still reported descriptively whatever its N (small N is flagged).

## 6. Statistics (reported for every family and every horizon)
Each family vs. the **non-family population** (all other discovery windows):
* N; mean and median `ret_H`; win % (`ret_H` > 0); mean and median MFE_H and MAE_H;
* effect size: mean difference (percentage points) and Cohen's d;
* 95% confidence interval of the mean difference (bootstrap, 10,000 resamples, fixed seed 20240601);
* unadjusted significance: Welch t-test p and permutation p;
* control regression (supplementary, one of the three decision conditions):
  `ret_H ~ net_pct + range_pct + eff + family_dummy`, HC3 robust errors, with window-only features from `audit.py`.
  It asks whether the family adds information **beyond simple measurable features**.

## 7. Null / permutation test
* Fixed seed 12345, **10,000 permutations**. Each permutation shuffles the outcome rows (all horizons, MFE and MAE
  jointly) against the family-membership matrix across the discovery observations: the outcome distribution and the
  dependence between horizons and between families are preserved.
* Statistic per (family, horizon): Welch t of `ret_H`, family vs non-family. Reported: observed value, null
  2.5/50/97.5 percentiles, unadjusted two-sided p, and whether the real effect is unusual relative to the null.
* **Family-wise correction:** Westfall–Young **maxT** across all primary (family x horizon) cells =
  3 families x 5 horizons = **15 cells**, giving adjusted p. MFE/MAE use the same permutations but are
  secondary and unadjusted (they scale with volatility). Exploratory families are shown with unadjusted p only.

## 8. Decision rule and reporting categories
**Three conditions** (all must hold for a primary family at a horizon H, with N >= 30):
1. maxT-adjusted permutation p for `ret_H` **< 0.05**;
2. the 95% bootstrap CI of the mean difference **excludes zero**;
3. the control regression's family dummy has the **same sign and p < 0.05** ("control regression agrees").

Medians, win %, MFE/MAE, effect sizes and all other cells are reported in full. No single test decides.

**Reporting categories (primary families, at discovery):**
* **PASS** — all three conditions hold at some horizon. If several horizons qualify, the one with the smallest
  adjusted p is the family's frozen hold-out horizon (ties: the shorter horizon).
* **DOES NOT PASS** — not PASS, N >= 30, **and** at every horizon the 95% CI of the mean difference lies entirely
  inside [-MDE_H, +MDE_H]. This means effects at least as large as MDE_H are not supported by the data. It says
  nothing about smaller effects and is **never** described as proof that no edge exists.
* **INCONCLUSIVE / LOW POWER** — everything else (N < 30, or a CI wider than +/-MDE_H at some horizon without meeting
  PASS). The data cannot support a reliable conclusion.

MDE_H = (z_(1-0.05/(2*15)) + z_0.80) * s_H * sqrt(1/n_family + 1/n_non-family) ~ 3.78 * s_H * sqrt(1/n_f + 1/n_nf),
with s_H the pooled SD of `ret_H` in the discovery sample (computed from the data, not assumed).

## 9. Freeze, then hold-out (exactly once)
Fixed order:
1. Discovery tagging (incl. top-up) complete; lock record written (section 13).
2. Discovery outcome analysis run **once** with the frozen code and reported (categories per section 8).
3. **Freeze:** tagging setup (section 2), family definitions (section 5), analysis code and decisions
   (sections 6-8), the discovery `windows.jsonl` hash, each PASS family's frozen horizon.
4. Tag the hold-out with the frozen setup. Hold-out windows lie **entirely** inside the hold-out period
   (window start >= 2024-06-01), are non-overlapping, use the **discovery 25.2% span** (not recomputed; wider windows
   excluded), and need 24 forward candles inside the available data. Same stratified, fill-capacity procedure.
5. Run the hold-out outcome evaluation **once** (the code writes a lock file and refuses to run again).
6. Report everything, good or bad. Nothing is modified based on hold-out results.

**Hold-out scope:** **ALL frozen families** (every shape in section 5) are evaluated on the hold-out with the same
statistics. No family is added or dropped after seeing hold-out data.

**Formal verdicts only for discovery-PASS families**, at their frozen horizon, with alpha_holdout = 0.05 / (number of
discovery-PASS families):
* **PASS** — same sign as discovery; one-sided permutation p < alpha_holdout (discovery direction); control-regression
  dummy same sign; mean difference >= 50% of the discovery estimate; N >= 30.
* **DOES NOT PASS** — not PASS, N >= 30, and the upper bound of the hold-out 95% CI (signed toward the discovery
  direction) is below 50% of the discovery estimate, i.e. the data rule out replicating at least half the discovery
  effect. (Still not proof that no edge exists.)
* **INCONCLUSIVE / LOW POWER** — everything else, including hold-out N < 30.

Every other family (primary families that did not pass discovery, and all exploratory ones) is reported
descriptively on the hold-out. It is **not** treated as a confirmatory success or failure.

## 10. Power (stated up front)
With ~580 windows (drift families ~90 each), 80% power and 15 maxT cells, the minimum detectable effect is about
0.43 x the SD of `ret_H`. Assuming BTC 1h-candle SD of roughly 0.6%, 1.1%, 1.5%, 2.1%, 3.0% at 1/3/6/12/24 h
(to be checked against the data) that is ~0.26 / 0.46 / 0.65 / 0.9 / 1.3 percentage points. Plausible true effects
are smaller. Underpowered negative results are reported as INCONCLUSIVE / LOW POWER, not as proof of no edge.

## 11. Constraints
* No trading rules, entry/exit logic, TP/SL or position sizing anywhere in this experiment.
* No interpretation or technical-analysis renaming of shapes before the hold-out result exists.
* No `impulse_up` or any other merged family.

## 12. Decisions recorded (from the user)
1. Family definition: **Option A** (three primary families; stair_step_up / sharp_rally / range_breakout_up kept
   separate and exploratory; no combined `impulse_up`, name reserved).
2. Hold-out scope: evaluate **all** frozen families; formal verdict only for discovery-PASS families; others descriptive.
3. Decision rule: keep the three conditions, 0.05 threshold and family-wise correction; categories PASS /
   DOES NOT PASS / INCONCLUSIVE-LOW POWER as defined in sections 8-9.
4. Timeframe: continue 1h exactly as defined; repeat on 5m only after this experiment is complete.
5. Top-up: option C, dry-run first; outcome module is built only **after** the top-up and this document are locked,
   exactly according to this frozen specification.

## 13. Locking procedure
1. `python -m src.discovery.tagset --timeframe 1h --topup 999 --dry-run`, then the real top-up run.
2. `python -m src.discovery.lock --timeframe 1h --write` verifies: every window has both clean tagging passes,
   windows are non-overlapping and before the cutoff, one chart style, one model/prompt/vocabulary. It records the
   sha256 of this document, `families.py`, vocabulary, prompts, `windows.jsonl` and `retags.jsonl`, the git commit,
   and the number of windows per family (tags only; no outcomes).
3. The resulting `docs/PREREG_LOCK.json` is committed. Only then is the outcome module built; it must verify this
   record before running and writes the lock hash into its output.
