"""The written rules as a candle-by-candle state machine, and the hypothetical outcome of each signal (an event study, never a trade).

SHORT (bear bias):  armed when a completed 15m candle has RSI >= 65 while the bias is bear; the signal is the first later completed candle that
closes below the most recent CONFIRMED 15m swing low; the risk level is the highest high since arming (the signal candle included). LONG is the mirror.
The reference price is the open of the candle after the signal candle: a measurement point, not a fill.
Outcome: the first of (a) the risk level reached (a high >= it for a short), (b) 15m RSI <= 35 at a close (>= 65 for a long) -> reference = next open,
(c) 96 candles after the reference candle -> next open. Result in units of the risk distance (R), gross and net of costs. Nothing is assumed filled.
"""
from __future__ import annotations

import numpy as np

from src.trendrsi import indicators as ind
from src.trendrsi import params as P


def find_signals(o, h, l, c, rsi, bias_short, bias_long, valid) -> list[dict]:
    n = len(c)
    sh, sl = ind.swings(h, l)
    K = P.SWING_K
    last_sl = last_sh = None
    arm = {"short": None, "long": None}                       # {"idx", "ext"} while armed
    out = []
    for t in range(n):
        j = t - K
        if j >= K:
            if sl[j]:
                last_sl = float(l[j])
            if sh[j]:
                last_sh = float(h[j])
        if not valid[t] or not np.isfinite(rsi[t]):
            arm = {"short": None, "long": None}
            continue
        for side in ("short", "long"):
            a = arm[side]
            bias = bias_short[t] if side == "short" else bias_long[t]
            stretched = rsi[t] >= P.RSI_ALMOST_OB if side == "short" else rsi[t] <= P.RSI_ALMOST_OS
            done = rsi[t] <= P.RSI_ALMOST_OS if side == "short" else rsi[t] >= P.RSI_ALMOST_OB
            if a is not None:
                if (not bias) or done or (t - a["idx"] > P.ARM_MAX_BARS):
                    arm[side] = a = None                      # the move already happened, the bias is gone, or the setup expired
                else:
                    a["ext"] = max(a["ext"], float(h[t])) if side == "short" else min(a["ext"], float(l[t]))
                    brk = (last_sl is not None and c[t] < last_sl) if side == "short" else (last_sh is not None and c[t] > last_sh)
                    if t > a["idx"] and brk:
                        out.append({"side": side, "t": t, "arm_idx": a["idx"], "risk_level": a["ext"],
                                    "break_level": last_sl if side == "short" else last_sh})
                        arm[side] = a = None
            if a is None and bias and stretched:
                arm[side] = {"idx": t, "ext": float(h[t]) if side == "short" else float(l[t])}
    return out


def outcome(sig: dict, o, h, l, c, rsi, valid_forward) -> dict:
    """Hypothetical result of one signal, from the open of the next candle. Returns the record, with status OK or EXCLUDED_<reason>."""
    n = len(c)
    t, side, risk_level = sig["t"], sig["side"], sig["risk_level"]
    r = t + 1
    rec = {**sig, "ref_idx": r}
    if r >= n:
        return {**rec, "status": "EXCLUDED_END_OF_DATA"}
    ref = float(o[r])
    risk = (risk_level - ref) if side == "short" else (ref - risk_level)
    if not risk > 0:
        return {**rec, "ref_px": ref, "status": "EXCLUDED_RISK_NOT_POSITIVE"}          # the reference already lies beyond the risk level
    if not valid_forward[r]:
        return {**rec, "ref_px": ref, "status": "EXCLUDED_DATA_GAP"}
    s = 1.0 if side == "long" else -1.0
    reason, exit_px, exit_idx = None, None, None
    mfe = mae = 0.0
    for k in range(r, min(r + P.TIME_STOP_BARS, n)):
        if not valid_forward[k]:
            return {**rec, "ref_px": ref, "status": "EXCLUDED_DATA_GAP"}
        fav = (h[k] - ref) if side == "long" else (ref - l[k])
        adv = (ref - l[k]) if side == "long" else (h[k] - ref)
        mfe, mae = max(mfe, fav), max(mae, adv)
        if (l[k] <= risk_level) if side == "long" else (h[k] >= risk_level):
            reason, exit_px, exit_idx = "risk_level", risk_level, k
            break
        done = (rsi[k] >= P.RSI_ALMOST_OB) if side == "long" else (rsi[k] <= P.RSI_ALMOST_OS)
        if done and k + 1 < n:
            reason, exit_px, exit_idx = "rsi", float(o[k + 1]), k + 1
            break
        if k - r + 1 >= P.TIME_STOP_BARS and k + 1 < n:
            reason, exit_px, exit_idx = "time", float(o[k + 1]), k + 1
            break
    if reason is None:
        return {**rec, "ref_px": ref, "status": "EXCLUDED_END_OF_DATA"}
    gross = s * (exit_px - ref) / risk
    cost = lambda slip: 2 * (P.TAKER_PCT + slip) / 100 * ref / risk              # noqa: E731  both legs, in units of R
    return {**rec, "status": "OK", "ref_px": ref, "exit_ref": exit_px, "exit_idx": exit_idx, "exit_reason": reason, "bars_held": exit_idx - r,
            "risk_pct": 100 * risk / ref, "gross_R": gross, "mfe_R": mfe / risk, "mae_R": mae / risk,
            **{f"net_R_slip{slip}": gross - cost(slip) for slip in P.SLIP_SENSITIVITY_PCT}}
