import json

import pytest

from src.setups import audit, costlog, params, prompts, store


def test_precision_requires_at_least_10_audited_trigger_cases():
    for n in range(0, 10):
        g = audit.precision_gate(n, n)                                        # even 100 % of a tiny sample never passes
        assert g["evaluated"] is False and g["passed"] is False and g["classification"] == audit.INSUFFICIENT
    assert audit.precision_gate(10, 7)["passed"] is True                      # exactly 70 % of 10 passes
    assert audit.precision_gate(10, 6)["passed"] is False and audit.precision_gate(10, 6)["classification"] is None
    assert audit.precision_gate(100, 70)["passed"] and not audit.precision_gate(100, 69)["passed"]


def test_recall_requires_at_least_10_eligible_supporting_actionable_now_charts():
    rows = [{"chart_id": f"S{i:04d}", "error": None, "parsed": {"status": "ACTIONABLE_NOW" if i % 2 else "DEVELOPING"}} for i in range(1, 41)]
    sup = [f"S{i:04d}" for i in range(1, 31)] + ["S0099"]
    e = audit.eligible_supporting_charts(rows, sup)
    assert e == [f"S{i:04d}" for i in range(1, 31) if i % 2] and len(e) == 15      # status and membership both required
    for k in range(0, 10):
        g = audit.recall_gate(e[:k] if k else [], set(e))
        assert g["evaluated"] is False and g["passed"] is False and g["classification"] == audit.INSUFFICIENT
    assert audit.recall_gate(e[:10], set(e[:5]))["passed"] is True                 # 5/10 = 50 % passes
    assert audit.recall_gate(e[:10], set(e[:4]))["passed"] is False
    g = audit.recall_gate(e, set(e[:8]) | {"S9999"})                                # recognized ids outside E_K are not counted
    assert g["numerator"] == 8 and g["denominator"] == 15


def test_verdict_classification_and_thresholds_unchanged():
    assert (params.PRECISION_MIN, params.RECALL_MIN) == (0.70, 0.50)
    assert (params.MIN_TRIGGER_CASES, params.MIN_RECALL_CHARTS, params.RECALL_WINDOW_CANDLES) == (10, 10, 2)
    ok = audit.fidelity_verdict(audit.precision_gate(20, 16), audit.recall_gate([f"c{i}" for i in range(10)], {f"c{i}" for i in range(6)}))
    assert ok["passed"] and ok["classification"] is None
    low = audit.fidelity_verdict(audit.precision_gate(20, 10), audit.recall_gate([f"c{i}" for i in range(10)], {f"c{i}" for i in range(6)}))
    assert not low["passed"] and low["classification"] == "NOT CODEABLE FAITHFULLY"
    thin = audit.fidelity_verdict(audit.precision_gate(9, 9), audit.recall_gate([f"c{i}" for i in range(10)], {f"c{i}" for i in range(10)}))
    assert not thin["passed"] and thin["classification"] == audit.INSUFFICIENT
    thin2 = audit.fidelity_verdict(audit.precision_gate(50, 50), audit.recall_gate(["a"], {"a"}))
    assert not thin2["passed"] and thin2["classification"] == audit.INSUFFICIENT


def test_frequency_gate_bounds():
    assert audit.frequency_gate(10, 5000)["passed"]                              # 0.2 %
    assert not audit.frequency_gate(9, 5000)["passed"] and audit.frequency_gate(9, 5000)["classification"] == "NOT CODEABLE / NOT SELECTIVE"
    assert audit.frequency_gate(500, 5000)["passed"] and not audit.frequency_gate(501, 5000)["passed"]
    assert not audit.frequency_gate(0, 0)["passed"]


def test_case_selection_is_seeded_and_stratified():
    pool = [(f"c{i:03d}", f"S{i % 3}") for i in range(60)]
    a, b = audit.select_cases(pool, 9), audit.select_cases(pool, 9)
    assert a == b and len(a) == 9
    assert sorted(int(c[1:]) % 3 for c in a) == [0, 0, 0, 1, 1, 1, 2, 2, 2]           # round-robin over strata
    assert audit.select_cases(pool, 500) and len(audit.select_cases(pool, 500)) == 60
    assert audit.select_cases(pool, 9, seed=1) != a


class FakeJudge:
    model = "fake"

    def __init__(self, answers):
        self.answers, self.calls = answers, 0

    def describe(self, png):
        self.calls += 1
        return {"text": json.dumps(self.answers[(self.calls - 1) % len(self.answers)]), "usage": {"prompt": 1000, "completion": 50}}


def test_judgements_unclear_counts_as_not_present_and_errors_are_not_audited(tmp_path):
    cases = [{"case_id": f"t{i}", "kind": "trigger", "png": b"x"} for i in range(10)] + [{"case_id": "n0", "kind": "non_trigger", "png": b"x"}]
    answers = [{"judgement": "PRESENT", "reason": "r"}] * 6 + [{"judgement": "UNCLEAR", "reason": "r"}] * 2 + [{"judgement": "NOT_PRESENT", "reason": "r"}] * 2 + [{"judgement": "PRESENT", "reason": "r"}]
    log = costlog.CostLog(tmp_path / "c.jsonl")
    rows = audit.run_judgements(cases, FakeJudge(answers), "DEF", tmp_path / "a.jsonl", log)
    assert len(rows) == 11 and len(log.rows("audit")) == 11
    g = audit.precision_from_judgements(rows)
    assert g["n"] == 10 and g["value"] == 0.6 and not g["passed"]                    # 6 PRESENT / 10; UNCLEAR is not present
    j = FakeJudge(answers)
    audit.run_judgements(cases, j, "DEF", tmp_path / "a.jsonl", log)
    assert j.calls == 0                                                               # resumable
    bad = audit.run_judgements([{"case_id": "e", "kind": "trigger", "png": b"x"}], FakeJudge([{"judgement": "MAYBE", "reason": "r"}]), "DEF", tmp_path / "b.jsonl", log)
    assert bad[0]["error"] and audit.precision_from_judgements(bad)["n"] == 0


def test_audit_prompt_shows_only_the_definition_text():
    c = {"name": "x_setup", "context_definition": "ctx", "conditions_sequence": ["a", "b"], "presence_rule": "pr", "trigger": "tr",
         "direction": "up", "invalidation": "inv", "information_required": ["i1"], "supporting_ids": ["S0001"]}
    text = prompts.definition_text(c)
    assert "S0001" not in text and "supporting" not in text.lower() and "Trigger: tr" in text and "Direction: up" in text
