"""Tripwires for the permanent REAL-FILLS policy (docs/REAL_FILLS_POLICY.md).

They do not prove a future backtest correct. They keep the required wording in the documents and make it impossible to
add execution/backtest behaviour by accident before an execution specification is frozen. The guard is BEHAVIOURAL
(tests/policy_guard.py parses the code): names such as execution_orders.py, fill_audit.py or order_simulator.py are fine.
"""
import hashlib
import json
import re
from pathlib import Path

import pytest

import config
from tests import policy_guard as pg

ROOT = Path(config.ROOT)
POLICY = ROOT / "docs" / "REAL_FILLS_POLICY.md"
REQUIRED_SENTENCE = ("Forward return, future high, future low, MFE and MAE are descriptive statistics of the historical "
                     "price series, measured from the close of the last candle of each visual window. They are not trade "
                     "fills, they were not shown to be executable prices, and they must not be read as realized trades.")


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace(">", " ").replace('"', "")).strip()


def test_policy_exists_with_its_core_rules():
    t = squash(POLICY.read_text(encoding="utf-8"))
    for phrase in ["PERMANENT", "A profitable backtest with impossible or unproven fills is a FAILED BACKTEST",
                   "Optimise for historical truth", "do not invent an order", "Never choose whichever sequence produces the better result",
                   "No hindsight fills", "No best-price selection", "UNKNOWN", "AMBIGUOUS", "frozen (hashed and committed) BEFORE the trading backtest",
                   "No optimisation against execution assumptions", "If the system cannot answer these questions, the fill is not valid",
                   "NOT trading backtests"]:
        assert squash(phrase) in t, phrase
    assert squash(REQUIRED_SENTENCE) in t


def test_documents_carry_the_required_wording_and_links():
    prereg = squash((ROOT / "docs" / "PREREGISTRATION_5M.md").read_text(encoding="utf-8"))
    assert "REAL_FILLS_POLICY.md" in prereg and squash(REQUIRED_SENTENCE) in prereg
    assert "descriptive statistics, not trade fills" in prereg
    assert "summary.json" in prereg and "limitation_statement" in prereg
    assert "REAL_FILLS_POLICY.md" in (ROOT / "README.md").read_text(encoding="utf-8")


# ------------------------------------------------------------------ behavioural guard ------------------------------
def write(root: Path, rel: str, text: str) -> None:
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")


def kinds(findings):
    return sorted((f[0], f[2]) for f in findings)


def test_the_real_repository_complies_at_this_research_stage():
    findings, problems = pg.check_repo(ROOT)
    assert findings == [] and problems == []
    assert not (ROOT / pg.GATE_FILE).exists()                      # no frozen execution spec exists yet


def test_innocent_names_are_not_rejected(tmp_path):
    write(tmp_path, "src/execution_orders.py", "ORDERS_SEEN = 0\n\ndef summarise():\n    return ORDERS_SEEN\n")
    write(tmp_path, "src/fill_audit.py", "def fill_audit(rows):\n    return len(rows)\n")
    write(tmp_path, "src/order_simulator.py", "class OrderSimulator:\n    def describe(self):\n        return 'nothing is placed'\n")
    write(tmp_path, "src/notes.py", '''"""Mentions stop_loss, take_profit and api.binance.com only in prose."""\n# comment: place_order(stop_loss=1)\nX = 1\n''')
    findings, problems = pg.check_repo(tmp_path)
    assert findings == [] and problems == []


@pytest.mark.parametrize("code,kind", [
    ("import ccxt\n", "import"),
    ("from backtrader import Cerebro\n", "import"),
    ("from autotrader import engine\n", "import"),
    ("def go(exchange):\n    exchange.create_order('BTC/USDT', 'limit', 'buy', 1, 100)\n", "call"),
    ("def go(sim):\n    sim.simulate_fill(candle)\n", "call"),
    ("def go():\n    return run(stop_loss=0.01)\n", "execution-parameter"),
    ("def go(row):\n    return row['fill_price']\n", "execution-key"),
    ("CFG = {'slippage': 0.0005}\n", "execution-key"),
    ("URL = 'https://fapi.binance.com/fapi/v1/order'\n", "exchange-host"),
])
def test_prohibited_behaviour_is_caught_under_any_filename(tmp_path, code, kind):
    write(tmp_path, "src/harmless_looking_name.py", code)
    findings, _ = pg.check_repo(tmp_path)
    assert [f[2] for f in findings] == [kind] and findings[0][0] == "src/harmless_looking_name.py"


def make_gate(root: Path, **over):
    spec = root / "docs" / "EXECUTION_SPEC_v1.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("frozen execution specification\n")
    (root / "docs" / "discovery_pass.json").write_text("{}")
    (root / "docs" / "holdout_pass.json").write_text("{}")
    lock = {"spec_file": "docs/EXECUTION_SPEC_v1.md", "spec_sha256": hashlib.sha256(spec.read_bytes()).hexdigest(),
            "source_experiment": "5m_v1", "discovery_pass_record": "docs/discovery_pass.json",
            "holdout_pass_record": "docs/holdout_pass.json", "checklist_complete": True,
            "allowed_paths": ["src/execution/*.py"], "frozen_at": "2030-01-01T00:00:00Z", **over}
    (root / pg.GATE_FILE).write_text(json.dumps(lock))
    return lock


def test_execution_code_is_allowed_only_behind_a_valid_frozen_spec_and_only_in_named_paths(tmp_path):
    exec_code = "def go(exchange):\n    exchange.create_order('x')\n"
    write(tmp_path, "src/execution/sim.py", exec_code)
    assert pg.check_repo(tmp_path)[0]                                   # no lock yet -> not permitted
    make_gate(tmp_path)
    assert pg.check_repo(tmp_path) == ([], [])                          # valid lock -> permitted in its own path
    write(tmp_path, "src/elsewhere.py", exec_code)
    assert [f[0] for f in pg.check_repo(tmp_path)[0]] == ["src/elsewhere.py"]      # but nowhere else
    write(tmp_path, "src/outcomes/analyze.py", exec_code)               # never inside a frozen research stage
    assert "src/outcomes/analyze.py" in [f[0] for f in pg.check_repo(tmp_path)[0]]


@pytest.mark.parametrize("over,expect", [
    ({"checklist_complete": False}, "checklist"),
    ({"spec_sha256": "0" * 64}, "frozen hash"),
    ({"holdout_pass_record": "docs/missing.json"}, "safeguards"),
    ({"allowed_paths": ["src/**"]}, "too broad"),
    ({"allowed_paths": ["src/exp5m/*.py"]}, "frozen research-stage"),
    ({"allowed_paths": []}, "empty"),
])
def test_an_invalid_or_weak_execution_lock_permits_nothing(tmp_path, over, expect):
    write(tmp_path, "src/execution/sim.py", "def go(e):\n    e.create_order(1)\n")
    make_gate(tmp_path, **over)
    findings, problems = pg.check_repo(tmp_path)
    assert findings and any(expect in p for p in problems)


def test_a_lock_missing_required_keys_is_a_problem(tmp_path):
    write(tmp_path, "src/execution/sim.py", "def go(e):\n    e.create_order(1)\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / pg.GATE_FILE).write_text(json.dumps({"spec_file": "x"}))
    findings, problems = pg.check_repo(tmp_path)
    assert findings and any("lacks" in p for p in problems)
