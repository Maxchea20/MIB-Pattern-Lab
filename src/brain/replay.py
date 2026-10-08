"""Live-like replay and the independent chronological batch scan of the Setup Brain.

`replay` feeds completed candles to the brain ONE AT A TIME from a generator; the brain keeps only 96 candles. `batch_scan` is a
second, differently structured implementation (all window states first, then the trigger pass over arrays). The two must agree
exactly; any difference is a bug. Neither computes a price outcome.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.brain import detectors as det
from src.brain.brain import OPS, SetupBrain, iso, STEP_NS


def candle_stream(df: pd.DataFrame):
    """Yield completed candles one by one, oldest first. `df` already excludes the still-forming candle (the loader drops it)."""
    ts = df["ts"].dt.as_unit("ns").astype("int64").to_numpy()
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    for i in range(len(df)):
        yield {"ts": int(ts[i]), "open": o[i], "high": h[i], "low": l[i], "close": c[i], "closed": True}


def replay(stream, brain: SetupBrain, log_path: Path | None = None) -> list[dict]:
    """Candle arrives -> brain updates -> FIRE / INVALIDATED logged -> next candle. Returns every event in order."""
    events: list[dict] = []
    f = open(log_path, "w", encoding="utf-8") if log_path else None
    try:
        for candle in stream:
            for e in brain.on_candle(candle):
                events.append(e)
                if f:
                    f.write(json.dumps(e) + "\n")
    finally:
        if f:
            f.close()
    return events


def batch_scan(ts, o, h, l, c, thr: dict, version: str = "unversioned", step_ns: int = STEP_NS, evaluate_fn=None) -> list[dict]:
    """Chronological batch scan over arrays: window states for every evaluable candle first, then fires and invalidations.
    Returns FIRE and INVALIDATED events in the same order and with the same fields as the replay (except `input_digest`)."""
    ts = np.asarray(ts, np.int64)
    h, l, c = (np.asarray(x, float) for x in (h, l, c))
    n = len(c)
    W = det.WINDOW
    ok = np.zeros(n, bool)
    states: list[dict] = [{} for _ in range(n)]
    for t in range(W - 1, n):
        if ts[t] - ts[t - W + 1] == (W - 1) * step_ns and np.all(np.diff(ts[t - W + 1:t + 1]) == step_ns):
            ok[t] = True
            states[t] = (evaluate_fn or det.evaluate)(h[t - W + 1:t + 1], l[t - W + 1:t + 1], c[t - W + 1:t + 1], thr)
    run = np.zeros((n, len(det.IDS)), int)                       # presence run length ending at t (0 = absent)
    start = np.zeros((n, len(det.IDS)), int)
    for t in range(n):
        for k, sid in enumerate(det.IDS):
            if ok[t] and sid in states[t]:
                if t > 0 and ok[t - 1] and sid in states[t - 1]:
                    run[t, k], start[t, k] = run[t - 1, k] + 1, start[t - 1, k]
                else:
                    run[t, k], start[t, k] = 1, t
    events, open_fires, last = [], [], {}
    streak: dict = {}
    for t in range(1, n):
        keep = []
        for f in open_fires:
            hit = next(((op, v) for op, v in f["invalidation_rules"] if OPS[op](c[t], v)), None)
            if hit is None:
                keep.append(f)
            else:
                events.append({"event": "INVALIDATED", "fire_id": f["fire_id"], "setup_id": f["setup_id"], "direction": f["direction"],
                               "invalidation_ts": iso(int(ts[t]) + step_ns), "invalidation_idx": t,
                               "rule": f"close {hit[0]} {hit[1]}", "candles_after_trigger": t - f["trigger_idx"]})
        open_fires = keep
        if ts[t] - ts[t - 1] != step_ns or not ok[t - 1]:
            continue
        for k, sid in enumerate(det.IDS):
            for direction, level, rules in states[t - 1].get(sid, []):
                if (c[t] > level) if direction == "up" else (c[t] < level):
                    key = (sid, direction)
                    streak[key] = streak.get(key, -1) + 1 if last.get(key) == t - 1 else 0
                    last[key] = t
                    f = {"event": "FIRE", "fire_id": f"{sid}-{t}-{direction}", "setup_id": sid, "setup_name": det.NAMES[sid],
                         "direction": direction, "timeframe": "15m", "trigger_idx": t,
                         "trigger_ts": iso(int(ts[t]) + step_ns), "trigger_candle_open_ts": iso(int(ts[t])),
                         "trigger_candle": {"open": float(o[t]), "high": float(h[t]), "low": float(l[t]), "close": float(c[t])},
                         "operative_level": level, "presence_len": int(run[t - 1, k]),
                         "presence_start_ts": iso(int(ts[start[t - 1, k]]) + step_ns),
                         "invalidation_rules": [(op, v) for op, v in rules], "streak_position": streak[key],
                         "detector_version_sha256": version}
                    events.append(f)
                    open_fires.append(f)
    return events


def comparable(events: list[dict]) -> list[dict]:
    """Events without the audit-only digest, for exact comparison between replay and batch."""
    return [{k: v for k, v in e.items() if k != "input_digest"} for e in events]


def dataset_card(df: pd.DataFrame, step_ns: int = STEP_NS) -> dict:
    ts = df["ts"].dt.as_unit("ns").astype("int64").to_numpy()
    d = np.diff(ts)
    bad = ((df["high"] < df["low"]) | (df["high"] < df[["open", "close"]].max(axis=1)) | (df["low"] > df[["open", "close"]].min(axis=1))).sum()
    gaps = int(((d != step_ns) & (d > 0)).sum())
    return {"rows": int(len(df)), "first_open": iso(int(ts[0])) if len(ts) else None, "last_open": iso(int(ts[-1])) if len(ts) else None,
            "gaps": gaps, "missing_candles": int(sum(x // step_ns - 1 for x in d[(d != step_ns) & (d > 0)])),
            "duplicate_timestamps": int((d == 0).sum()), "out_of_order": int((d < 0).sum()), "invalid_ohlc_rows": int(bad)}
