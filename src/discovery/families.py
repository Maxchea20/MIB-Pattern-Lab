"""Frozen family definitions (pre-registration section 5). Pure data - no outcomes.

Every vocabulary shape except `none` is its own single-tag family. Nothing is merged (no combined
`impulse_up`; that name is reserved for possible future work and must NOT be defined here).
Only the three PRIMARY families are confirmatory; all others are descriptive.
"""
from __future__ import annotations

from src.discovery import vocab

PRIMARY = ("sideways_range", "drift_up", "drift_down")
RESERVED_UNUSED = ("impulse_up",)
FAMILIES = tuple(n for n in vocab.NAMES if n != vocab.NONE_TAG)          # one family per shape
EXPLORATORY = tuple(n for n in FAMILIES if n not in PRIMARY)             # incl. stair_step_up, sharp_rally,
                                                                          # range_breakout_up (kept separate)


def membership(stable: dict[str, list[str]]) -> dict[str, set[str]]:
    """{end_ts: stable tags} -> {family: set of end_ts}. A window may belong to several families;
    windows with no stable tag (or only `none`) belong to none and stay in the non-family population."""
    out = {f: set() for f in FAMILIES}
    for end_ts, tags in stable.items():
        for t in tags:
            if t in out:
                out[t].add(end_ts)
    return out
