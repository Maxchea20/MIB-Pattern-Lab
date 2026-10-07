"""Prompt templates, lints and response validators for Setup Discovery (pre-registration sections 5-7, appendices A/B).

Prompts never name a technical-analysis concept (strict whole-word prompt lint). Model output may use whatever words it
chooses, but is rejected if it contains performance or promise language (output lint). Nothing here sees an outcome.
"""
from __future__ import annotations

import hashlib
import json
import re

from src.setups import params

# ----------------------------------------------------------------------------------------------- Stage A ----
A_SYSTEM = (
    "You are a careful, disciplined observer of price charts. You are shown a single chart made of candles. Treat it as a "
    "LIVE chart: the right edge is the present moment and nothing after it exists. Use only what is visible in the image. "
    "Do not use outside knowledge about what happened. Do not guess what happens after the right edge. Respond with one "
    "JSON object only.")

A_USER = """Imagine you are looking at this chart live, right now, at the right edge.

Is there a recognisable, potentially actionable trading situation developing or present at the right edge? If there is, describe exactly what you see and what would make it actionable. If there is not, say so. "none" is a perfectly good answer; do not force a situation that is not clearly there.

Return a JSON object with exactly these keys:
- "status": "ACTIONABLE_NOW" if the event that makes it actionable has already happened on or before the last candle; "DEVELOPING" if a situation is forming but that event has not happened yet; "NONE" if there is no recognisable situation.
- "visible_summary": 1-2 sentences describing the price path left to right (appearance only).
- "context": what price was doing before the situation developed ("" if NONE).
- "location": what observable price relationship, visible on this chart, makes the current situation interesting ("" if NONE).
- "development": the sequence of price behaviour immediately before the potential trade, in order ("" if NONE).
- "trigger": the exact observable event, on a completed candle, that makes the situation actionable ("" if NONE).
- "direction": "up", "down", or "undetermined" (use "undetermined" if the direction cannot be determined from the chart, and for NONE).
- "invalidation": the observable event that would show the situation has failed ("" if NONE).
- "expected_behavior": the kind of later price behaviour that would make it successful, described in words, without promising any outcome ("" if NONE).
- "information_required": a list of the specific chart elements (candles, levels, ranges) needed to recognise this situation ([] if NONE).

Describe only what is visible. Do not say or imply that the situation will work or is likely to succeed."""

A_KEYS = ("status", "visible_summary", "context", "location", "development", "trigger", "direction", "invalidation",
          "expected_behavior", "information_required")
A_STATUS = ("ACTIONABLE_NOW", "DEVELOPING", "NONE")
DIRECTIONS = ("up", "down", "undetermined")

# ----------------------------------------------------------------------------------------------- Stage B ----
B_SYSTEM = (
    "You are a careful analyst who consolidates written descriptions of chart situations. You see only text descriptions, "
    "each with an id. You have no information about what happened after any chart, so you must never say or imply that any "
    "situation works, wins, or is reliable. Use only what is in the descriptions; do not add conditions that are not in "
    "them. Respond with one JSON object only.")

B_KEYS_BLOCK = """Return {"candidates": [ ... ]} where each candidate has exactly these keys:
- "name": a short descriptive snake_case name of the situation
- "context_definition": what price was doing before the situation
- "conditions_sequence": an ordered list of observable conditions that must hold, in order
- "presence_rule": when the situation counts as PRESENT, before it is actionable
- "trigger": the exact observable event, on a completed candle, that makes it actionable
- "direction": "up", "down" or "undetermined"
- "invalidation": the observable event that shows it has failed
- "information_required": a list of the chart elements needed to recognise it
- "supporting_ids": the ids of the descriptions it was derived from"""

B_CHUNK_USER_TEMPLATE = """Below are descriptions of situations observed on live price charts. Each has an id.

Group descriptions that describe the same recurring situation. Return at most 8 distinct candidate situations, and only candidates whose actionable event is an observable event on a completed candle. Merge near-duplicates now; prefer fewer, genuinely distinct candidates.

""" + B_KEYS_BLOCK + """

Descriptions:
{DESCRIPTIONS}"""

B_FINAL_USER_TEMPLATE = """Below are candidate situations that were proposed from separate batches of descriptions of situations observed on live price charts. Each candidate lists the ids of the descriptions it was derived from.

Merge candidates that describe the same recurring situation. Return at most 8 distinct candidate situations, and only candidates whose actionable event is an observable event on a completed candle. Merge near-duplicates now; prefer fewer, genuinely distinct candidates. The "supporting_ids" of a merged candidate must be all the ids of the candidates merged into it.

""" + B_KEYS_BLOCK + """

Candidates:
{CANDIDATES}"""

B_KEYS = ("name", "context_definition", "conditions_sequence", "presence_rule", "trigger", "direction", "invalidation",
          "information_required", "supporting_ids")

RETRY_SUFFIX = ("\n\nYour previous answer was rejected for these reasons: {problems}\n"
                "Return the corrected JSON object only.")

# ---------------------------------------------------------------------------------------------- audit -------
AUDIT_SYSTEM = (
    "You are a careful, disciplined observer of price charts. You are shown a single chart made of candles and a written "
    "definition of a situation. Treat the chart as LIVE: the right edge is the present moment and nothing after it exists. "
    "Use only what is visible in the image. Respond with one JSON object only.")

AUDIT_USER_TEMPLATE = """Here is a written definition of a situation:

{DEFINITION}

Look at the chart at the right edge. Decide whether this situation is present: all of its presence conditions hold on the completed candles up to and including the last candle, or its trigger event happened on one of the last two candles.

Return a JSON object with exactly these keys:
- "judgement": "PRESENT", "NOT_PRESENT" or "UNCLEAR"
- "reason": one sentence describing what you see that supports the judgement.

Judge only what is visible. Do not say or imply that the situation will work."""

AUDIT_KEYS = ("judgement", "reason")
AUDIT_JUDGEMENTS = ("PRESENT", "NOT_PRESENT", "UNCLEAR")

# ----------------------------------------------------------------------------------------------- lints ------
PROMPT_FORBIDDEN = ("breakout", "bos", "choch", "liquidity", "sweep", "fvg", "fair value gap", "support", "resistance",
                    "order block", "trend", "continuation", "reversal", "momentum", "mean reversion", "pattern",
                    "candlestick", "bullish", "bearish", "indicator", "volume")
# Output lint (section 5): performance / promise language. A bare "edge" is NOT in the list because the prompts themselves
# say "the right edge" and nearly every answer would contain it; the performance meaning is covered by these phrases.
OUTPUT_FORBIDDEN_WORDS = ("profit", "profitable", "win", "wins", "winning", "works", "probability", "likely", "guaranteed",
                          "target", "backtest")
OUTPUT_FORBIDDEN_PHRASES = ("take profit", "stop loss", "trading edge", "statistical edge", "predictive edge",
                            "positive edge", "an edge", "has edge", "have edge")


def _find(text: str, terms) -> list[str]:
    t = " ".join(str(text).lower().split())
    return sorted({w for w in terms if re.search(r"(?<![a-z0-9_])" + re.escape(w) + r"(?![a-z0-9_])", t)})


def lint_prompt(text: str) -> list[str]:
    return _find(text, PROMPT_FORBIDDEN)


def lint_templates() -> dict[str, list[str]]:
    return {k: lint_prompt(v) for k, v in templates().items()}


def _leaves(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from _leaves(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _leaves(v)
    elif isinstance(x, str):
        yield x


def lint_output(obj) -> list[str]:
    text = " ".join(_leaves(obj))
    return sorted(set(_find(text, OUTPUT_FORBIDDEN_WORDS) + _find(text, OUTPUT_FORBIDDEN_PHRASES)))


def templates() -> dict[str, str]:
    return {"A_SYSTEM": A_SYSTEM, "A_USER": A_USER, "B_SYSTEM": B_SYSTEM, "B_CHUNK_USER_TEMPLATE": B_CHUNK_USER_TEMPLATE,
            "B_FINAL_USER_TEMPLATE": B_FINAL_USER_TEMPLATE, "AUDIT_SYSTEM": AUDIT_SYSTEM,
            "AUDIT_USER_TEMPLATE": AUDIT_USER_TEMPLATE, "RETRY_SUFFIX": RETRY_SUFFIX}


def template_hashes() -> dict[str, str]:
    return {k: hashlib.sha256(v.encode()).hexdigest() for k, v in templates().items()}


# ------------------------------------------------------------------------------------------- validators ------
def _is_str_list(x) -> bool:
    return isinstance(x, list) and all(isinstance(i, str) for i in x)


def validate_stage_a(obj) -> list[str]:
    """Problems with one Stage A response (empty list = accepted). Structure and lint only: no judgement of content."""
    if not isinstance(obj, dict):
        return ["response is not a JSON object"]
    p = []
    if set(obj) != set(A_KEYS):
        p.append(f"keys must be exactly {list(A_KEYS)}; got {sorted(obj)}")
        return p
    if obj["status"] not in A_STATUS:
        p.append(f"status must be one of {list(A_STATUS)}")
    if obj["direction"] not in DIRECTIONS:
        p.append(f"direction must be one of {list(DIRECTIONS)}")
    for k in A_KEYS:
        if k == "information_required":
            if not _is_str_list(obj[k]):
                p.append("information_required must be a list of strings")
        elif k not in ("status", "direction") and not isinstance(obj[k], str):
            p.append(f"{k} must be a string")
    if not p and obj["status"] != "NONE":
        for k in ("context", "development", "trigger", "invalidation"):
            if not obj[k].strip():
                p.append(f"{k} must be non-empty when status is {obj['status']}")
    if not p:
        bad = lint_output(obj)
        if bad:
            p.append(f"performance/promise language is not allowed: {bad}")
    return p


def validate_candidate(c, allowed_ids: set[str]) -> list[str]:
    if not isinstance(c, dict):
        return ["candidate is not an object"]
    if set(c) != set(B_KEYS):
        return [f"candidate keys must be exactly {list(B_KEYS)}; got {sorted(c)}"]
    p = []
    for k in ("name", "context_definition", "presence_rule", "trigger", "invalidation"):
        if not isinstance(c[k], str) or not c[k].strip():
            p.append(f"{k} must be a non-empty string")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", str(c["name"])):
        p.append("name must be snake_case")
    if c["direction"] not in DIRECTIONS:
        p.append(f"direction must be one of {list(DIRECTIONS)}")
    for k in ("conditions_sequence", "information_required"):
        if not _is_str_list(c[k]) or not c[k]:
            p.append(f"{k} must be a non-empty list of strings")
    ids = c["supporting_ids"]
    if not _is_str_list(ids) or not ids:
        p.append("supporting_ids must be a non-empty list of strings")
    else:
        unknown = sorted(set(ids) - allowed_ids)
        if unknown:
            p.append(f"supporting_ids not found among the input descriptions: {unknown[:5]}")
    if not p:
        bad = lint_output(c)
        if bad:
            p.append(f"performance/promise language is not allowed: {bad}")
    return p


def validate_stage_b(obj, allowed_ids: set[str]) -> tuple[list[dict] | None, list[str]]:
    """-> (candidates, problems). At most MAX_CANDIDATES; names unique; every candidate valid."""
    if not isinstance(obj, dict) or not isinstance(obj.get("candidates"), list):
        return None, ["response must be an object with a 'candidates' list"]
    cands = obj["candidates"]
    p = []
    if len(cands) > params.MAX_CANDIDATES:
        p.append(f"at most {params.MAX_CANDIDATES} candidates are allowed; got {len(cands)}")
    for i, c in enumerate(cands):
        p += [f"candidate {i + 1}: {x}" for x in validate_candidate(c, allowed_ids)]
    names = [c.get("name") for c in cands if isinstance(c, dict)]
    if len(set(names)) != len(names):
        p.append("candidate names must be unique")
    return (None if p else cands), p


def validate_audit(obj) -> list[str]:
    if not isinstance(obj, dict) or set(obj) != set(AUDIT_KEYS):
        return [f"keys must be exactly {list(AUDIT_KEYS)}"]
    p = []
    if obj["judgement"] not in AUDIT_JUDGEMENTS:
        p.append(f"judgement must be one of {list(AUDIT_JUDGEMENTS)}")
    if not isinstance(obj["reason"], str):
        p.append("reason must be a string")
    return p


# ----------------------------------------------------------------------------------------------- rendering ---
def render_description(row: dict) -> str:
    """Text shown to Stage B for one Stage A description. Carries the chart id and the model's own words ONLY: no
    timestamp, stratum or any other property of the chart."""
    o = row["parsed"]
    return "\n".join([f"id: {row['chart_id']}", f"status: {o['status']}", f"context: {o['context']}",
                      f"location: {o['location']}", f"development: {o['development']}", f"trigger: {o['trigger']}",
                      f"direction: {o['direction']}", f"invalidation: {o['invalidation']}",
                      f"expected_behavior: {o['expected_behavior']}",
                      "information_required: " + "; ".join(o["information_required"])])


def render_candidates(cands: list[dict]) -> str:
    return json.dumps(cands, indent=1, sort_keys=True)


def definition_text(c: dict) -> str:
    """Frozen definition text of one candidate as shown in the fidelity audit (no supporting ids, no counts)."""
    lines = [f"Name: {c['name']}", f"Context: {c['context_definition']}", "Conditions, in order:"]
    lines += [f"  {i}. {x}" for i, x in enumerate(c["conditions_sequence"], 1)]
    lines += [f"Present when: {c['presence_rule']}", f"Trigger: {c['trigger']}", f"Direction: {c['direction']}",
              f"Invalidation: {c['invalidation']}", "Information required: " + "; ".join(c["information_required"])]
    return "\n".join(lines)
