"""Prompts, language lint and vocabulary validation for the 5M discovery (outcome-blind throughout).

Three steps, all seeing ONLY chart images or text derived from them (never prices after T, never outcomes):
  D1  free-form visual description of each chart in the description-stage subsample;
  D2  one consolidation call: group the recurring shape names into a small set of visual families (names and
      one-sentence visual definitions are written by the model, not by us);
  D3  classification of every sampled chart against the frozen families (two passes, 2nd with reversed order;
      stable tags = tags present in BOTH passes).
No technical-analysis concepts are named in any prompt. The LINT rejects them in prompts and in the vocabulary.
"""
from __future__ import annotations

import hashlib
import json
import re

from src.exp5m import params

# --- Two different rules --------------------------------------------------------------------------------------
# (1) PROMPT RULE (original instruction): the prompts themselves must not name technical-analysis concepts, so the
#     model is not primed to look for them. Every template is linted against PROMPT_FORBIDDEN.
# (2) VOCABULARY RULE (user decision 6): the discovered family names/definitions may use natural structural words
#     (trend, breakout, reversal, impulse, consolidation, pullback, ...). They are rejected ONLY if they
#       (a) prescribe or imply a trading decision, an outcome interpretation or a market-sentiment bias, or
#       (b) refer to things that are not visually present in a clean chart (indicators, volume, drawn levels).
#     Judgment calls: bullish/bearish/bull/bear stay forbidden (sentiment, not geometry); support/resistance stay
#     forbidden (inferred levels that are not drawn). We never add pattern names or concepts ourselves.
VOCAB_FORBIDDEN = frozenset("""
buy buys buying sell sells selling long longs short shorts entry entries exit exits target targets
profit profits profitable profitability winning winner trade trades trading trader signal signals setup setups
bullish bearish bull bear
outcome outcomes forward future predict predicts prediction forecast favorable favourable
volume indicator indicators rsi macd atr ema sma bollinger liquidity fvg bos choch support resistance
""".split())
VOCAB_FORBIDDEN_PHRASES = (r"stop[\s_]*loss", r"take[\s_]*profit")

PROMPT_FORBIDDEN = frozenset("""
trend trends trending uptrend downtrend breakout breakouts breakdown breakdowns sweep sweeps doji hammer engulfing
harami marubozu momentum pullback retracement reversal reversals continuation consolidation accumulation
distribution impulse correction
""".split()) | VOCAB_FORBIDDEN

D1_SYSTEM = (
    "You are a careful visual analyst. You are shown a single chart image made of candles. Describe ONLY what is "
    "visible in the image, using plain geometric language: the shape and sequence of the candles and the overall "
    "geometry of the price path from left to right. Do not use outside knowledge. Do not guess what happens after "
    "the right edge of the chart. Respond with one JSON object only."
)

D1_USER = """Describe the visual structure of this chart.

Return a JSON object with exactly these keys:
- "summary": 1-2 sentences describing the overall shape of the price path, left to right.
- "structure": a list of brief phrases describing consecutive visual phases, left to right.
- "shape_tags": up to 5 brief lowercase snake_case names describing the visual shapes you see (appearance only; reuse the same name when you see the same shape).
- "notable_features": a list of specific visual details, described by position in the chart.
"""

D2_SYSTEM = (
    "You organise descriptions of chart shapes into a small set of visually distinct families. You work only from "
    "the appearance that was described. Respond with one JSON object only."
)

D2_USER_TEMPLATE = """Below are shape names that were used to describe {n_charts} charts (with how often each name was used), followed by a sample of descriptions.

SHAPE NAMES (name: count)
{tag_table}

SAMPLE DESCRIPTIONS
{summaries}

Group the recurring shapes into between {k_min} and {k_max} families that look clearly different from each other.
Rules:
- Each family name is lowercase snake_case and describes appearance only.
- Use only plain geometric words that describe appearance.
- Each family has a one-sentence visual definition (at most 25 words) that a person could apply to a new chart by looking at it.
- Families must cover shapes that recur; ignore one-off names.
- Do not mention anything other than what is visible in a chart.

Return JSON: {{"families": [{{"name": <name>, "definition": <definition>, "member_names": [<shape names>]}}]}}"""

D3_SYSTEM = (
    "You are a careful visual analyst. You are shown a single chart image made of candles. Classify only what is "
    "visible, using ONLY the shape names provided. Do not use outside knowledge and do not guess what happens after "
    "the right edge. Respond with one JSON object only."
)

D3_USER_TEMPLATE = """Choose which of these shape names describe the chart's overall price path, left to right.

{lines}

Rules:
- Pick 1 to {max_tags} names that clearly apply, most prominent first.
- Use "{none}" alone if nothing fits well. Do not force a fit; do not invent names.

Return JSON: {{"tags": [<names>], "primary": <the most prominent name>}}"""

TEMPLATES = {"D1_SYSTEM": D1_SYSTEM, "D1_USER": D1_USER, "D2_SYSTEM": D2_SYSTEM, "D2_USER_TEMPLATE": D2_USER_TEMPLATE,
             "D3_SYSTEM": D3_SYSTEM, "D3_USER_TEMPLATE": D3_USER_TEMPLATE}


def template_hashes() -> dict[str, str]:
    return {k: hashlib.sha256(v.encode()).hexdigest() for k, v in TEMPLATES.items()}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def lint(text: str) -> list[str]:
    """VOCABULARY lint: forbidden words/phrases found in a family name or definition (snake_case split into words)."""
    low = text.lower()
    hits = {t for t in _tokens(low) if t in VOCAB_FORBIDDEN}
    hits |= {m.group(0).replace("_", " ") for pat in VOCAB_FORBIDDEN_PHRASES for m in re.finditer(pat, low)}
    return sorted(hits)


def lint_prompt(text: str) -> list[str]:
    """PROMPT lint (stricter): the prompt templates must not name technical-analysis concepts either."""
    return sorted({t for t in _tokens(text) if t in PROMPT_FORBIDDEN} | set(lint(text)))


def lint_templates() -> dict[str, list[str]]:
    """Lint every prompt template (placeholders are not words, so they never trigger)."""
    return {k: lint_prompt(v) for k, v in TEMPLATES.items()}


# --------------------------------------------------------------- D2 output validation -------------------------
NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


def validate_families(obj) -> tuple[list[dict] | None, list[str]]:
    """-> (families, problems). A vocabulary is accepted only if there are no problems."""
    probs: list[str] = []
    fams = obj.get("families") if isinstance(obj, dict) else None
    if not isinstance(fams, list):
        return None, ["missing 'families' list"]
    if not (params.VOCAB_MIN <= len(fams) <= params.VOCAB_MAX):
        probs.append(f"{len(fams)} families; need {params.VOCAB_MIN}-{params.VOCAB_MAX}")
    names, clean = set(), []
    for f in fams:
        n, d = str(f.get("name", "")).strip(), str(f.get("definition", "")).strip()
        if not NAME_RE.match(n):
            probs.append(f"bad name {n!r}")
        if n == params.NONE_TAG:
            probs.append("'none' is reserved")
        if n in names:
            probs.append(f"duplicate name {n!r}")
        names.add(n)
        if not d or len(d.split()) > 25:
            probs.append(f"definition of {n!r} empty or longer than 25 words")
        bad = lint(n + " " + d)
        if bad:
            probs.append(f"{n!r} uses forbidden words {bad}")
        clean.append({"name": n, "definition": d, "member_names": [str(m) for m in f.get("member_names", [])]})
    return (clean if not probs else None), probs


class Vocabulary:
    """Frozen families (+ the reserved `none`). Order is the discovery order; pass 2 reverses it."""

    def __init__(self, families: list[dict]):
        self.families = [{"name": f["name"], "definition": f["definition"]} for f in families]
        self.names = [f["name"] for f in self.families] + [params.NONE_TAG]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.families, sort_keys=True).encode()).hexdigest()

    def user_prompt(self, reverse: bool = False) -> str:
        fams = self.families[::-1] if reverse else self.families
        lines = "\n".join(f"- {f['name']}: {f['definition']}" for f in fams)
        lines += f"\n- {params.NONE_TAG}: no clear shape from this list applies (use alone)"
        return D3_USER_TEMPLATE.format(lines=lines, max_tags=params.MAX_TAGS, none=params.NONE_TAG)

    def validate_tags(self, obj):
        """-> (tags, primary, error). Unknown names are errors, never repaired."""
        if not isinstance(obj, dict) or not isinstance(obj.get("tags"), list):
            return None, None, "missing 'tags' list"
        tags = [str(t).strip() for t in obj["tags"]]
        if not tags or len(tags) > params.MAX_TAGS or len(set(tags)) != len(tags):
            return None, None, f"need 1-{params.MAX_TAGS} unique tags, got {tags}"
        bad = [t for t in tags if t not in self.names]
        if bad:
            return None, None, f"unknown tags: {bad}"
        if params.NONE_TAG in tags and len(tags) > 1:
            return None, None, "'none' must be used alone"
        primary = str(obj.get("primary", tags[0])).strip()
        return (tags, primary, None) if primary in tags else (None, None, f"primary {primary!r} not in tags")


RETRY_SUFFIX = ("\n\nYour previous answer was rejected for these reasons: {problems}\n"
                "Return a corrected JSON object that follows all the rules.")
