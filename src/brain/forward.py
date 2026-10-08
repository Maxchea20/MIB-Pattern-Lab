"""Descriptive observation of what the market did AFTER each FIRE. These are statistics of the historical price series measured from the
ANALYTICAL REFERENCE PRICE (the open of the candle after the trigger candle). They are not fills, not trades and not results of any order.
Nothing here places, assumes or simulates an entry, stop, target or exit. Where the intrabar order of two events is unknowable from
15m candles the field says so instead of guessing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.brain import detectors as det
from src.brain.brain import STEP_NS, iso

HORIZONS = (1, 3, 6, 12, 24)
MAX_FWD = 24


def trailing_vol(c: np.ndarray, win: int = 96) -> np.ndarray:
    """Std of close-to-close log returns over the `win` candles ending at each candle (NaN until available). Causal."""
    r = np.diff(np.log(c), prepend=np.nan)
    s = pd.Series(r).rolling(win - 1, min_periods=win - 1).std(ddof=0)
    out = s.to_numpy().copy()
    out[: win - 1] = np.nan
    return out


def vol_cuts(c: np.ndarray, ts: np.ndarray, cutoff_ns: int) -> tuple[float, float]:
    v = trailing_vol(c)
    v = v[(ts < cutoff_ns) & np.isfinite(v)]
    if not len(v):
        return float("nan"), float("nan")
    lo, hi = np.quantile(v, [1 / 3, 2 / 3])
    return float(lo), float(hi)


def observe(fires: list[dict], invalidations: list[dict], ts, o, h, l, c, cutoff_ns: int, step_ns: int = STEP_NS) -> list[dict]:
    ts = np.asarray(ts, np.int64)
    o, h, l, c = (np.asarray(x, float) for x in (o, h, l, c))
    n = len(c)
    inv = {e["fire_id"]: e for e in invalidations}
    vol = trailing_vol(c)
    lo, hi = vol_cuts(c, ts, cutoff_ns)
    out = []
    for f in fires:
        t = f["trigger_idx"]
        s = 1.0 if f["direction"] == "up" else -1.0
        row = {k: v for k, v in f.items() if k not in ("event",)}
        in_sample = int(ts[t]) < cutoff_ns
        row["period"] = "IN_SAMPLE" if in_sample else "UNSEEN"
        row["month"] = iso(int(ts[t]))[:7]
        v = vol[t]
        row["vol_tercile"] = None if not np.isfinite(v) else ("low" if v <= lo else ("high" if v > hi else "mid"))
        # contiguous forward candles after the trigger candle
        k_av = 0
        while k_av < MAX_FWD and t + k_av + 1 < n and ts[t + k_av + 1] - ts[t + k_av] == step_ns:
            k_av += 1
        row["n_forward_available"] = k_av
        row["forward_crosses_boundary"] = bool(in_sample and k_av > 0 and int(ts[t + k_av]) >= cutoff_ns)   # forward window reaches the unseen period
        e = inv.get(f["fire_id"])
        row["invalidation_ts"] = e["invalidation_ts"] if e else None
        row["candles_to_invalidation"] = e["candles_after_trigger"] if e else None
        row["invalidated_within_24"] = bool(e and e["candles_after_trigger"] <= MAX_FWD)
        if k_av == 0:
            row.update({"analytical_reference_price": None})
            out.append(row)
            continue
        ref = float(o[t + 1])
        row["analytical_reference_price"] = ref
        for H in HORIZONS:
            row[f"fwd_return_pct_h{H}"] = float(s * (c[t + H] / ref - 1) * 100) if H <= k_av else None
        sl = slice(t + 1, t + 1 + k_av)
        hi_f, lo_f, cl_f = h[sl], l[sl], c[sl]
        row["future_high_pct"] = float((hi_f.max() / ref - 1) * 100)
        row["future_low_pct"] = float((lo_f.min() / ref - 1) * 100)
        fav = (hi_f / ref - 1) * 100 if s > 0 else (1 - lo_f / ref) * 100          # favorable excursion per candle (% of reference)
        adv = (1 - lo_f / ref) * 100 if s > 0 else (hi_f / ref - 1) * 100
        row["mfe_pct"], row["mae_pct"] = float(fav.max()), float(adv.max())
        row["candle_of_mfe"], row["candle_of_mae"] = int(fav.argmax()) + 1, int(adv.argmax()) + 1
        # both extremes on one candle: their order inside the candle is unknown, never guessed
        row["mfe_mae_same_candle_order_unknown"] = bool(row["candle_of_mfe"] == row["candle_of_mae"])
        sc = s * (cl_f / ref - 1)
        pos, neg = np.flatnonzero(sc > 0), np.flatnonzero(sc < 0)
        row["first_favorable_close_candle"] = int(pos[0]) + 1 if len(pos) else None
        row["first_adverse_close_candle"] = int(neg[0]) + 1 if len(neg) else None
        out.append(row)
    return out


def _stat(x: list[float]) -> dict:
    a = np.array([v for v in x if v is not None], float)
    if not len(a):
        return {"n": 0}
    return {"n": int(len(a)), "mean": float(a.mean()), "median": float(np.median(a)), "p25": float(np.quantile(a, .25)),
            "p75": float(np.quantile(a, .75)), "share_positive": float((a > 0).mean())}


def summarize(rows: list[dict]) -> dict:
    """Per setup and period: counts and descriptive distributions. No test, no gate, no pass/fail."""
    out: dict = {}
    for sid in det.IDS:
        for period in ("IN_SAMPLE", "UNSEEN", "ALL"):
            r = [x for x in rows if x["setup_id"] == sid and (period == "ALL" or x["period"] == period)]
            usable = [x for x in r if not (x["period"] == "IN_SAMPLE" and x["forward_crosses_boundary"])] if period != "ALL" else r
            runs = [x for x in r if x["streak_position"] == 0]
            out.setdefault(sid, {})[period] = {
                "fires": len(r), "long": sum(x["direction"] == "up" for x in r), "short": sum(x["direction"] == "down" for x in r),
                "first_in_streak": len(runs), "max_streak_position": max([x["streak_position"] for x in r], default=None),
                "forward_rows_used": len(usable),
                "forward_return_pct": {f"h{H}": _stat([x.get(f"fwd_return_pct_h{H}") for x in usable]) for H in HORIZONS},
                "mfe_pct": _stat([x.get("mfe_pct") for x in usable]), "mae_pct": _stat([x.get("mae_pct") for x in usable]),
                "candles_to_first_favorable_close": _stat([x.get("first_favorable_close_candle") for x in usable]),
                "candles_to_first_adverse_close": _stat([x.get("first_adverse_close_candle") for x in usable]),
                "candles_to_invalidation": _stat([x.get("candles_to_invalidation") for x in r]),
                "invalidated_within_24": sum(1 for x in r if x["invalidated_within_24"]),
                "never_invalidated_by_end_of_data": sum(1 for x in r if x["invalidation_ts"] is None),
                "mfe_mae_same_candle_order_unknown": sum(1 for x in usable if x.get("mfe_mae_same_candle_order_unknown")),
                "by_month": pd.Series([x["month"] for x in r]).value_counts().sort_index().to_dict() if r else {},
                "by_vol_tercile": pd.Series([x["vol_tercile"] for x in r if x["vol_tercile"]]).value_counts().to_dict() if r else {},
            }
    return out


def overlap(rows: list[dict], presence_pairs: dict, presence_candles: dict) -> dict:
    """Same-candle fire overlap and presence overlap for every pair of setups; nothing is merged or removed."""
    by = {sid: {x["trigger_idx"] for x in rows if x["setup_id"] == sid} for sid in det.IDS}
    m: dict = {}
    for i, a in enumerate(det.IDS):
        for b in det.IDS[i + 1:]:
            u = len(by[a] | by[b])
            p = presence_pairs.get((a, b), 0)
            pu = presence_candles[a] + presence_candles[b] - p
            m[f"{a}/{b}"] = {"same_candle_fires": len(by[a] & by[b]), "fire_jaccard": (len(by[a] & by[b]) / u) if u else 0.0,
                             "presence_both": p, "presence_jaccard": (p / pu) if pu else 0.0}
    return m
