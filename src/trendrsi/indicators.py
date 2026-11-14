"""Causal indicators and multi-timeframe alignment. A value at candle i uses candles <= i only; a higher-timeframe value is used at a 15m candle
only once that higher-timeframe candle has CLOSED (close time <= the 15m candle's close time)."""
from __future__ import annotations

import numpy as np

from src.trendrsi import params as P

NAN = float("nan")


def rsi_wilder(c, n: int = P.RSI_LEN) -> np.ndarray:
    c = np.asarray(c, float)
    out = np.full(len(c), NAN)
    if len(c) <= n:
        return out
    d = np.diff(c)
    up, dn = np.clip(d, 0, None), np.clip(-d, 0, None)
    au, ad = up[:n].mean(), dn[:n].mean()
    out[n] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    for i in range(n, len(d)):
        au, ad = (au * (n - 1) + up[i]) / n, (ad * (n - 1) + dn[i]) / n
        out[i + 1] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    return out


def ema(c, span: int) -> np.ndarray:
    c = np.asarray(c, float)
    a = 2.0 / (span + 1)
    out = np.empty(len(c))
    if not len(c):
        return out
    out[0] = c[0]
    for i in range(1, len(c)):
        out[i] = a * c[i] + (1 - a) * out[i - 1]
    return out


def swings(h, l, k: int = P.SWING_K):
    """Boolean arrays: swing high / low AT candle j (needs k candles on both sides). The swing is KNOWN only at candle j + k."""
    h, l = np.asarray(h, float), np.asarray(l, float)
    n = len(h)
    sh, sl = np.zeros(n, bool), np.zeros(n, bool)
    for j in range(k, n - k):
        if h[j] >= h[j - k:j].max() and h[j] > h[j + 1:j + 1 + k].max():
            sh[j] = True
        if l[j] <= l[j - k:j].min() and l[j] < l[j + 1:j + 1 + k].min():
            sl[j] = True
    return sh, sl


def htf_bias(ts15_close, d4, d1):
    """d4 / d1: dicts with open_ms, close, ema, slope arrays and the candle length in ms. -> (bear, bull) boolean arrays per 15m candle."""
    def at(d):
        close_ms = d["open_ms"] + d["step_ms"]
        k = np.searchsorted(close_ms, ts15_close, side="right") - 1          # latest higher-timeframe candle already closed
        return k
    k4, k1 = at(d4), at(d1)
    ok = (k4 >= 0) & (k1 >= 0)
    k4c, k1c = np.where(k4 < 0, 0, k4), np.where(k1 < 0, 0, k1)
    bear = ok & (d4["close"][k4c] < d4["ema"][k4c]) & (d4["slope"][k4c] < 0) & (d1["close"][k1c] < d1["ema"][k1c]) & (d1["slope"][k1c] < 0)
    bull = ok & (d4["close"][k4c] > d4["ema"][k4c]) & (d4["slope"][k4c] > 0) & (d1["close"][k1c] > d1["ema"][k1c]) & (d1["slope"][k1c] > 0)
    return bear, bull


def htf_pack(open_ms, close, span: int, slope_bars: int, step_ms: int) -> dict:
    e = ema(close, span)
    s = np.full(len(e), NAN)
    s[slope_bars:] = e[slope_bars:] - e[:-slope_bars]
    return {"open_ms": np.asarray(open_ms, np.int64), "close": np.asarray(close, float), "ema": e, "slope": s, "step_ms": step_ms}
