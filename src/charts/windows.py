"""Rolling window construction: window(T) = candles[T-59 .. T]."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.charts.normalize import METHOD, normalize_window
from src.data.loader import CandleSet, tf_to_seconds
from src.validation.window_validation import validate_window


@dataclass
class Window:
    symbol: str
    timeframe: str
    lookback: int
    end_ts: pd.Timestamp
    raw: pd.DataFrame      # raw OHLC (ts, open, high, low, close), exactly `lookback` rows
    norm: pd.DataFrame     # normalized OHLC, same index
    norm_method: str = METHOD


def valid_end_indices(df: pd.DataFrame, timeframe, lookback: int) -> np.ndarray:
    """Positional indices i such that df[i-lookback+1 .. i] is a gap-free run of candles."""
    ts = df["ts"].dt.as_unit("ns").astype("int64").to_numpy()
    step_ns = tf_to_seconds(timeframe) * 1_000_000_000
    idx = np.arange(lookback - 1, len(df))
    ok = (ts[idx] - ts[idx - (lookback - 1)]) == (lookback - 1) * step_ns
    return idx[ok]


def build_window(cs: CandleSet, end_ts, lookback: int) -> Window:
    """Window ending exactly at `end_ts`. Only rows with ts <= end_ts are ever touched."""
    end_ts = pd.Timestamp(end_ts)
    if end_ts.tzinfo is None:
        end_ts = end_ts.tz_localize("UTC")
    df = cs.df
    pos = df["ts"].searchsorted(end_ts, side="right")  # first index with ts > T
    visible = df.iloc[:pos]                            # future candles dropped here
    if len(visible) == 0 or visible["ts"].iloc[-1] != end_ts:
        raise ValueError(f"No closed candle with timestamp {end_ts}")
    raw = visible.iloc[-lookback:][["ts", "open", "high", "low", "close"]].reset_index(drop=True)
    validate_window(raw, end_ts, cs.timeframe, lookback)
    return Window(cs.symbol, cs.timeframe, lookback, end_ts, raw, normalize_window(raw))


def valid_end_timestamps(cs: CandleSet, lookback: int) -> pd.DatetimeIndex:
    idx = valid_end_indices(cs.df, cs.timeframe, lookback)
    return pd.DatetimeIndex(cs.df["ts"].iloc[idx])


def sample_end_timestamps(cs: CandleSet, lookback: int, count: int, seed=None) -> list[pd.Timestamp]:
    """Pick `count` window-end timestamps. seed=None: evenly spaced across all history
    (deterministic); otherwise a seeded random sample (sorted)."""
    ends = valid_end_timestamps(cs, lookback)
    if len(ends) == 0:
        raise ValueError("No valid windows available")
    count = min(count, len(ends))
    if seed is None:
        picks = np.linspace(0, len(ends) - 1, count).round().astype(int)
    else:
        picks = np.sort(np.random.default_rng(seed).choice(len(ends), count, replace=False))
    return [ends[i] for i in picks]
