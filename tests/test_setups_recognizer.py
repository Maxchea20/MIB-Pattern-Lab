"""Recognizer tests on CONSTRUCTED series only (no market data, no outcomes)."""
import ast
from pathlib import Path

import numpy as np
import pytest

from src.setups import derive_params as dp
from src.setups import recognizer as rz

Q = {"ZR": (0.3754, 0.5916), "EFF": (0.1079, 0.2482), "UP": (0.1889, 0.3250), "DN": (0.1845, 0.3316), "RET": (0.6908, 1.2846),
     "REB": (0.1886, 0.3229), "DT_C1": (0.0890, 0.2014), "DT_C2": (0.0618, 0.1511), "DF_C3": (0.1397, 0.2933),
     "DF_C4": (0.1162, 0.2387), "DF_C6": (0.0651, 0.1571), "DT_C7": (0.1307, 0.2815), "DF_C8": (0.1072, 0.2296)}
THR = {k: {"lo": v[0], "hi": v[1]} for k, v in Q.items()}
STEP = 900_000_000_000
E = 0.3


def path(pts, n=96):
    return np.interp(np.arange(n), [p[0] for p in pts], [p[1] for p in pts])


def state(c, e=E):
    return rz.window_state(c + e, c - e, c, THR)


def zigzag_range(end=96.0):
    base = np.r_[np.full(72, 100.0), np.interp(np.arange(24), [0, 4, 24], [100, 104, end])]
    zz = np.where(np.arange(96) % 2 == 0, 1.2, -1.2)
    return base + zz * np.r_[np.full(72, 1.0), np.full(24, 1.5)]


PATHS = {
    "C1": path([(0, 105), (15, 100), (60, 120), (70, 117), (85, 119.5), (95, 119.5)]),
    "C2": path([(0, 100), (10, 105), (50, 80), (80, 92), (95, 92)]),
    "C3": zigzag_range(),
    "C4": path([(0, 100), (20, 90), (30, 95), (45, 86), (55, 91), (65, 87.5), (75, 89), (95, 88)]),
    "C6": path([(0, 105), (12, 100), (55, 120), (85, 104), (95, 105)]),
    "C7": path([(0, 100), (10, 105), (50, 80), (80, 92), (95, 92)]),
    "C8": path([(0, 100), (40, 120), (60, 105), (75, 115), (95, 106)]),
}


def run(c, e=E):
    ts = np.arange(len(c), dtype=np.int64) * STEP
    return rz.recognize(ts, c, c + e, c - e, c, THR)


def extend(c, *closes):
    return np.r_[c, closes]


@pytest.mark.parametrize("cand", rz.ORDER)
def test_positive_presence_then_trigger_on_the_next_closing_candle_then_invalidation(cand):
    c = PATHS[cand]
    st = state(c)[cand]
    assert st is not None, f"{cand} presence expected on the constructed window"
    level = st[0]
    up = rz.DIRECTION[cand] == "up"
    trig = level + 1.0 if up else level - 1.0
    ev = [e for e in run(extend(c, trig)) if e["cand"] == cand]
    assert len(ev) == 1 and ev[0]["trigger_idx"] == 96 and ev[0]["presence_start_idx"] <= 95 and ev[0]["presence_len"] >= 1
    assert ev[0]["counted"] and ev[0]["invalidation_idx"] is None
    breach = -1000.0 if up else 1000.0
    ev = [e for e in run(extend(c, trig, breach)) if e["cand"] == cand]
    assert ev[0]["trigger_idx"] == 96 and ev[0]["invalidation_idx"] == 97


@pytest.mark.parametrize("cand", rz.ORDER)
def test_touching_the_level_without_closing_beyond_is_not_a_trigger(cand):
    c = PATHS[cand]
    level = state(c)[cand][0]
    up = rz.DIRECTION[cand] == "up"
    inside = level - 0.1 if up else level + 0.1
    series = extend(c, inside)
    ts = np.arange(len(series), dtype=np.int64) * STEP
    h, l = series + E, series - E
    h[-1] = level + 5 if up else h[-1]            # the wick pokes through, the close does not
    l[-1] = level - 5 if not up else l[-1]
    assert [e for e in rz.recognize(ts, series, h, l, series, THR) if e["cand"] == cand] == []


NEGATIVES = {
    "C1": path([(0, 119.5), (95, 119.5)]),                                                      # no prior up-leg
    "C2": path([(0, 100), (10, 105), (50, 80), (80, 92), (95, 82)]),                              # not pressing into the rebound high
    "C3": zigzag_range(end=103.0),                                                              # closes mid-range, not the lower third
    "C4": path([(0, 100), (20, 90), (30, 95), (45, 86), (95, 88)]),                              # no descending structure after the break
    "C6": path([(0, 105), (12, 100), (55, 120), (85, 97), (95, 98)]),                            # RET > 1: J-14
    "C7": path([(0, 90), (95, 100)]),                                                           # no prior decline
    "C8": path([(0, 100), (40, 120), (60, 105), (75, 115), (95, 112)]),                          # far above the support
}


@pytest.mark.parametrize("cand", rz.ORDER)
def test_breaking_one_condition_removes_presence(cand):
    assert state(NEGATIVES[cand])[cand] is None


def test_c6_retracement_cap_j14_boundaries():
    # RET just under 1.0 is allowed, just over 1.0 is not (lower threshold q33 unchanged)
    for low, expect in ((100.5, True), (99.0, False)):
        c = path([(0, 105), (12, 100), (55, 120), (85, low), (95, low + 0.5)])
        assert (state(c)["C6"] is not None) == expect, low


def test_flat_and_degenerate_windows_have_no_presence():
    assert all(v is None for v in state(np.full(96, 50.0)).values())
    c = PATHS["C1"].copy()
    assert all(v is None for v in rz.window_state(c[:90] + E, c[:90] - E, c[:90], THR).values())   # short window: not evaluated


def test_c5_is_not_present_anywhere():
    assert "C5" not in rz.ORDER and "C5" not in rz.DIRECTION and "C5" not in rz.NAMES


def test_lockout_logs_but_does_not_count_a_second_trigger_inside_it():
    c = PATHS["C7"]
    level = state(c)["C7"][0]
    # two consecutive closes beyond the level: the second is inside the lockout (presence is re-evaluated, trigger is logged)
    ev = [e for e in run(extend(c, level + 1, level + 1.2, level + 1.4)) if e["cand"] == "C7"]
    counted = [e for e in ev if e["counted"]]
    assert len(counted) == 1 and counted[0]["trigger_idx"] == 96
    assert all(e["locked_by"] == 96 for e in ev if not e["counted"])


def test_gap_in_the_series_blocks_evaluation():
    c = extend(PATHS["C7"], state(PATHS["C7"])["C7"][0] + 1)
    ts = np.arange(len(c), dtype=np.int64) * STEP
    ts[50:] += STEP                                         # one missing candle inside the 96-candle window
    assert [e for e in rz.recognize(ts, c, c + E, c - E, c, THR) if e["cand"] == "C7"] == []


def walk(n=4000, seed=7):
    rng = np.random.default_rng(seed)
    return 100 + np.cumsum(rng.normal(0, 1.0, n)) + 8 * np.sin(np.arange(n) / 40.0)


def strip(ev, m):
    keep = ("cand", "trigger_idx", "presence_start_idx", "presence_len", "level", "counted", "locked_by")
    out = []
    for e in ev:
        if e["trigger_idx"] < m:
            d = {k: e[k] for k in keep}
            d["invalidation_idx"] = e["invalidation_idx"] if (e["invalidation_idx"] is not None and e["invalidation_idx"] < m) else None
            out.append(d)
    return out


def test_prefix_invariance_noise_after_and_scale_invariance():
    c = walk()
    full = run(c)
    assert len(full) > 20 and len({e["cand"] for e in full}) >= 3          # not vacuous
    for m in (300, 1000, 2222, 3500):
        assert strip(run(c[:m]), m) == strip(full, m)                      # later candles removed
        noisy = c.copy()
        noisy[m:] = np.random.default_rng(m).uniform(50, 500, len(c) - m)  # later candles replaced by noise
        assert strip(run(noisy), m) == strip(full, m)
    scaled = run(c * 7.0, e=E * 7.0)
    assert [(e["cand"], e["trigger_idx"], e["presence_len"], e["counted"]) for e in scaled] == \
           [(e["cand"], e["trigger_idx"], e["presence_len"], e["counted"]) for e in full]


def test_window_state_depends_only_on_its_own_window():
    c = walk(300)
    a = rz.window_state(c[100:196] + E, c[100:196] - E, c[100:196], THR)
    poisoned = c.copy()
    poisoned[:100] = 1e9
    poisoned[196:] = -1e9
    b = rz.window_state(poisoned[100:196] + E, poisoned[100:196] - E, poisoned[100:196], THR)
    assert a == b


def test_pivot_is_unknown_until_k_candles_after_it():
    h = np.r_[np.linspace(1, 5, 5), 9.0, 5, 4, 3, 2]                       # peak at index 5
    l = h - 0.5
    assert dp.swings(h[:6 + dp.K - 1], l[:6 + dp.K - 1])[0] == []          # only K-1 candles after it
    assert dp.swings(h[:6 + dp.K], l[:6 + dp.K])[0] == [5]                 # confirmed at j + K


def test_deterministic_output():
    c = walk(1500, 3)
    assert run(c) == run(c.copy())


def test_module_has_no_outcome_or_evaluation_imports():
    src = Path(rz.__file__).read_text(encoding="utf-8")
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            mods.add(node.module or "")
    assert mods <= {"__future__", "numpy", "src.setups.derive_params"}, mods
    names = {n.id.lower() for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Name)} | \
            {n.attr.lower() for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Attribute)}
    for bad in ("forward_return", "mfe", "mae", "pnl", "profit", "outcome", "outcomes"):
        assert not any(bad in x for x in names), bad
