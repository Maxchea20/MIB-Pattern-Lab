import ast
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.loader import build_candles
from src.setups import derive_params as dp
from src.setups import params
from tests.conftest import make_ohlc

START = pd.Timestamp("2025-10-01T00:00:00Z")


def win(seed=0, n=96):
    rng = np.random.default_rng(seed)
    c = 100 + np.cumsum(rng.normal(0, 1, n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + rng.uniform(0.1, 0.8, n)
    l = np.minimum(o, c) - rng.uniform(0.1, 0.8, n)
    return o, h, l, c


def test_swings_need_k_candles_on_both_sides_inside_the_window():
    h = np.array([1, 2, 3, 9, 3, 2, 1, 1, 1, 1.0])
    l = h - 0.5
    sh, _ = dp.swings(h, l)
    assert sh == [3]
    sh2, _ = dp.swings(h[:6], l[:6])           # only 2 candles after the peak: not yet confirmed
    assert sh2 == []


def test_measures_known_geometry():
    n = 96
    h = np.full(n, 10.0); l = np.full(n, 9.0); c = np.full(n, 9.5)
    h[40] = 20.0                                # swing high (all neighbours 10)
    l[20] = 0.0                                 # swing low earlier
    m = dp.measures(c, h, l, c)
    R = 20.0
    assert m["UP"] == pytest.approx(1.0)
    assert m["RET"] == pytest.approx((20.0 - 9.0) / 20.0)      # pullback low 9 (tie-free: min low after the high)
    assert m["ZR"] == pytest.approx(1.0 / R)
    assert m["DT_C7"] == pytest.approx((10.0 - 9.5) / R)
    assert m["DF_C3"] == pytest.approx((9.5 - 9.0) / R)
    assert m["EFF"] == 0.0                      # flat closes: zero path -> 0
    assert math.isnan(m["DN"])                  # the only swing low precedes the only swing high


def test_zero_range_is_undefined():
    z = np.full(96, 5.0)
    assert all(math.isnan(v) for v in dp.measures(z, z, z, z).values())


def test_prefix_invariance_and_independence_from_anything_but_the_window():
    o, h, l, c = win(1)
    base = dp.measures(o, h, l, c)
    again = dp.measures(o.copy(), h.copy(), l.copy(), c.copy())
    assert all((base[k] == again[k]) or (math.isnan(base[k]) and math.isnan(again[k])) for k in base)
    # scale invariance: quantities are in range units
    s = dp.measures(o * 7, h * 7, l * 7, c * 7)
    for k in base:
        assert (math.isnan(base[k]) and math.isnan(s[k])) or base[k] == pytest.approx(s[k])


def test_c4_broken_swing_low_then_a_later_swing_low():
    n = 96
    h = np.full(n, 10.0); l = np.full(n, 9.0); c = np.full(n, 9.5)
    l[20] = 5.0                                 # swing low
    c[30] = 4.0; l[30] = 4.0                    # first close below it: the break
    l[60] = 3.0                                 # later, lower swing low
    m = dp.measures(c, h, l, c)
    assert not math.isnan(m["DF_C4"])
    assert m["DF_C4"] == pytest.approx((9.5 - 3.0) / (10.0 - 3.0))
    flat = dp.measures(np.full(n, 9.5), h, np.full(n, 9.0), np.full(n, 9.5))
    assert math.isnan(flat["DF_C4"])            # no swing low is ever broken


def test_derive_ignores_holdout_and_counts_gap_free_windows(monkeypatch):
    raw = make_ohlc(6000, start_ms=int(START.timestamp() * 1000), step_ms=900_000, seed=5, base=100_000.0)
    df = build_candles(raw, "BTC/USDT", "15m", "synthetic", as_of="2100-01-01").df
    cut = START + pd.Timedelta(days=40)
    monkeypatch.setattr(params, "DISCOVERY_END", cut.strftime("%Y-%m-%dT%H:%M:%SZ"))
    res = dp.derive(df)
    poisoned = df.copy()
    poisoned.loc[poisoned["ts"] >= cut, ["open", "high", "low", "close"]] *= 9.0
    assert dp.derive(poisoned) == res
    assert res["n_positions"] > 0
    for k, v in res["quantities"].items():
        if v["n_defined"]:
            assert v["q25"] <= v["q33"] <= v["q40"] <= v["q60"] <= v["q67"] <= v["q75"]


def test_module_imports_no_outcome_or_execution_code():
    src = Path(dp.__file__).read_text(encoding="utf-8")
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            mods.add(node.module or "")
    assert not any(("outcome" in m or "validation" in m or "exp5m" in m) for m in mods)
    assert "DT_C5" not in dp.KEYS                  # C5 is NOT CODEABLE and excluded


def test_refuses_to_overwrite_existing_output(tmp_path):
    out = tmp_path / "d.json"
    out.write_text("{}")
    with pytest.raises(SystemExit):
        dp.main(["--out", str(out)])
