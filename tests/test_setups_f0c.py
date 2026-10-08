"""Amendment F0c: the support rule (>= 15 verified ids, by count alone) is applied BEFORE the cap of 8 in the final merge."""
import json
import random
import shutil

import pytest

from src.setups import discover as dv, lock, params, prompts, store
from tests.test_setups_discover import FakeText, b_run_dir, cand, stage_a_ok


def ids_in(user):
    return [l.split(": ")[1] for l in user.splitlines() if l.startswith("id: ")]


def candidates_in(user):
    """The candidates JSON of a final-merge prompt (a retry appends the rejection reasons after it)."""
    return json.JSONDecoder().raw_decode(user.split("Candidates:\n")[1])[0]


def chunk_response(user, sizes, names):
    """Candidates built from the ids present in this chunk prompt: sizes[i] ids for candidate i."""
    ids, out, pos = ids_in(user), [], 0
    for size, name in zip(sizes, names):
        out.append(cand(name, ids[pos:pos + size]))
        pos += size
    return {"candidates": out}


def run_scenario(tmp_path, n_described, chunk_sizes, final_fn):
    """Two chunks (120 + rest). chunk_sizes = {1: [...], 2: [...]} candidate sizes; final_fn(candidates_shown) -> response."""
    d, rows = b_run_dir(tmp_path, n=n_described + 5)
    names = {1: [f"chunk_one_{i}" for i in range(8)], 2: [f"chunk_two_{i}" for i in range(8)]}
    state = {"chunk": 0}

    def fn(user, n):
        if "Descriptions:" in user:
            state["chunk"] += 1
            return chunk_response(user, chunk_sizes[state["chunk"]], names[state["chunk"]])
        return final_fn(candidates_in(user))

    t = FakeText(fn)
    return d, t


def echo(shown):
    return {"candidates": [cand(c["name"], c["supporting_ids"]) for c in shown]}


# ---------------------------------------------------------------------------- the five behaviours ---------
def test_nine_returned_one_below_15_verified_is_set_aside_and_eight_survivors_are_accepted(tmp_path):
    d, t = run_scenario(tmp_path, 125, {1: [15] * 7 + [6], 2: [5]}, echo)
    # chunk 1: 8 candidates (one with 6 ids), chunk 2: one candidate with 5 ids -> 9 shown to the final call, TWO below 15
    rec = dv.run_stage_b(d, t, candidates_path=tmp_path / "c.json")
    assert len(rec["candidates"]) == 7 and {x["name"] for x in rec["dropped"]} == {"chunk_one_7", "chunk_two_0"}
    (tmp_path / "b").mkdir()
    d2, t2 = run_scenario(tmp_path / "b", 125, {1: [15] * 8, 2: [5]}, echo)
    rec2 = dv.run_stage_b(d2, t2, candidates_path=tmp_path / "b" / "c.json")          # exactly the observed pattern: 9 shown, one weak
    assert len(rec2["candidates"]) == 8 and [x["name"] for x in rec2["dropped"]] == ["chunk_two_0"]
    assert rec2["dropped"][0]["verified_distinct_supporting_descriptions"] == 5
    assert t2.calls == 3                                                                # 2 chunk calls + ONE final call: accepted at once
    att = store.load_jsonl(d2 / dv.STAGE_B_FILE)
    assert att[-1]["kind"] == "final" and att[-1]["accepted"] and att[-1]["rule"] == dv.RULE and len(att[-1]["candidates"]) == 9   # the 9 returned stay on record


def test_nine_returned_all_at_least_15_is_rejected_and_the_cap_is_not_raised(tmp_path):
    d, t = run_scenario(tmp_path, 140, {1: [15] * 8, 2: [20]}, echo)
    with pytest.raises(SystemExit):
        dv.run_stage_b(d, t, candidates_path=tmp_path / "c.json")
    att = [a for a in store.load_jsonl(d / dv.STAGE_B_FILE) if a["kind"] == "final"]
    assert len(att) == params.MAX_ATTEMPTS and not any(a["accepted"] for a in att)
    assert "9 remain; at most 8 are allowed" in att[0]["problems"][0] and params.MAX_CANDIDATES == 8 and not (tmp_path / "c.json").exists()


def test_eight_returned_all_at_least_15_is_accepted(tmp_path):
    d, t = run_scenario(tmp_path, 140, {1: [15] * 7, 2: [20]}, echo)
    rec = dv.run_stage_b(d, t, candidates_path=tmp_path / "c.json")
    assert len(rec["candidates"]) == 8 and rec["dropped"] == [] and t.calls == 3


# --------------------------------------------------------------------- by count alone, never by content -------
def shown(support_sizes, **text):
    base = [f"S{i:04d}" for i in range(1, 80)]
    return {"candidates": [cand(f"cand_{i}", base[:k], **text) for i, k in enumerate(support_sizes)]}


def survivors(obj, allowed):
    got, problems = prompts.validate_stage_b(obj, allowed, params.MIN_SUPPORT)
    assert problems == [], problems
    return [c["name"] for c in got if len(c["supporting_ids"]) >= params.MIN_SUPPORT]


def test_survival_depends_only_on_the_verified_count_not_on_order_text_or_name():
    allowed = {f"S{i:04d}" for i in range(1, 60)}                              # ids S0060-S0079 are NOT in the input
    sizes = [20, 14, 15, 16, 3, 40, 15, 17, 14]                                # 9 candidates; verified count = min(size, 59)
    base = survivors(shown(sizes), allowed)
    assert base == ["cand_0", "cand_2", "cand_3", "cand_5", "cand_6", "cand_7"]
    for seed in range(5):                                                       # shuffle the ORDER: the same counts survive
        order = list(range(len(sizes)))
        random.Random(seed).shuffle(order)
        obj = {"candidates": [cand(f"cand_{i}", [f"S{j:04d}" for j in range(1, sizes[i] + 1)]) for i in order]}
        assert sorted(survivors(obj, allowed)) == sorted(base)
    for text in ({"trigger": "a very attractive and clean breakout trigger"}, {"trigger": "x", "presence_rule": "y", "invalidation": "z"}):
        assert survivors(shown(sizes, **text), allowed) == base               # swapping ALL descriptive text changes nothing
    # citing many ids does not help if they cannot be verified; the unverified ids stay on record
    obj = {"candidates": [cand("padded", [f"S{i:04d}" for i in range(1, 11)] + [f"S9{i:03d}" for i in range(40)])]}
    got, p = prompts.validate_stage_b(obj, allowed, params.MIN_SUPPORT)
    assert p == [] and len(got[0]["supporting_ids"]) == 10 and len(got[0]["unverified_supporting_ids"]) == 40
    assert survivors(obj, allowed) == []


def test_pruning_code_reads_only_supporting_ids():
    import ast, inspect
    src = inspect.getsource(prompts.validate_stage_b)
    tree = ast.parse(src)
    keys = {n.slice.value for n in ast.walk(tree) if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)}
    survivor_lines = [l for l in src.splitlines() if "survivors = " in l]
    assert len(survivor_lines) == 1 and 'c["supporting_ids"]' in survivor_lines[0] and "min_support" in survivor_lines[0]
    assert {"trigger", "name", "direction", "context_definition"}.isdisjoint(set(survivor_lines[0].replace('"', " ").split()))


# --------------------------------------------------------------------------- F0b behaviour is intact ---------
def test_f0b_behaviour_chunk_cap_unknown_ids_and_zero_verified_are_unchanged():
    allowed = {f"S{i:04d}" for i in range(1, 30)}
    nine = {"candidates": [cand(f"c_{i}", ["S0001"]) for i in range(9)]}
    assert prompts.validate_stage_b(nine, allowed)[0] is None                        # chunk call: more than 8 RETURNED is still rejected
    assert "at most 8 candidates are allowed; got 9" in prompts.validate_stage_b(nine, allowed)[1][0]
    ok, p = prompts.validate_stage_b({"candidates": [cand("a_one", ["S0001", "S9999"])]}, allowed)
    assert p == [] and ok[0]["unverified_supporting_ids"] == ["S9999"]               # an unknown id alone does not reject
    for ms in (None, params.MIN_SUPPORT):                                            # no verified id at all rejects, in chunk and final
        assert prompts.validate_stage_b({"candidates": [cand("a_one", ["S9999"])]}, allowed, ms)[0] is None


def test_accepted_f0b_chunk_calls_are_reused_and_rejected_f0b_final_attempts_do_not_count(tmp_path):
    d, rows = b_run_dir(tmp_path, n=65)
    rule_b = "F0b_verified_citations"
    ids = [f"S{i:04d}" for i in range(6, 66)]
    chunk_c = [{**c, "cited_supporting_ids": c["supporting_ids"], "unverified_supporting_ids": []} for c in [cand("only_a", ids[:30])]]
    history = [{"rule": rule_b, "kind": "chunk", "index": 1, "attempt": 1, "accepted": True, "problems": [], "candidates": chunk_c, "raw": "{}"}]
    history += [{"rule": rule_b, "kind": "final", "index": 0, "attempt": i, "accepted": False, "problems": ["at most 8 candidates are allowed; got 9"],
                 "candidates": None, "raw": "{}"} for i in (1, 2, 3)]
    history = [{"kind": "chunk", "index": 1, "attempt": i, "accepted": False, "problems": ["old"], "candidates": None, "raw": "{}"} for i in (1, 2, 3)] + history
    (d / dv.STAGE_B_FILE).write_text("\n".join(json.dumps(r) for r in history) + "\n")
    t = FakeText(lambda u, n: echo(candidates_in(u)))
    rec = dv.run_stage_b(d, t, candidates_path=tmp_path / "c.json")
    assert t.calls == 1                                                              # the F0b chunk is reused; ONE fresh final call
    assert rec["earlier_rejected_attempts"] == {"F0 (no rule field)": 3, "F0b": 3} and len(rec["candidates"]) == 1
    lines = store.load_jsonl(d / dv.STAGE_B_FILE)
    assert lines[:len(history)] == history and lines[-1]["rule"] == dv.RULE and lines[-1]["kind"] == "final"   # history untouched, new row appended


def test_f0b_final_attempts_that_were_accepted_under_a_stricter_reading_are_not_reused_for_the_final_call(tmp_path):
    d, rows = b_run_dir(tmp_path, n=65)
    ids = [f"S{i:04d}" for i in range(6, 66)]
    c = {**cand("only_a", ids[:30]), "cited_supporting_ids": ids[:30], "unverified_supporting_ids": []}
    hist = [{"rule": "F0b_verified_citations", "kind": "chunk", "index": 1, "attempt": 1, "accepted": True, "problems": [], "candidates": [c], "raw": "{}"},
            {"rule": "F0b_verified_citations", "kind": "final", "index": 0, "attempt": 1, "accepted": True, "problems": [], "candidates": [c], "raw": "{}"}]
    (d / dv.STAGE_B_FILE).write_text("\n".join(json.dumps(r) for r in hist) + "\n")
    t = FakeText(lambda u, n: echo(candidates_in(u)))
    dv.run_stage_b(d, t, candidates_path=tmp_path / "c.json")
    assert t.calls == 1                                                              # the final call is made afresh under F0c


def test_no_outcome_data_enters_the_final_merge(tmp_path):
    d, t = run_scenario(tmp_path, 125, {1: [15] * 8, 2: [5]}, echo)
    poisoned = [json.loads(l) for l in (d / dv.STAGE_A_FILE).read_text().splitlines()]
    for r in poisoned:
        r.update({"ret_24": 123.456, "outcome": "WIN_SECRET", "forward_return": 77.7})
    (d / dv.STAGE_A_FILE).write_text("\n".join(json.dumps(r) for r in poisoned) + "\n")
    seen = []
    orig = t.fn
    t.fn = lambda u, n: (seen.append(u), orig(u, n))[1]
    dv.run_stage_b(d, t, candidates_path=tmp_path / "c.json")
    assert not any(w in "\n".join(seen) for w in ("123.456", "WIN_SECRET", "77.7", "ret_24", "forward_return"))


# -------------------------------------------------------------------------------------- the F0c lock ---------
@pytest.fixture
def f0c_env(tmp_path, monkeypatch):
    cur = lock.current_record()
    f0 = {"locked_at": "2026-10-07T15:22:14+00:00", "git_commit": "f0commit", **cur}
    f0["sha256"] = dict(cur["sha256"])
    for k in lock.F0B_AMENDED:
        f0["sha256"][k] = "0" * 64                                   # F0 predates both amendments
    f0p = tmp_path / "f0.json"
    f0p.write_text(json.dumps(f0))
    run = tmp_path / "run"
    run.mkdir()
    for n in lock.F0B_PRESERVED:
        (run / n).write_text(f"record {n}\n")
    (run / "stage_b_attempts.jsonl").write_text("\n".join(json.dumps({"attempt": i}) for i in range(1, 9)) + "\n")
    (run / "cost_log.jsonl").write_text("\n".join(json.dumps({"call": i}) for i in range(1, 8)) + "\n")
    # an F0b lock written when only the first 3 attempt lines and 5 cost lines existed, with F0b hashes that are now stale
    f0b = {"locked_at": "2026-10-08T04:31:57+00:00", "git_commit": "f0bcommit",
           "amended_files": {k: {"f0_sha256": "0" * 64, "f0b_sha256": "1" * 64} for k in lock.F0B_AMENDED},
           "preserved_append_only_prefixes": {"stage_b_attempts.jsonl": lock._lines_sha(run / "stage_b_attempts.jsonl", 3),
                                              "cost_log.jsonl": lock._lines_sha(run / "cost_log.jsonl", 5)}}
    f0bp = tmp_path / "f0b.json"
    f0bp.write_text(json.dumps(f0b))
    return f0p, f0bp, run, tmp_path / "f0c.json"


def write_f0c(f0p, f0bp, run, path):
    rec = lock.f0c_record(run, f0p, f0bp)
    path.write_text(json.dumps({"locked_at": "x", **rec}))
    return rec


def test_f0c_records_all_three_hashes_and_verifies(f0c_env):
    f0p, f0bp, run, f0c = f0c_env
    rec = write_f0c(f0p, f0bp, run, f0c)
    assert set(rec["amended_files"]) == set(lock.F0B_AMENDED)
    assert all(v["f0_sha256"] == "0" * 64 and v["f0b_sha256"] == "1" * 64 and v["f0c_sha256"] not in ("0" * 64, "1" * 64) for v in rec["amended_files"].values())
    assert rec["original_f0_lock"]["file_sha256"] == lock.file_sha256(f0p) and rec["earlier_amendment_f0b"]["lock_file_sha256"] == lock.file_sha256(f0bp)
    assert rec["preserved_append_only_prefixes"]["stage_b_attempts.jsonl"]["lines"] == 8       # 3 F0 + 5 F0b rows in the real file
    assert lock.verify_f0c(f0c, run, f0p, f0bp)["f0c"]["amendment"]["id"] == "F0c"


def test_f0c_refuses_when_another_frozen_file_differs_from_the_f0_lock(f0c_env):
    f0p, f0bp, run, f0c = f0c_env
    f0 = json.loads(f0p.read_text())
    f0["sha256"]["src/setups/sampling.py"] = "2" * 64
    f0p.write_text(json.dumps(f0))
    with pytest.raises(SystemExit):
        lock.f0c_record(run, f0p, f0bp)


def test_f0c_detects_tampering_but_allows_appending(f0c_env):
    f0p, f0bp, run, f0c = f0c_env
    write_f0c(f0p, f0bp, run, f0c)
    with open(run / "stage_b_attempts.jsonl", "a") as f:
        f.write(json.dumps({"attempt": 9}) + "\n")
    with open(run / "cost_log.jsonl", "a") as f:
        f.write(json.dumps({"call": 8}) + "\n")
    assert lock.verify_f0c(f0c, run, f0p, f0bp)                                       # appending (a new Stage B run) is fine
    good = (run / "stage_b_attempts.jsonl").read_text()
    lines = good.splitlines()
    (run / "stage_b_attempts.jsonl").write_text("\n".join([lines[0]] + [json.dumps({"attempt": 99})] + lines[2:]) + "\n")   # edit a preserved line
    with pytest.raises(SystemExit):
        lock.verify_f0c(f0c, run, f0p, f0bp)
    (run / "stage_b_attempts.jsonl").write_text(good)
    assert lock.verify_f0c(f0c, run, f0p, f0bp)
    for target in (f0p, f0bp):                                                         # neither earlier lock may ever be edited
        original = target.read_text()
        d = json.loads(original)
        d["locked_at"] = "tampered"
        target.write_text(json.dumps(d))
        with pytest.raises(SystemExit):
            lock.verify_f0c(f0c, run, f0p, f0bp)
        target.write_text(original)
    (run / "stage_a.jsonl").write_text("changed\n")
    with pytest.raises(SystemExit):
        lock.verify_f0c(f0c, run, f0p, f0bp)


def test_the_latest_lock_governs_and_is_written_once(f0c_env, monkeypatch):
    f0p, f0bp, run, f0c = f0c_env
    write_f0c(f0p, f0bp, run, f0c)
    for name, val in (("DESIGN_LOCK", f0p), ("F0B_LOCK", f0bp), ("F0C_LOCK", f0c), ("RUN_DIR", run)):
        monkeypatch.setattr(lock, name, val)
    assert lock.verify_design_lock()["f0c"]["amendment"]["id"] == "F0c"
    sha12 = json.loads(f0p.read_text())["sha256"]["preregistration_setups"][:12]
    assert lock.require_design_lock(sha12)
    with pytest.raises(SystemExit):
        lock.main(["--write-f0c", "--db", "data/market_Data_Clean.db"])
