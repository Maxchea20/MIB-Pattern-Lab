import numpy as np
import pandas as pd
import pytest

from src.charts.normalize import normalize_window
from src.charts.renderer import chart_filename, render_window
from src.charts.windows import (build_window, sample_end_timestamps, valid_end_indices,
                                valid_end_timestamps)
from src.data.loader import CandleSet, build_candles
from src.validation.window_validation import WindowValidationError, validate_window
from tests.conftest import make_ohlc

L = 60


def _t(cs, i):
    return cs.df["ts"].iloc[i]


# Test 1
def test_window_has_exactly_60_candles(cs500):
    assert len(build_window(cs500, _t(cs500, 200), L).raw) == 60


# Test 2
def test_last_candle_is_T(cs500):
    T = _t(cs500, 200)
    w = build_window(cs500, T, L)
    assert w.raw["ts"].iloc[-1] == T and w.norm["ts"].iloc[-1] == T


# Test 3
def test_no_candle_after_T(cs500):
    T = _t(cs500, 200)
    w = build_window(cs500, T, L)
    assert (w.raw["ts"] <= T).all()
    assert w.raw["ts"].iloc[0] == _t(cs500, 200 - 59)


# Test 4
def test_chronological_order(cs500):
    w = build_window(cs500, _t(cs500, 300), L)
    assert w.raw["ts"].is_monotonic_increasing and w.raw["ts"].is_unique


def test_validator_rejects_bad_windows(cs500):
    T = _t(cs500, 200)
    raw = build_window(cs500, T, L).raw
    with pytest.raises(WindowValidationError):
        validate_window(raw.iloc[1:], T, "5m", L)                       # 59 candles
    with pytest.raises(WindowValidationError):
        validate_window(raw.iloc[::-1].reset_index(drop=True), T, "5m", L)  # reversed
    with pytest.raises(WindowValidationError):
        validate_window(raw, T - pd.Timedelta(minutes=5), "5m", L)     # last != T
    future = cs500.df.iloc[142:202][["ts", "open", "high", "low", "close"]].reset_index(drop=True)
    with pytest.raises(WindowValidationError):
        validate_window(future, T, "5m", L)                            # contains candle after T
    gap = raw.drop(index=30).reset_index(drop=True)
    with pytest.raises(WindowValidationError):
        validate_window(gap, T, "5m", L)                               # gap / wrong size


def test_cannot_build_window_before_enough_history_or_missing_T(cs500):
    with pytest.raises(Exception):
        build_window(cs500, _t(cs500, 10), L)                           # < 60 candles
    with pytest.raises(ValueError):
        build_window(cs500, _t(cs500, 100) + pd.Timedelta(minutes=1), L)


def test_windows_never_span_a_gap():
    raw = make_ohlc(300).drop(index=150).reset_index(drop=True)
    cs = build_candles(raw, "BTC/USDT", "5m", as_of="2100-01-01")
    for T in valid_end_timestamps(cs, L):
        w = build_window(cs, T, L)             # validate_window would raise on a gap
        assert w.raw["ts"].diff().dropna().eq(pd.Timedelta(minutes=5)).all()
    assert len(valid_end_indices(cs.df, "5m", L)) < len(cs.df) - L + 1


# Test 7
def test_normalization_ignores_future_candles(cs500):
    T = _t(cs500, 250)
    w1 = build_window(cs500, T, L)
    # wildly different future must not change the window or its normalization
    fut = cs500.df.copy()
    fut.loc[fut["ts"] > T, ["open", "high", "low", "close"]] = 1e9
    w2 = build_window(CandleSet(fut, "BTC/USDT", "5m", "x"), T, L)
    pd.testing.assert_frame_equal(w1.norm, w2.norm)
    pd.testing.assert_frame_equal(w1.raw, w2.raw)
    # and data truncated at T is identical to the full dataset
    trunc = CandleSet(cs500.df[cs500.df["ts"] <= T].reset_index(drop=True), "BTC/USDT", "5m", "x")
    pd.testing.assert_frame_equal(w1.norm, build_window(trunc, T, L).norm)


def test_normalization_scale_invariant_and_raw_kept(cs500):
    w = build_window(cs500, _t(cs500, 250), L)
    scaled = w.raw.copy()
    scaled[["open", "high", "low", "close"]] *= 100_000 / 60_000
    np.testing.assert_allclose(normalize_window(scaled)[["open", "high", "low", "close"]].to_numpy(),
                               w.norm[["open", "high", "low", "close"]].to_numpy(), rtol=1e-9)
    assert w.norm["close"].iloc[-1] == 0.0          # anchored on close at T
    assert w.raw["close"].iloc[-1] > 1000           # raw prices preserved


def test_chart_is_deterministic_and_nonempty(cs500, tmp_path):
    w = build_window(cs500, _t(cs500, 250), L)
    a = render_window(w, tmp_path / "a" / chart_filename(w))
    b = render_window(w, tmp_path / "b" / chart_filename(w))
    assert a.read_bytes() == b.read_bytes() and a.stat().st_size > 5000


def test_chart_independent_of_future(cs500, tmp_path):
    T = _t(cs500, 250)
    a = render_window(build_window(cs500, T, L), tmp_path / "a.png")
    trunc = CandleSet(cs500.df[cs500.df["ts"] <= T].reset_index(drop=True), "BTC/USDT", "5m", "x")
    b = render_window(build_window(trunc, T, L), tmp_path / "b.png")
    assert a.read_bytes() == b.read_bytes()


def test_sampling_is_deterministic_and_valid(cs500):
    s1 = sample_end_timestamps(cs500, L, 20)
    assert s1 == sample_end_timestamps(cs500, L, 20) and len(set(s1)) == 20
    assert s1 == sorted(s1) and s1[0] == _t(cs500, 59) and s1[-1] == _t(cs500, 499)
    assert sample_end_timestamps(cs500, L, 5, seed=1) == sample_end_timestamps(cs500, L, 5, seed=1)
