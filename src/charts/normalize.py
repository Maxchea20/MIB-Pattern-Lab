"""Window normalization.

Method ``last_close_pct`` (default):

    norm = (price / close_T - 1) * 100        for open, high, low, close

where ``close_T`` is the close of the LAST candle in the window (the candle at T,
already closed at T). Every normalized value is therefore the percentage distance
from the most recent known close. BTC at $60,000 and at $100,000 with the same
relative movement give identical normalized windows.

Look-ahead safety: the function receives ONLY the window (candles <= T) and uses
only values inside it. It never sees, and cannot depend on, any later candle.
Raw OHLC values are returned untouched alongside the normalized ones.
"""
from __future__ import annotations

import pandas as pd

from src.data.loader import OHLC

METHOD = "last_close_pct"


def normalize_window(raw: pd.DataFrame, method: str = METHOD) -> pd.DataFrame:
    if method != METHOD:
        raise ValueError(f"Unknown normalization method: {method!r}")
    ref = float(raw["close"].iloc[-1])
    out = raw[["ts"]].copy()
    for k in OHLC:
        out[k] = (raw[k].astype(float) / ref - 1.0) * 100.0
    return out
