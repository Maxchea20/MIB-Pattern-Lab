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
