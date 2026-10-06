"""Look-ahead-bias safety checks for chart windows. Every window passes through here."""
from __future__ import annotations

import pandas as pd

from src.data.loader import OHLC, invalid_ohlc_mask, tf_to_seconds


class WindowValidationError(AssertionError):
    pass


def validate_window(raw: pd.DataFrame, end_ts, timeframe, lookback: int) -> None:
    """Raise WindowValidationError unless `raw` is exactly `lookback` contiguous,
    ordered, unique, valid candles whose LAST candle is `end_ts` (nothing after it)."""
    end_ts = pd.Timestamp(end_ts)
    step = pd.Timedelta(seconds=tf_to_seconds(timeframe))
    if len(raw) != lookback:
        raise WindowValidationError(f"window has {len(raw)} candles, expected {lookback}")
    ts = raw["ts"]
    if ts.duplicated().any():
        raise WindowValidationError("duplicate timestamps in window")
    if not ts.is_monotonic_increasing:
        raise WindowValidationError("window is not chronologically ordered")
    if ts.iloc[-1] != end_ts:
        raise WindowValidationError(f"last candle {ts.iloc[-1]} != T {end_ts}")
    if (ts > end_ts).any():
        raise WindowValidationError("window contains candles after T (look-ahead)")
    if not (ts.diff().dropna() == step).all():
        raise WindowValidationError("window has gaps / irregular spacing")
    if invalid_ohlc_mask(raw[OHLC]).any():
        raise WindowValidationError("window contains invalid OHLC rows")
