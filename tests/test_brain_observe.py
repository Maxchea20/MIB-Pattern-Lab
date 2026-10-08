"""Observation layer, freeze, derivation, scan wiring, dataset integrity and the REAL FILLS ONLY firewall."""
import ast
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import config
from src.brain import derive_s5, forward, freeze, scan
from src.brain import detectors as det
from src.brain.brain import STEP_NS
from src.setups import params
from tests.test_brain_brain import arrays, fires, run_series, START_NS
from tests.test_brain_detectors import THR
from tests.test_setups_recognizer import walk
from tests import policy_guard

ROOT = Path(config.ROOT)


def fire(t, direction="up", sid="S7", fid=None):
    return {"event": "FIRE", "fire_id": fid or f"{sid}-{t}-{direction}", "setup_id": sid, "direction": direction, "trigger_idx": t,
            "streak_position": 0}


def test_forward_observation_is_measured_from_the_next_open_and_is_signed_by_direction():
    n = 60
    ts = START_NS + np.arange(n, dtype=np.int64) * STEP_NS
    o = np.full(n, 100.0); c = np.full(n, 100.0); h = np.full(n, 100.0); l = np.full(n, 100.0)
    o[11], c[11], h[11], l[11] = 100.0, 102.0, 103.0, 99.0           # reference = open of candle 11 (the candle after the trigger candle 10)
    c[13], c[16] = 104.0, 98.0
    rows_up = forward.observe([fire(10)], [], ts, o, h, l, c, cutoff_ns=int(ts[-1]) + 1)
    r = rows_up[0]
    assert r["analytical_reference_price"] == 100.0
    assert r["fwd_return_pct_h1"] == pytest.approx(2.0) and r["fwd_return_pct_h3"] == pytest.approx(4.0)
    assert r["mfe_pct"] == pytest.approx(4.0) or r["mfe_pct"] >= 3.0
    rows_dn = forward.observe([fire(10, "down")], [], ts, o, h, l, c, cutoff_ns=int(ts[-1]) + 1)
    assert rows_dn[0]["fwd_return_pct_h1"] == pytest.approx(-2.0)
    assert rows_dn[0]["first_favorable_close_candle"] == 6 or rows_dn[0]["first_favorable_close_candle"] is not None


def test_forward_observation_is_censored_not_invented_at_the_end_of_the_data():
    n = 30
    ts = START_NS + np.arange(n, dtype=np.int64) * STEP_NS
    x = np.full(n, 100.0)
    r = forward.observe([fire(26)], [], ts, x, x, x, x, cutoff_ns=int(ts[-1]) + 1)[0]
    assert r["n_forward_available"] == 3 and r["fwd_return_pct_h6"] is None and r["fwd_return_pct_h1"] == 0.0
    last = forward.observe([fire(29)], [], ts, x, x, x, x, cutoff_ns=int(ts[-1]) + 1)[0]
    assert last["analytical_reference_price"] is None and last["n_forward_available"] == 0


def test_same_candle_order_of_mfe_and_mae_is_flagged_unknown_not_guessed():
    n = 40
    ts = START_NS + np.arange(n, dtype=np.int64) * STEP_NS
    o = np.full(n, 100.0); c = np.full(n, 100.0); h = np.full(n, 100.0); l = np.full(n, 100.0)
    h[11], l[11] = 105.0, 95.0                                      # both extremes inside one candle
    r = forward.observe([fire(10)], [], ts, o, h, l, c, cutoff_ns=int(ts[-1]) + 1)[0]
    assert r["mfe_pct"] == pytest.approx(5.0) and r["mae_pct"] == pytest.approx(5.0) and r["mfe_mae_same_candle_order_unknown"] is True


def test_period_labels_and_boundary_flag_keep_the_unseen_period_separate():
    n = 200
    ts = START_NS + np.arange(n, dtype=np.int64) * STEP_NS
    x = np.full(n, 100.0)
    cutoff = int(ts[100])
    rows = forward.observe([fire(50), fire(95), fire(150)], [], ts, x, x, x, x, cutoff_ns=cutoff)
    assert [r["period"] for r in rows] == ["IN_SAMPLE", "IN_SAMPLE", "UNSEEN"]
    assert rows[0]["forward_crosses_boundary"] is False and rows[1]["forward_crosses_boundary"] is True


def test_observation_rows_contain_no_execution_fields():
    n = 60
    ts = START_NS + np.arange(n, dtype=np.int64) * STEP_NS
    x = np.full(n, 100.0)
    r = forward.observe([fire(10)], [], ts, x, x, x, x, cutoff_ns=10**30)[0]
    bad = {"entry", "exit", "stop", "target", "fill", "pnl", "profit", "tp", "sl", "slippage", "fee", "leverage"}
    for k in r:
        assert not any(b in k.lower().split("_") for b in bad), k
    assert "analytical_reference_price" in r


def test_trailing_volatility_is_causal():
    c = walk(500, 3)
    v = forward.trailing_vol(c)
    c2 = c.copy()
    c2[300:] = 1.0
    assert np.allclose(v[:300], forward.trailing_vol(c2)[:300], equal_nan=True)


def test_derive_s5_measures_distance_to_the_spike_high_and_refuses_to_overwrite(tmp_path):
    from tests.test_brain_detectors import S5_PATH, E
    m = derive_s5.measure_dt_c5(S5_PATH + E, S5_PATH - E, S5_PATH)
    R = (S5_PATH + E).max() - (S5_PATH - E).min()
    assert m == pytest.approx(((S5_PATH + E)[62] - S5_PATH[-1]) / R)
    assert np.isnan(derive_s5.measure_dt_c5(*[np.full(96, 5.0)] * 3))
    out = tmp_path / "d.json"
    out.write_text("{}")
    with pytest.raises(SystemExit):
        derive_s5.main(["--out", str(out)])
    assert "outcome" not in Path(derive_s5.__file__).read_text().lower().replace("no outcome", "")


def make_root(tmp_path):
    root = tmp_path / "repo"
    for n in freeze.DETECTOR_FILES + freeze.THRESHOLD_FILES + freeze.CONTEXT_FILES:
        p = root / n
        p.parent.mkdir(parents=True, exist_ok=True)
        src = ROOT / n
        p.write_text(src.read_text(encoding="utf-8") if src.exists() else "{}", encoding="utf-8")
    return root


def test_detector_freeze_is_written_once_and_any_change_blocks_the_scan(tmp_path):
    root = make_root(tmp_path)
    path = tmp_path / "freeze.json"
    rec = freeze.write(root, path)
    assert rec["detector_version_sha256"] == freeze.detector_version(root) and len(rec["setups"]) == 9
    with pytest.raises(SystemExit):
        freeze.write(root, path)
    assert freeze.verify(root, path)["detector_version_sha256"] == rec["detector_version_sha256"]
    (root / "src/brain/detectors.py").write_text((root / "src/brain/detectors.py").read_text() + "\n# tweak\n")
    with pytest.raises(SystemExit):
        freeze.verify(root, path)
    shutil.copy(ROOT / "src/brain/detectors.py", root / "src/brain/detectors.py")
    freeze.verify(root, path)
    (root / "results/brain/derived_s5.json").write_text('{"changed": 1}')                      # a changed threshold also blocks it
    with pytest.raises(SystemExit):
        freeze.verify(root, path)
    with pytest.raises(SystemExit):
        freeze.verify(root, tmp_path / "missing.json")


def test_observation_layer_is_not_part_of_the_detector_hash():
    names = set(freeze.DETECTOR_FILES)
    for n in ("src/brain/forward.py", "src/brain/examples.py", "src/brain/scan.py", "src/brain/replay.py"):
        assert n not in names


def test_scan_end_to_end_on_constructed_data(tmp_path):
    c = walk(5000, 17)
    ts, o, h, l, cc = arrays(c)
    df = pd.DataFrame({"ts": pd.to_datetime(ts, unit="ns", utc=True), "open": o, "high": h, "low": l, "close": cc})
    cutoff = pd.Timestamp(int(ts[3500]), tz="UTC").isoformat()
    res = scan.run_scan(df, THR, "v", tmp_path / "out", cutoff=cutoff, examples=True)
    assert res["replay_equals_batch"] and res["cross_check_experiment3"]["identical"] and res["fires"] > 20
    s = res["summary"]
    assert sum(s[i]["ALL"]["fires"] for i in det.IDS) == res["fires"]
    assert all(s[i]["IN_SAMPLE"]["fires"] + s[i]["UNSEEN"]["fires"] == s[i]["ALL"]["fires"] for i in det.IDS)
    rep = (tmp_path / "out" / "SETUP_BRAIN_REPORT.md").read_text()
    assert rep.startswith("## SETUP BRAIN RESULT") and "| S9 |" in rep
    for word in ("PASS", "FAIL", "profit", "winning"):
        assert word not in rep
    assert (tmp_path / "out" / "fires.jsonl").exists() and any((tmp_path / "out" / "examples").glob("S*.png"))
    again = scan.run_scan(df, THR, "v", tmp_path / "out2", cutoff=cutoff, examples=False)
    assert again["final_input_digest"] == res["final_input_digest"] and again["fires"] == res["fires"]


def test_dataset_card_detects_gaps_duplicates_and_bad_ohlc():
    from src.brain import replay
    ts = START_NS + np.arange(10, dtype=np.int64) * STEP_NS
    ts = np.delete(ts, 4)
    x = np.full(len(ts), 100.0)
    df = pd.DataFrame({"ts": pd.to_datetime(ts, unit="ns", utc=True), "open": x, "high": x, "low": x, "close": x})
    df.loc[2, "high"] = 90.0
    card = replay.dataset_card(df)
    assert card["gaps"] == 1 and card["missing_candles"] == 1 and card["invalid_ohlc_rows"] == 1 and card["duplicate_timestamps"] == 0


def test_documented_binance_dataset_integrity():
    cov = json.loads((ROOT / "docs/setups/COVERAGE_RESEARCH_BINANCE_REPORT.json").read_text(encoding="utf-8"))
    s = cov["series"]["15m"]
    assert cov["database_sha256"] == params.EXPECTED_DB_SHA256 and cov["database_bytes"] == params.EXPECTED_DB_BYTES
    assert cov["symbol"] == "BTC/USDT" and s["gap_count"] == 0 and s["duplicate_timestamps"] == 0 and s["invalid_ohlc_rows"] == 0
    assert s["rows"] == 37728 and s["latest"].startswith("2026-09-28")


def test_real_fills_firewall_brain_has_no_execution_or_outcome_code():
    findings, problems = policy_guard.check_repo(ROOT)
    assert findings == [] and "src/brain/" in policy_guard.PROTECTED_DIRS
    for f in (ROOT / "src/brain").glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
               {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        assert not any(("outcome" in m or "validation" in m or "exp5m" in m or "execution" in m) for m in mods), (f.name, mods)
        names = {n.id.lower() for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr.lower() for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert not names & {"fill_price", "stop_loss", "take_profit", "entry_price", "exit_price", "slippage", "pnl"}, f.name


def test_experiment3_files_are_untouched_by_this_experiment():
    lock = json.loads((ROOT / "docs/PREREG_SETUPS_F1_LOCK.json").read_text())
    assert (ROOT / "docs/setups/EXPERIMENT3_CLOSING_SUMMARY.md").exists() and lock
