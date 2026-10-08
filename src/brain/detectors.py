"""The nine independent setup detectors of the Setup Brain (docs/brain/EXPERIMENT4_PLAN.md).

Each detector is a pure function of ONE 96-candle window (decision candle = the last). S1-S4 and S6-S8 are the
Experiment 3 translations, imported unchanged. S5 and S9 are translated here. A detector returns the list of
(direction, operative level, invalidation rules) that are *present* at the decision candle; the brain fires when the NEXT
completed candle closes beyond a level that was present on the previous candle. Nothing here knows about fills, orders,
targets, stops or outcomes: an invalidation rule is only the definition of when a setup stops being present.

Interpretations (not forced by the frozen AI wording) are listed in INTERPRETATIONS and reported with every result.
"""
from __future__ import annotations

import numpy as np

from src.setups import recognizer as rz
from src.setups.derive_params import EDGE, K, swings

WINDOW = rz.WINDOW
RECENT = rz.RECENT
IDS = ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9")
RZ_KEY = {"S1": "C1", "S2": "C2", "S3": "C3", "S4": "C4", "S6": "C6", "S7": "C7", "S8": "C8"}
NAMES = {"S1": "bullish_breakout_from_right_edge_consolidation", "S2": "bullish_rebound_breakout_after_drop",
         "S3": "bearish_breakdown_from_right_edge_range", "S4": "bearish_continuation_below_broken_support",
         "S5": "bullish_continuation_after_spike_and_pullback", "S6": "bearish_rejection_from_recent_high",
         "S7": "bullish_breakout_from_right_edge_range", "S8": "bearish_breakdown_from_right_edge_support",
         "S9": "tight_range_breakout_both_directions"}
DIRECTIONS = {"S1": "up", "S2": "up", "S3": "down", "S4": "down", "S5": "up", "S6": "down", "S7": "up", "S8": "down", "S9": "both"}
INTERPRETATIONS = {
    "S1-S4,S6-S8": "Numeric translations of docs/setups/RECOGNIZER_PARAMETER_TABLE.md (judgments J-1..J-14); includes J-9 (c_t < c_{t-3} is OUR translation of 'bearish candles push') and J-14 (C6 RET <= 1.0).",
    "S5": "J-15: the breakout level is the latest confirmed swing high before the spike's swing high; 'the spike breaks above it' = a completed close above it at or before the spike high; 'holds above' = no later completed close below it. Other S5 conditions as in the Experiment 3 table; the q33 of DT(spike high) is derived (price-only) by src/brain/derive_s5.py.",
    "S9": "J-16: range = last 24 candles; compact = ZR <= q33(ZR); a prior move exists = UP or DN defined and > q33; direction is decided only at the trigger. 'Repeated tests' and 'waiting near one side' are not coded. The presence condition 'close inside the range' is true by construction (the range includes the decision candle).",
}
NEEDED = rz.NEEDED + ("DT_C5",)


def with_s5_threshold(thr: dict, derived_s5: dict) -> dict:
    """thr from rz.thresholds_from(...) plus the derived q33/q67 of DT_C5."""
    q = derived_s5["quantities"]["DT_C5"]
    return {**thr, "DT_C5": {"lo": q["q33"], "hi": q["q67"]}}


def _geometry(h, l, c):
    n = len(c)
    R = h.max() - l.min()
    ez = slice(n - EDGE, n)
    zh, zl = float(h[ez].max()), float(l[ez].min())
    return n, R, zh, zl


def window_s5(h, l, c, thr) -> list:
    h, l, c = (np.asarray(x, float) for x in (h, l, c))
    n, R, zh, zl = _geometry(h, l, c)
    if n != WINDOW or not R > 0:
        return []
    t = n - 1
    sh, sl = swings(h, l)
    if len(sh) < 2:
        return []
    jH, jB = sh[-1], sh[-2]
    hH, hB = h[jH], h[jB]
    if jH < n - RECENT or not hH > hB:
        return []
    before = [j for j in sl if j < jH]
    if not before or not hH > l[before[-1]]:
        return []
    lB = l[before[-1]]
    up = (hH - lB) / R
    ret = (hH - l[jH:].min()) / (hH - lB)
    zr = (zh - zl) / R
    if not up >= thr["UP"]["hi"]:                                   # E1: sharp upward impulse
        return []
    if not (ret <= thr["RET"]["lo"] or zr <= thr["ZR"]["lo"]):      # E2: shallow pullback or tight consolidation ...
        return []
    if h[jH + 1:].max() > hH:                                       # ... and no high above the spike high since
        return []
    brk = next((k for k in range(jB + 1, jH + 1) if c[k] > hB), None)   # E3: the spike breaks above the previous confirmed swing high
    if brk is None or c[brk + 1:].min() < hB:                       # ... and no later completed close back below it
        return []
    if not (hH - c[t]) / R <= thr["DT_C5"]["lo"]:                   # E4: compressing near the high
        return []
    return [("up", float(hH), [("lt", float(hB))])]


def window_s9(h, l, c, thr) -> list:
    h, l, c = (np.asarray(x, float) for x in (h, l, c))
    n, R, zh, zl = _geometry(h, l, c)
    if n != WINDOW or not R > 0 or not zh > zl:
        return []
    t = n - 1
    if not (zh - zl) / R <= thr["ZR"]["lo"]:
        return []
    sh, sl = swings(h, l)
    prior = False
    if sh:
        jH = sh[-1]
        before = [j for j in sl if j < jH]
        if before and h[jH] > l[before[-1]]:
            prior |= (h[jH] - l[before[-1]]) / R > thr["UP"]["lo"]
    if sl:
        jL = sl[-1]
        before = [j for j in sh if j < jL]
        if before and h[before[-1]] > l[jL]:
            prior |= (h[before[-1]] - l[jL]) / R > thr["DN"]["lo"]
    if not prior or not zl <= c[t] <= zh:
        return []
    return [("up", zh, [("le", zh)]), ("down", zl, [("ge", zl)])]


def evaluate(h, l, c, thr: dict) -> dict:
    """-> {setup_id: [(direction, level, [(op, level), ...]), ...]} for setups PRESENT at the decision candle (last of the arrays)."""
    base = rz.window_state(h, l, c, thr)
    out = {}
    for sid, key in RZ_KEY.items():
        s = base[key]
        if s is not None:
            out[sid] = [(rz.DIRECTION[key], float(s[0]), [(op, float(v)) for op, v in s[1]])]
    s5 = window_s5(h, l, c, thr)
    if s5:
        out["S5"] = s5
    s9 = window_s9(h, l, c, thr)
    if s9:
        out["S9"] = s9
    return out
