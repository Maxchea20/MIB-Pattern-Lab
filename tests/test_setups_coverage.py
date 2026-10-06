import sqlite3

import numpy as np
import pandas as pd

from src.setups import coverage_audit as ca

T0 = int(pd.Timestamp("2026-04-01T00:00:00Z").timestamp())
N1 = 60 * 24 * 6                       # six days of 1m candles


def base_1m(seed=0):
    rng = np.random.default_rng(seed)
    close = 60000 * np.exp(np.cumsum(rng.normal(0, 0.0005, N1)))
    open_ = np.concatenate([[60000.0], close[:-1]])
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.0002, N1)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.0002, N1)))
    return pd.DataFrame({"ts": T0 + 60 * np.arange(N1), "open": open_, "high": high, "low": low, "close": close})


def agg(d, k):
    g = np.arange(len(d)) // k
    a = d.groupby(g).agg(ts=("ts", "first"), open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
    return a.iloc[: len(d) // k]


def make_db(path, drop_5m=None, bump_15m_high=None, with_1m=True):
    d1 = base_1m()
    d5, d15 = agg(d1, 5), agg(d1, 15)
    if drop_5m is not None:
        d5 = d5.drop(index=d5.index[drop_5m])
    if bump_15m_high is not None:
        d15 = d15.copy()
        d15.iloc[bump_15m_high, d15.columns.get_loc("high")] *= 1.01
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE candles (symbol TEXT, timeframe TEXT, ts INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL)")
    for tf, d in (("1m", d1 if with_1m else d1.iloc[:0]), ("5m", d5), ("15m", d15)):
        con.executemany("INSERT INTO candles VALUES ('BTC_USDT',?,?,?,?,?,?,1)",
                        [(tf, int(r.ts), r.open, r.high, r.low, r.close) for r in d.itertuples()])
    con.commit()
    con.close()


CUT = "2026-04-04T00:00:00Z"


def run(path, **kw):
    return ca.audit(path, cutoff=CUT, lookback=8, forward=4, min_gap=2, **kw)


def test_clean_database_reports_complete_children_and_exact_aggregates(tmp_path):
    db = tmp_path / "m.db"
    make_db(db)
    r = run(db)
    c5, c1 = r["child_candle_cross_checks"]["15m_vs_5m"], r["child_candle_cross_checks"]["15m_vs_1m"]
    assert c5["children_per_parent"] == 3 and c1["children_per_parent"] == 15
    # the loader drops the last stored candle of each series, so the final parent may lack a child: at most 1
    assert c5["parents_without_complete_children"] <= 1 and c1["parents_without_complete_children"] <= 1
    assert all(m["mismatching_parents"] == 0 for m in c5["aggregate_mismatch"].values())
    assert c5["open_time_check"]["parent_open_equals_child_open_at_same_label"] == 1.0
    assert c5["open_time_check"]["parent_open_equals_child_open_one_parent_step_earlier"] < 0.1
    f = r["discovery_holdout_feasibility"]
    assert f["usable_candles_before_cutoff"] > 0 and f["usable_candles_from_cutoff"] > 0
    assert f["discovery_positions_with_full_lookback_and_forward_path"] > 0
    assert f["holdout_positions_with_full_lookback_and_forward_path"] > 0
    assert r["series"]["15m"]["gap_count"] == 0 and r["database_sha256"] and not r["warnings"]


def test_missing_child_and_mismatching_aggregate_are_reported(tmp_path):
    db = tmp_path / "m.db"
    make_db(db, drop_5m=100, bump_15m_high=50)
    r = run(db)
    c5 = r["child_candle_cross_checks"]["15m_vs_5m"]
    assert c5["parents_without_complete_children"] >= 1
    assert c5["aggregate_mismatch"]["high"]["mismatching_parents"] == 1
    text = " ".join(r["warnings"])
    assert "15m_vs_5m" in text and "5m: 1 gaps" in text


def test_absent_1m_series_is_reported_not_fatal(tmp_path):
    db = tmp_path / "m.db"
    make_db(db, with_1m=False)
    r = run(db)
    assert r["series"]["1m"]["available"] is False
    assert "15m_vs_1m" not in r["child_candle_cross_checks"]
    assert any("1m: series not found" in w for w in r["warnings"])
    assert r["series"]["15m"]["available"] and r["series"]["5m"]["available"]


def test_audit_is_read_only_and_makes_no_outcome(tmp_path):
    db = tmp_path / "m.db"
    make_db(db)
    before = db.read_bytes()
    r = run(db)
    assert db.read_bytes() == before
    blob = str(r).lower()
    for word in ("forward_return", "mfe", "mae", "outcome_label"):
        assert word not in blob
