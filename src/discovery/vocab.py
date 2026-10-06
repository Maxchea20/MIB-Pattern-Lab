"""Frozen shape vocabulary + re-tag prompt (Stage 3).

The vocabulary was distilled from the recurring concepts in the first 50 free-form descriptions
(sideways/flat, sharp drop, rounded top, stair steps, V reversals, edge spikes ...). It is purely
visual: no direction-of-trade language, no outcomes. Changing ANY definition changes
VOCAB_SHA256 -> bump VOCAB_VERSION and treat results as a new experiment.
"""
from __future__ import annotations

import hashlib

VOCAB_VERSION = "vocab-v1"
NONE_TAG = "none"

VOCAB: list[tuple[str, str]] = [
    ("sideways_range", "price oscillates inside a band with no clear net direction for most of the window"),
    ("tight_compression", "candles are very small and the whole window sits in a very narrow band"),
    ("choppy_volatile", "large candles alternate in colour with big swings but no net direction"),
    ("drift_up", "gradual net rise made of ordinary-sized candles, no single dominant jump"),
    ("drift_down", "gradual net fall made of ordinary-sized candles, no single dominant drop"),
    ("stair_step_up", "rise in distinct steps: a push up, a pause, then another push up"),
    ("stair_step_down", "fall in distinct steps: a push down, a pause, then another push down"),
    ("sharp_rally", "one sudden steep rise made of a few large same-colour candles"),
    ("sharp_drop", "one sudden steep fall made of a few large same-colour candles"),
    ("v_reversal", "a sharp fall followed by a sharp recovery back toward the starting level"),
    ("inverted_v", "a sharp rise followed by a sharp fall back toward the starting level"),
    ("rounded_top", "gradual rise, a flat or curved crest, then a gradual fall (arc shape)"),
    ("rounded_bottom", "gradual fall, a flat or curved trough, then a gradual rise (bowl shape)"),
    ("range_breakout_up", "a sideways band followed by an abrupt move up out of it that holds"),
    ("range_breakdown", "a sideways band followed by an abrupt move down out of it that holds"),
    ("spike_and_retrace", "a one- or two-candle spike (big body or extended wick) that is quickly undone"),
    ("terminal_spike_up", "a sharp jump up within the last ~10 candles at the right edge"),
    ("terminal_spike_down", "a sharp jump down within the last ~10 candles at the right edge"),
    (NONE_TAG, "no clear shape from this list applies (use alone)"),
]
NAMES = [n for n, _ in VOCAB]
VOCAB_SHA256 = hashlib.sha256("\n".join(f"{n}:{d}" for n, d in VOCAB).encode()).hexdigest()

RETAG_VERSION = "retag-v1"
MAX_TAGS = 3

RETAG_SYSTEM = (
    "You are a careful visual analyst. You are shown a single candlestick chart image. Classify only "
    "what is visible, using ONLY the shape names provided. Do not use outside knowledge and do not "
    "guess what happens after the right edge. Respond with one JSON object only."
)


def ordered_vocab(reverse: bool = False) -> list[tuple[str, str]]:
    items = [v for v in VOCAB if v[0] != NONE_TAG]
    items = items[::-1] if reverse else items
    return items + [(NONE_TAG, dict(VOCAB)[NONE_TAG])]


def retag_user(reverse: bool = False) -> str:
    lines = "\n".join(f"- {n}: {d}" for n, d in ordered_vocab(reverse))
    return (
        "Choose which of these shape names describe the chart's overall price path, left to right.\n\n"
        f"{lines}\n\n"
        f"Rules:\n- Pick 1 to {MAX_TAGS} names that clearly apply, most prominent first.\n"
        f"- Use \"{NONE_TAG}\" alone if nothing fits well. Do not force a fit; do not invent names.\n"
        "- A quiet, flat chart is still a valid shape (see sideways_range / tight_compression).\n\n"
        'Return JSON: {"tags": [<names>], "primary": <the most prominent name>}'
    )


def validate_tags(obj) -> tuple[list[str] | None, str | None, str | None]:
    """-> (tags, primary, error). Rejects unknown names; never silently repairs."""
    if not isinstance(obj, dict) or not isinstance(obj.get("tags"), list):
        return None, None, "missing 'tags' list"
    tags = [str(t).strip() for t in obj["tags"]]
    if not tags or len(tags) > MAX_TAGS or len(set(tags)) != len(tags):
        return None, None, f"need 1-{MAX_TAGS} unique tags, got {tags}"
    bad = [t for t in tags if t not in NAMES]
    if bad:
        return None, None, f"unknown tags: {bad}"
    if NONE_TAG in tags and len(tags) > 1:
        return None, None, "'none' must be used alone"
    primary = str(obj.get("primary", tags[0])).strip()
    if primary not in tags:
        return None, None, f"primary {primary!r} not in tags"
    return tags, primary, None
