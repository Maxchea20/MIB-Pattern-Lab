"""Token -> USD accounting for the hard spending cap."""
from __future__ import annotations

import config


def call_cost(usage: dict | None, price: dict | None = None) -> float:
    """USD for one call from recorded usage ({'prompt','completion'}). Cached-token discounts are
    ignored on purpose (conservative). Unknown usage counts as 0 (the call may still have billed)."""
    if not usage:
        return 0.0
    p = price or config.OPENAI_PRICE_USD_PER_M
    return ((usage.get("prompt") or 0) * p["input"] + (usage.get("completion") or 0) * p["output"]) / 1e6


def total_cost(rows: list[dict], price: dict | None = None) -> float:
    return sum(call_cost(r.get("usage"), price) for r in rows)
