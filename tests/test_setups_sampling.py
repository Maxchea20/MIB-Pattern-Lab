import json

import numpy as np
import pandas as pd
import pytest

from src.charts.renderer import render_window
from src.charts.windows import build_window
from src.data.loader import CandleSet, build_candles
from src.setups import params, sampling
from tests.conftest import make_ohlc

START = pd.Timestamp("2025-10-01T00:00:00Z")
STEP_MS = 900_000


def series(n=8000, seed=0):
    raw = make_ohlc(n, start_ms=int(START.timestamp() * 1000), step_ms=STEP_MS, seed=seed, base=100_000.0)
    return build_candles(raw, "BTC/USDT", "15m", "synthetic", as_of="2100-01-01").df


@pytest.fixture
def small(monkeypatch):
    monkeypatch.setattr(params, "DISCOVERY_END", (START + pd.Timedelta(days=60)).isoformat())
    monkeypatch.setattr(params, "PER_STRATUM", 6)
    monkeypatch.setattr(params, "MIN_GAP_CANDLES", 10)
    return params


def test_candidates_use_only_pre_cutoff_data_and_a_complete_forward_path(small):
    df = series()
    cand, funnel, d = sampling.candidates(df)
    cutoff = pd.Timestamp(params.DISCOVERY_END)
    assert d["ts"].max() < cutoff and (cand["end_ts"] < cutoff).all()
    last_ok = d["ts"].iloc[-1 - params.FORWARD_MAX]
    assert cand["end_ts"].max() <= last_ok                                    # every candidate has 24 candles after it
    assert funnel["candidates"] == len(cand) and funnel["excluded_no_complete_forward_path_before_cutoff"] == params.FORWARD_MAX
    poisoned = df.copy()
    poisoned.loc[poisoned["ts"] >= cutoff, ["open", "high", "low", "close"]] *= 7.0   # hold-out data must never matter
    cand2, _, _ = sampling.candidates(poisoned)
    pd.testing.assert_frame_equal(cand, cand2)


def test_selection_is_deterministic_spaced_quota_bound_and_first_stratum_wins(small):
    cand, _, _ = sampling.candidates(series())
    cuts = sampling.cutpoints(cand)
    picks, short, c = sampling.select(cand, cuts)
    picks2, short2, _ = sampling.select(cand, cuts)
    assert [(t, s) for t, s, _ in picks] == [(t, s) for t, s, _ in picks2] and short == short2
    ts = [t for t, _, _ in picks]
    assert len(set(ts)) == len(ts) and ts == sorted(ts)
    gap = pd.Timedelta(minutes=15 * params.MIN_GAP_CANDLES)
    assert all(b - a >= gap for a, b in zip(ts, ts[1:]))                      # never closer than MIN_GAP candles
    per = pd.Series([s for _, s, _ in picks]).value_counts()
    assert (per <= params.PER_STRATUM).all() and set(per.index) <= set(params.STRATA)
    masks = sampling.stratum_masks(c, cuts)
    for t, s, i in picks:
        assert masks[s][i]                                                    # every pick satisfies its stratum rule


def test_stratum_rules_match_the_preregistered_table():
    cand = pd.DataFrame({"eff": [0.9, 0.1, 0.5, 0.5, 0.5, 0.5], "abs_net": [5.0, 0.1, 2.0, 2.0, 2.0, 2.0],
                         "re": [1.0, 1.0, 3.0, 0.2, 1.0, 1.0], "sharp": [1.0, 1.0, 1.0, 1.0, 9.0, 0.1]})
    cuts = {"eff": [0.3, 0.7], "abs_net": [1.0, 3.0], "re": [0.5, 2.0], "sharp": [0.5, 5.0]}
    m = sampling.stratum_masks(cand, cuts)
    assert m["S1_directional"].tolist() == [True, False, False, False, False, False]
    assert m["S2_sideways"].tolist() == [False, True, False, False, False, False]
    assert m["S3_expansion"].tolist() == [False, False, True, False, False, False]
    assert m["S4_compression"].tolist() == [False, False, False, True, False, False]
    assert m["S5_sharp"].tolist() == [False, False, False, False, True, False]
    assert m["S6_slow"].tolist() == [False, False, False, False, False, True]
    nan = pd.DataFrame({"eff": [np.nan], "abs_net": [1.0], "re": [np.nan], "sharp": [np.nan]})
    assert not any(v.any() for v in sampling.stratum_masks(nan, cuts).values())   # NaN never qualifies


def test_build_gives_neutral_ids_and_a_chronology_free_order(small, tmp_path):
    df = series()
    meta, rows = sampling.build(df, tmp_path)
    assert meta["n_selected"] == len(rows) > 0 and meta["chart_style_sha256"] == sampling.style_sha()
    assert [r["chart_id"] for r in rows] == [f"S{i:04d}" for i in range(1, len(rows) + 1)]
    assert all(r["chart"] == r["chart_id"] + ".png" and (tmp_path / "charts" / r["chart"]).exists() for r in rows)
    times = [r["end_ts"] for r in rows]
    assert times != sorted(times)                                              # shuffled, so order carries no chronology
    saved = [json.loads(l) for l in (tmp_path / "windows_setups.jsonl").read_text().splitlines()]
    assert saved == rows
    meta2, rows2 = sampling.build(df, tmp_path / "again")
    assert [(r["end_ts"], r["image_sha256"]) for r in rows] == [(r["end_ts"], r["image_sha256"]) for r in rows2]   # deterministic


def test_chart_depends_only_on_candles_up_to_T(tmp_path):
    df = series(1200)
    t = df["ts"].iloc[500]
    other = df.copy()
    other.loc[other["ts"] > t, ["open", "high", "low", "close"]] *= 3.0           # alter everything after T
    p1, p2 = tmp_path / "a.png", tmp_path / "b.png"
    for d, p in ((df, p1), (other, p2)):
        render_window(build_window(CandleSet(d, "BTC/USDT", "15m", "x"), t, params.LOOKBACK), p, sampling.chart_style())
    assert p1.read_bytes() == p2.read_bytes()


def test_chart_has_96_candles_and_no_dates(small):
    df = series(1200)
    w = build_window(CandleSet(df, "BTC/USDT", "15m", "x"), df["ts"].iloc[300], params.LOOKBACK)
    assert len(w.raw) == 96 == params.LOOKBACK
    st = sampling.chart_style()
    assert st == {"axis_labels": "pct", "time_labels": "relative", "y_span_pct": None}


def test_dryrun_report_is_read_only_deterministic_and_complete(small, tmp_path, monkeypatch):
    from src.setups import dryrun_report
    monkeypatch.chdir(tmp_path)
    before = sorted(p.name for p in tmp_path.iterdir())
    r = dryrun_report.report(series())
    assert sorted(p.name for p in tmp_path.iterdir()) == before                  # nothing written
    assert r["determinism"]["selection_identical_on_rerun"] and r["determinism"]["build_metadata_identical_on_rerun"]
    assert set(r["eligible_pool_per_stratum_(a_window_may_qualify_for_several)"]) == set(params.STRATA)
    assert sum(r["selected_per_stratum"].values()) == r["n_selected"] and r["all_selected_before_cutoff"]
    assert r["min_gap_between_selected_windows_candles"] >= params.MIN_GAP_CANDLES
    assert sum(r["candidates_by_first_matching_stratum"].values()) == r["funnel"]["candidates"]
