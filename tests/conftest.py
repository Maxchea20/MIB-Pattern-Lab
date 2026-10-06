import sqlite3

import numpy as np
import pandas as pd
import pytest

from src.data.loader import build_candles

STEP = 300_000  # 5m in ms
T0 = 1_700_000_000_000 // STEP * STEP


def make_ohlc(n, start_ms=T0, step_ms=STEP, seed=0, base=60_000.0):
    rng = np.random.default_rng(seed)
    close = base * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    open_ = np.concatenate([[base], close[:-1]])
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.0007, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.0007, n)))
    return pd.DataFrame({"timestamp": start_ms + step_ms * np.arange(n),
                         "open": open_, "high": high, "low": low, "close": close})


@pytest.fixture
def raw500():
    return make_ohlc(500)


@pytest.fixture
def cs500(raw500):
    return build_candles(raw500, "BTC/USDT", "5m", "synthetic", as_of="2100-01-01", on_duplicates="error")


@pytest.fixture
def synthetic_db(tmp_path):
    p = tmp_path / "market_Data_Clean.db"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE candles (symbol TEXT, timeframe TEXT, open_time INTEGER, "
                "open REAL, high REAL, low REAL, close REAL, volume REAL)")
    for sym, tf, df in [("BTC/USDT", "5m", make_ohlc(400)),
                        ("BTC/USDT", "1m", make_ohlc(100, step_ms=60_000, seed=2)),
                        ("ETH/USDT", "5m", make_ohlc(100, seed=3, base=3000))]:
        con.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,1.0)",
                        [(sym, tf, int(r.timestamp), r.open, r.high, r.low, r.close) for r in df.itertuples()])
    con.commit(); con.close()
    return p
