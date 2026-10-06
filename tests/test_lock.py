import json

import pandas as pd
import pytest

import config
from src.discovery import families, lock, vocab
from tests.test_vocab import Tagger, run_dir  # noqa: F401  (fixtures)
from src.discovery.retag import run_retag


def test_families_are_unmerged_and_impulse_up_is_reserved():
    assert families.PRIMARY == ("sideways_range", "drift_up", "drift_down")
    assert "impulse_up" not in families.FAMILIES and families.RESERVED_UNUSED == ("impulse_up",)
    for sep in ("stair_step_up", "sharp_rally", "range_breakout_up"):
        assert sep in families.EXPLORATORY and sep not in families.PRIMARY
    assert set(families.FAMILIES) == set(vocab.NAMES) - {vocab.NONE_TAG}
    m = families.membership({"a": ["drift_up", "stair_step_up"], "b": [], "c": ["none"]})
    assert m["drift_up"] == {"a"} and m["stair_step_up"] == {"a"} and all("b" not in v and "c" not in v for v in m.values())


@pytest.fixture
def locked_dir(run_dir, monkeypatch):
    monkeypatch.setattr(config, "DISCOVERY_END_BY_TF", {"1h": "2026-06-01T00:00:00Z"})
    # run_dir fixture windows are daily timestamps -> >= 60h apart; add the keys the lock needs
    rows = [json.loads(l) for l in (run_dir / "descriptions.jsonl").read_text().splitlines()]
    for i, r in enumerate(rows):
        r["chart_style_sha256"] = "abc"
        r["end_ts"] = f"2026-01-{1 + 3 * i:02d}T00:00:00+00:00"          # 72h apart (>= one 60h window)
    (run_dir / "descriptions.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    (run_dir / "windows.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    run_retag(run_dir, Tagger(lambda png, n: {"tags": ["sideways_range"]}), passes=2)
    return run_dir


def test_lock_ok_records_hashes_and_family_counts(locked_dir):
    rec = lock.build_lock(locked_dir, "1h")
    assert rec["n_windows"] == 6 and rec["family_window_counts"]["sideways_range"] == 6
    assert rec["family_window_counts"]["drift_up"] == 0 and len(rec["sha256"]["windows_jsonl"]) == 64
    assert rec["sha256"]["vocab"] == vocab.VOCAB_SHA256 and rec["primary_families"] == list(families.PRIMARY)


def test_lock_refuses_incomplete_overlapping_late_or_mixed(locked_dir, monkeypatch):
    # incomplete tagging
    rows = [json.loads(l) for l in (locked_dir / "retags.jsonl").read_text().splitlines()]
    (locked_dir / "retags.jsonl").write_text("\n".join(json.dumps(r) for r in rows[:-1]), encoding="utf-8")
    with pytest.raises(SystemExit, match="lack a clean tagging pass"):
        lock.build_lock(locked_dir, "1h")
    (locked_dir / "retags.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    # cutoff before the last window
    monkeypatch.setattr(config, "DISCOVERY_END_BY_TF", {"1h": "2026-01-10T00:00:00Z"})
    with pytest.raises(SystemExit, match="cutoff"):
        lock.build_lock(locked_dir, "1h")
    monkeypatch.setattr(config, "DISCOVERY_END_BY_TF", {"1h": "2026-06-01T00:00:00Z"})
    # different model mixed in
    rows2 = [dict(r, model="other") if i == 0 else r for i, r in enumerate(rows)]
    (locked_dir / "retags.jsonl").write_text("\n".join(json.dumps(r) for r in rows2), encoding="utf-8")
    with pytest.raises(SystemExit, match="mixed model"):
        lock.build_lock(locked_dir, "1h")
