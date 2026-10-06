"""Fixed chart scale for discovery.

span = SPAN_QUANTILE-quantile of window ranges, (max high - min low) / close_T * 100, over the
DISCOVERY period only (never the held-out data), rounded up to SPAN_STEP_PCT. Every discovery
chart then has the same vertical span in %. Windows wider than the span would be clipped, so they
are excluded from sampling (documented bias: the most extreme ~1% of windows are not shown).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import config
from src.charts.windows import valid_end_indices


def window_ranges_pct(df: pd.DataFrame, timeframe, lookback: int) -> pd.Series:
    hi = df["high"].rolling(lookback).max()
    lo = df["low"].rolling(lookback).min()
    rng = (hi - lo) / df["close"] * 100.0          # close_T = last close of the window
    idx = valid_end_indices(df, timeframe, lookback)
    return pd.Series(rng.to_numpy()[idx], index=pd.DatetimeIndex(df["ts"].iloc[idx]))


def choose_span(ranges: pd.Series, q=None, step=None) -> float:
    q = config.SPAN_QUANTILE if q is None else q
    step = config.SPAN_STEP_PCT if step is None else step
    return round(math.ceil(float(np.quantile(ranges.to_numpy(), q)) / step) * step, 10)


def eligible_ends(ranges: pd.Series, span: float) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(ranges.index[ranges.to_numpy() <= span])
