# Pre-registration (written before any outcome analysis)

Status when written: **no forward-return / outcome data has been examined.** Only chart shapes, AI tags and
window-only geometry features (`src/discovery/audit.py`) have been looked at.

## Data split (fixed)
| timeframe | discovery period (shapes may be studied) | hold-out (locked) |
|---|---|---|
| 5m, 15m | up to 2026-06-01 (exclusive) | 2026-06-01 onward |
| 1h | 2020-06 up to 2024-06-01 (exclusive) | 2024-06-01 onward |

* The hold-out is used **once**, at the end, only for shapes/rules frozen beforehand. No tuning after seeing it.
* Enforced in code: `config.discovery_end(tf)` -> `discover.discovery_candles()` removes later candles before any
  window is built; sampling asserts that every window ends before the cutoff.
* The first 1h pilot (100 windows, folder `tagset_v1_1h`) included ~20 windows after 2024-06-01. Only tags were
  looked at (never outcomes). Those windows are not reused; the full 1h run uses a fresh folder
  (`tagset_v1_1h_cut20240601`).
* The chosen timeframe for the outcome test is 1h (best shape variety and tag reliability in the pilots).

## Still to be fixed BEFORE looking at any outcome
1. Frozen vocabulary (shapes with real support only).
2. Forward horizon(s) and measure (forward return of the close, in %, no trading rules).
3. Baseline: all windows, and a "plain net-move" control (a window-only rule with the same direction as the shape).
4. Multiple-testing correction across the number of shapes tested.
5. Minimum sample per shape for a shape to be tested at all.

---

# OUTCOME TEST PLAN — DRAFT v1 (NOT YET APPROVED)

Status when written: the 1h discovery tagging (431 windows) is done. **No forward-return data has been examined.**
Nothing below may be changed after the first outcome is looked at. If the user does not approve, nothing runs.

## 1. Frozen tagging configuration
* Model `gpt-5.4-mini`; prompt `retag-v1`; vocabulary `vocab-v1` (sha256 `3eab422efbf6279f...`); 2 passes
  (pass 2 lists the vocabulary reversed); a window's tags = tags present in BOTH passes ("stable").
* Charts: fixed-span, anonymised (% vs close at T, T-50..T), 1h, 60 candles. Held-out windows must be tagged with
  exactly this configuration. The prompt/vocabulary files are not edited.

## 2. Windows
* Discovery sample = `results/discovery/tagset_v1_1h_cut20240601` (431 non-overlapping windows, stratified by window
  range). The baseline is the SAME 431 windows (not the whole market).
* Windows with no stable tag are kept (as "untagged") in the baseline.

## 3. Families (defined from tag names only, before outcomes)
Confirmatory (stable on >= 30 discovery windows; max 4 tests):
| family | definition |
|---|---|
| F_sideways | sideways_range |
| F_drift_up | drift_up |
| F_drift_down | drift_down |
| F_impulse_up | stair_step_up OR sharp_rally OR range_breakout_up |

Exploratory (descriptive means only, no claims, no hold-out run): sharp_drop, rounded_top, rounded_bottom,
terminal_spike_up, terminal_spike_down, choppy_volatile, tight_compression, v_reversal, spike_and_retrace.
Never observed (dropped): stair_step_down, inverted_v, range_breakdown, none.
A window can belong to several families.

## 4. Outcome measure (the only place that may read candles after T)
* R = 100 * (close[T+12] / close[T] - 1), 12 one-hour candles (12 hours) after the window end T. Entry = close of T.
  No fees/slippage in R; a 0.2% round-trip cost line is shown for reference only.
* Windows whose 12 following candles are missing or contain a gap are excluded and counted.
* Secondary, descriptive only: H = 24. Not tested.
* Window spacing (60h) exceeds the horizon, so outcome periods do not overlap.
* Code: `src/outcomes/` is the only module allowed to read candles after T. A test asserts the tagging /
  chart pipeline never imports it.

## 5. Tests (per confirmatory family)
1. Descriptive: mean R of the family vs. all other windows (permutation test, 10,000 label shuffles).
2. **Primary criterion** ("adds beyond simple features"): OLS `R ~ net_pct + range_pct + eff + family_dummy`
   (window-only features; HC3 robust errors; two-sided). A family passes discovery if its dummy has
   **Holm-adjusted p < 0.05 across the 4 families**.
3. If none passes: record "no detectable effect at this power". No new families, horizons or vocabulary on this data.

## 6. Power (stated up front)
With a 12h return std of ~2.1%, 80% power and Holm over 4 tests, the minimum detectable effect is roughly
0.9% (drift_up/down, n=69), ~1.2% (impulse_up, n~39), ~0.8% (sideways). Plausible real effects are far smaller.
A "no result" therefore means inconclusive for small effects, not proof of no edge. Only large effects can pass.

## 7. Hold-out (one shot)
* Only for families that pass 5.2. Tag hold-out windows (2024-06-01 onward, non-overlapping, same sampling) with the
  frozen configuration in section 1; compute R the same way.
* Pass = same sign as discovery, one-sided p < 0.05 for the family dummy in the same regression, and effect >= 50%
  of the discovery estimate. Report the result whatever it is. The hold-out is never re-used or tuned on.
