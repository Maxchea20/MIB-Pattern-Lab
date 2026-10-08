"""S1 v2 - `bullish_breakout_from_right_edge_consolidation`, translated again (docs/brain/S1_REVIEW_AND_PROPOSAL.md, approved as translation
corrections, not performance optimization). v1 (src/brain/detectors.py + src/setups/recognizer.py C1) stays frozen and untouched.

Three corrections to how the frozen English is turned into numbers:
  1. 'small consolidation, pause, OR pullback': the literal OR  ZR <= q33(ZR)  or  RET <= q33(RET)  (no new threshold).
  2. 'top of that local range / prior swing high': the resistance is the PAUSE'S OWN HIGH - the highest high from the candle after the leg's swing
     high (at most the last 24 candles) to the decision candle - not a fixed 24-candle zone that a spike or the leg's top can contaminate.
  3. 'a prior upward leg or rebound is in place': UPnet = (swing high - lowest low before it in the window) / R, not only the last zig.
Everything else is as in v1 (96-candle window, confirmed swings K = 3, recent = last 48, q33 for 'small/near', trigger = a close beyond the level that
was present on the previous candle, invalidation as information, no lockout). Pure price code; no outcome, no order, no fill.
"""
from __future__ import annotations

import numpy as np

from src.setups.derive_params import EDGE, swings

WINDOW = 96
RECENT = 48
KEYS = ("UPnet", "DT_S1v2")
NAN = float("nan")


def _prep(h, l, c):
    h, l, c = (np.asarray(x, float) for x in (h, l, c))
    n = len(c)
    R = float(h.max() - l.min())
    sh, sl = swings(h, l)
    return h, l, c, n, R, sh, sl


def pause_high(h, jH: int, n: int) -> float:
    """Highest high over the pause: the candles after the leg's swing high, but never more than the last 24 candles."""
    return float(h[max(jH + 1, n - EDGE):].max())


def quantities(h, l, c) -> dict:
    """The two quantities that are new in v2, for the price-only derivation. NaN when undefined."""
    h, l, c, n, R, sh, sl = _prep(h, l, c)
    out = {k: NAN for k in KEYS}
    if not R > 0 or not sh:
        return out
    jH = sh[-1]
    hH = float(h[jH])
    if jH >= 1 and hH > l[:jH].min():
        out["UPnet"] = float((hH - l[:jH].min()) / R)
    out["DT_S1v2"] = float((pause_high(h, jH, n) - c[-1]) / R)
    return out


def window_s1_v2(h, l, c, thr: dict) -> list:
    """-> [("up", level, [(op, value), ...])] when S1 v2 is PRESENT at the decision candle (last of the arrays), else []."""
    h, l, c, n, R, sh, sl = _prep(h, l, c)
    if n != WINDOW or not R > 0 or not sh:
        return []
    t = n - 1
    jH = sh[-1]
    hH = float(h[jH])
    q = quantities(h, l, c)
    if not (jH >= n - RECENT and q["UPnet"] == q["UPnet"] and q["UPnet"] > thr["UPnet"]["lo"]):          # A1
        return []
    zr = (h[n - EDGE:].max() - l[n - EDGE:].min()) / R
    pbl = float(l[jH:].min())
    bef = [j for j in sl if j < jH]
    ret = (hH - pbl) / (hH - l[bef[-1]]) if bef and hH > l[bef[-1]] else None
    if not (zr <= thr["ZR"]["lo"] or (ret is not None and ret <= thr["RET"]["lo"])):                       # A2 (literal OR)
        return []
    if not q["DT_S1v2"] <= thr["DT_S1v2"]["lo"]:                                                           # A3
        return []
    L = pause_high(h, jH, n)
    return [("up", L, [("lt", pbl), ("le", L)])]


def explain_s1_v2(h, l, c, thr: dict) -> dict:
    """Verbose condition reading written separately from window_s1_v2 (the tests require them to agree)."""
    h, l, c, n, R, sh, sl = _prep(h, l, c)
    if n != WINDOW or not R > 0:
        return {"present": False, "conditions": [{"condition": "window", "ok": False, "detail": "needs 96 candles and a positive range"}], "level": None}
    if not sh:
        return {"present": False, "conditions": [{"condition": "A1 swing high", "ok": False, "detail": "no confirmed swing high"}], "level": None}
    t = n - 1
    jH = sh[-1]
    hH = float(h[jH])
    low_before = float(l[:jH].min()) if jH >= 1 else None
    upnet = (hH - low_before) / R if low_before is not None and hH > low_before else None
    zr = (h[n - EDGE:].max() - l[n - EDGE:].min()) / R
    pbl = float(l[jH:].min())
    bef = [j for j in sl if j < jH]
    ret = (hH - pbl) / (hH - l[bef[-1]]) if bef and hH > l[bef[-1]] else None
    L = pause_high(h, jH, n)
    dt = (L - c[t]) / R
    f = lambda v: "undefined" if v is None else f"{v:.4f}"                    # noqa: E731
    C = [
        {"condition": "A1 recent swing high and net up-leg > q33(UPnet)", "ok": jH >= n - RECENT and upnet is not None and upnet > thr["UPnet"]["lo"],
         "detail": f"swing high idx {jH} (recent from {n - RECENT}), UPnet {f(upnet)} vs q33 {thr['UPnet']['lo']:.4f}"},
        {"condition": "A2 compact edge ZR <= q33 OR shallow pullback RET <= q33", "ok": bool(zr <= thr["ZR"]["lo"] or (ret is not None and ret <= thr["RET"]["lo"])),
         "detail": f"ZR {zr:.4f} vs q33 {thr['ZR']['lo']:.4f}; RET {f(ret)} vs q33 {thr['RET']['lo']:.4f}"},
        {"condition": "A3 close near the pause high DT <= q33", "ok": bool(dt <= thr["DT_S1v2"]["lo"]),
         "detail": f"DT {dt:.4f} vs q33 {thr['DT_S1v2']['lo']:.4f} (pause high {L:.2f}, close {c[t]:.2f})"},
    ]
    C[0]["ok"] = bool(C[0]["ok"])
    return {"present": all(k["ok"] for k in C), "conditions": C, "level": L}
