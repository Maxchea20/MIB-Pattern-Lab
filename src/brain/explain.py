"""Condition-by-condition explanation of every detector at one 96-candle window. READ-ONLY DIAGNOSTIC: it changes no detector, no threshold
and no scan result. It is written separately from src/brain/detectors.py (verbose, from the parameter table), and the tests require that
'all conditions pass' is equivalent to the detector reporting PRESENT, so it also serves as an independent re-implementation check."""
from __future__ import annotations

import numpy as np

from src.brain import detectors as det
from src.setups.derive_params import EDGE, swings

OKTXT = {True: "ok", False: "NO"}


def _c(label, ok, text):
    return {"condition": label, "ok": bool(ok), "detail": text}


def context(h, l, c) -> dict:
    h, l, c = (np.asarray(x, float) for x in (h, l, c))
    n = len(c)
    t = n - 1
    R = float(h.max() - l.min())
    zh, zl = float(h[n - EDGE:].max()), float(l[n - EDGE:].min())
    sh, sl = swings(h, l)
    d = {"n": n, "t": t, "R": R, "zh": zh, "zl": zl, "sh": sh, "sl": sl, "c": float(c[t]), "recent_from": n - det.RECENT}
    if R > 0:
        st = np.abs(np.diff(c[n - EDGE:]))
        d["ZR"] = (zh - zl) / R
        d["EFF"] = abs(c[t] - c[t - (EDGE - 1)]) / st.sum() if st.sum() > 0 else 0.0
    d.update(jH=None, hH=None, lB=None, UP=None, RET=None, pbl=None, jL=None, lL=None, hB=None, DN=None, REB=None, rh=None, jB=None, hPrev=None)
    if sh:
        d["jH"], d["hH"] = sh[-1], float(h[sh[-1]])
        d["pbl"] = float(l[sh[-1]:].min())
        bef = [j for j in sl if j < sh[-1]]
        if bef and d["hH"] > l[bef[-1]] and R > 0:
            d["lB"] = float(l[bef[-1]])
            d["UP"] = (d["hH"] - d["lB"]) / R
            d["RET"] = (d["hH"] - d["pbl"]) / (d["hH"] - d["lB"])
        if len(sh) > 1:
            d["jB"], d["hPrev"] = sh[-2], float(h[sh[-2]])
    if sl:
        d["jL"], d["lL"] = sl[-1], float(l[sl[-1]])
        d["rh"] = float(h[sl[-1]:].max())
        d["REB"] = (d["rh"] - d["lL"]) / R if R > 0 else None
        bef = [j for j in sh if j < sl[-1]]
        if bef and h[bef[-1]] > d["lL"] and R > 0:
            d["hB"] = float(h[bef[-1]])
            d["DN"] = (d["hB"] - d["lL"]) / R
    return d


def explain(sid: str, h, l, c, thr: dict) -> dict:
    """-> {'present': bool, 'conditions': [{'condition','ok','detail'}], 'level': ...}"""
    h, l, c = (np.asarray(x, float) for x in (h, l, c))
    x = context(h, l, c)
    n, t, R = x["n"], x["t"], x["R"]
    if n != det.WINDOW or not R > 0:
        return {"present": False, "conditions": [_c("window", False, f"needs 96 candles and a positive range (n={n}, R={R})")]}
    T = thr
    ct = x["c"]
    q = lambda k, w: T[k][w]                                            # noqa: E731
    recent = lambda j: j is not None and j >= x["recent_from"]          # noqa: E731
    num = lambda v: "undefined" if v is None else f"{v:.4f}"            # noqa: E731
    C: list = []
    level = None
    if sid == "S1":
        C.append(_c("A1 recent swing high and up-leg > q33", recent(x["jH"]) and x["UP"] is not None and x["UP"] > q("UP", "lo"),
                    f"swing high idx {x['jH']} (recent from {x['recent_from']}), UP {num(x['UP'])} vs q33 {q('UP', 'lo'):.4f}"))
        C.append(_c("A2 compact right edge ZR <= q33", x["ZR"] <= q("ZR", "lo"), f"ZR {x['ZR']:.4f} vs q33 {q('ZR', 'lo'):.4f}"))
        if x["jH"] is not None:
            res1 = x["zh"] if (x["jH"] < n - EDGE or x["hH"] < ct) else min(x["zh"], x["hH"])
            level = res1
            C.append(_c("A3 close near the top DT <= q33", (res1 - ct) / R <= q("DT_C1", "lo"), f"DT {(res1 - ct) / R:.4f} vs q33 {q('DT_C1', 'lo'):.4f} (level {res1:.2f})"))
        else:
            C.append(_c("A3 close near the top", False, "no confirmed swing high"))
    elif sid == "S2":
        level = x["rh"]
        C.append(_c("B1 recent swing low and decline >= q67", recent(x["jL"]) and x["DN"] is not None and x["DN"] >= q("DN", "hi"),
                    f"swing low idx {x['jL']}, DN {num(x['DN'])} vs q67 {q('DN', 'hi'):.4f}"))
        C.append(_c("B2 close above the low and rebound > q33", x["lL"] is not None and ct > x["lL"] and x["REB"] is not None and x["REB"] > q("REB", "lo"),
                    f"close {ct:.2f} vs low {x['lL']}, REB {num(x['REB'])} vs q33 {q('REB', 'lo'):.4f}"))
        C.append(_c("B3 pressing into the rebound high DT <= q33", x["rh"] is not None and (x["rh"] - ct) / R <= q("DT_C2", "lo"),
                    f"DT {num(None if x['rh'] is None else (x['rh'] - ct) / R)} vs q33 {q('DT_C2', 'lo'):.4f}"))
    elif sid == "S3":
        level = x["zl"]
        pos = lambda v: (v - x["zl"]) / (x["zh"] - x["zl"]) if x["zh"] > x["zl"] else None      # noqa: E731
        C.append(_c("C3a sideways/choppy EFF <= q33", x["EFF"] <= q("EFF", "lo"), f"EFF {x['EFF']:.4f} vs q33 {q('EFF', 'lo'):.4f}"))
        okb = x["jH"] is not None and x["jH"] >= n - EDGE and pos(x["hH"]) is not None and pos(x["hH"]) >= 2 / 3
        C.append(_c("C3b roll-over high in the upper third of the right edge", okb, f"swing high idx {x['jH']} (edge from {n - EDGE}), position {num(None if x['hH'] is None else pos(x['hH']))}"))
        okc = pos(ct) is not None and pos(ct) <= 1 / 3 and ct < c[t - 3]
        C.append(_c("C3c close in the lower third and below 3 candles ago", okc, f"position {num(pos(ct))}, close {ct:.2f} vs {c[t - 3]:.2f}"))
        C.append(_c("C3d near the floor DF <= q33", (ct - x["zl"]) / R <= q("DF_C3", "lo"), f"DF {(ct - x['zl']) / R:.4f} vs q33 {q('DF_C3', 'lo'):.4f}"))
    elif sid == "S4":
        best = None
        for jS in x["sl"]:
            b = next((k for k in range(jS + 1, n) if c[k] < l[jS]), None)
            if b is not None and (best is None or (b, l[jS]) > best):
                best = (b, float(l[jS]))
        C.append(_c("D1 a swing low was broken by a close", best is not None, f"break idx/level {best}"))
        if best is not None:
            b, lS = best
            shs, sls = [j for j in x["sh"] if j > b], [j for j in x["sl"] if j > b]
            C.append(_c("D2 close still below the broken level", ct < lS, f"close {ct:.2f} vs broken level {lS:.2f}"))
            lh = len(shs) >= 2 and h[shs[-1]] < h[shs[-2]]
            ll = len(sls) >= 2 and l[sls[-1]] < l[sls[-2]]
            C.append(_c("D3 lower high or lower low after the break", lh or ll, f"swing highs after break {len(shs)}, lows {len(sls)}; lower_high={lh} lower_low={ll}"))
            if sls:
                llv = float(l[sls[-1]])
                level = llv
                C.append(_c("D4 above the latest minor low and near it DF <= q33", ct >= llv and (ct - llv) / R <= q("DF_C4", "lo"),
                            f"minor low {llv:.2f}, DF {(ct - llv) / R:.4f} vs q33 {q('DF_C4', 'lo'):.4f}"))
            else:
                C.append(_c("D4 a minor low after the break exists", False, "none"))
    elif sid == "S5":
        sh, sl = x["sh"], x["sl"]
        level = x["hH"]
        C.append(_c("E0 two confirmed swing highs", len(sh) >= 2, f"{len(sh)} confirmed swing highs"))
        if len(sh) >= 2:
            jH, jB, hH, hB = x["jH"], x["jB"], x["hH"], x["hPrev"]
            C.append(_c("E1 recent spike high above the previous swing high, up-leg >= q67", recent(jH) and hH > hB and x["UP"] is not None and x["UP"] >= q("UP", "hi"),
                        f"spike idx {jH}, spike high {hH:.2f}, previous swing high {hB:.2f}, UP {num(x['UP'])} vs q67 {q('UP', 'hi'):.4f}"))
            C.append(_c("E2 shallow pullback or tight range, no higher high since", x["RET"] is not None and (x["RET"] <= q("RET", "lo") or x["ZR"] <= q("ZR", "lo")) and not h[jH + 1:].max() > hH,
                        f"RET {num(x['RET'])} vs q33 {q('RET', 'lo'):.4f}; ZR {x['ZR']:.4f} vs q33 {q('ZR', 'lo'):.4f}; max high since {h[jH + 1:].max():.2f}"))
            brk = next((k for k in range(jB + 1, jH + 1) if c[k] > hB), None)
            held = brk is not None and not c[brk + 1:].min() < hB
            C.append(_c("E3 broke above the previous swing high (a close) and held above it", held,
                        f"first close above {hB:.2f}: idx {brk}; lowest close since: {None if brk is None else round(float(c[brk + 1:].min()), 2)}"))
            C.append(_c("E4 near the spike high DT <= q33", (hH - ct) / R <= q("DT_C5", "lo"), f"DT {(hH - ct) / R:.4f} vs q33 {q('DT_C5', 'lo'):.4f}"))
    elif sid == "S6":
        level = x["pbl"]
        up_ok = x["UP"] is not None
        C.append(_c("F1 recent swing high in the top third of the window", up_ok and recent(x["jH"]) and (x["hH"] - l.min()) / R >= 2 / 3,
                    f"swing high idx {x['jH']}, height {num(None if x['hH'] is None else (x['hH'] - l.min()) / R)}"))
        C.append(_c("F2 no close above the high since, close below it", x["jH"] is not None and ct < x["hH"] and not c[x["jH"] + 1:].max() > x["hH"],
                    f"close {ct:.2f} vs high {x['hH']}"))
        C.append(_c("F3 up-leg > q33 and retracement in (q33, 1.0]", up_ok and x["UP"] > q("UP", "lo") and q("RET", "lo") < x["RET"] <= 1.0,
                    f"UP {num(x['UP'])} vs q33 {q('UP', 'lo'):.4f}; RET {num(x['RET'])} vs q33 {q('RET', 'lo'):.4f}"))
        C.append(_c("F4 near the pullback low DF <= q33", x["pbl"] is not None and (ct - x["pbl"]) / R <= q("DF_C6", "lo"),
                    f"DF {num(None if x['pbl'] is None else (ct - x['pbl']) / R)} vs q33 {q('DF_C6', 'lo'):.4f}"))
    elif sid == "S7":
        level = x["zh"]
        C.append(_c("H1 a decline preceded: DN > q33", x["DN"] is not None and x["DN"] > q("DN", "lo"), f"DN {num(x['DN'])} vs q33 {q('DN', 'lo'):.4f}"))
        C.append(_c("H2 rebound > q33 or compact edge", x["REB"] is not None and (x["REB"] > q("REB", "lo") or x["ZR"] <= q("ZR", "lo")),
                    f"REB {num(x['REB'])} vs q33 {q('REB', 'lo'):.4f}; ZR {x['ZR']:.4f} vs q33 {q('ZR', 'lo'):.4f}"))
        C.append(_c("H3 near the local high DT <= q33", (x["zh"] - ct) / R <= q("DT_C7", "lo"), f"DT {(x['zh'] - ct) / R:.4f} vs q33 {q('DT_C7', 'lo'):.4f}"))
    elif sid == "S8":
        level = x["lL"]
        i1 = (x["UP"] is not None and x["UP"] > q("UP", "lo")) or (x["REB"] is not None and x["REB"] > q("REB", "lo"))
        C.append(_c("I1 prior rise or bounce", i1, f"UP {num(x['UP'])}, REB {num(x['REB'])} vs q33 {q('UP', 'lo'):.4f}/{q('REB', 'lo'):.4f}"))
        lh = len(x["sh"]) >= 2 and h[x["sh"][-1]] < h[x["sh"][-2]]
        C.append(_c("I2 lower-high sequence, choppy edge or rebound", lh or x["EFF"] <= q("EFF", "lo") or (x["REB"] is not None and x["REB"] > q("REB", "lo")),
                    f"lower_high={lh}, EFF {x['EFF']:.4f} vs q33 {q('EFF', 'lo'):.4f}, REB {num(x['REB'])}"))
        C.append(_c("I3 recent swing low, above it, near it, pressing lower", recent(x["jL"]) and ct >= x["lL"] and (ct - x["lL"]) / R <= q("DF_C8", "lo") and ct < c[t - 3],
                    f"swing low idx {x['jL']}, DF {num(None if x['lL'] is None else (ct - x['lL']) / R)} vs q33 {q('DF_C8', 'lo'):.4f}, close {ct:.2f} vs 3 ago {c[t - 3]:.2f}"))
        C.append(_c("I4 rolling over from a recent high", recent(x["jH"]) and ct < x["hH"], f"swing high idx {x['jH']}, high {x['hH']}"))
    elif sid == "S9":
        level = {"up": x["zh"], "down": x["zl"]}
        prior = (x["UP"] is not None and x["UP"] > q("UP", "lo")) or (x["DN"] is not None and x["DN"] > q("DN", "lo"))
        C.append(_c("compact range ZR <= q33", x["zh"] > x["zl"] and x["ZR"] <= q("ZR", "lo"), f"ZR {x['ZR']:.4f} vs q33 {q('ZR', 'lo'):.4f}"))
        C.append(_c("a prior move exists", prior, f"UP {num(x['UP'])}, DN {num(x['DN'])}"))
        C.append(_c("close inside the range", x["zl"] <= ct <= x["zh"], f"close {ct:.2f} in [{x['zl']:.2f}, {x['zh']:.2f}]"))
    return {"present": bool(C) and all(k["ok"] for k in C), "conditions": C, "level": level}


def first_failure(e: dict) -> str | None:
    return next((k["condition"] for k in e["conditions"] if not k["ok"]), None)
