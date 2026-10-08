# Amendment F0c — order of the two Stage B validation rules (final merge)

**Status: APPROVED by the project owner on 2026-10-08 (Option 1 / F0c) and applied. Locked by `docs/PREREG_SETUPS_DESIGN_LOCK_F0C.json`, which is written after this text is committed.** Amends `docs/PREREGISTRATION_SETUPS.md` section 6 as already amended by
`docs/setups/AMENDMENT_F0B.md`, and nothing else. No threshold changes: **8** candidates, **15** verified supporting
descriptions, chunk size **120**, all caps, seeds, templates, the dataset and the Stage A record stay exactly as locked.

## Why — and an explicit disclosure

Section 6 lists two validation rules for Stage B without saying in which order they apply: "at most 8 candidates" and "at
least 15 distinct supporting descriptions per candidate (otherwise dropped on count alone)". The F0 and F0b code applied the cap
**first**, to everything the model returned, and the support rule afterwards.

**Disclosure.** This ambiguity was resolved **after** the model's output had been seen. Under F0b, the two chunk calls were
accepted (7 + 2 candidates) and the final consolidation call was rejected on all 3 attempts (commit `ccf3f73`) with "at most 8
candidates are allowed; got 9". The three responses were the same 9 candidates (the 9 chunk candidates, unmerged), with 0
unverified ids, of which 8 have between 15 and 47 verified supporting descriptions and **one has 6**. Applying the
already-frozen 15-description rule before the cap would leave 8. This was observed before the precedence was chosen. It is a
non-outcome validation failure: no price, return or outcome exists in the process. The choice is justified on its logic (a
candidate that fails the support rule is not part of the result, so it should not count against the cap), not on the
candidates' content, and the project owner approved it on 2026-10-08 knowing this. It is disclosed in the final report.
The cap itself is **not** raised.

## Text replaced (the validation rules of section 6 as amended by F0b)

> … at most 8 candidates with unique names; … a candidate must have at least 15 distinct verified supporting descriptions in the
> final output, otherwise it is dropped on count alone …

## Replacement text

> **Rule order, rule F0c.**
> *Chunk calls:* as under F0b (structure, unique names, lint; at most 8 candidates returned; citations verified; every
> candidate keeps at least one verified id).
> *Final consolidation call:* (1) structure, unique names and lint are checked on everything returned; (2) citations are
> verified against the ids in that call's input, and every candidate keeps at least one verified id; (3) every candidate with
> **fewer than 15 distinct verified supporting descriptions is set aside by count alone** and listed under `dropped` with its
> cited and verified counts; (4) the **survivors are counted: at most 8** are allowed, and an answer with more than 8 survivors
> is rejected (up to 3 attempts, reasons appended, no hand editing). Which candidates survive depends on the verified-support
> **count alone**: never on content, order, name, direction or any other property. The model's answer is otherwise taken as
> returned: nothing is merged, split, renamed, reordered or chosen by us.
>
> Attempts: the three F0 attempts and the three F0b final-merge attempts stay in `stage_b_attempts.jsonl` as history and do
> **not** count; the final merge gets a fresh set of 3 attempts under F0c. The two chunk calls accepted under F0b remain valid
> (their validation is unchanged) and are reused, not paid for again. The three rejected F0b final-merge responses are
> **not** reinterpreted as accepted.

## Exact changes

| File | Change |
|---|---|
| `src/setups/prompts.py` | `validate_stage_b` gets `min_support`: with it, the cap applies to the survivors of the support rule; without it (chunk calls) nothing changes |
| `src/setups/discover.py` | `RULE` becomes `F0c_prune_before_cap`; the final call passes `min_support`; accepted F0b chunk attempts are reused; attempt counting uses the current rule only; the output lists earlier rejected attempts by rule |
| `src/setups/lock.py` (not hashed by F0) | `--write-f0c`, `verify_f0c`; the latest lock that exists governs |
| `docs/setups/AMENDMENT_F0C.md` | this document |
| tests | `tests/test_setups_f0c.py` (new); two assertions updated in `tests/test_setups_f0b.py` |

Not changed: `params.py` and every other F0-frozen file, the prompt templates (hashes identical), the pre-registration, design
doc, policy, dataset, archived modules, the F0 lock file, the F0b lock file, the F0b amendment, the Stage A record, and any line
already in `stage_b_attempts.jsonl` / `cost_log.jsonl`.

## What the F0c lock records and every step then verifies

`docs/PREREG_SETUPS_DESIGN_LOCK_F0C.json` (written once, after approval): the file hashes of the **F0 lock** and the **F0b lock**
(neither is ever edited) and of both amendment documents; for `prompts.py` and `discover.py` the F0, F0b **and** F0c hashes; every
other file F0 froze byte-identical; the test files; the Stage A record and chart verification; the existing lines of the
append-only files (the 3 F0 + 5 F0b Stage B attempt rows, and the cost lines so far) and the earlier F0b prefixes; templates,
parameters, config and dataset unchanged.
