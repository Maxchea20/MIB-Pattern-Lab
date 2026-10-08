"""Detector set v2 = the v1 set with ONLY S1 replaced by src/brain/s1_v2.py. S2-S9 are the v1 functions called unchanged."""
from __future__ import annotations

from src.brain import detectors as det
from src.brain import s1_v2

IDS = det.IDS
NAMES = det.NAMES
WINDOW = det.WINDOW
INTERPRETATIONS = {**det.INTERPRETATIONS,
                   "S1v2": "J-17 literal OR (ZR <= q33 or RET <= q33); J-18 resistance = the pause's own high (since the leg's swing high, at most 24 candles), DT <= its own derived q33; "
                           "J-19 net up-leg UPnet = (swing high - lowest low before it)/R > its own derived q33. Approved as translation corrections, not optimization."}


def with_s1v2_thresholds(thr: dict, derived: dict) -> dict:
    q = derived["quantities"]
    return {**thr, "UPnet": {"lo": q["UPnet"]["q33"], "hi": q["UPnet"]["q67"]}, "DT_S1v2": {"lo": q["DT_S1v2"]["q33"], "hi": q["DT_S1v2"]["q67"]}}


def evaluate(h, l, c, thr: dict) -> dict:
    out = det.evaluate(h, l, c, thr)
    out.pop("S1", None)
    s1 = s1_v2.window_s1_v2(h, l, c, thr)
    if s1:
        out["S1"] = s1
    return out
