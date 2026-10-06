"""Forward outcomes after a window end T (pre-registration section 4).

This is the ONLY module allowed to read candles after T. The tagging / chart / data code must never import it
(test-enforced). Entry reference = close of T. No TP/SL, no costs, no trading rules, no sign flipping.

For each horizon H (in candles; 1h timeframe => hours) in HORIZONS:
    ret_H = 100 * (close[T+H] / close[T] - 1)
    fh_H  = max(high[T+1 .. T+H])           fl_H = min(low[T+1 .. T+H])        (prices)
    mfe_H = 100 * (fh_H / close[T] - 1)     mae_H = 100 * (fl_H / close[T] - 1)
A window is excluded (and counted by reason) unless the HMAX following candles exist and are gap-free.
Callers pass candles that already stop at the discovery cutoff, so no hold-out candle can be read.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

HORIZONS = (1, 3, 6, 12, 24)


def outcome_columns(horizons=HORIZONS) -> list[str]:
    return [f"{k}_{h}" for h in horizons for k in ("ret", "mfe", "mae", "fh", "fl")]


def forward_outcomes(df: pd.DataFrame, end_ts, step_seconds: int, horizons=HORIZONS):
    """df: candles with columns ts, high, low, close (sorted, unique). end_ts: iterable of window ends T.
    Returns (DataFrame of valid windows, {reason: count})."""
    ts = df["ts"].dt.as_unit("ns").astype("int64").to_numpy()
    close, high, low = (df[c].to_numpy(float) for c in ("close", "high", "low"))
    step = int(step_seconds) * 1_000_000_000
    hmax = max(horizons)
    rows, excluded = [], {"end_candle_missing": 0, "insufficient_forward_candles": 0, "gap_in_forward_path": 0}
    for t in end_ts:
        t_ns = pd.Timestamp(t).as_unit("ns").value
        pos = int(np.searchsorted(ts, t_ns))
        if pos >= len(ts) or ts[pos] != t_ns:
            excluded["end_candle_missing"] += 1
            continue
        if pos + hmax >= len(ts):
            excluded["insufficient_forward_candles"] += 1       # data (or the discovery period) ends first
            continue
        if ts[pos + hmax] - ts[pos] != hmax * step:               # unique + increasing => contiguous iff equal
            excluded["gap_in_forward_path"] += 1
            continue
        c0 = close[pos]
        row = {"end_ts": pd.Timestamp(t).isoformat(), "entry_close": c0}
        for h in horizons:
            fh = float(high[pos + 1: pos + h + 1].max())
            fl = float(low[pos + 1: pos + h + 1].min())
            row[f"ret_{h}"] = 100.0 * (close[pos + h] / c0 - 1.0)
            row[f"fh_{h}"], row[f"fl_{h}"] = fh, fl
            row[f"mfe_{h}"] = 100.0 * (fh / c0 - 1.0)
            row[f"mae_{h}"] = 100.0 * (fl / c0 - 1.0)
        rows.append(row)
    return pd.DataFrame(rows), excluded
