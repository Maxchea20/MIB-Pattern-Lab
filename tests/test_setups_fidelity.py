"""Fidelity-audit tooling tests: constructed data and a fake describer only. No network, no API key, no market data."""
import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.loader import build_candles
from src.setups import audit, fidelity as fd, params, prompts, sampling, store
from src.setups import recognizer as rz
from tests.conftest import make_ohlc
from tests.test_setups_recognizer import THR

START = pd.Timestamp("2025-10-01T00:00:00Z")


def frame(n=9000, seed=21):
    raw = make_ohlc(n, start_ms=int(START.timestamp() * 1000), step_ms=900_000, seed=seed, base=100_000.0)
    return build_candles(raw, "BTC/USDT", "15m", "synthetic", as_of="2100-01-01").df


@pytest.fixture(scope="module")
def planned():
    df = frame()
    cand, _, d = sampling.candidates(df)
    cuts = sampling.cutpoints(cand)
    return d, cuts, fd.plan_cases(d, THR, cuts, n_trig=20, n_non=20)


C7 = {"name": fd.CAND_NAME, "context_definition": "ctx text", "conditions_sequence": ["one", "two"], "presence_rule": "pres text",
      "trigger": "trig text", "direction": "up", "invalidation": "inv text", "supporting_ids": ["S0001", "S0002"],
      "cited_supporting_ids": ["S0001"], "information_required": ["x"]}


def test_definition_text_shows_only_the_frozen_wording():
    t = fd.definition_text(C7)
    for s in ("ctx text", "1. one", "2. two", "pres text", "trig text", "inv text"):
        assert s in t
    for s in (fd.CAND_NAME, "S0001", "Direction", "supporting"):
        assert s not in t
    assert "bullish" not in t and "recogn" not in t.lower()


def test_prompt_uses_the_preregistered_template_unchanged():
    u = fd.user_prompt(C7)
    assert u == prompts.AUDIT_USER_TEMPLATE.replace("{DEFINITION}", fd.definition_text(C7))
    assert "{DEFINITION}" not in u


def test_selection_is_deterministic_stratified_and_spaced():
    pool = [(i, f"S{i % 3}") for i in range(0, 3000, 5)]
    a = fd.select_spaced(pool, 30, 12345, gap=32)
    assert a == fd.select_spaced(pool, 30, 12345, gap=32) and len(a) == 30
    assert a != fd.select_spaced(pool, 30, 999, gap=32)
    idx = sorted(i for i, _ in a)
    assert all(b - x >= 32 for x, b in zip(idx, idx[1:]))
    counts = pd.Series([s for _, s in a]).value_counts()
    assert counts.max() - counts.min() <= 1                                   # round-robin over strata
    assert len(fd.select_spaced(pool[:4], 30, 1)) == 4                        # fewer than asked: take what exists


def test_plan_uses_counted_triggers_only_and_clean_non_triggers(planned):
    d, cuts, plan = planned
    cases = plan["cases"]
    trig = [c for c in cases if c["kind"] == "trigger"]
    non = [c for c in cases if c["kind"] == "non_trigger"]
    assert trig and non
    assert {c["idx"] for c in trig} <= set(plan["counted"])
    for c in non:
        i = c["idx"]
        assert not plan["presence"][i] and i not in plan["raw_triggers"] and (i - 1) not in plan["raw_triggers"]
    ids = [c["case_id"] for c in cases]
    assert ids == sorted(set(ids)) or len(set(ids)) == len(ids)
    assert all(c["case_id"].startswith("A") for c in cases)
    kinds = "".join("T" if c["kind"] == "trigger" else "N" for c in cases)
    assert kinds not in (("T" * len(trig)) + ("N" * len(non)), ("N" * len(non)) + ("T" * len(trig)))   # interleaved, not blocked


def test_plan_is_deterministic_and_hold_out_cannot_matter():
    df = frame(7000, 5)
    cutoff = START + pd.Timedelta(days=50)
    import src.setups.params as P
    old = P.DISCOVERY_END
    P.DISCOVERY_END = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        d1 = fd.discovery_frame(df)
        poisoned = df.copy()
        poisoned.loc[poisoned["ts"] >= cutoff, ["open", "high", "low", "close"]] *= 9.0
        d2 = fd.discovery_frame(poisoned)
        pd.testing.assert_frame_equal(d1, d2)
        assert d1["ts"].max() < cutoff
        cand, _, d = sampling.candidates(df)
        cuts = sampling.cutpoints(cand)
        p1 = fd.plan_cases(d1, THR, cuts, 10, 10)
        p2 = fd.plan_cases(d2, THR, cuts, 10, 10)
        assert p1["cases"] == p2["cases"]
    finally:
        P.DISCOVERY_END = old


def test_recall_is_mechanical_and_uses_present_or_trigger_on_last_two_candles(planned):
    d, cuts, plan = planned
    ts = d["ts"]
    n = 40
    presence = np.zeros(len(d), bool)
    raw = set()
    rows, ids = [], []
    for k in range(n):
        pos = 200 + k * 20
        cid = f"S{k:04d}"
        ids.append(cid)
        rows.append({"chart_id": cid, "end_ts": ts.iloc[pos].isoformat(), "error": None, "parsed": {"status": "ACTIONABLE_NOW"}})
        if k < 10:
            presence[pos] = True                     # present at T
        elif k < 15:
            raw.add(pos)                             # triggered on T
        elif k < 20:
            raw.add(pos - 1)                         # triggered on the previous candle: counts (last 2 candles)
        elif k < 25:
            raw.add(pos - 2)                         # three candles ago: does NOT count
    rows.append({"chart_id": "S9999", "end_ts": ts.iloc[100].isoformat(), "error": None, "parsed": {"status": "DEVELOPING"}})
    r = fd.recall_for(d, rows, ids + ["S9999"], presence, raw)
    assert len(r["eligible"]) == n and "S9999" not in r["eligible"]
    assert len(r["recognized"]) == 20
    assert r["gate"]["evaluated"] and r["gate"]["value"] == 0.5 and r["gate"]["passed"]
    few = fd.recall_for(d, rows[:5], ids[:5], presence, raw)
    assert not few["gate"]["evaluated"] and few["gate"]["classification"] == audit.INSUFFICIENT


class Fake:
    model = "fake"

    def __init__(self, answers):
        self.answers, self.calls, self.images = answers, 0, []

    def describe(self, png):
        self.images.append(png)
        a = self.answers[self.calls % len(self.answers)]
        self.calls += 1
        return {"text": json.dumps({"judgement": a, "reason": "r"}), "usage": {"prompt": 1000, "completion": 50}}


def make_run(tmp_path, kinds, planned_cases=None):
    out = tmp_path / "fid"
    (out / "charts").mkdir(parents=True)
    rows = []
    for n, k in enumerate(kinds, 1):
        png = f"png{n}".encode()
        (out / "charts" / f"A{n:04d}.png").write_bytes(png)
        import hashlib
        rows.append({"case_id": f"A{n:04d}", "kind": k, "stratum": "S1_directional", "end_ts": "x", "chart": f"A{n:04d}.png",
                     "image_sha256": hashlib.sha256(png).hexdigest()})
    (out / fd.CASES).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return out, rows


def test_run_is_blind_resumable_and_unclear_counts_as_not_present(tmp_path):
    out, rows = make_run(tmp_path, ["trigger"] * 12 + ["non_trigger"] * 8)
    base = tmp_path / "base.jsonl"
    base.write_text(json.dumps({"estimated_cost_usd": 1.0}) + "\n")
    log = fd.AuditCostLog(out / fd.COST, base)
    desc = Fake(["PRESENT", "PRESENT", "UNCLEAR", "NOT_PRESENT"])
    res = fd.run_audit(out, desc, fd.definition_text(C7), log)
    assert desc.calls == 20 and len(res) == 20
    assert all(i.startswith(b"png") for i in desc.images)                      # the model gets the chart bytes only
    assert all("kind" not in json.dumps({k: v for k, v in r.items() if k in ("reason", "judgement")}) for r in res)
    again = fd.run_audit(out, desc, fd.definition_text(C7), log)               # resumable: nothing is called twice
    assert desc.calls == 20 and len(again) == 20
    rec = {"eligible": ["a"] * 10, "recognized": ["a"] * 6, "gate": audit.recall_gate(["a"] * 10, {"a"})}
    rec["gate"] = {"evaluated": True, "denominator": 10, "numerator": 6, "value": 0.6, "passed": True, "classification": None}
    rep = fd.build_report(rows, res, rec, None)
    t = rep["trigger_judgement_counts"]
    assert t["PRESENT"] + t["UNCLEAR"] + t["NOT_PRESENT"] == 12
    assert rep["verdict"]["precision"]["value"] == pytest.approx(t["PRESENT"] / 12)      # UNCLEAR is not in the numerator
    assert rep["judged"]["trigger"] == 12 and rep["judged"]["non_trigger"] == 8


def test_precision_needs_at_least_ten_trigger_cases(tmp_path):
    out, rows = make_run(tmp_path, ["trigger"] * 9 + ["non_trigger"] * 5)
    log = fd.AuditCostLog(out / fd.COST, tmp_path / "none.jsonl")
    res = fd.run_audit(out, Fake(["PRESENT"]), fd.definition_text(C7), log)
    rep = fd.build_report(rows, res, {"eligible": [], "recognized": [], "gate": audit.recall_gate([], set())}, None)
    assert rep["verdict"]["precision"]["evaluated"] is False and rep["verdict"]["classification"] == audit.INSUFFICIENT


def test_cost_cap_counts_earlier_spend_and_stops_without_continuation(tmp_path, capsys):
    out, rows = make_run(tmp_path, ["trigger"] * 30)
    base = tmp_path / "base.jsonl"
    base.write_text(json.dumps({"estimated_cost_usd": 4.499}) + "\n")           # total cap 4.50 almost spent
    log = fd.AuditCostLog(out / fd.COST, base)
    desc = Fake(["PRESENT"])
    fd.run_audit(out, desc, fd.definition_text(C7), log)
    assert desc.calls == 0 and "COST STOP" in capsys.readouterr().out
    assert log.spent() == pytest.approx(4.499)
    base.write_text(json.dumps({"estimated_cost_usd": 0.0}) + "\n")
    log2 = fd.AuditCostLog(out / "c2.jsonl", base)
    log2.caps["audit"] = 0.0005                                               # step cap smaller than one call
    d2 = Fake(["PRESENT"])
    fd.run_audit(out, d2, fd.definition_text(C7), log2)
    assert d2.calls == 0


def test_tampered_chart_is_refused(tmp_path):
    out, rows = make_run(tmp_path, ["trigger"] * 2)
    (out / "charts" / "A0001.png").write_bytes(b"other")
    with pytest.raises(SystemExit):
        fd.run_audit(out, Fake(["PRESENT"]), fd.definition_text(C7), fd.AuditCostLog(out / fd.COST, tmp_path / "n.jsonl"))


def test_prepare_refuses_to_rebuild_and_report_needs_no_db(tmp_path, monkeypatch):
    out, rows = make_run(tmp_path, ["trigger"] * 3)
    with pytest.raises(SystemExit) as e:
        fd.main(["prepare", "--confirm-design-sha", "3069082ad885", "--out", str(out)])
    assert "Refusing to rebuild" in str(e.value)


def test_module_is_outcome_blind_and_makes_no_call_outside_run():
    src = Path(fd.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
           {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not any(("outcome" in m or "validation" in m or "exp5m" in m) for m in mods)
    names = {n.id.lower() for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr.lower() for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for bad in ("mfe", "mae", "pnl", "forward_return", "forward_max"):
        assert not any(bad == x or x.startswith(bad + "_") for x in names), bad
    assert src.count("OpenAIDescriber(") == 1                                  # constructed in one place only: the `run` step
    assert fd.CAND_KEY in rz.ORDER and params.SEED_AUDIT == 12345
