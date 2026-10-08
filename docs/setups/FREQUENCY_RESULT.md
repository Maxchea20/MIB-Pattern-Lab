# Frequency check result and decision (discovery period, price-only)

Report file: `results/setups/recognizer/frequency_report.json` (SHA-256 of the user's uploaded copy:
`81b33e01e33fd01412eb4e02f54698c864bc8bf9e18946f4f3cbef7b9bc87ec8`; to be pushed by the user). Produced by recognizer
`8b62623b…`, script `ffa0bf85…`, derived parameters `6bb57d64…`, canonical database `1535c535…`. 26,113 evaluated candles.
No return, outcome, MFE, MAE or R was computed. Hold-out not read. No rule or threshold changed.

| Cand | Raw triggers (share) | Counted (share) | Suppressed | Under lock | Never invalidated by data end | G1 (≥100 counted) |
|---|---|---|---|---|---|---|
| C1 | 213 (0.82 %) | 78 (0.30 %) | 135 | 41.3 % | 0 | no: INCONCLUSIVE / LOW FREQUENCY (78 < 100) |
| C2 | 451 (1.73 %) | 17 (0.07 %) | 434 | 94.7 % | 1 | no |
| C3 | 129 (0.49 %) | 14 (0.05 %) | 115 | 92.3 % | 1 | no |
| C4 | 74 (0.28 %) | 13 (0.05 %) | 61 | 84.5 % | 1 | no |
| C6 | 183 (0.70 %) | 11 (0.04 %) | 172 | 95.9 % | 1 | no |
| C7 | 478 (1.83 %) | 135 (0.52 %) | 343 | 49.5 % | 0 | **yes** |
| C8 | 461 (1.77 %) | 29 (0.11 %) | 432 | 93.7 % | 1 | no |

* Raw-trigger share is inside the 0.2 %–10 % band for all seven. Counted share is below 0.2 % for C2, C3, C4, C6, C8.
* For C2, C3, C4, C6 and C8 a single occurrence stayed open to (or near) the end of the data (up to 22,766 candles, about
  237 days), so the preregistered lockout ("until the later of the invalidation and 24 candles after the trigger") blocked
  almost all later counted triggers. This is a finding about the frozen recognizer's invalidation levels, not a coding error.
* Pairwise overlap is modest (largest presence Jaccard: C6/C8 0.158, C1/C7 0.117, C2/C7 0.117, C3/C8 0.103).

## Decision (user, Path 1)

The preregistered lockout is kept. **No cap, no amendment, no alternative lockout was computed or will be.** Consequences:

* **C7 proceeds** to the fidelity audit (135 counted occurrences).
* **C1** is INCONCLUSIVE / LOW FREQUENCY (78 counted; not a failure of the idea).
* **C2, C3, C4, C6, C8** do not proceed under G1; the lockout diagnostics above are part of the experiment's result.
* C5 is NOT CODEABLE (J-5 declined).

Sequence from here: C7 fidelity audit, then (if it passes) F2 freeze, then the G2 outcome analysis. No R before F2.
