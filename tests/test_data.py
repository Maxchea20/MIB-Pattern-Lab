import sqlite3

import pandas as pd
import pytest

from src.data import inspect_db
from src.data.loader import (DuplicateTimestampError, build_candles, filter_closed,
                             load_candles, tf_to_seconds)
from tests.conftest import make_ohlc


def test_loader_discovers_schema_and_filters_btc_5m(synthetic_db):
    cs = load_candles(synthetic_db, "BTC/USDT", "5m", as_of="2100-01-01")
    assert len(cs.df) == 399 and cs.stats["trailing_dropped"] == 1   # last stored candle dropped (may be forming)
    assert cs.df["ts"].is_monotonic_increasing
    assert cs.df["ts"].diff().dropna().dt.total_seconds().eq(300).all()


def test_database_not_modified_and_opened_readonly(synthetic_db):
    before = synthetic_db.read_bytes()
    load_candles(synthetic_db, "BTC/USDT", "5m", as_of="2100-01-01")
    inspect_db.build_report(synthetic_db)
    assert synthetic_db.read_bytes() == before


def test_inspection_report_contents(synthetic_db):
    rep = inspect_db.build_report(synthetic_db)
    for s in ["candles", "open_time", "BTC/USDT", "Duplicates", "Missing candles", "Invalid rows", "Rows:"]:
        assert s in rep


# Test 5: duplicates rejected by default, handled explicitly on request
def test_duplicate_timestamps_rejected_by_default():
    raw = make_ohlc(100)
    raw = pd.concat([raw, raw.iloc[[50]]], ignore_index=True)
    with pytest.raises(DuplicateTimestampError):
        build_candles(raw, "BTC/USDT", "5m", as_of="2100-01-01")


def test_duplicate_timestamps_keep_last_policy():
    raw = make_ohlc(100)
    raw = pd.concat([raw, raw.iloc[[50]]], ignore_index=True)
    cs = build_candles(raw, "BTC/USDT", "5m", as_of="2100-01-01", on_duplicates="keep_last")
    assert cs.df["ts"].is_unique and len(cs.df) == 100


# Test 6: unclosed candles are excluded
def test_unclosed_candle_excluded():
    raw = make_ohlc(100)
    last_open = pd.Timestamp(int(raw["timestamp"].iloc[-1]), unit="ms", tz="UTC")
    # "now" is in the middle of the last candle -> it is not closed yet
    cs = build_candles(raw, "BTC/USDT", "5m", as_of=last_open + pd.Timedelta(minutes=2))
    assert cs.df["ts"].iloc[-1] == last_open - pd.Timedelta(minutes=5)
    assert cs.stats["unclosed_dropped"] == 1
    # exactly at close time it IS closed
    cs2 = build_candles(raw, "BTC/USDT", "5m", as_of=last_open + pd.Timedelta(minutes=5))
    assert cs2.df["ts"].iloc[-1] == last_open


def test_closed_flag_column_honoured():
    raw = make_ohlc(10)
    raw["closed_flag"] = [1] * 9 + [0]
    cs = build_candles(raw, "BTC/USDT", "5m", as_of="2100-01-01")
    assert len(cs.df) == 9


def test_invalid_ohlc_rows_dropped():
    raw = make_ohlc(50)
    raw.loc[10, "high"] = raw.loc[10, "low"] * 0.5
    cs = build_candles(raw, "BTC/USDT", "5m", as_of="2100-01-01")
    assert cs.stats["invalid_dropped"] == 1 and len(cs.df) == 49


def test_timeframe_parsing():
    assert tf_to_seconds("5m") == tf_to_seconds("5min") == 300
    assert tf_to_seconds("1H") == 3600 and tf_to_seconds("4h") == 14400
