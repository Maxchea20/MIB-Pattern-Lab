"""Discovery prompt. Chart-only, outcome-blind.

The model sees ONE clean chart image and this text. It is never told the timestamp, the
file name, what happened afterwards, or what counts as "good". Bump PROMPT_VERSION on ANY edit.
"""
import hashlib

PROMPT_VERSION = "discovery-v1"

SYSTEM_PROMPT = (
    "You are a careful visual analyst. You are shown a single candlestick chart image. "
    "Describe ONLY what is visible in the image: the shape and sequence of the candles and the "
    "overall geometry of the price path from left to right. Do not use outside knowledge. "
    "Do not guess what happens after the right edge of the chart. Respond with one JSON object only."
)

USER_PROMPT = """Describe the visual structure of this chart.

Return a JSON object with exactly these keys:
- "summary": 1-2 sentences describing the overall shape of the price path, left to right.
- "structure": a list of brief phrases describing consecutive visual phases, left to right.
- "pattern_tags": up to 5 brief lowercase snake_case names for the visual shapes you see
  (your own names; reuse the same name when you see the same shape).
- "notable_features": a list of specific visual details (e.g. unusually large candles, extended wicks,
  clusters of small candles, sharp reversals), described by position in the chart.
- "clarity": integer 1-5, how clear and distinct the overall shape is (1 = noisy, 5 = very clear).
"""

PROMPT_SHA256 = hashlib.sha256((SYSTEM_PROMPT + "\n" + USER_PROMPT).encode()).hexdigest()
