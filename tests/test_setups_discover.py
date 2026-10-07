import hashlib
import json

import pytest

from src.setups import costlog, discover as dv, params, prompts, store


def stage_a_ok(n=3, status="DEVELOPING", **kw):
    obj = {"status": status, "visible_summary": "a rise then a pause", "context": "a steady rise", "location": "near the top of the range",
           "development": "two small pullbacks", "trigger": "a close above the pause", "direction": "up",
           "invalidation": "a close below the pause", "expected_behavior": "further rise in words", "information_required": ["last 20 candles"]}
    obj.update(kw)
    return obj


class FakeImage:
    model = "fake-model"

    def __init__(self, fn=None, usage=None):
        self.fn = fn or (lambda png, n: stage_a_ok())
        self.usage, self.calls = usage or {"prompt": 1000, "completion": 400}, 0

    def describe(self, png):
        self.calls += 1
        out = self.fn(png, self.calls)
        return {"text": out if isinstance(out, str) else json.dumps(out), "usage": self.usage}


@pytest.fixture
def run_dir(tmp_path):
    (tmp_path / "charts").mkdir()
    rows = []
    for i in range(1, 9):
        data = f"png-{i}".encode()
        name = f"S{i:04d}.png"
        (tmp_path / "charts" / name).write_bytes(data)
        rows.append({"chart_id": f"S{i:04d}", "end_ts": f"2026-01-{i:02d}T00:00:00+00:00", "chart": name, "stratum": "S1_directional",
                     "image_sha256": hashlib.sha256(data).hexdigest(), "chart_style_sha256": "style", "features": {}})
    (tmp_path / "windows_setups.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return tmp_path


# ------------------------------------------------------------------------------------ cost log -----------
def test_cost_log_records_fields_and_enforces_caps(tmp_path):
    log = costlog.CostLog(tmp_path / "c.jsonl", caps={"stage_a": 0.02, "stage_b": 1, "audit": 1}, total_cap=0.05)
    assert log.allow("stage_a")
    for _ in range(3):
        if log.allow("stage_a"):
            row = log.record("stage_a", "m", {"prompt": 1000, "completion": 1000})
    assert set(row) >= {"step", "call_number", "model", "input_tokens", "output_tokens", "estimated_cost_usd",
                        "cumulative_step_usd", "cumulative_total_usd"}
    assert row["call_number"] == len(log.rows("stage_a")) and log.spent("stage_a") <= 0.02 + 0.006
    assert not log.allow("stage_a")                                            # step cap reached: no further call
    tot = costlog.CostLog(tmp_path / "t.jsonl", caps={"stage_a": 10, "stage_b": 10, "audit": 10}, total_cap=0.01)
    tot.record("stage_a", "m", {"prompt": 1000, "completion": 1000})
    assert not tot.allow("stage_b")                                            # total cap binds across stages


def test_caps_are_the_approved_ones():
    assert (params.CAP_STAGE_A, params.CAP_STAGE_B, params.CAP_AUDIT, params.CAP_TOTAL) == (3.00, 0.50, 1.00, 4.50)
    assert params.CAP_STAGE_A + params.CAP_STAGE_B + params.CAP_AUDIT == params.CAP_TOTAL


# ------------------------------------------------------------------------------------ validators --------
def test_stage_a_validation_and_output_lint():
    assert prompts.validate_stage_a(stage_a_ok()) == []
    assert prompts.validate_stage_a(stage_a_ok(status="NONE", context="", location="", development="", trigger="", direction="undetermined",
                                               invalidation="", expected_behavior="", information_required=[])) == []
    assert prompts.validate_stage_a(stage_a_ok(status="MAYBE"))
    assert prompts.validate_stage_a(stage_a_ok(direction="long"))
    assert prompts.validate_stage_a(stage_a_ok(trigger=""))                      # a situation without a trigger is rejected
    assert prompts.validate_stage_a({**stage_a_ok(), "extra": 1})
    for bad in ("this will likely win", "a profitable setup", "the target is the high", "it works well", "a trading edge here"):
        assert prompts.validate_stage_a(stage_a_ok(expected_behavior=bad)), bad
    assert prompts.validate_stage_a(stage_a_ok(visible_summary="price stalls at the right edge of the chart")) == []   # 'edge' alone is fine


def test_prompts_are_clean_and_match_the_preregistered_appendix():
    import re
    from pathlib import Path
    assert all(not v for v in prompts.lint_templates().values())
    t = Path(__file__).resolve().parents[1].joinpath("docs/PREREGISTRATION_SETUPS.md").read_text(encoding="utf-8")
    blocks = [b.rstrip("\n") for b in re.findall(r"```\n(.*?)```", t[t.index("## Appendix A"):], re.S)]
    assert blocks[:4] == [prompts.A_SYSTEM, prompts.A_USER, prompts.B_SYSTEM, prompts.B_CHUNK_USER_TEMPLATE]


# ------------------------------------------------------------------------------------ Stage A -----------
def test_stage_a_runs_resumes_logs_and_hides_nothing_it_should_not(run_dir):
    f = FakeImage()
    rows = dv.run_stage_a(run_dir, f)
    assert len(rows) == 8 == f.calls and all(r["parsed"]["status"] == "DEVELOPING" and r["step"] == "A" for r in rows)
    log = costlog.CostLog(run_dir / dv.COST_FILE)
    assert len(log.rows("stage_a")) == 8 and log.spent("stage_a") > 0
    f2 = FakeImage()
    dv.run_stage_a(run_dir, f2)
    assert f2.calls == 0                                                        # resumable: nothing is paid for twice


def test_stage_a_records_errors_and_retries_them_next_run(run_dir):
    f = FakeImage(lambda png, n: "not json" if n == 2 else (stage_a_ok(expected_behavior="it will win") if n == 3 else stage_a_ok()))
    rows = dv.run_stage_a(run_dir, f)
    errs = [r for r in rows if r["error"]]
    assert len(errs) == 2 and any("invalid JSON" in r["error"] for r in errs) and any("performance" in r["error"] for r in errs)
    f2 = FakeImage()
    rows2 = dv.run_stage_a(run_dir, f2)
    assert f2.calls == 2 and len(store.clean_rows(rows2)) == 8


def test_stage_a_stops_at_the_cost_cap_and_never_continues(run_dir, monkeypatch):
    monkeypatch.setattr(params, "CAPS", {"stage_a": 0.02, "stage_b": 0.5, "audit": 1.0})
    log = costlog.CostLog(run_dir / dv.COST_FILE)
    f = FakeImage(usage={"prompt": 3000, "completion": 1000})                    # ~$0.0068 per call
    rows = dv.run_stage_a(run_dir, f, log)
    assert 0 < f.calls < 8 and log.spent("stage_a") <= 0.02
    n = f.calls
    dv.run_stage_a(run_dir, f, log)
    assert f.calls == n                                                          # the cap does not reset on a re-run


# ------------------------------------------------------------------------------------ Stage B -----------
def descriptions(n, status="DEVELOPING"):
    return [{"chart_id": f"S{i:04d}", "end_ts": f"2026-02-{(i % 27) + 1:02d}T00:00:00+00:00", "stratum": "S3_expansion",
             "parsed": stage_a_ok(status=status), "error": None} for i in range(1, n + 1)]


def cand(name="range_break_up", ids=(), **kw):
    c = {"name": name, "context_definition": "a quiet range", "conditions_sequence": ["quiet range", "a probe", "a close beyond"],
         "presence_rule": "the probe has happened", "trigger": "a close beyond the range", "direction": "up",
         "invalidation": "a close back inside", "information_required": ["last 40 candles"], "supporting_ids": list(ids)}
    c.update(kw)
    return c


class FakeText:
    model = "fake-text"

    def __init__(self, fn):
        self.fn, self.calls, self.prompts = fn, 0, []

    def call(self, system, user):
        self.calls += 1
        self.prompts.append(user)
        return {"text": json.dumps(self.fn(user, self.calls)), "usage": {"prompt": 5000, "completion": 800}}


def b_run_dir(tmp_path, n=130, statuses=None):
    d = tmp_path / "run"
    d.mkdir()
    rows = descriptions(n)
    for r in rows[:5]:
        r["parsed"] = stage_a_ok(status="NONE", context="", location="", development="", trigger="", direction="undetermined",
                                 invalidation="", expected_behavior="", information_required=[])
    (d / dv.STAGE_A_FILE).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (d / "windows_setups.jsonl").write_text("\n".join(json.dumps({"chart_id": r["chart_id"]}) for r in rows) + "\n")
    return d, rows


def test_stage_b_hides_time_and_stratum_and_uses_only_non_none_descriptions(tmp_path):
    d, rows = b_run_dir(tmp_path)
    seen = []

    def fn(user, n):
        seen.append(user)
        ids = [l.split(": ")[1] for l in user.splitlines() if l.startswith("id: ")]
        return {"candidates": [cand(ids=ids)]} if "Descriptions:" in user else {"candidates": [cand(ids=sorted({i for c in json.loads(user.split("Candidates:\n")[1]) for i in c["supporting_ids"]}))]}

    out = tmp_path / "cands.json"
    rec = dv.run_stage_b(d, FakeText(fn), candidates_path=out)
    chunk_prompts = [u for u in seen if "Descriptions:" in u]
    assert len(chunk_prompts) == 2                                              # 125 non-NONE descriptions -> chunks of 120 + 5
    text = "\n".join(seen)
    assert "2026-02" not in text and "S3_expansion" not in text and "end_ts" not in text
    assert all(f"id: S{i:04d}" not in text for i in range(1, 6))                # NONE descriptions are not sent
    assert len(rec["candidates"]) == 1 and len(rec["candidates"][0]["supporting_ids"]) == 125 >= params.MIN_SUPPORT
    assert json.loads(out.read_text())["candidates"][0]["name"] == "range_break_up"
    with pytest.raises(SystemExit):
        dv.run_stage_b(d, FakeText(fn), candidates_path=out)                    # written once, then frozen


def test_stage_b_drops_candidates_with_too_little_support_on_count_alone(tmp_path):
    d, rows = b_run_dir(tmp_path, n=40)

    def fn(user, n):
        ids = [f"S{i:04d}" for i in range(6, 41)]
        if "Candidates:" in user:
            return {"candidates": [cand("big_one", ids[:20]), cand("small_one", ids[20:30])]}
        return {"candidates": [cand("big_one", ids[:20]), cand("small_one", ids[20:30])]}

    rec = dv.run_stage_b(d, FakeText(fn), candidates_path=tmp_path / "c.json")
    assert [c["name"] for c in rec["candidates"]] == ["big_one"]
    assert rec["dropped"][0]["name"] == "small_one" and rec["dropped"][0]["distinct_supporting_descriptions"] == 10


def test_stage_b_validation_retries_then_fails_loudly_and_caches_accepted_calls(tmp_path):
    d, rows = b_run_dir(tmp_path, n=30)
    good = lambda ids: {"candidates": [cand(ids=ids)]}

    def fn(user, n):
        if "Candidates:" not in user:
            return good([f"S{i:04d}" for i in range(6, 31)])
        return {"candidates": [cand(ids=["S9999"])]}                            # unknown ids: always invalid

    t = FakeText(fn)
    with pytest.raises(SystemExit):
        dv.run_stage_b(d, t, candidates_path=tmp_path / "c.json")
    assert t.calls == 1 + params.MAX_ATTEMPTS                                   # 1 chunk call + 3 failed final attempts
    assert "rejected for these reasons" in t.prompts[-1] and not (tmp_path / "c.json").exists()
    t2 = FakeText(fn)
    with pytest.raises(SystemExit):
        dv.run_stage_b(d, t2, candidates_path=tmp_path / "c.json")
    assert t2.calls == 0 or all("Candidates:" in p for p in t2.prompts)         # the accepted chunk call is not paid for twice


def test_stage_b_needs_a_complete_stage_a_and_handles_no_setups(tmp_path):
    d, rows = b_run_dir(tmp_path, n=10)
    (d / "windows_setups.jsonl").write_text("\n".join(json.dumps({"chart_id": f"S{i:04d}"}) for i in range(1, 12)) + "\n")
    with pytest.raises(SystemExit):
        dv.run_stage_b(d, FakeText(lambda u, n: {}), candidates_path=tmp_path / "c.json")
    d2 = tmp_path / "all_none"
    d2.mkdir()
    none = [{**r, "parsed": stage_a_ok(status="NONE", context="", location="", development="", trigger="", direction="undetermined",
                                      invalidation="", expected_behavior="", information_required=[])} for r in descriptions(5)]
    (d2 / dv.STAGE_A_FILE).write_text("\n".join(json.dumps(r) for r in none) + "\n")
    (d2 / "windows_setups.jsonl").write_text("\n".join(json.dumps({"chart_id": r["chart_id"]}) for r in none) + "\n")
    t = FakeText(lambda u, n: {})
    rec = dv.run_stage_b(d2, t, candidates_path=tmp_path / "n.json")
    assert rec["candidates"] == [] and "no recurring setup" in rec["note"] and t.calls == 0


def test_chunking_is_seeded_and_deterministic():
    clean = {r["chart_id"]: r for r in descriptions(250)}
    a, b = dv.make_chunks(clean), dv.make_chunks(clean)
    assert [[r["chart_id"] for r in c] for c in a] == [[r["chart_id"] for r in c] for c in b]
    assert [len(c) for c in a] == [120, 120, 10]
