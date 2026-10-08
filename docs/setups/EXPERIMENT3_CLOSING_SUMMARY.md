# Experiment 3 (15M setup discovery) — closing summary

**Status: ACCEPTED by the reviewer after three wording edits (this version).** Facts below are from committed files; interpretation is marked as such.

## Result

**No candidate reached F2. No outcome, return, MFE, MAE or R was ever computed. The hold-out (2026-06-01 onward) was never read.**
The pipeline stopped at the preregistered gates G0/G1, as designed.

| Candidate | Stage reached | Preregistered classification |
|---|---|---|
| C1 bullish_breakout_from_right_edge_consolidation | frequency | INCONCLUSIVE / LOW FREQUENCY (78 counted occurrences, < 100); not audited |
| C2 bullish_rebound_breakout_after_drop | frequency | fails G1 (17 counted); not audited |
| C3 bearish_breakdown_from_right_edge_range | frequency | fails G1 (14 counted); not audited |
| C4 bearish_continuation_below_broken_support | frequency | fails G1 (13 counted); not audited |
| C5 bullish_continuation_after_spike_and_pullback | translation | NOT CODEABLE (J-5 declined: "prior breakout zone" has no objective referent) |
| C6 bearish_rejection_from_recent_high | frequency | fails G1 (11 counted); not audited |
| C7 bullish_breakout_from_right_edge_range | fidelity audit | **NOT CODEABLE FAITHFULLY**: precision 87/100 (passes ≥ 70 %), recall 3/12 = 25 % (fails ≥ 50 %) |
| C8 bearish_breakdown_from_right_edge_support | frequency | fails G1 (29 counted); not audited |

(The tiny-n "not audited" candidates were never given the chance to fail or pass fidelity, because G1 comes first.)

## What was done, in order (all committed)

1. Design and pre-registration locked (F0). 558 neutral 15M charts (96 candles, % axis, relative time) sampled outcome-blind.
2. Stage A (558 descriptions) and Stage B (consolidation) by gpt-5.4-mini; amendments F0b (verified citations) and F0c (final-merge rule order) were adopted after seeing Stage B failures; the cap of 8 candidates was not raised. Definitions frozen at F1 (8 candidates).
3. Recognizer parameter table (translation of each definition into numbers on completed candles); judgments J-1 … J-14 recorded. J-5 declined, J-9 flagged, J-14 (C6 `RET ≤ 1.0`) decided after seeing the derived RET distribution (disclosed).
4. Price-only derivation of 33/67 percentile thresholds (26,113 discovery positions); recognizer built with prefix-invariance, causality, determinism and import-firewall tests.
5. Frequency check on the discovery period; decision (Path 1): the preregistered lockout was kept, no cap or alternative lockout was computed.
6. C7 fidelity audit: 100 counted triggers + 100 non-trigger cases, model shown only the frozen wording and the chart; recall mechanical on 12 eligible Stage A charts.

Spend: Stage A/B $1.0524, fidelity audit $0.1802; total $1.2326 of the $4.50 ceiling.

## Facts worth keeping

* **Raw trigger frequency was in the 0.2 %–10 % band for all seven** (0.28 %–1.83 %). Counted occurrences collapsed for C2, C3, C4, C6, C8 because one occurrence per candidate was never invalidated (locks up to 22,766 candles, ~237 days) and the frozen lockout blocks later counted triggers until invalidation. Preserved as a finding about the frozen invalidation levels.
* **C7 precision 87 % but recall 25 %.** The recognizer agreed with the frozen visual definition on 87/100 sampled trigger cases (87 PRESENT, 12 NOT_PRESENT, 1 UNCLEAR), but recall was only 3/12 = 25 % against the eligible Stage A actionable charts (recognized: S0121, S0444, S0550; S0550 is the only one with a trigger; the denominator is small). The recognizer therefore appears selective relative to the AI descriptions, but this audit does not establish general semantic fidelity beyond these sampled cases. The model also judged 31 of 100 non-trigger candles PRESENT (context, not a gate), so "present" in the model's eyes is broad. There were no audit errors.
* Overlap among recognizers was modest (largest presence Jaccard C6/C8 0.158).

## Interpretation (not a result)

The numeric translation of loose chart language, including several simultaneous "small"/"near" conditions mapped to q33 thresholds, produced a substantially narrower recognizer than the original natural-language descriptions. For several candidates, the frozen invalidation rule also left occurrences under lock for very long periods, so most raw triggers were suppressed before they could become counted occurrences. These are properties of the frozen translation and counting procedure, not evidence about the market. Nothing here tests whether any setup has directional behavior; that was never tested.

## Disclosed amendments, post-hoc decisions, and measurement conventions

| Item | Kind | Note |
|---|---|---|
| F0b | amendment after Stage B citation failures | unknown supporting ids dropped and audited; support = verified ids |
| F0c | amendment (rule-order clarification) after the Stage B final merge exceeded the cap | candidates with < 15 verified ids set aside by count, then the cap of 8 applies; ordering resolved after seeing the output; the cap was not raised |
| J-14 | post-hoc interpretive decision | C6 `RET ≤ 1.0`, decided after seeing the derived RET distribution; no outcome existed |
| Counted-trigger precision | measurement convention | the audited trigger cases are the counted (post-lockout) C7 occurrences, the population that would enter later analysis |
| Recall | mechanical convention | a chart is recognized if C7 is present at T or a raw trigger occurred on T or T-1 |

None of these used any outcome, and none was outcome-driven tuning. The frequency artifact states that no rule or threshold was changed.

## Not done / not claimed

No F2 freeze, no outcome code, no statistics, no hold-out run, no execution spec, no backtest. No claim of any edge. REAL FILLS ONLY policy untouched. 1H and 5M archives untouched.

## Key artifacts (SHA-256 of line-ending-normalised files)

| File | SHA-256 |
|---|---|
| results/setups/recognizer/derived_parameters.json | 6bb57d6443e97b7eb046da4fda9e8c268d4d788c264f3af537f9054739c7e7f1 |
| results/setups/recognizer/frequency_report.json | 81b33e01e33fd01412eb4e02f54698c864bc8bf9e18946f4f3cbef7b9bc87ec8 |
| results/setups/fidelity/audit_cases.jsonl | 169209b6b19ba147d8df87199a49f4fd7467ba7fc66dd4a4ff58e0b1581f80cd |
| results/setups/fidelity/recall.json | c0d061cd60ceb837bb5a47cf3e911f233ac0b79c6df088458d017aac7b9d1f9c |
| results/setups/fidelity/audit_judgements.jsonl | acce485e2edd7cf6c138ba2435874f454e16e9cb13ef803dc95fb67e05174b76 |
| results/setups/fidelity/cost_log.jsonl | 9a85e5f3e1eb10aee7dfaaeda05df8313e7f85b5d4af30dea5c31bada5adfac3 |
| results/setups/fidelity/fidelity_report.json | f591497575d938c8a392caa8f9fca8e9905c290af6f8b8677efc26b0a16b7bf0 |
| src/setups/recognizer.py | 8b62623b9385cabb5c2a20db3131ee739da3b9eaee2e00cdd854b90af7d8e6f8 |

Canonical database: `data/research_binance.db`, SHA-256 `1535c535…27e9f`.
