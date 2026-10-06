import json
import sqlite3

import numpy as np
import pandas as pd
import pytest

import config
from src.data.loader import build_candles
from src.exp5m import coverage, lock5m, params, prompts5m, sampling
from tests.conftest import make_ohlc

START = pd.Timestamp("2025-10-01T00:00:00Z")
STEP_MS = 300_000


def series(n=30000, seed=0, base=100_000.0):
    raw = make_ohlc(n, start_ms=int(START.timestamp() * 1000), step_ms=STEP_MS, seed=seed, base=base)
    return build_candles(raw, "BTC/USDT", "5m", "synthetic", as_of="2100-01-01").df


@pytest.fixture
def small_design(monkeypatch):
    monkeypatch.setattr(params, "CALIBRATION_DAYS", 10)
    monkeypatch.setattr(params, "DISCOVERY_END", (START + pd.Timedelta(days=90)).isoformat())
    monkeypatch.setattr(params, "N_TARGET", 40)
    return params


# ------------------------------------------------------------------- coverage ---------------------------------
def test_coverage_detects_planted_problems(tmp_path):
    db = tmp_path / "m.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE candles (symbol TEXT, timeframe TEXT, ts INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL)")
    d = make_ohlc(500, start_ms=int(START.timestamp() * 1000), step_ms=STEP_MS)
    rows = [(int(r.timestamp // 1000), r.open, r.high, r.low, r.close) for r in d.itertuples()]
    rows = rows[:100] + rows[106:]                                      # 6 missing candles (one gap)
    rows.append(rows[10])                                               # duplicate timestamp
    rows.append((rows[50][0] + 7,) + rows[50][1:])                      # off-grid timestamp
    rows.append((rows[60][0] + 1, 100.0, 90.0, 95.0, 99.0))             # invalid OHLC (high < low), also off-grid
    con.executemany("INSERT INTO candles VALUES ('BTC_USDT','5m',?,?,?,?,?,1)", rows)
    con.commit(); con.close()
    rep = coverage.coverage(db)
    assert rep["missing_candles_total"] == 6 and rep["gap_count"] == 1 and rep["largest_gap_candles"] == 6
    assert rep["duplicate_timestamps"] == 1 and rep["off_grid_timestamps"] == 2 and rep["invalid_ohlc_rows"] == 1
    assert rep["stored_timestamp_unit"] == "seconds" and "UTC" in rep["timezone_assumption"]
    assert "error" in rep["loader"] and "duplicate" in rep["loader"]["error"].lower()    # reported, not a crash
    assert len(rep["database_sha256"]) == 64 and rep["earliest"].startswith("2025-10-01T00:00:00")


# ------------------------------------------------------------------- causal scale + candidates ------------------
def test_span_uses_only_the_calibration_prefix(small_design):
    df = series()
    span, cal_end, n = sampling.calibration_span(df)
    poisoned = df.copy()
    poisoned.loc[poisoned["ts"] >= cal_end, ["open", "high", "low", "close"]] *= 3.0     # wild data AFTER the prefix
    span2, cal_end2, _ = sampling.calibration_span(poisoned)
    assert span2 == span and cal_end2 == cal_end and n > 0


def test_candidates_respect_every_rule_and_never_read_holdout(small_design):
    df = series()
    cand, span, cal_end, funnel, d = sampling.candidates(df)
    cutoff = pd.Timestamp(params.DISCOVERY_END)
    step = pd.Timedelta(minutes=5)
    assert len(cand) > 100 and (cand["end_ts"] < cutoff).all() and (cand["range_pct"] <= span + 1e-9).all()
    assert (cand["end_ts"] - 59 * step >= cal_end).all()                                  # window starts after calibration
    assert (cand["end_ts"] + params.FORWARD_MAX * step < cutoff).all()                    # forward path stays before cutoff
    assert funnel["candidates"] == len(cand) and d["ts"].max() < cutoff
    poisoned = df.copy()
    poisoned.loc[poisoned["ts"] >= cutoff, ["open", "high", "low", "close"]] = 1e9       # hold-out data must not matter
    cand2 = sampling.candidates(poisoned)[0]
    pd.testing.assert_frame_equal(cand, cand2)


def test_candidate_decision_is_blind_to_prices_after_the_window(small_design):
    df = series()
    k = 20000
    alt = df.copy()
    alt.loc[k:, ["open", "high", "low", "close"]] = alt.loc[k:, ["open", "high", "low", "close"]].to_numpy()[::-1] * 2.0
    a, b = sampling.candidates(df)[0], sampling.candidates(alt)[0]
    horizon = df["ts"].iloc[k - 30]
    pd.testing.assert_frame_equal(a[a["end_ts"] < horizon].reset_index(drop=True), b[b["end_ts"] < horizon].reset_index(drop=True))


def test_gap_in_forward_path_excludes_window(small_design):
    df = series()
    df = df.drop(index=5000).reset_index(drop=True)                                         # missing candle
    cand, *_ = sampling.candidates(df)
    gap_ts = series()["ts"].iloc[5000]
    bad = (cand["end_ts"] > gap_ts - 24 * pd.Timedelta(minutes=5)) & (cand["end_ts"] < gap_ts + 60 * pd.Timedelta(minutes=5))
    assert not bad.any()                                                                   # no window spans or precedes the gap closely


# ------------------------------------------------------------------- selection ------------------------------------
def test_selection_deterministic_balanced_nonoverlapping(small_design):
    df = series()
    cand = sampling.candidates(df)[0]
    a, b = sampling.select(cand), sampling.select(cand)
    assert a == b and 0 < len(a) <= params.N_TARGET
    ts = [t for t, _, _ in a]
    assert ts == sorted(ts) and min(y - x for x, y in zip(ts, ts[1:])) >= pd.Timedelta(minutes=5 * 60)
    counts = pd.Series([s for _, s, _ in a]).value_counts()
    assert counts.max() <= params.N_TARGET // params.N_STRATA
    by = {s: [r for _, st, r in a if st == s] for s in counts.index}
    assert max(by["Q1_quiet"]) <= min(by["Q4_active"])                                      # strata ordered by window range
    assert ts[0] < START + pd.Timedelta(days=40) and ts[-1] > START + pd.Timedelta(days=60)  # spread over the whole period


def test_build_renders_clean_deterministic_windows(small_design, monkeypatch, tmp_path):
    monkeypatch.setattr(params, "N_TARGET", 12)
    df = series()
    meta, rows = sampling.build(df, tmp_path / "a")
    meta2, rows2 = sampling.build(df, tmp_path / "b")
    assert meta["n_selected"] == len(rows) == len(rows2) > 0
    assert [r["image_sha256"] for r in rows] == [r["image_sha256"] for r in rows2]          # byte-identical charts
    assert meta["windows5m_jsonl_sha256"] == meta2["windows5m_jsonl_sha256"]
    assert sum(r["description_stage"] for r in rows) == (len(rows) + params.D1_EVERY - 1) // params.D1_EVERY
    saved = json.loads((tmp_path / "a" / "sample_meta.json").read_text())
    assert saved["span_pct"] == meta["span_pct"] and saved["funnel"]["candidates"] > 0
    assert all((tmp_path / "a" / "charts" / r["chart"]).stat().st_size > 5000 for r in rows)


# ------------------------------------------------------------------- prompts + lint -------------------------------
def test_prompts_are_free_of_forbidden_language():
    assert all(v == [] for v in prompts5m.lint_templates().values())
    vocab_text = " ".join(prompts5m.TEMPLATES.values()).lower()
    for w in ("trend", "breakout", "support", "resistance", "volume", "indicator", "signal", "buy", "sell", "outcome"):
        assert w not in vocab_text.split() and w not in prompts5m.lint(vocab_text)
    assert prompts5m.lint("a sharp_reversal then an uptrend with high volume") == ["reversal", "uptrend", "volume"]
    assert prompts5m.lint("sideways_range drift_up drift_down stair_step") == []


def fam(name, definition="price moves in a narrow band with small candles"):
    return {"name": name, "definition": definition, "member_names": [name]}


def test_validate_families_accepts_good_and_rejects_bad():
    good = {"families": [fam(n) for n in ("sideways_range", "drift_up", "drift_down", "steep_fall", "steep_rise", "arch_shape")]}
    fams, probs = prompts5m.validate_families(good)
    assert probs == [] and len(fams) == 6
    cases = {
        "too few": {"families": [fam("a_b")] * 3},
        "too many": {"families": [fam(f"shape_{i}") for i in range(11)]},
        "forbidden word in name": {"families": [fam(n) for n in ("sideways_range", "drift_up", "drift_down", "steep_fall", "steep_rise", "upward_trend")]},
        "forbidden word in definition": {"families": [fam(n) for n in ("a_one", "b_two", "c_three", "d_four", "e_five")] + [fam("f_six", "a breakout from a flat band")]},
        "duplicate": {"families": [fam("same_name")] * 6},
        "reserved none": {"families": [fam(n) for n in ("none", "b_two", "c_three", "d_four", "e_five", "f_six")]},
        "bad snake_case": {"families": [fam(n) for n in ("Bad Name", "b_two", "c_three", "d_four", "e_five", "f_six")]},
        "long definition": {"families": [fam(n) for n in ("a_one", "b_two", "c_three", "d_four", "e_five")] + [fam("f_six", "word " * 30)]},
        "not a list": {"families": "x"},
    }
    for label, obj in cases.items():
        assert prompts5m.validate_families(obj)[0] is None, label


def test_vocabulary_prompt_reversal_and_tag_validation():
    names = ("sideways_range", "drift_up", "drift_down", "steep_fall", "steep_rise", "arch_shape")
    v = prompts5m.Vocabulary([fam(n) for n in names])
    p1, p2 = v.user_prompt(False), v.user_prompt(True)
    assert p1 != p2 and p1.index("sideways_range") < p1.index("arch_shape") and p2.index("arch_shape") < p2.index("sideways_range")
    assert p1.strip().splitlines()[-1].startswith("Return JSON") and prompts5m.lint(p1) == []
    assert v.names[-1] == "none" and len(v.sha256) == 64
    assert v.validate_tags({"tags": ["drift_up", "arch_shape"], "primary": "drift_up"})[2] is None
    for bad in ({"tags": ["trend_up"]}, {"tags": ["none", "drift_up"]}, {"tags": []}, {"tags": ["drift_up"], "primary": "arch_shape"}, {}):
        assert v.validate_tags(bad)[2] is not None


# ------------------------------------------------------------------- design lock + archive -----------------------
def test_archived_1h_experiment_is_untouched_by_5m_work():
    from pathlib import Path
    assert all(lock5m.archive_1h_intact().values())
    names = {f.name for f in (Path(config.ROOT) / "src" / "outcomes").glob("*.py")}
    assert names == {"__init__.py", "analyze.py", "forward.py", "stats.py"}                # nothing added to the frozen glob


def test_5m_discovery_code_never_imports_outcome_code():
    from pathlib import Path
    for f in (Path(config.ROOT) / "src" / "exp5m").glob("*.py"):
        if f.name == "outcomes5m.py":                                                       # the only module allowed (built later)
            continue
        txt = f.read_text(encoding="utf-8")
        assert "src.outcomes" not in txt and "forward_outcomes" not in txt, f.name


def test_design_lock_detects_changes_and_requires_confirmation(tmp_path, monkeypatch):
    prereg, cov = tmp_path / "PREREGISTRATION_5M.md", tmp_path / "COVERAGE_REPORT.json"
    prereg.write_text("frozen design\n"); cov.write_text("{}\n")
    monkeypatch.setattr(lock5m, "PREREG", prereg); monkeypatch.setattr(lock5m, "COVERAGE", cov)
    monkeypatch.setattr(lock5m, "DESIGN_LOCK", tmp_path / "lock.json")
    with pytest.raises(SystemExit, match="not frozen"):
        lock5m.require_design_lock("x" * 12)
    assert lock5m.main(["--write"]) == 0
    with pytest.raises(SystemExit, match="written once"):
        lock5m.main(["--write"])
    lock = json.loads((tmp_path / "lock.json").read_text())
    sha12 = lock["sha256"]["preregistration_5m"][:12]
    assert lock5m.require_design_lock(sha12)["experiment"] == params.EXPERIMENT
    with pytest.raises(SystemExit, match="confirm-design-sha"):
        lock5m.require_design_lock("000000000000")
    prereg.write_text("frozen design (edited)\n")
    with pytest.raises(SystemExit, match="MISMATCH"):
        lock5m.require_design_lock(sha12)
    prereg.write_text("frozen design\n")
    monkeypatch.setattr(params, "N_TARGET", 601)                                            # a parameter change is caught too
    with pytest.raises(SystemExit, match="MISMATCH"):
        lock5m.require_design_lock(sha12)
