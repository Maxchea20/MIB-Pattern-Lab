# Setup Brain — detector translations (Experiment 4, `brain_15m_v1`)

Nine independent detectors on completed 15-minute candles. A detector is PRESENT at candle `t` when its conditions hold on the last 96
candles ending at `t`. A FIRE occurs at the first candle `t'` whose close is beyond the operative level that was present at `t'−1`.
No lockout, voting, ranking, veto or merging. A FIRE is a signal, not a fill.

Conventions are those of `docs/setups/RECOGNIZER_PARAMETER_TABLE.md` (window `W` = 96 candles, range `R`, right edge = last 24, "recent" = last 48,
confirmed swing with `K = 3` known only at `j+3`, bands `q33`/`q67` from `results/setups/recognizer/derived_parameters.json`).

| Setup | Source of the translation |
|---|---|
| S1 `bullish_breakout_from_right_edge_consolidation` | Experiment 3 table, C1, imported unchanged |
| S2 `bullish_rebound_breakout_after_drop` | C2 |
| S3 `bearish_breakdown_from_right_edge_range` | C3 (J-9: `c_t < c_{t−3}` is our translation of "bearish candles push") |
| S4 `bearish_continuation_below_broken_support` | C4 |
| S5 `bullish_continuation_after_spike_and_pullback` | this document (below) |
| S6 `bearish_rejection_from_recent_high` | C6 (J-14: `RET ≤ 1.0`) |
| S7 `bullish_breakout_from_right_edge_range` | C7 |
| S8 `bearish_breakdown_from_right_edge_support` | C8 |
| S9 `tight_range_breakout_both_directions` | this document (below) |

## S5 (J-15, decided by the reviewer for this experiment)

Let `SH*` = latest confirmed swing high (index `jH`, price `hH`), `SH_prev` = the confirmed swing high before it (index `jB`, price `hB` = the **breakout level**).

* **E1** `SH*` is recent (`jH ≥ t−47`), `hH > hB`, and the up-leg `UP = (hH − lB)/R ≥ q67(UP)` where `lB` is the latest confirmed swing low before `jH`.
* **E2** `RET ≤ q33(RET)` **or** `ZR ≤ q33(ZR)`, and no high above `hH` since `jH`.
* **E3 breakout and hold:** the spike broke above the breakout level — some completed close in `(jB, jH]` is above `hB` (the first such candle is `k0`); and it holds — no completed close in `(k0, t]` is below `hB`.
* **E4** `(hH − c_t)/R ≤ q33(DT_C5)`, where `q33(DT_C5)` is derived price-only on the discovery period by `src/brain/derive_s5.py`.
* Presence = E1 ∧ E2 ∧ E3 ∧ E4. **Trigger:** `c_{t'} > hH` (level at `t'−1`). **Invalidation (information, frozen at the trigger):** the first later completed close `< hB`.
* If a close falls below `hB` before the continuation, E3 fails and S5 is no longer present for that structure.
* The previous swing high is the nearest *confirmed* one before the spike's swing high (it is known causally). Choosing the nearest rather than a higher earlier one is an interpretation. "Breaks above" means a completed close, as everywhere else.

## S9 (J-16, approved translation)

* Range = last 24 candles: `ZoneHigh`, `ZoneLow`. Presence: `ZR = (ZoneHigh − ZoneLow)/R ≤ q33(ZR)`; a prior move exists (`UP` or `DN` defined and `> q33`); `ZoneLow ≤ c_t ≤ ZoneHigh`.
  The last condition is true by construction because the range includes the decision candle; it is kept as approved and reported as such.
* Trigger: `c_{t'} > ZoneHigh_{t'−1}` → UP fire; `c_{t'} < ZoneLow_{t'−1}` → DOWN fire. Direction is decided only at the trigger.
* Invalidation (information): UP: first later close `≤ ZoneHigh`; DOWN: first later close `≥ ZoneLow`.
* Not coded: "repeated tests of the same highs and lows", "waiting near one side".
