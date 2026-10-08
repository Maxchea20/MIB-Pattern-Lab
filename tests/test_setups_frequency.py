import ast
from pathlib import Path

import numpy as np
import pytest

from src.setups import frequency_check as fc
from src.setups import recognizer as rz
from tests.test_setups_recognizer import THR, STEP, E, PATHS, walk


def series(c):
    ts = np.arange(len(c), dtype=np.int64) * STEP
    return ts, c, c + E, c - E, c


def test_report_counts_on_a_constructed_series_and_is_consistent_with_recognize():
    c = np.r_[PATHS["C7"], rz.window_state(PATHS["C7"] + E, PATHS["C7"] - E, PATHS["C7"], THR)["C7"][0] + 1.0]
    rep = fc.check(*series(c), THR)
    v = rep["candidates"]["C7"]
    assert rep["n_candles"] == 97 and rep["n_evaluated_candles"] == 2
    assert v["raw_triggers"] == v["counted_triggers"] + v["suppressed_triggers"] == 1
    assert v["presence_candles"] >= 1 and v["lockout"]["occurrences_never_invalidated_by_end_of_data"] == 1


def test_observer_does_not_change_recognizer_decisions():
    c = walk(2500, 11)
    base = rz.recognize(*series(c), THR)
    seen = []
    again = rz.recognize(*series(c), THR, on_state=lambda t, ok, st: seen.append(t))
    assert base == again and len(seen) == len(c)


def test_pairwise_overlap_and_shares_on_random_walk():
    rep = fc.check(*series(walk(4000, 7)), THR)
    assert len(rep["pairs"]) == 21 and set(rep["candidates"]) == set(rz.ORDER)
    for v in rep["candidates"].values():
        assert v["raw_triggers"] == v["counted_triggers"] + v["suppressed_triggers"]
        assert v["frequency_raw"]["share"] == pytest.approx(v["raw_triggers"] / rep["n_evaluated_candles"])
    for p in rep["pairs"].values():
        assert 0.0 <= p["presence_jaccard"] <= 1.0 and 0.0 <= p["raw_trigger_jaccard"] <= 1.0
    assert fc.jaccard({1, 2}, {2, 3}) == pytest.approx(1 / 3) and fc.jaccard(set(), set()) == 0.0
    assert fc.render(rep)


def test_runs_helper():
    assert fc._runs(np.array([0, 1, 1, 0, 1, 1, 1], bool)) == [2, 3]


def test_refuses_to_overwrite_and_has_no_outcome_code(tmp_path):
    out = tmp_path / "r.json"
    out.write_text("{}")
    with pytest.raises(SystemExit):
        fc.main(["--out", str(out)])
    src = Path(fc.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
           {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not any(("outcome" in m or "validation" in m or "exp5m" in m) for m in mods if m)
    names = {n.id.lower() for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not any(b in x for x in names for b in ("mfe", "mae", "pnl", "forward_return"))
