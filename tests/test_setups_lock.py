import ast
import json
from pathlib import Path

import pytest

from src.setups import lock, params

ROOT = Path(__file__).resolve().parents[1]
SETUPS = ROOT / "src" / "setups"


def test_database_verification(tmp_path, monkeypatch):
    good = tmp_path / "research_binance.db"
    good.write_bytes(b"abc")
    monkeypatch.setattr(params, "EXPECTED_DB_BYTES", 3)
    monkeypatch.setattr(params, "EXPECTED_DB_SHA256", lock.sha256_file_bytes(good))
    assert lock.verify_database(good)["bytes"] == 3
    good.write_bytes(b"abd")
    with pytest.raises(SystemExit):
        lock.verify_database(good)                                           # same size, different content
    for name in ("market_Data_Clean.db", "MARKET_DATA_CLEAN.DB", "other.db"):
        (tmp_path / name).write_bytes(b"abc")
        with pytest.raises(SystemExit):
            lock.verify_database(tmp_path / name)
    with pytest.raises(SystemExit):
        lock.verify_database(tmp_path / "missing" / "research_binance.db")


def test_design_lock_record_verifies_and_detects_changes(tmp_path):
    rec = lock.current_record()
    assert rec["dataset"]["sha256"] == params.EXPECTED_DB_SHA256 and rec["dataset"]["bytes"] == 71_098_368
    assert "canonical dataset for the Setup Discovery experiment" in rec["dataset"]["statement"]
    assert set(lock.DESIGN_FILES) <= set(rec["sha256"]) and all(rec["archive_intact"].values())
    p = tmp_path / "lock.json"
    p.write_text(json.dumps({"locked_at": "x", **rec}))
    assert lock.verify_design_lock(p)["experiment"] == params.EXPERIMENT
    sha12 = rec["sha256"]["preregistration_setups"][:12]
    assert lock.require_design_lock(sha12, p)
    for bad in (None, "", "000000000000", sha12[:6]):
        with pytest.raises(SystemExit):
            lock.require_design_lock(bad, p)
    t = json.loads(p.read_text())
    t["sha256"]["src/setups/params.py"] = "0" * 64
    p.write_text(json.dumps(t))
    with pytest.raises(SystemExit):
        lock.verify_design_lock(p)
    t = json.loads(p.read_text())
    t["sha256"]["src/setups/params.py"] = rec["sha256"]["src/setups/params.py"]
    t["parameters"]["CAP_TOTAL"] = 99.0
    p.write_text(json.dumps(t))
    with pytest.raises(SystemExit):
        lock.verify_design_lock(p)
    with pytest.raises(SystemExit):
        lock.verify_design_lock(tmp_path / "missing.json")


def test_lock_is_written_once_and_refuses_without_the_canonical_database(tmp_path, monkeypatch):
    monkeypatch.setattr(lock, "DESIGN_LOCK", tmp_path / "lock.json")
    with pytest.raises(SystemExit):
        lock.main(["--write", "--db", str(tmp_path / "market_Data_Clean.db")])
    assert not (tmp_path / "lock.json").exists()


# ---------------------------------------------------------------- firewall: discovery code never reaches outcome code ----
FORBIDDEN_IMPORT_PARTS = ("outcome", "forward", "outcomes5m")


def test_setups_modules_never_import_outcome_or_forward_code():
    files = sorted(SETUPS.glob("*.py"))
    assert files
    for f in files:
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [f"{node.module}.{a.name}" for a in node.names]
            for n in names:
                assert not any(part in n.lower() for part in FORBIDDEN_IMPORT_PARTS), f"{f.name} imports {n}"


def test_no_outcome_module_exists_yet_and_archived_outcome_package_is_untouched():
    assert not [f for f in SETUPS.glob("*.py") if "outcome" in f.name.lower() or "forward" in f.name.lower()]
    freeze = json.loads((ROOT / "docs" / "OUTCOME_CODE_FREEZE.json").read_text())["files"]
    assert {x for x in freeze if x.startswith("src/outcomes/")} == {f"src/outcomes/{p.name}" for p in (ROOT / "src" / "outcomes").glob("*.py")}


def test_setups_is_a_protected_directory_for_the_real_fills_tripwire():
    from tests import policy_guard
    assert "src/setups/" in policy_guard.PROTECTED_DIRS
