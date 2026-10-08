import numpy as np
import pytest

from src.brain import detectors as det
from src.brain import explain as ex
from tests.test_brain_detectors import S5_PATH, THR, s9_path
from tests.test_setups_recognizer import PATHS, walk


def windows(seed, count=1500):
    c = walk(count + 96, seed)
    rng = np.random.default_rng(seed)
    for t in range(95, len(c)):
        w = c[t - 95:t + 1]
        e = rng.uniform(0.05, 0.6)
        yield w, w + e, w - e


def test_explanation_agrees_with_the_detectors_on_many_random_windows_and_constructed_ones():
    seen = {s: 0 for s in det.IDS}
    mism = []
    ws = [(w, h, l) for seed in (1, 2, 3, 4) for w, h, l in windows(seed)]
    ws += [(p, p + .3, p - .3) for p in list(PATHS.values()) + [S5_PATH, s9_path()]]
    for w, h, l in ws:
        got = det.evaluate(h, l, w, THR)
        for sid in det.IDS:
            e = ex.explain(sid, h, l, w, THR)
            if e["present"] != (sid in got):
                mism.append(sid)
            seen[sid] += sid in got
    assert not mism, set(mism)
    assert all(v > 0 for k, v in seen.items() if k in ("S1", "S2", "S3", "S4", "S6", "S7", "S8", "S9")) and seen["S5"] > 0


def test_explanation_names_the_failing_condition():
    w = S5_PATH.copy()
    w[70] = 105.0
    e = ex.explain("S5", w + .3, w - .3, w, THR)
    assert not e["present"] and "E3" in ex.first_failure(e)
    flat = np.full(96, 50.0)
    assert not ex.explain("S1", flat, flat, flat, THR)["present"]
