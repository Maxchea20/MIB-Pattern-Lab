"""Deterministic recognizer for the seven CODEABLE setups (docs/setups/RECOGNIZER_PARAMETER_TABLE.md).

Pure price code. No outcome, forward-return or evaluation code, no data loading, no thresholds of its own: the numeric
thresholds are passed in (derived once by src.setups.derive_params and frozen at F2). C5 is NOT CODEABLE and absent.

Causality: `window_state` receives ONE 96-candle window (decision candle = last) and nothing else. `recognize` walks a
series candle by candle; a trigger at candle t' uses presence/level computed at t'-1 and the close of t'. Invalidation and
lockout are decided with candles <= the current one, so every event at t' is identical if later candles are removed.
"""
from __future__ import annotations

import numpy as np

from src.setups.derive_params import EDGE, K, swings

WINDOW = 96
RECENT = 48                      # "recent" = last 48 candles (J-7)
LOCKOUT = 24                     # candles after a trigger (pre-registration de-duplication)
DIRECTION = {"C1": "up", "C2": "up", "C3": "down", "C4": "down", "C6": "down", "C7": "up", "C8": "down"}
ORDER = tuple(DIRECTION)         # C5 deliberately absent
NAMES = {"C1": "bullish_breakout_from_right_edge_consolidation", "C2": "bullish_rebound_breakout_after_drop",
         "C3": "bearish_breakdown_from_right_edge_range", "C4": "bearish_continuation_below_broken_support",
         "C6": "bearish_rejection_from_recent_high", "C7": "bullish_breakout_from_right_edge_range",
         "C8": "bearish_breakdown_from_right_edge_support"}
NEEDED = ("ZR", "EFF", "UP", "DN", "RET", "REB", "DT_C1", "DT_C2", "DF_C3", "DF_C4", "DF_C6", "DT_C7", "DF_C8")


def thresholds_from(derived: dict, lo="q33", hi="q67") -> dict:
    """derived = parsed derived_parameters.json -> {quantity: {'lo': .., 'hi': ..}} (primary bands 33/67)."""
    q = derived["quantities"]
    return {k: {"lo": q[k][lo], "hi": q[k][hi]} for k in NEEDED}


def _ok(x) -> bool:
    return x is not None and np.isfinite(x)


def window_state(h, l, c, thr: dict) -> dict:
    """-> {cand: None | (level, [(op, inv_level), ...])} for the decision candle (last of the arrays). None = no presence."""
    h, l, c = (np.asarray(x, float) for x in (h, l, c))
    n = len(c)
    t = n - 1
    out = {k: None for k in ORDER}
    R = h.max() - l.min()
    if n != WINDOW or not R > 0:
        return out
    ez = slice(n - EDGE, n)
    zh, zl = h[ez].max(), l[ez].min()
    ZR = (zh - zl) / R
    steps = np.abs(np.diff(c[n - EDGE:]))
    EFF = abs(c[t] - c[t - (EDGE - 1)]) / steps.sum() if steps.sum() > 0 else 0.0
    sh, sl = swings(h, l)
    recent = n - RECENT
    T = thr
    up = dn = ret = reb = pbl = hH = lL = rh = None
    jH = jL = None
    if sh:
        jH = sh[-1]
        hH = h[jH]
        pbl = l[jH:].min()
        before = [j for j in sl if j < jH]
        if before and hH > l[before[-1]]:
            lB = l[before[-1]]
            up = (hH - lB) / R
            ret = (hH - pbl) / (hH - lB)
    if sl:
        jL = sl[-1]
        lL = l[jL]
        rh = h[jL:].max()
        reb = (rh - lL) / R
        before = [j for j in sh if j < jL]
        if before and h[before[-1]] > lL:
            dn = (h[before[-1]] - lL) / R
    # C1
    if _ok(up) and jH >= recent and up > T["UP"]["lo"] and ZR <= T["ZR"]["lo"]:
        in_e = jH >= n - EDGE
        res1 = zh if (not in_e or hH < c[t]) else min(zh, hH)
        if (res1 - c[t]) / R <= T["DT_C1"]["lo"]:
            out["C1"] = (res1, [("lt", pbl), ("le", res1)])
    # C2
    if _ok(dn) and jL >= recent and dn >= T["DN"]["hi"] and c[t] > lL and reb > T["REB"]["lo"] \
            and (rh - c[t]) / R <= T["DT_C2"]["lo"]:
        out["C2"] = (rh, [("lt", lL)])
    # C3
    if zh > zl and EFF <= T["EFF"]["lo"] and jH is not None and jH >= n - EDGE and (hH - zl) / (zh - zl) >= 2 / 3 \
            and (c[t] - zl) / (zh - zl) <= 1 / 3 and c[t] < c[t - 3] and (c[t] - zl) / R <= T["DF_C3"]["lo"]:
        out["C3"] = (zl, [("gt", hH)])
    # C4
    best = None
    for jS in sl:
        brk = next((b for b in range(jS + 1, n) if c[b] < l[jS]), None)
        if brk is not None and (best is None or (brk, l[jS]) > best):
            best = (brk, l[jS])
    if best is not None:
        b, lS = best
        shs = [j for j in sh if j > b]
        sls = [j for j in sl if j > b]
        lower_high = len(shs) >= 2 and h[shs[-1]] < h[shs[-2]]
        lower_low = len(sls) >= 2 and l[sls[-1]] < l[sls[-2]]
        if c[t] < lS and (lower_high or lower_low) and sls:
            ll = l[sls[-1]]
            if c[t] >= ll and (c[t] - ll) / R <= T["DF_C4"]["lo"]:
                inv = min(lS, h[shs[-1]]) if shs else lS
                out["C4"] = (ll, [("gt", inv)])
    # C6
    if _ok(up) and jH >= recent and (hH - l.min()) / R >= 2 / 3 and c[t] < hH and c[jH + 1:].max() <= hH \
            and up > T["UP"]["lo"] and T["RET"]["lo"] < ret <= 1.0 and (c[t] - pbl) / R <= T["DF_C6"]["lo"]:
        out["C6"] = (pbl, [("gt", hH)])
    # C7
    if _ok(dn) and dn > T["DN"]["lo"] and (reb > T["REB"]["lo"] or ZR <= T["ZR"]["lo"]) \
            and (zh - c[t]) / R <= T["DT_C7"]["lo"]:
        out["C7"] = (zh, [("lt", zl), ("le", zh)])
    # C8
    if jL is not None and jH is not None:
        i1 = (_ok(up) and up > T["UP"]["lo"]) or (reb > T["REB"]["lo"])
        lower_high8 = len(sh) >= 2 and h[sh[-1]] < h[sh[-2]]
        i2 = lower_high8 or EFF <= T["EFF"]["lo"] or reb > T["REB"]["lo"]
        if i1 and i2 and jL >= recent and c[t] >= lL and (c[t] - lL) / R <= T["DF_C8"]["lo"] and c[t] < c[t - 3] \
                and jH >= recent and c[t] < hH:
            out["C8"] = (lL, [("gt", hH), ("ge", lL)])
    return out


_OPS = {"gt": lambda x, v: x > v, "ge": lambda x, v: x >= v, "lt": lambda x, v: x < v, "le": lambda x, v: x <= v}


def recognize(ts, o, h, l, c, thr: dict, step_ns: int = 900_000_000_000) -> list[dict]:
    """Walk the series; return trigger events in candle order. `ts` = int64 ns open times.

    Triggers inside a lockout are logged with counted=False (pre-registration). Event: cand, trigger_idx, presence_start_idx, presence_len, level, invalidation_idx (None until a close breaches the
    frozen invalidation level; a later candle can only fill it in), direction. Index i = candle i of the arrays."""
    ts = np.asarray(ts, np.int64)
    o, h, l, c = (np.asarray(x, float) for x in (o, h, l, c))
    n = len(c)
    prev = {k: None for k in ORDER}          # state at t-1
    run = {k: 0 for k in ORDER}
    active = {k: None for k in ORDER}        # last occurrence per candidate (for invalidation + lockout)
    events: list[dict] = []
    prev_ok = False
    for t in range(n):
        ok = t >= WINDOW - 1 and (ts[t] - ts[t - WINDOW + 1]) == (WINDOW - 1) * step_ns
        for k in ORDER:                      # invalidation of earlier occurrences, using candle t only
            a = active[k]
            if a is not None and a["event"]["invalidation_idx"] is None and t > a["event"]["trigger_idx"]:
                if any(_OPS[op](c[t], v) for op, v in a["inv"]):
                    a["event"]["invalidation_idx"] = t
        state = {k: None for k in ORDER}
        if ok:
            s = t - WINDOW + 1
            state = window_state(h[s:t + 1], l[s:t + 1], c[s:t + 1], thr)
        for k in ORDER:
            if ok and prev_ok and prev[k] is not None and (ts[t] - ts[t - 1]) == step_ns:
                level = prev[k][0]
                beyond = c[t] > level if DIRECTION[k] == "up" else c[t] < level
                a = active[k]
                ev0 = a["event"] if a is not None else None
                locked = ev0 is not None and (ev0["invalidation_idx"] is None
                                              or t <= max(ev0["invalidation_idx"], ev0["trigger_idx"] + LOCKOUT)
                                              )
                if beyond:
                    ev = {"cand": k, "direction": DIRECTION[k], "trigger_idx": t, "presence_start_idx": t - run[k],
                          "presence_len": run[k], "level": float(level), "invalidation_idx": None,
                          "counted": not locked, "locked_by": ev0["trigger_idx"] if locked else None}
                    events.append(ev)
                    if not locked:
                        active[k] = {"event": ev, "inv": prev[k][1]}
            run[k] = run[k] + 1 if (state[k] is not None and prev[k] is not None) else (1 if state[k] is not None else 0)
        prev, prev_ok = state, ok
    return events
