"""S1 v2 (S1 only) tests: translation corrections, causality, equivalence with the frozen v1 for S2-S9, replay == batch, derivation, freeze."""
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import config
from src.brain import detectors as det
from src.brain import detectors_v2 as d2
from src.brain import derive_s1v2, freeze_v2, replay, s1_v2, s1v2_report, scan
from src.brain.brain import SetupBrain
from src.brain.brain_v2 import SetupBrainV2
from tests.test_brain_brain import arrays, fires, stream
from tests.test_brain_detectors import THR as THR_V1
from tests.test_setups_recognizer import path, walk

ROOT = Path(config.ROOT)
THR = {**THR_V1, "UPnet": {"lo": 0.30, "hi": 0.6}, "DT_S1v2": {"lo": 0.08, "hi": 0.2}}
E = 0.3


def ev1(c, e=E):
    c = np.asarray(c, float)
    return det.evaluate(c + e, c - e, c, THR)


def ev2(c, e=E):
    c = np.asarray(c, float)
    return d2.evaluate(c + e, c - e, c, THR)


# a spike INSIDE the last 24 candles, then a tight pause just under it (S0120 / S0535 style)
SPIKE_THEN_PAUSE = path([(0, 105), (12, 100), (40, 100), (60, 112), (80, 140), (81, 130), (95, 128.8)])
# the leg is a net rise but the last zig is tiny (choppy rise), then a compact pause (S0201 / S0159 style)
CHOPPY_RISE = path([(0, 100), (50, 130), (70, 128.5), (80, 131), (84, 129.5), (95, 130.2)])


def zz(c, width, start):
    z = np.where(np.arange(len(c)) % 2 == 0, width, -width)
    return c + z * (np.arange(len(c)) >= start)


def test_spike_then_tight_pause_is_recognised_by_v2_and_not_by_v1():
    assert "S1" not in ev1(SPIKE_THEN_PAUSE) and "S1" in ev2(SPIKE_THEN_PAUSE)
    (d, level, rules), = ev2(SPIKE_THEN_PAUSE)["S1"]
    h = SPIKE_THEN_PAUSE + E
    assert d == "up" and level == pytest.approx(h[81:].max())               # the pause's own high, not the spike wick
    assert level < h[80] - 5
    assert rules[0][0] == "lt" and rules[1] == ("le", pytest.approx(level))


def test_choppy_net_rise_counts_as_a_prior_upward_leg_in_v2():
    c = zz(CHOPPY_RISE, 0.0, 0)
    assert "S1" in ev2(c)
    q = s1_v2.quantities(c + E, c - E, c)
    assert q["UPnet"] > 0.8                                                  # net rise from the window's low, not the last small zig


def test_literal_or_accepts_a_shallow_pullback_when_the_range_is_not_compact():
    wide = path([(0, 100), (20, 100), (60, 130), (75, 120), (88, 140), (89, 139), (95, 138.9)])   # last-24 range is wide, pullback after the high is tiny
    assert "S1" not in ev1(wide) and "S1" in ev2(wide)
    e = s1_v2.explain_s1_v2(wide + E, wide - E, wide, THR)
    a2 = [k for k in e["conditions"] if k["condition"].startswith("A2")][0]
    assert a2["ok"] and "ZR 0.5" in a2["detail"]                                # ZR fails on its own; the pullback branch carries it


def test_v2_does_not_fire_on_a_reversal_candle_or_a_pure_momentum_run():
    rev = path([(0, 110), (60, 100), (90, 99.5), (94, 99.4), (95, 106)])
    assert "S1" not in ev2(rev)
    run = path([(0, 100), (95, 140)])                                         # steady rise, no confirmed swing high
    assert "S1" not in ev2(run)


def test_trigger_is_the_next_close_beyond_the_pause_high_and_the_level_is_causal():
    c = SPIKE_THEN_PAUSE
    h = c + E
    L = h[81:].max()
    series = np.r_[c, L + 0.5]
    ts, o, hh, l, cc = arrays(series)
    brain = SetupBrainV2(THR, "t", evaluate=d2.evaluate)
    ev = [e for e in replay.replay(stream(ts, o, hh, l, cc), brain) if e["event"] == "FIRE" and e["setup_id"] == "S1"]
    assert len(ev) == 1 and ev[0]["trigger_idx"] == 96 and ev[0]["operative_level"] == pytest.approx(L)
    ts, o, hh, l, cc = arrays(np.r_[c, L - 0.05])
    assert not [e for e in replay.replay(stream(ts, o, hh, l, cc), SetupBrainV2(THR, "t", evaluate=d2.evaluate)) if e["setup_id"] == "S1"]


def test_explanation_agrees_with_the_v2_detector_on_many_windows():
    seen = {True: 0, False: 0}
    bad = 0
    for seed in (1, 2, 3):
        c = walk(2500, seed)
        rng = np.random.default_rng(seed)
        for t in range(95, len(c)):
            w = c[t - 95:t + 1]
            e = rng.uniform(0.05, 0.6)
            got = bool(s1_v2.window_s1_v2(w + e, w - e, w, THR))
            exp = s1_v2.explain_s1_v2(w + e, w - e, w, THR)["present"]
            bad += got != exp
            seen[got] += 1
    for w in (SPIKE_THEN_PAUSE, CHOPPY_RISE):
        assert bool(s1_v2.window_s1_v2(w + E, w - E, w, THR)) == s1_v2.explain_s1_v2(w + E, w - E, w, THR)["present"]
    assert bad == 0 and seen[True] > 0 and seen[False] > 0


def test_brain_v2_with_the_v1_function_is_the_v1_brain():
    c = walk(3000, 8)
    ts, o, h, l, cc = arrays(c)
    a = replay.replay(stream(ts, o, h, l, cc), SetupBrain(THR, "x"))
    b = replay.replay(stream(ts, o, h, l, cc), SetupBrainV2(THR, "x"))
    assert len(fires(a)) > 10 and a == b


def test_s2_to_s9_are_the_v1_functions_and_only_s1_differs():
    c = walk(4000, 12)
    ts, o, h, l, cc = arrays(c)
    v1 = fires(replay.replay(stream(ts, o, h, l, cc), SetupBrain(THR, "v")))
    v2 = fires(replay.replay(stream(ts, o, h, l, cc), SetupBrainV2(THR, "v", evaluate=d2.evaluate)))
    strip = lambda ev, s: [{k: x for k, x in e.items() if k != "input_digest"} for e in ev if (e["setup_id"] == "S1") == s]      # noqa: E731
    assert strip(v1, False) == strip(v2, False) and len(strip(v1, False)) > 20
    assert strip(v1, True) != strip(v2, True) or not strip(v2, True)


@pytest.mark.parametrize("seed,gap", [(4, None), (9, 900)])
def test_v2_replay_equals_chronological_batch_scan(seed, gap):
    c = walk(3000, seed)
    ts, o, h, l, cc = arrays(c, gap_at=gap)
    a = replay.replay(stream(ts, o, h, l, cc), SetupBrainV2(THR, "v", evaluate=d2.evaluate))
    b = replay.batch_scan(ts, o, h, l, cc, THR, "v", evaluate_fn=d2.evaluate)
    assert any(e["setup_id"] == "S1" for e in fires(a)) and replay.comparable(a) == replay.comparable(b)


def test_v2_is_causal_prefix_invariance_and_noise_after():
    c = walk(3000, 6)
    run = lambda x: [e for e in replay.replay(stream(*arrays(x)[:1], *arrays(x)[1:]), SetupBrainV2(THR, "v", evaluate=d2.evaluate)) if e["event"] == "FIRE"]      # noqa: E731
    full = run(c)
    key = lambda ev, m: [{k: v for k, v in e.items() if k != "input_digest"} for e in ev if e["trigger_idx"] < m]      # noqa: E731
    assert any(e["setup_id"] == "S1" for e in full)
    for m in (500, 1500, 2500):
        assert key(run(c[:m]), m) == key(full, m)
        noisy = c.copy()
        noisy[m:] = np.random.default_rng(m).uniform(10, 900, len(c) - m)
        assert key(run(noisy), m) == key(full, m)


def test_v2_derivation_quantities_and_refusal_to_overwrite(tmp_path):
    c = SPIKE_THEN_PAUSE
    q = s1_v2.quantities(c + E, c - E, c)
    h, l = c + E, c - E
    R = h.max() - l.min()
    assert q["UPnet"] == pytest.approx((h[80] - l[:80].min()) / R)
    assert q["DT_S1v2"] == pytest.approx((h[81:].max() - c[-1]) / R)
    flat = np.full(96, 5.0)
    assert all(np.isnan(v) for v in s1_v2.quantities(flat, flat, flat).values())
    out = tmp_path / "d.json"
    out.write_text("{}")
    with pytest.raises(SystemExit):
        derive_s1v2.main(["--out", str(out)])


def make_root(tmp_path):
    root = tmp_path / "repo"
    for n in freeze_v2.NAMES + freeze_v2.CONTEXT_FILES:
        p = root / n
        p.parent.mkdir(parents=True, exist_ok=True)
        src = ROOT / n
        p.write_text(src.read_text(encoding="utf-8") if src.exists() else "{}", encoding="utf-8")
    return root


def test_v2_freeze_is_written_once_and_any_change_blocks_the_scan(tmp_path):
    root = make_root(tmp_path)
    path_ = tmp_path / "f.json"
    rec = freeze_v2.write(root, path_)
    assert rec["detector_version_sha256"] != json.loads((ROOT / "docs/brain/BRAIN_FREEZE.json").read_text())["detector_version_sha256"]
    with pytest.raises(SystemExit):
        freeze_v2.write(root, path_)
    freeze_v2.verify(root, path_)
    (root / "src/brain/s1_v2.py").write_text((root / "src/brain/s1_v2.py").read_text() + "\n# tweak\n")
    with pytest.raises(SystemExit):
        freeze_v2.verify(root, path_)
    shutil.copy(ROOT / "src/brain/s1_v2.py", root / "src/brain/s1_v2.py")
    (root / "results/brain_v2/derived_s1v2.json").write_text('{"changed": 1}')
    with pytest.raises(SystemExit):
        freeze_v2.verify(root, path_)


def test_v1_freeze_still_verifies_because_no_v1_file_was_touched():
    from src.brain import freeze
    if (ROOT / "results/brain/derived_s5.json").exists():
        assert freeze.verify()["detector_version_sha256"]


def test_scan_end_to_end_and_report_pieces(tmp_path):
    c = walk(6000, 23)
    ts, o, h, l, cc = arrays(c)
    df = pd.DataFrame({"ts": pd.to_datetime(ts, unit="ns", utc=True), "open": o, "high": h, "low": l, "close": cc})
    cutoff = pd.Timestamp(int(ts[3500]), tz="UTC").isoformat()
    r1 = scan.run_scan(df, THR, "v1", tmp_path / "v1", cutoff=cutoff, examples=False)
    r2 = scan.run_scan(df, THR, "v2", tmp_path / "v2", cutoff=cutoff, examples=False, brain_factory=lambda t, v: SetupBrainV2(t, v, evaluate=d2.evaluate),
                       evaluate_fn=d2.evaluate, cross_skip=("S1",))
    assert r1["replay_equals_batch"] and r2["replay_equals_batch"] and r2["cross_check_experiment3"]["identical"]
    v1 = [json.loads(x) for x in (tmp_path / "v1" / "fires.jsonl").read_text().splitlines()]
    v2 = [json.loads(x) for x in (tmp_path / "v2" / "fires.jsonl").read_text().splitlines()]
    cmp_ = s1v2_report.compare_v1_v2(v1, v2)
    assert cmp_["s2_s9_identical"] and cmp_["s1"]["v2_fires"] > 0
    stage_a = [{"chart_id": f"S{i:04d}", "end_ts": df["ts"].iloc[300 + 70 * i].isoformat(), "error": None, "parsed": {"status": "ACTIONABLE_NOW"}} for i in range(12)]
    cited = s1v2_report.cited12(df, stage_a, [r["chart_id"] for r in stage_a], THR, v2)
    assert len(cited) == 12 and all(len(x["steps"]) == 7 for x in cited)
    ex = s1v2_report.unseen_examples(v2, {r["trigger_idx"] for r in v1 if r["setup_id"] == "S1"}, ts, o, h, l, cc, THR, tmp_path / "ex", n=10)
    assert 0 < len(ex) <= 10 and all((tmp_path / "ex" / e["chart"]).exists() for e in ex)
    txt = s1v2_report.render(cmp_, cited, ex)
    assert "PASS" not in txt and "profit" not in txt.lower()
