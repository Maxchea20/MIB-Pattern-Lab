# Amendment F0b — Stage B citation handling

**Status: DRAFT FOR REVIEW. Not applied, not locked.** Amends `docs/PREREGISTRATION_SETUPS.md` section 6 and nothing else.
The pre-registration file itself is **not edited** (its hash `3069082a…` and the F0 lock stay as they are). This document
supersedes only the sentence quoted below, and only from the moment the F0b lock is written.

## Why

The Stage B run on 2026-10-08 stopped under the F0 rule: chunk 1 failed all 3 attempts because the model cited supporting
ids that were not in its input. The record is committed (`e1f99af`: `stage_b_attempts.jsonl`, `cost_log.jsonl`; no
candidates were written). Audit of the three rejected answers: 2 of 122, 2 of 149 and 15 of 249 cited ids were unknown
(1.6 %, 1.3 %, 6.0 %); every unknown id was a real chart that had not been shown to the model (14 NONE charts, 1 from the
other chunk); every candidate still had many verified ids. A citation is bookkeeping about provenance; one wrong id
rejected an otherwise well-formed answer. No outcome of any kind exists or was used. This amendment repairs the bookkeeping;
it gives the model no new opportunity to change what a setup is.

## Text replaced (section 6, "Validation (Python)")

> Validation (Python): valid JSON and schema; `direction` in the enum; every `supporting_id` exists; **at most 8**
> candidates; **at least 15 distinct supporting descriptions** per candidate (otherwise dropped on count alone); output
> lint; no performance language.

## Replacement text

> **Validation (Python), rule F0b.** Valid JSON and schema; `direction` in the enum; **at most 8** candidates with unique
> names; output lint; no performance language. **Citations are verified, not trusted.** For every Stage B call, the *verified
> ids* are the ids that were actually present in **that call's input**: for a chunk call, the descriptions of that chunk; for
> the final consolidation call, the ids carried by the candidates shown to it. For each candidate:
> 1. `supporting_ids` becomes the sorted set of **distinct cited ids that are verified**. Nothing is ever substituted,
>    inferred, added or repaired;
> 2. what the model cited, verbatim (`cited_supporting_ids`), and every id that could not be verified
>    (`unverified_supporting_ids`) are **kept in the record** of the attempt and of the candidate, together with the counts
>    cited / verified;
> 3. an unverified id **never counts** towards support and **never rejects** an answer by itself; an answer is rejected only
>    for a structural problem, or if a candidate has **no** verified id;
> 4. a candidate must have **at least 15 distinct verified supporting descriptions** in the final output, otherwise it is
>    dropped on count alone (and listed, with its counts, under `dropped`).
>
> The same rule applies to the chunk calls and to the final consolidation call. Up to 3 attempts per call remain, with the
> rejection reasons appended and no hand editing. Attempts recorded before this amendment (the three F0 attempts, which have
> no `rule` field) stay in the file as history and **do not count** towards the attempts of this rule: the first attempt
> under F0b is a fresh one. Prompts, parameters, thresholds (15, 8, 120), seeds, caps and the Stage A record are unchanged.

## Exact changes

| File | Change |
|---|---|
| `src/setups/prompts.py` | `validate_candidate` no longer rejects unknown ids; new `verify_citations`; `validate_stage_b` returns candidates with verified support and an audit; `render_candidates` shows the nine prompt keys only |
| `src/setups/discover.py` | `RULE` marker; attempts filtered by rule; citation audit stored in each attempt and in the candidate file; the final call is verified against the ids in its own input; dropped candidates record verified/cited counts |
| `src/setups/lock.py` (not hashed by F0) | `--write-f0b`, `verify_f0b`; once the F0b lock exists it governs every pipeline step |
| `docs/setups/AMENDMENT_F0B.md` | this document |
| `tests/test_setups_discover.py`, `tests/test_setups_lock.py`, `tests/test_setups_f0b.py` | updated / new tests |

Not changed: `params.py`, `sampling.py`, `audit.py`, `costlog.py`, `store.py`, all prompt **templates** (their hashes are
unchanged), `docs/PREREGISTRATION_SETUPS.md`, the design document, the policy, the coverage report, the F0 lock file, the
dataset, any archived module.

## What the F0b lock preserves and checks

`docs/PREREG_SETUPS_DESIGN_LOCK_F0B.json` (written once, after approval) records, and every step then verifies:
* the **original F0 lock** file hash (the F0 lock file is never edited);
* every file F0 froze is **byte-identical, except exactly `prompts.py` and `discover.py`**, whose F0 and F0b hashes are both recorded;
* the hash of **this amendment**, and the hashes of all `tests/test_setups_*.py`;
* the **Stage A record** (`stage_a.jsonl`, `windows_setups.jsonl`, `sample_meta.json`, `chart_verification.json`);
* the **existing lines** of the append-only `stage_b_attempts.jsonl` (the three failed attempts) and `cost_log.jsonl`
  (line count and hash of the lines that exist now);
* prompt-template hashes, parameters, config and dataset exactly as in F0.

## Limits

This changes how citations are counted. It does not look at, select among, or modify any description or candidate text, and
no price, return or outcome is read. Candidates are not renamed, merged or split. It is disclosed in the final report.
