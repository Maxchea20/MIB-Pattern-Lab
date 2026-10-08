"""Detector tests on constructed series only (no market data, no network, no outcome)."""
import numpy as np
import pytest

from src.brain import detectors as det
from src.setups import derive_params as dp
from src.setups import recognizer as rz
from tests.test_setups_recognizer import PATHS, THR as THR7, path

THR = {**THR7, "DT_C5": {"lo": 0.06, "hi": 0.12}}
E = 0.3


def ev(c, e=E, thr=THR):
    c = np.asarray(c, float)
    return det.evaluate(c + e, c - e, c, thr)


S5_PATH = path([(0, 100), (10, 95), (30, 110), (40, 104), (62, 130), (80, 126), (95, 128.5)])


def s5_with_dip(close_at=70, level=105.0):
    c = S5_PATH.copy()
    c[close_at] = level                                      # one completed close back below the broken swing high (110.3)
    return c


def test_s5_present_with_breakout_level_and_continuation_trigger_level():
    out = ev(S5_PATH)
    assert "S5" in out
    (direction, level, rules), = out["S5"]
    h = S5_PATH + E
    assert direction == "up" and level == pytest.approx(h[62])                  # trigger level = the spike high
    assert rules == [("lt", pytest.approx(h[30]))]                              # invalidation = close below the broken swing high (breakout level)
    sh, _ = dp.swings(S5_PATH + E, S5_PATH - E)
    assert sh[-2] == 30 and sh[-1] == 62                                        # previous confirmed swing high, then the spike's


def test_s5_breakout_level_is_the_previous_confirmed_swing_high_not_a_later_or_higher_one():
    c = path([(0, 100), (10, 95), (20, 108), (30, 110), (40, 104), (62, 130), (80, 126), (95, 128.5)])
    (d, level, rules), = ev(c)["S5"]
    assert rules[0][1] == pytest.approx(110 + E)                                # nearest confirmed swing high before the spike (30), not 20


def test_s5_invalidated_when_a_completed_close_falls_back_below_the_broken_high():
    assert "S5" not in ev(s5_with_dip())
    c = S5_PATH.copy()
    c[70] = 110.3 + 0.01                                                        # a close still above the level keeps it present
    assert "S5" in ev(c)
    c = S5_PATH.copy()
    c[70] = 110.3 - 0.01                                                        # one tick below: the hold fails
    assert "S5" not in ev(c)


def test_s5_requires_a_close_above_the_previous_swing_high_inside_the_spike():
    c = path([(0, 100), (10, 95), (30, 110), (40, 104), (62, 109.9), (80, 106), (95, 108)])   # never closes above 110.3
    assert "S5" not in ev(c)


def test_s5_other_frozen_conditions_are_kept():
    assert "S5" not in ev(path([(0, 100), (10, 95), (30, 110), (40, 104), (62, 130), (80, 126), (95, 118)]))     # not compressing near the high
    assert "S5" not in ev(path([(0, 100), (4, 160), (10, 95), (30, 110), (40, 104), (45, 112), (62, 113), (80, 112), (95, 112.5)]))  # mild move: UP below q67


def test_s5_spike_peak_is_unknown_until_k_candles_later_no_lookahead():
    c = path([(0, 100), (10, 95), (30, 110), (40, 104), (92, 130), (93, 129), (95, 128.5)])    # peak at 92: only 3 candles after -> confirmed at 95
    h, l = c + E, c - E
    sh, _ = dp.swings(h, l)
    assert 92 in sh                                                              # exactly K candles after: confirmed now
    c2 = path([(0, 100), (10, 95), (30, 110), (40, 104), (93, 130), (95, 129)])                # peak at 93: 2 candles after -> NOT confirmed
    h2, l2 = c2 + E, c2 - E
    assert 93 not in dp.swings(h2, l2)[0]
    assert "S5" not in ev(c2)


def test_s5_trigger_is_a_close_above_the_spike_high():
    from tests.test_brain_brain import run_series
    h = S5_PATH + E
    ev_ = [e for e in run_series(np.r_[S5_PATH, h[62] + 1.0]) if e["setup_id"] == "S5"]
    assert len(ev_) == 1 and ev_[0]["trigger_idx"] == 96 and ev_[0]["direction"] == "up"
    ev_ = [e for e in run_series(np.r_[S5_PATH, h[62] - 0.5]) if e["setup_id"] == "S5"]
    assert ev_ == []


def s9_path(width=0.8):
    base = path([(0, 105), (10, 100), (40, 120), (60, 110), (72, 110), (95, 110)])
    zz = np.where(np.arange(96) % 2 == 0, width, -width)
    return base + zz * np.r_[np.zeros(72), np.ones(24)]


def test_s9_present_with_both_boundaries_and_direction_decided_only_at_trigger():
    out = ev(s9_path())
    assert "S9" in out
    dirs = {d: (lvl, r) for d, lvl, r in out["S9"]}
    assert set(dirs) == {"up", "down"}
    c = s9_path()
    h, l = c + E, c - E
    assert dirs["up"][0] == pytest.approx(h[72:].max()) and dirs["down"][0] == pytest.approx(l[72:].min())
    assert dirs["up"][1] == [("le", pytest.approx(dirs["up"][0]))] and dirs["down"][1] == [("ge", pytest.approx(dirs["down"][0]))]


def test_s9_not_present_when_the_range_is_wide():
    assert "S9" not in ev(s9_path(width=6.0))


def test_s9_not_present_without_a_prior_move():
    c = 110 + np.where(np.arange(96) % 2 == 0, 0.8, -0.8)                       # flat chop for the whole window
    assert "S9" not in ev(c)


def test_experiment3_detectors_are_imported_unchanged():
    for sid, key in det.RZ_KEY.items():
        c = PATHS[key]
        direct = rz.window_state(c + E, c - E, c, THR)[key]
        got = ev(c).get(sid)
        assert (got is None) == (direct is None)
        if direct is not None:
            assert got[0][1] == pytest.approx(direct[0]) and got[0][0] == rz.DIRECTION[key]


def test_nine_detectors_are_listed_and_independent_of_each_other():
    assert det.IDS == ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9") and set(det.NAMES) == set(det.IDS)
    c = S5_PATH
    only = ev(c)
    assert "S5" in only
    c7 = ev(PATHS["C7"])
    assert "S7" in c7 and "S2" in c7                                            # two detectors true on one window, neither vetoes the other
