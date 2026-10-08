"""Setup Brain v2: the v1 brain (src/brain/brain.py, frozen and untouched) with the detector function injected, so that S1 v2 can be used.
The candle loop below is a copy of the v1 loop with `det.evaluate` replaced by `self.evaluate`; tests prove it behaves identically when given the v1 function.

Original v1 docstring: The Setup Brain: one completed 15m candle in, FIRE / INVALIDATED events out.

For every completed candle, in order:
    1. check the invalidation rules of earlier FIREs (this candle's close only)
    2. FIRE any setup that was PRESENT on the previous candle and whose operative level this candle closes beyond
    3. evaluate all nine detectors on the last 96 candles and keep their state for the next candle

Nine independent detectors: no voting, no consensus, no ranking, no veto, no merging, no lockout, no frequency gate. Every valid FIRE
is recorded; consecutive fires of one setup are kept and labelled (`streak_position`); same-candle fires of different setups are
separate events. The brain holds only the last 96 candles: it cannot see a future candle, and an incomplete candle is refused.

A FIRE is a signal. It carries no entry, no fill, no stop, no target. The analytical reference price (open of the next candle) does
not exist yet when a FIRE is emitted and is attached later by the observation layer; it is never an execution price.
"""
from __future__ import annotations

import hashlib
from collections import deque

import numpy as np
import pandas as pd

from src.brain import detectors as det

STEP_NS = 900 * 1_000_000_000
OPS = {"gt": lambda x, v: x > v, "ge": lambda x, v: x >= v, "lt": lambda x, v: x < v, "le": lambda x, v: x <= v}


def iso(ns: int) -> str:
    return pd.Timestamp(ns, tz="UTC").isoformat()


class SetupBrainV2:
    def __init__(self, thr: dict, detector_version: str = "unversioned", step_ns: int = STEP_NS, evaluate=None):
        self.thr, self.version, self.step_ns = thr, detector_version, step_ns
        self.evaluate = evaluate or det.evaluate
        self.buf: deque = deque(maxlen=det.WINDOW)
        self.idx = -1                                           # index of the last candle consumed
        self.prev_state: dict = {}                              # presence at the previous candle (None if not evaluated)
        self.run = {s: 0 for s in det.IDS}                      # length of the unbroken presence run ending at the previous candle
        self.run_start: dict = {}                               # setup -> open time of the first candle of that run
        self.last_fire_idx: dict = {}                           # (setup, direction) -> idx of its last fire
        self.streak: dict = {}                                  # (setup, direction) -> streak position of its last fire
        self.open_fires: list[dict] = []                        # fires whose invalidation has not happened yet
        self.digest = hashlib.sha256()                          # hash of every candle consumed so far (audit: no future input)
        self.rejected_incomplete = 0
        self.presence_candles = {s: 0 for s in det.IDS}
        self.presence_pairs: dict = {}
        self.evaluated_candles = 0
        self.gaps = 0

    # ------------------------------------------------------------------------------------------------ input
    def on_candle(self, candle: dict) -> list[dict]:
        """candle: {ts (open time, int ns UTC), open, high, low, close, closed (default True)}."""
        if not candle.get("closed", True):
            self.rejected_incomplete += 1
            return []
        ts = int(candle["ts"])
        if self.buf and ts <= self.buf[-1][0]:
            raise ValueError("candles must arrive in strictly increasing time order")
        if self.buf and ts - self.buf[-1][0] != self.step_ns:    # a gap: no window or previous state may span it
            self.gaps += 1
            self.buf.clear()
            self.prev_state, self.run, self.run_start = {}, {s: 0 for s in det.IDS}, {}
        o, h, l, c = (float(candle[k]) for k in ("open", "high", "low", "close"))
        self.buf.append((ts, o, h, l, c))
        self.idx += 1
        self.digest.update(f"{ts},{o!r},{h!r},{l!r},{c!r};".encode())
        events: list[dict] = []
        # 1. invalidation of earlier fires (candle t only)
        still = []
        for f in self.open_fires:
            hit = next(((op, v) for op, v in f["invalidation_rules"] if OPS[op](c, v)), None)
            if hit is None:
                still.append(f)
            else:
                events.append({"event": "INVALIDATED", "fire_id": f["fire_id"], "setup_id": f["setup_id"], "direction": f["direction"],
                               "invalidation_ts": iso(ts + self.step_ns), "invalidation_idx": self.idx,
                               "rule": f"close {hit[0]} {hit[1]}", "candles_after_trigger": self.idx - f["trigger_idx"]})
        self.open_fires = still
        # 2. fires: presence on the previous candle AND this candle closes beyond that level
        for sid in det.IDS:
            for direction, level, rules in self.prev_state.get(sid) or []:
                if (c > level) if direction == "up" else (c < level):
                    key = (sid, direction)
                    self.streak[key] = self.streak.get(key, -1) + 1 if self.last_fire_idx.get(key) == self.idx - 1 else 0
                    self.last_fire_idx[key] = self.idx
                    run = self.run[sid]
                    fire = {"event": "FIRE", "fire_id": f"{sid}-{self.idx}-{direction}", "setup_id": sid, "setup_name": det.NAMES[sid],
                            "direction": direction, "timeframe": "15m", "trigger_idx": self.idx,
                            "trigger_ts": iso(ts + self.step_ns), "trigger_candle_open_ts": iso(ts),
                            "trigger_candle": {"open": o, "high": h, "low": l, "close": c},
                            "operative_level": level, "presence_len": run,
                            "presence_start_ts": iso(self.run_start[sid] + self.step_ns),
                            "invalidation_rules": [(op, v) for op, v in rules],
                            "streak_position": self.streak[key], "detector_version_sha256": self.version,
                            "input_digest": self.digest.copy().hexdigest()}
                    events.append(fire)
                    self.open_fires.append(fire)
        # 3. evaluate every detector on the last 96 completed candles
        state: dict = {}
        if len(self.buf) == det.WINDOW:
            a = np.array(self.buf, float)
            state = self.evaluate(a[:, 2], a[:, 3], a[:, 4], self.thr)
            self.evaluated_candles += 1
            present = sorted(state)
            for s in present:
                self.presence_candles[s] += 1
            for i, s in enumerate(present):
                for u in present[i + 1:]:
                    self.presence_pairs[(s, u)] = self.presence_pairs.get((s, u), 0) + 1
        for sid in det.IDS:
            cont = sid in state and bool(self.prev_state.get(sid))
            self.run[sid] = self.run[sid] + 1 if cont else (1 if sid in state else 0)
            if sid in state and not cont:
                self.run_start[sid] = ts
        self.prev_state = state
        return events
