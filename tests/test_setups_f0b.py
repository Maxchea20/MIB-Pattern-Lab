"""Amendment F0b: unknown supporting ids are dropped and audited, support = distinct VERIFIED ids, no outcome involved."""
import json
import shutil
from pathlib import Path

import pytest

from src.setups import discover as dv, lock, params, prompts, store
from tests.test_setups_discover import FakeText, b_run_dir, cand, stage_a_ok


# ------------------------------------------------------------------------ verify_citations ----------
def test_unknown_ids_never_count_known_ids_do_and_mixed_keeps_only_verified():
    c = cand(ids=["S0001", "S0002", "S0001", "S9999", "S0003", "S8888"])
    (v,) = prompts.verify_citations([c], {"S0001", "S0002", "S0003", "S0004"})
    assert v["supporting_ids"] == ["S0001", "S0002", "S0003"]                          # distinct, sorted, verified only
    assert v["unverified_supporting_ids"] == ["S8888", "S9999"]                        # never silently discarded
    assert v["cited_supporting_ids"] == ["S0001", "S0002", "S0001", "S9999", "S0003", "S8888"]   # verbatim, order and duplicates kept
    assert set(v["supporting_ids"]) <= set(c["supporting_ids"]) & {"S0001", "S0002", "S0003", "S0004"}   # nothing substituted or inferred
    (u,) = prompts.verify_citations([cand(ids=["S7001", "S7002"])], {"S0001"})
    assert u["supporting_ids"] == [] and u["unverified_supporting_ids"] == ["S7001", "S7002"]      # unknown ids give no support at all
    (k,) = prompts.verify_citations([cand(ids=["S0001", "S0002"])], {"S0001", "S0002", "S0003"})
    assert k["supporting_ids"] == ["S0001", "S0002"] and k["unverified_supporting_ids"] == []      # the S0003 the model did not cite is NOT added


def test_validation_rejects_only_structural_problems_or_a_candidate_without_any_verified_id():
    allowed = {f"S{i:04d}" for i in range(1, 30)}
    ok, p = prompts.validate_stage_b({"candidates": [cand(ids=["S0001", "S9999"])]}, allowed)
    assert p == [] and ok[0]["supporting_ids"] == ["S0001"] and ok[0]["unverified_supporting_ids"] == ["S9999"]   # an unknown id alone does not reject
    none, p = prompts.validate_stage_b({"candidates": [cand(ids=["S9998", "S9999"])]}, allowed)
    assert none is None and "none of its supporting_ids" in p[0]
    assert prompts.validate_stage_b({"candidates": [cand(ids=["S0001"], direction="long")]}, allowed)[0] is None
    assert prompts.validate_stage_b({"candidates": [cand(ids=["S0001"], trigger="it will win")]}, allowed)[0] is None
    assert prompts.validate_stage_b({"candidates": [cand("a_one", ["S0001"]), cand("a_one", ["S0002"])]}, allowed)[0] is None


def test_render_candidates_shows_only_the_nine_prompt_keys():
    (v,) = prompts.verify_citations([cand(ids=["S0001", "S9999"])], {"S0001"})
    shown = json.loads(prompts.render_candidates([v]))
    assert set(shown[0]) == set(prompts.B_KEYS) and shown[0]["supporting_ids"] == ["S0001"]
    assert "S9999" not in prompts.render_candidates([v])


# ---------------------------------------------------------------------------- end to end ----------
def ids(a, b):
    return [f"S{i:04d}" for i in range(a, b + 1)]


def test_stage_b_counts_only_verified_support_and_keeps_the_audit(tmp_path):
    d, rows = b_run_dir(tmp_path, n=65)                      # S0001-S0005 are NONE; S0006-S0065 are described
    seen = []

    def fn(user, n):
        seen.append(user)
        if "Descriptions:" in user:                          # chunk call: 30 + 16 + 10 verified ids, with unknown ids mixed in
            return {"candidates": [cand("big_a", ids(6, 35) + ["S9001", "S9002"]), cand("mid_b", ids(40, 55) + ["S9003"]),
                                   cand("small_c", ids(56, 65))]}
        return {"candidates": [cand("big_a", ids(6, 35) + ["S9100"]),                        # 30 verified + 1 unknown -> kept
                               cand("lost_b", ids(40, 53) + ["S9101", "S9102"]),             # 14 verified + 2 unknown -> dropped (<15)
                               cand("edge_d", ids(6, 20) + ["S9103"])]}                      # exactly 15 verified + 1 unknown -> kept

    out = tmp_path / "cands.json"
    rec = dv.run_stage_b(d, FakeText(fn), candidates_path=out)
    kept = {c["name"]: c for c in rec["candidates"]}
    assert set(kept) == {"big_a", "edge_d"} and len(kept["edge_d"]["supporting_ids"]) == 15 == params.MIN_SUPPORT
    assert kept["big_a"]["unverified_supporting_ids"] == ["S9100"] and "S9100" not in kept["big_a"]["supporting_ids"]
    (dropped,) = rec["dropped"]
    assert dropped["name"] == "lost_b" and dropped["verified_distinct_supporting_descriptions"] == 14 and dropped["cited_distinct"] == 16
    assert dropped["unverified_supporting_ids"] == ["S9101", "S9102"]
    assert rec["rule"] == dv.RULE and rec["earlier_rejected_attempts"] == {"F0 (no rule field)": 0, "F0b": 0}
    # the audit of the chunk call is in the candidate file AND in the attempt record
    assert any(a["unverified_supporting_ids"] == ["S9001", "S9002"] for a in rec["chunk_citation_audit"][0])
    attempts = store.load_jsonl(d / dv.STAGE_B_FILE)
    assert all(a["rule"] == dv.RULE for a in attempts) and [a["kind"] for a in attempts] == ["chunk", "final"]
    assert attempts[0]["candidates"][0]["unverified_supporting_ids"] == ["S9001", "S9002"]
    assert attempts[1]["citation_audit"][1]["verified_distinct"] == 14
    # the final call saw only the verified ids of the chunk candidates, never the unknown ones
    assert "S9001" not in seen[-1] and "S9003" not in seen[-1]


def test_final_call_is_verified_against_the_ids_in_its_own_input(tmp_path):
    d, rows = b_run_dir(tmp_path, n=65)

    def fn(user, n):
        if "Descriptions:" in user:
            return {"candidates": [cand("only_a", ids(6, 25))]}
        return {"candidates": [cand("only_a", ids(6, 25) + ids(26, 40))]}               # S0026-S0040 are REAL charts, but not in the final input

    rec = dv.run_stage_b(d, FakeText(fn), candidates_path=tmp_path / "c.json")
    (c,) = rec["candidates"]
    assert c["supporting_ids"] == ids(6, 25) and c["unverified_supporting_ids"] == ids(26, 40)


def test_attempts_made_under_the_f0_rule_do_not_count_and_stay_in_the_file(tmp_path):
    d, rows = b_run_dir(tmp_path, n=65)
    old = [{"kind": "chunk", "index": 1, "attempt": i, "accepted": False, "problems": ["supporting_ids not found"], "candidates": None, "raw": "{}"}
           for i in (1, 2, 3)]
    (d / dv.STAGE_B_FILE).write_text("\n".join(json.dumps(r) for r in old) + "\n")
    t = FakeText(lambda u, n: {"candidates": [cand("x_setup", ids(6, 30))]})
    rec = dv.run_stage_b(d, t, candidates_path=tmp_path / "c.json")
    assert t.calls == 2 and rec["earlier_rejected_attempts"]["F0 (no rule field)"] == 3 and len(rec["candidates"]) == 1
    lines = store.load_jsonl(d / dv.STAGE_B_FILE)
    assert lines[:3] == old and all(r.get("rule") == dv.RULE for r in lines[3:])         # history preserved, appended after


def test_no_outcome_data_enters_stage_b(tmp_path):
    d, rows = b_run_dir(tmp_path, n=40)
    poisoned = [json.loads(l) for l in (d / dv.STAGE_A_FILE).read_text().splitlines()]
    for r in poisoned:
        r.update({"ret_24": 123.456, "mfe_12": 9.87, "outcome": "WIN_SECRET", "forward_return": 77.7})
    (d / dv.STAGE_A_FILE).write_text("\n".join(json.dumps(r) for r in poisoned) + "\n")
    seen = []

    def fn(user, n):
        seen.append(user)
        return {"candidates": [cand("x_setup", ids(6, 40))]}

    dv.run_stage_b(d, FakeText(fn), candidates_path=tmp_path / "c.json")
    text = "\n".join(seen)
    assert not any(w in text for w in ("123.456", "9.87", "WIN_SECRET", "77.7", "ret_24", "mfe_12", "forward_return"))


# ----------------------------------------------------------------------------------- F0b lock ----------
@pytest.fixture
def f0b_env(tmp_path, monkeypatch):
    """A tiny world in which the F0 lock was written BEFORE prompts.py / discover.py changed (their F0 hashes are stale)."""
    cur = lock.current_record()
    f0 = {"locked_at": "2026-10-07T15:22:14+00:00", "git_commit": "deadbeef", **cur}
    f0["sha256"] = dict(cur["sha256"])
    for k in lock.F0B_AMENDED:
        f0["sha256"][k] = "0" * 64                           # what F0 recorded before the amendment
    f0p = tmp_path / "f0.json"
    f0p.write_text(json.dumps(f0))
    run = tmp_path / "run"
    run.mkdir()
    for n in lock.F0B_PRESERVED:
        (run / n).write_text(f"record {n}\n")
    (run / "stage_b_attempts.jsonl").write_text("\n".join(json.dumps({"attempt": i}) for i in (1, 2, 3)) + "\n")
    (run / "cost_log.jsonl").write_text("\n".join(json.dumps({"call": i}) for i in range(1, 6)) + "\n")
    return f0p, run, tmp_path / "f0b.json"


def write_f0b(f0p, run, path):
    rec = lock.f0b_record(run, f0p)
    path.write_text(json.dumps({"locked_at": "x", **rec}))
    return rec


def test_f0b_records_both_hashes_of_exactly_the_two_amended_files_and_verifies(f0b_env):
    f0p, run, f0b = f0b_env
    rec = write_f0b(f0p, run, f0b)
    assert set(rec["amended_files"]) == set(lock.F0B_AMENDED)
    assert all(v["f0_sha256"] == "0" * 64 and v["f0b_sha256"] != "0" * 64 for v in rec["amended_files"].values())
    assert rec["original_f0_lock"]["file_sha256"] == lock.file_sha256(f0p) and rec["amendment"]["document_sha256"]
    assert set(rec["tests_sha256"]) >= {"tests/test_setups_f0b.py", "tests/test_setups_discover.py"}
    assert lock.verify_f0b(f0b, run, f0p)["f0b"]["amendment"]["id"] == "F0b"


def test_f0b_refuses_when_any_other_frozen_file_differs_from_the_f0_lock(f0b_env):
    f0p, run, f0b = f0b_env
    f0 = json.loads(f0p.read_text())
    f0["sha256"]["src/setups/params.py"] = "1" * 64
    f0p.write_text(json.dumps(f0))
    with pytest.raises(SystemExit):
        lock.f0b_record(run, f0p)


def test_f0b_detects_tampering_with_every_preserved_thing(f0b_env, tmp_path):
    f0p, run, f0b = f0b_env
    write_f0b(f0p, run, f0b)
    # appending to the append-only files is allowed (Stage B re-runs add attempts and cost lines) ...
    with open(run / "stage_b_attempts.jsonl", "a") as f:
        f.write(json.dumps({"attempt": 4}) + "\n")
    with open(run / "cost_log.jsonl", "a") as f:
        f.write(json.dumps({"call": 6}) + "\n")
    assert lock.verify_f0b(f0b, run, f0p)
    # ... editing an existing line is not
    lines = (run / "stage_b_attempts.jsonl").read_text().splitlines()
    (run / "stage_b_attempts.jsonl").write_text("\n".join([json.dumps({"attempt": 99})] + lines[1:]) + "\n")
    with pytest.raises(SystemExit):
        lock.verify_f0b(f0b, run, f0p)
    (run / "stage_b_attempts.jsonl").write_text("\n".join(lines) + "\n")
    assert lock.verify_f0b(f0b, run, f0p)
    (run / "stage_a.jsonl").write_text("changed\n")                                   # Stage A record
    with pytest.raises(SystemExit):
        lock.verify_f0b(f0b, run, f0p)
    (run / "stage_a.jsonl").write_text("record stage_a.jsonl\n")
    f0 = json.loads(f0p.read_text())                                                    # the original F0 lock file itself
    f0["locked_at"] = "tampered"
    f0p.write_text(json.dumps(f0))
    with pytest.raises(SystemExit):
        lock.verify_f0b(f0b, run, f0p)


def test_f0b_lock_is_written_once_and_governs_afterwards(f0b_env, monkeypatch):
    f0p, run, f0b = f0b_env
    write_f0b(f0p, run, f0b)
    monkeypatch.setattr(lock, "F0B_LOCK", f0b)
    monkeypatch.setattr(lock, "F0C_LOCK", f0b.parent / "no_f0c_lock_here.json")
    monkeypatch.setattr(lock, "RUN_DIR", run)
    monkeypatch.setattr(lock, "DESIGN_LOCK", f0p)
    assert lock.verify_design_lock()["f0b"]["amendment"]["id"] == "F0b"               # F0b is what verify_design_lock() checks now
    sha12 = json.loads(f0p.read_text())["sha256"]["preregistration_setups"][:12]
    assert lock.require_design_lock(sha12)
    with pytest.raises(SystemExit):
        lock.main(["--write-f0b", "--db", "data/market_Data_Clean.db"])               # refuses the wrong database before anything else
