"""F1: the setup definitions are frozen exactly as returned; the record covers Stage A, Stage B (with the failed attempts),
the cost log and the lock chain; nothing may change afterwards; the discovery AI steps are closed."""
import json
import shutil
from pathlib import Path

import pytest

from src.setups import lock, params

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results" / "setups" / "discovery"


@pytest.fixture
def env(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    for n in lock.F1_RUN_FILES:
        shutil.copy(RUN / n, run / n)
    cand = tmp_path / "SETUP_CANDIDATES.json"
    shutil.copy(lock.CANDIDATES, cand)
    return run, cand, tmp_path / "f1.json"


def write(run, cand, f1):
    rec = lock.f1_record(run, cand)
    f1.write_text(json.dumps({"locked_at": "x", **rec}))
    return rec


def test_record_freezes_the_real_candidates_stage_a_stage_b_and_costs(env):
    run, cand, f1 = env
    rec = write(run, cand, f1)
    assert rec["candidates_file"]["n_candidates"] == len(rec["candidates"]) <= params.MAX_CANDIDATES
    assert all(c["verified_supporting_descriptions"] >= params.MIN_SUPPORT for c in rec["candidates"])
    assert rec["stage_a"]["n_descriptions"] == 558 and sum(rec["stage_a"]["status_counts"].values()) == 558
    rows = rec["stage_b"]["rows"]
    assert len(rows) == rec["stage_b"]["attempt_rows"] and sum(1 for r in rows if r["rule"] == "F0") == 3     # the failed attempts are frozen too
    assert sum(1 for r in rows if r["rule"].startswith("F0b") and not r["accepted"]) == 3
    assert rec["cost"]["lines"] > 0 and set(rec["files_sha256"]) == set(lock.F1_RUN_FILES)
    assert set(rec["locks_sha256"]) == {"f0", "f0b", "f0c", "amendment_f0b", "amendment_f0c"}
    assert lock.verify_f1(f1, run, cand)["id"] == "F1"


def test_the_candidate_file_must_be_exactly_the_accepted_final_response(env):
    run, cand, f1 = env
    d = json.loads(cand.read_text())
    d["candidates"][0]["name"] = "renamed_by_hand"                              # a rename after the model returned it
    cand.write_text(json.dumps(d))
    with pytest.raises(SystemExit):
        lock.f1_record(run, cand)
    d = json.loads(lock.CANDIDATES.read_text())
    d["candidates"][0]["trigger"] = d["candidates"][0]["trigger"] + " plus a tweak"
    cand.write_text(json.dumps(d))
    with pytest.raises(SystemExit):
        lock.f1_record(run, cand)
    d = json.loads(lock.CANDIDATES.read_text())
    d["candidates"] = d["candidates"][:-1]                                       # removing a candidate
    cand.write_text(json.dumps(d))
    with pytest.raises(SystemExit):
        lock.f1_record(run, cand)
    d = json.loads(lock.CANDIDATES.read_text())
    d["candidates"].append(d["dropped"] and {**d["candidates"][0], "name": "added_by_hand"})   # adding / merging / splitting
    cand.write_text(json.dumps(d))
    with pytest.raises(SystemExit):
        lock.f1_record(run, cand)


def test_nothing_in_the_frozen_record_may_change_afterwards(env):
    run, cand, f1 = env
    write(run, cand, f1)
    assert lock.verify_f1(f1, run, cand)
    # a candidate's text
    original = cand.read_text()
    d = json.loads(original)
    d["candidates"][3]["invalidation"] = "changed"
    cand.write_text(json.dumps(d))
    with pytest.raises(SystemExit):
        lock.verify_f1(f1, run, cand)
    cand.write_text(original)
    assert lock.verify_f1(f1, run, cand)
    # every run file is frozen as a WHOLE: no appended AI call, no edit
    for name in lock.F1_RUN_FILES:
        before = (run / name).read_bytes()
        with open(run / name, "ab") as fh:
            fh.write(b'{"appended": true}\n' if name.endswith("l") else b" ")
        with pytest.raises(SystemExit):
            lock.verify_f1(f1, run, cand)
        (run / name).write_bytes(before)
        assert lock.verify_f1(f1, run, cand)
    # one Stage A description edited
    lines = (run / "stage_a.jsonl").read_text().splitlines()
    r = json.loads(lines[0])
    r["parsed"]["status"] = "NONE" if r["parsed"]["status"] != "NONE" else "DEVELOPING"
    (run / "stage_a.jsonl").write_text("\n".join([json.dumps(r)] + lines[1:]) + "\n")
    with pytest.raises(SystemExit):
        lock.verify_f1(f1, run, cand)


def test_f1_requires_a_complete_stage_a_and_the_design_chain(env, monkeypatch):
    run, cand, f1 = env
    lines = (run / "stage_a.jsonl").read_text().splitlines()
    (run / "stage_a.jsonl").write_text("\n".join(lines[1:]) + "\n")             # drop the first chart's row
    with pytest.raises(SystemExit):
        lock.f1_record(run, cand)
    (run / "stage_a.jsonl").write_text("\n".join(lines) + "\n")
    monkeypatch.setattr(lock, "F0C_LOCK", run / "no_such_f0c.json")             # the F0 -> F0b -> F0c chain must hold
    with pytest.raises(SystemExit):
        lock.f1_record(run, cand)


def test_after_f1_the_discovery_ai_steps_are_closed_but_read_only_verification_still_works(env, monkeypatch, tmp_path):
    run, cand, f1 = env
    write(run, cand, f1)
    sha12 = json.loads(lock.F0C_LOCK.read_text())["original_f0_lock"]  # noqa: F841  (chain is intact)
    monkeypatch.setattr(lock, "F1_LOCK", f1)
    pre = lock.verify_design_lock()["sha256"]["preregistration_setups"][:12]
    with pytest.raises(SystemExit) as e:
        lock.require_design_lock(pre)                                           # sampling / Stage A / Stage B all start here
    assert "closed" in str(e.value)
    assert lock.verify_design_lock()                                            # the chain itself still verifies
    # later stages go through require_f1
    monkeypatch.setattr(lock, "RUN_DIR", run)
    monkeypatch.setattr(lock, "CANDIDATES", cand)
    assert lock.require_f1(pre)
    with pytest.raises(SystemExit):
        lock.require_f1("000000000000")
    with pytest.raises(SystemExit):
        lock.require_f1(None)


def test_f1_lock_is_written_once_and_only_for_the_canonical_database(env, monkeypatch, tmp_path):
    run, cand, f1 = env
    monkeypatch.setattr(lock, "F1_LOCK", f1)
    with pytest.raises(SystemExit):
        lock.main(["--write-f1", "--db", str(tmp_path / "market_Data_Clean.db")])
    assert not f1.exists()
    f1.write_text("{}")
    monkeypatch.setattr(lock, "verify_database", lambda p: {"file": "research_binance.db", "bytes": params.EXPECTED_DB_BYTES, "sha256": params.EXPECTED_DB_SHA256})
    with pytest.raises(SystemExit) as e:
        lock.main(["--write-f1"])
    assert "already exists" in str(e.value)


def test_f1_module_never_reaches_outcome_code():
    import ast
    for node in ast.walk(ast.parse((ROOT / "src" / "setups" / "lock.py").read_text(encoding="utf-8"))):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else ([node.module or ""] if isinstance(node, ast.ImportFrom) else [])
        assert not any(w in n.lower() for n in names for w in ("outcome", "forward")), names
