import hashlib
import json

import pytest

from src.exp5m import discover5m as d5, io5m, lock5m, params, prompts5m

NAMES = ("sideways_range", "drift_up", "drift_down", "steep_fall", "steep_rise", "arch_shape")


def fam(name, definition="price moves in a narrow band with small candles"):
    return {"name": name, "definition": definition, "member_names": [name]}


def good_vocab_json():
    return {"families": [fam(n) for n in NAMES]}


@pytest.fixture
def run_dir(tmp_path):
    (tmp_path / "charts").mkdir()
    rows = []
    for i in range(12):
        data = f"png-{i}".encode()
        name = f"w{i:02d}.png"
        (tmp_path / "charts" / name).write_bytes(data)
        rows.append({"end_ts": f"2026-01-{i + 1:02d}T00:00:00+00:00", "chart": name, "stratum": "Q1_quiet", "range_pct": 1.0,
                     "image_sha256": hashlib.sha256(data).hexdigest(), "chart_style_sha256": "style",
                     "description_stage": i % 2 == 0})
    (tmp_path / "windows5m.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (tmp_path / "sample_meta.json").write_text(json.dumps({"windows5m_jsonl_sha256": lock5m.file_sha256(tmp_path / "windows5m.jsonl")}))
    return tmp_path


class FakeImage:
    model = "fake-model"

    def __init__(self, fn, usage=None):
        self.fn, self.usage, self.calls = fn, usage or {"prompt": 1000, "completion": 50}, 0

    def describe(self, png):
        self.calls += 1
        out = self.fn(png, self.calls)
        return {"text": out if isinstance(out, str) else json.dumps(out), "usage": self.usage}


def d1_ok(png, n):
    return {"summary": f"a gradual rise then a flat band {png.decode()}", "structure": ["rise", "flat"],
            "shape_tags": ["Gradual Rise", "flat_band"], "notable_features": []}


# ---------------------------------------------------------------- D1 ------------------------------------------
def test_d1_runs_only_description_stage_resumes_and_records(run_dir):
    f = FakeImage(d1_ok)
    rows = d5.run_d1(run_dir, f)
    assert len(rows) == 6 == f.calls and all(r["step"] == "D1" and r["model"] == "fake-model" for r in rows)
    assert {r["end_ts"] for r in rows} == {w["end_ts"] for w in io5m.load_jsonl(run_dir / "windows5m.jsonl") if w["description_stage"]}
    f2 = FakeImage(d1_ok)
    d5.run_d1(run_dir, f2)
    assert f2.calls == 0                                                        # resumable: nothing is paid for twice


def test_d1_bad_responses_are_errors_and_retried(run_dir):
    f = FakeImage(lambda png, n: "not json" if n == 2 else ({"summary": 5} if n == 3 else d1_ok(png, n)))
    rows = d5.run_d1(run_dir, f)
    assert sum(1 for r in rows if r["error"]) == 2 and len(io5m.clean_rows(rows)) == 4
    f2 = FakeImage(d1_ok)
    d5.run_d1(run_dir, f2)
    assert f2.calls == 2 and len(io5m.clean_rows(io5m.load_jsonl(run_dir / "d1_descriptions.jsonl"))) == 6


def test_d1_budget_stop_and_hash_guard(run_dir):
    f = FakeImage(d1_ok, usage={"prompt": 100_000, "completion": 0})            # $0.075 per call
    rows = d5.run_d1(run_dir, f, budget_usd=0.2)
    assert 0 < len(rows) < 6 and lock5m_cost(rows) <= 0.2
    (run_dir / "charts" / "w04.png").write_bytes(b"tampered")
    with pytest.raises(SystemExit, match="does not match"):
        d5.run_d1(run_dir, FakeImage(d1_ok))


def lock5m_cost(rows):
    from src.discovery import cost
    return cost.total_cost(rows)


# ---------------------------------------------------------------- D2 ------------------------------------------
class FakeText:
    model = "fake-model"

    def __init__(self, responses):
        self.responses, self.prompts = list(responses), []

    def call(self, system, user):
        self.prompts.append(user)
        r = self.responses.pop(0)
        return {"text": r if isinstance(r, str) else json.dumps(r), "usage": {"prompt": 3000, "completion": 400}}


def test_d2_input_is_deterministic_and_normalised(run_dir):
    d5.run_d1(run_dir, FakeImage(d1_ok))
    rows = io5m.load_jsonl(run_dir / "d1_descriptions.jsonl")
    a, b = d5.build_d2_input(rows), d5.build_d2_input(rows)
    assert a == b and a[0] == 6 and "gradual_rise: 6" in a[1] and "flat_band: 6" in a[1]
    assert a[2].count("\n") == 5


def test_d2_retries_with_feedback_then_freezes_vocabulary_once(run_dir, tmp_path):
    d5.run_d1(run_dir, FakeImage(d1_ok))
    bad = {"families": [fam(n) for n in NAMES[:-1]] + [fam("upward_trend")]}                # forbidden word
    caller = FakeText([bad, good_vocab_json()])
    vp = tmp_path / "vocab.json"
    v = d5.run_d2(run_dir, caller, vp)
    assert v.names[:-1] == list(NAMES) and v.names[-1] == "none"
    assert len(caller.prompts) == 2 and "rejected" not in caller.prompts[0] and "rejected" in caller.prompts[1]
    assert prompts5m.lint(caller.prompts[0]) == []                                          # first prompt is lint-clean
    attempts = io5m.load_jsonl(run_dir / "d2_attempts.jsonl")
    assert [a["accepted"] for a in attempts] == [False, True] and "trend" in " ".join(attempts[0]["problems"])
    rec = json.loads(vp.read_text())
    assert rec["sha256"] == v.sha256 and rec["attempt_accepted"] == 2 and d5.load_vocabulary(vp).sha256 == v.sha256
    with pytest.raises(SystemExit, match="already exists"):
        d5.run_d2(run_dir, FakeText([good_vocab_json()]), vp)                               # written once, never replaced
    rec["families"][0]["definition"] = "edited by hand"
    vp.write_text(json.dumps(rec))
    with pytest.raises(SystemExit, match="recorded hash"):
        d5.load_vocabulary(vp)


def test_d2_all_attempts_fail_stops_without_fixing_by_hand(run_dir, tmp_path):
    d5.run_d1(run_dir, FakeImage(d1_ok))
    bad = {"families": [fam("a_one")]}
    caller = FakeText([bad] * params.D2_MAX_ATTEMPTS)
    vp = tmp_path / "vocab.json"
    with pytest.raises(SystemExit, match="failed all attempts"):
        d5.run_d2(run_dir, caller, vp)
    assert not vp.exists() and len(caller.prompts) == params.D2_MAX_ATTEMPTS


def test_d2_requires_complete_d1(run_dir, tmp_path):
    d5.run_d1(run_dir, FakeImage(d1_ok), budget_usd=0.0001)
    with pytest.raises(SystemExit, match="incomplete"):
        d5.run_d2(run_dir, FakeText([good_vocab_json()]), tmp_path / "v.json")


# ---------------------------------------------------------------- D3 + discovery lock ----------------------------
def freeze_everything(run_dir, tmp_path, monkeypatch):
    d5.run_d1(run_dir, FakeImage(d1_ok))
    vp = tmp_path / "vocab.json"
    monkeypatch.setattr(io5m, "VOCAB_FILE", vp)
    vocab = d5.run_d2(run_dir, FakeText([good_vocab_json()]), vp)
    return vocab


def test_d3_two_passes_reversed_order_stable_tags_and_resume(run_dir, tmp_path, monkeypatch):
    vocab = freeze_everything(run_dir, tmp_path, monkeypatch)
    seen = []

    def factory(user):
        seen.append(user)
        return FakeImage(lambda png, n: {"tags": ["drift_up"]} if png != b"png-3" else {"tags": ["drift_up"] if n % 2 else ["steep_rise"]})

    rows = d5.run_d3(run_dir, factory, vocab)
    assert len(rows) == 24 and seen[0] != seen[1] and seen[0].index("sideways_range") < seen[0].index("arch_shape")
    assert seen[1].index("arch_shape") < seen[1].index("sideways_range")
    st = io5m.stable_tags(rows, 2)
    assert len(st) == 12 and st["2026-01-01T00:00:00+00:00"] == ["drift_up"]
    again = d5.run_d3(run_dir, lambda u: FakeImage(lambda p, n: {"tags": ["drift_up"]}), vocab)
    assert len(again) == 24                                                                 # nothing re-requested
    bad = FakeImage(lambda png, n: {"tags": ["made_up"]})
    (run_dir / "tags5m.jsonl").unlink()
    r = d5.run_d3(run_dir, lambda u: bad, vocab)
    assert all("unknown tags" in x["error"] for x in r)                                      # unknown names are errors


def test_discovery_lock_counts_tags_only_and_refuses_incomplete(run_dir, tmp_path, monkeypatch):
    vocab = freeze_everything(run_dir, tmp_path, monkeypatch)
    monkeypatch.setattr(params, "N_MIN", 5)
    design = tmp_path / "design.json"
    design.write_text("{}")
    monkeypatch.setattr(lock5m, "DESIGN_LOCK", design)
    monkeypatch.setattr(lock5m, "verify_design_lock", lambda: {"sha256": {"preregistration_5m": "x" * 64}})
    with pytest.raises(SystemExit, match="lack a clean tagging pass"):
        lock5m.build_discovery_lock(run_dir)
    d5.run_d3(run_dir, lambda u: FakeImage(lambda png, n: {"tags": ["drift_up"] if int(png.decode().split("-")[1]) < 6 else ["sideways_range"]}), vocab)
    rec = lock5m.build_discovery_lock(run_dir)
    assert rec["n_windows"] == 12 and rec["family_window_counts"]["drift_up"] == 6 and rec["family_window_counts"]["sideways_range"] == 6
    assert rec["confirmatory_families"] == ["drift_up", "sideways_range"] and rec["n_confirmatory_cells"] == 10
    assert rec["vocabulary"]["sha256"] == vocab.sha256 and len(rec["sha256"]["tags5m_jsonl"]) == 64
    (run_dir / "windows5m.jsonl").write_text((run_dir / "windows5m.jsonl").read_text() + "\n")
    with pytest.raises(SystemExit, match="changed since the sample was built"):
        lock5m.build_discovery_lock(run_dir)
