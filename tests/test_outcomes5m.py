import json

import numpy as np
import pandas as pd
import pytest

from src.data.loader import build_candles
from src.exp5m import io5m, outcomes5m as o5, params
from src.outcomes import analyze as arch
from tests.conftest import make_ohlc
from tests.test_exp5m import START, STEP_MS

FAMS = ["fam_a", "fam_b", "fam_c", "fam_d"]


def synth(n_windows=150, seed=1):
    raw = make_ohlc(20000, start_ms=int(START.timestamp() * 1000), step_ms=STEP_MS, seed=seed)
    cs = build_candles(raw, "BTC/USDT", "5m", "synthetic", as_of="2100-01-01")
    ends = [cs.df["ts"].iloc[100 + 80 * i] for i in range(n_windows)]
    windows = [{"end_ts": e.isoformat(), "stratum": "Q1_quiet"} for e in ends]
    rng = np.random.default_rng(seed)
    tags = []
    for w in windows:
        base = [f for f in FAMS[:3] if rng.random() < 0.5][:2] or ["fam_a"]
        for p in (1, 2):
            t = list(base) if (p == 1 or rng.random() < 0.9) else ["none"]
            tags.append({"end_ts": w["end_ts"], "pass": p, "tags": t, "error": None})
    return cs, windows, tags


def test_membership_uses_stable_tags_only_and_ignores_none():
    tags = [{"end_ts": "2025-11-01T00:00:00+00:00", "pass": 1, "tags": ["fam_a", "fam_b"], "error": None},
            {"end_ts": "2025-11-01T00:00:00+00:00", "pass": 2, "tags": ["fam_a"], "error": None},
            {"end_ts": "2025-11-01T00:05:00+00:00", "pass": 1, "tags": ["none"], "error": None},
            {"end_ts": "2025-11-01T00:05:00+00:00", "pass": 2, "tags": ["none"], "error": None},
            {"end_ts": "2025-11-01T00:10:00+00:00", "pass": 1, "tags": ["fam_b"], "error": None}]   # pass 2 missing
    mem = o5.membership_from_tags(tags, ["fam_a", "fam_b", "none_like"])
    assert mem["fam_a"] == {"2025-11-01T00:00:00+00:00"} and mem["fam_b"] == set() and mem["none_like"] == set()


def test_statistics_are_the_archived_ones():
    assert o5.arch is arch
    o5.assert_same_statistics()
    assert tuple(params.HORIZONS) == tuple(arch.HORIZONS) and params.N_MIN == arch.N_MIN


def test_run_analysis_end_to_end_on_random_data_gives_no_pass():
    cs, windows, tags = synth()
    obs, excluded, mem, table, cats = o5.run_analysis(cs, windows, tags, FAMS, ["fam_a", "fam_b"], B_perm=300, B_boot=300)
    assert len(obs) == len(windows) and sum(excluded.values()) == 0
    assert set(cats) == {"fam_a", "fam_b"} and set(table["family"]) == set(FAMS)
    assert all(c["N"] >= params.N_MIN for c in cats.values())
    assert o5.final_statement(cats) == o5.NO_PASS_STATEMENT if not any(
        c["category"] == arch.CATEGORY_PASS for c in cats.values()) else True
    assert table[table["family"] == "fam_d"]["N"].eq(0).all()          # unused family stays out, no crash


def test_report_carries_required_statements():
    cs, windows, tags = synth()
    obs, excluded, mem, table, cats = o5.run_analysis(cs, windows, tags, FAMS, ["fam_a"], B_perm=200, B_boot=200)
    meta = {"design_prereg_sha256": "d" * 64, "discovery_lock_sha256": "e" * 64, "code_sha256": "c" * 64, "B_perm": 200,
            "B_boot": 200, "n_windows": len(windows), "n_valid": len(obs), "excluded": excluded,
            "limitation_statement": "LIMITATION-TEXT", "real_fills_statement": o5.REAL_FILLS_SENTENCE,
            "final_statement": o5.final_statement(cats)}
    rep = o5.render_report(table, cats, meta, {f: 1 for f in FAMS})
    assert "LIMITATION-TEXT" in rep and o5.REAL_FILLS_SENTENCE in rep and "not trade fills" in rep
    low = rep.lower()
    for bad in ("profit", "edge exists", "buy", "sell"):
        assert bad not in low.replace("does not mean no edge exists", "")


def test_required_sentence_must_be_in_policy(tmp_path):
    p = tmp_path / "policy.md"
    p.write_text("nothing here", encoding="utf-8")
    with pytest.raises(SystemExit):
        o5.require_required_statements(p)
    assert o5.require_required_statements() == o5.REAL_FILLS_SENTENCE        # the real policy has it verbatim


def test_freeze_is_written_once_and_detects_changes(tmp_path, monkeypatch):
    f = tmp_path / "freeze.json"
    rec = o5.write_freeze(f)
    assert o5.check_freeze(f)["code_sha256"] == rec["code_sha256"]
    with pytest.raises(SystemExit):
        o5.write_freeze(f)
    data = json.loads(f.read_text())
    data["code_sha256"] = "0" * 64
    f.write_text(json.dumps(data))
    with pytest.raises(SystemExit):
        o5.check_freeze(f)
    with pytest.raises(SystemExit):
        o5.check_freeze(tmp_path / "missing.json")


def test_frozen_set_adds_nothing_to_the_archived_1h_outcome_package():
    one_h = json.loads((o5.config.ROOT / "docs" / "OUTCOME_CODE_FREEZE.json").read_text())["files"]
    archived_outcomes = {x for x in one_h if x.startswith("src/outcomes/")}
    now = {x for x in o5.frozen_files() if x.startswith("src/outcomes/")}
    assert now == archived_outcomes


def test_execute_refuses_without_locks(tmp_path):
    with pytest.raises((SystemExit, FileNotFoundError)):                 # refuses before touching data or output
        o5.execute("none.db", tmp_path, tmp_path / "out", "116cf0266102")      # no outcome freeze / discovery lock yet
    assert not (tmp_path / "out").exists()


def test_execute_full_path_with_stubbed_locks(tmp_path, monkeypatch):
    cs, windows, tags = synth(n_windows=120)
    run = tmp_path / "run"
    run.mkdir()
    (run / "windows5m.jsonl").write_text("\n".join(json.dumps(w) for w in windows), encoding="utf-8")
    (run / "tags5m.jsonl").write_text("\n".join(json.dumps(t) for t in tags), encoding="utf-8")
    (run / "sample_meta.json").write_text(json.dumps({"limitation_statement": "LIMIT-XYZ"}), encoding="utf-8")
    stable = io5m.stable_tags(tags, params.PASSES)
    counts = {f: sum(1 for t in stable.values() if f in t) for f in FAMS}
    conf = [f for f, n in counts.items() if n >= params.N_MIN]
    lock = {"vocabulary": {"families": [{"name": f, "definition": "x"} for f in FAMS]},
            "family_window_counts": counts, "confirmatory_families": conf}
    monkeypatch.setattr(o5.lock5m, "require_design_lock", lambda c: {"sha256": {"preregistration_5m": "a" * 64}})
    monkeypatch.setattr(o5, "check_freeze", lambda *a, **k: {})
    monkeypatch.setattr(o5, "verify_discovery_lock", lambda *a, **k: lock)
    monkeypatch.setattr(o5, "file_sha256", lambda p: "f" * 64)
    monkeypatch.setattr(o5, "load_candles", lambda *a, **k: cs)
    monkeypatch.setattr(params, "DISCOVERY_END", "2100-01-01T00:00:00Z")
    out = tmp_path / "out"
    s = o5.execute("x.db", run, out, "aaaaaaaaaaaa", B_perm=200, B_boot=200)
    assert conf and set(s["categories"]) == set(conf) and s["n_valid"] == len(windows)
    summ = json.loads((out / "summary.json").read_text())
    assert summ["limitation_statement"] == "LIMIT-XYZ" and summ["real_fills_statement"] == o5.REAL_FILLS_SENTENCE
    assert (out / "report.md").read_text().count(o5.REAL_FILLS_SENTENCE) >= 2 and (out / "RUN_COMPLETE.json").exists()
    assert (summ["any_pass"] is False and summ["final_statement"] == o5.NO_PASS_STATEMENT) or summ["any_pass"]
    with pytest.raises(SystemExit):                                       # run-once marker
        o5.execute("x.db", run, out, "aaaaaaaaaaaa", B_perm=200, B_boot=200)
    s2 = o5.execute("x.db", run, out, "aaaaaaaaaaaa", B_perm=200, B_boot=200, rerun_identical=True)
    assert s2["categories"].keys() == s["categories"].keys()


def test_no_confirmatory_family_gives_the_standard_statement(tmp_path, monkeypatch):
    cs, windows, tags = synth(n_windows=20)                               # far below N_MIN=30 per family
    run = tmp_path / "run"
    run.mkdir()
    (run / "windows5m.jsonl").write_text("\n".join(json.dumps(w) for w in windows), encoding="utf-8")
    (run / "tags5m.jsonl").write_text("\n".join(json.dumps(t) for t in tags), encoding="utf-8")
    (run / "sample_meta.json").write_text(json.dumps({"limitation_statement": "L"}), encoding="utf-8")
    lock = {"vocabulary": {"families": [{"name": f, "definition": "x"} for f in FAMS]},
            "family_window_counts": {f: 5 for f in FAMS}, "confirmatory_families": []}
    monkeypatch.setattr(o5.lock5m, "require_design_lock", lambda c: {"sha256": {"preregistration_5m": "a" * 64}})
    monkeypatch.setattr(o5, "check_freeze", lambda *a, **k: {})
    monkeypatch.setattr(o5, "verify_discovery_lock", lambda *a, **k: lock)
    monkeypatch.setattr(o5, "file_sha256", lambda p: "f" * 64)
    monkeypatch.setattr(o5, "load_candles", lambda *a, **k: cs)
    monkeypatch.setattr(params, "DISCOVERY_END", "2100-01-01T00:00:00Z")
    s = o5.execute("x.db", run, tmp_path / "out", "aaaaaaaaaaaa")
    assert s["final_statement"] == o5.NO_PASS_STATEMENT and s["holdout_allowed"] is False
    assert o5.REAL_FILLS_SENTENCE in (tmp_path / "out" / "report.md").read_text()
