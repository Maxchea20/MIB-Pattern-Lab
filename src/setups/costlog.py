"""Hard-capped AI cost log (pre-registration section 11).

Every call is logged with: model, step, call number, input tokens, output tokens, estimated cost, cumulative cost.
A call is NOT started when cumulative cost + the estimate for that call would exceed the step cap or the total cap;
there is no automatic continuation and no way to raise a cap from the command line. The estimate for the next call
is COST_SAFETY x the largest call seen so far in the step (a fixed first-call estimate before any call is measured).
The log file is append-only and is the source of truth for the cumulative total across stages and re-runs.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.discovery import cost as _cost
from src.setups import params, store


class CostLog:
    def __init__(self, path: Path, caps: dict | None = None, total_cap: float | None = None, price: dict | None = None):
        self.path = Path(path)
        self.caps = dict(params.CAPS if caps is None else caps)
        self.total_cap = params.CAP_TOTAL if total_cap is None else total_cap
        self.price = price

    def rows(self, step: str | None = None) -> list[dict]:
        r = store.load_jsonl(self.path)
        return [x for x in r if step is None or x["step"] == step]

    def spent(self, step: str | None = None) -> float:
        return float(sum(r["estimated_cost_usd"] for r in self.rows(step)))

    def estimate(self, step: str) -> float:
        costs = [r["estimated_cost_usd"] for r in self.rows(step)]
        return params.COST_SAFETY * max(costs) if costs else params.FIRST_CALL_ESTIMATE_USD[step]

    def allow(self, step: str) -> bool:
        est = self.estimate(step)
        return (self.spent(step) + est <= self.caps[step]) and (self.spent() + est <= self.total_cap)

    def record(self, step: str, model: str | None, usage: dict | None) -> dict:
        usage = usage or {}
        c = _cost.call_cost(usage, self.price)
        n = len(self.rows(step)) + 1
        row = {"step": step, "call_number": n, "model": model, "input_tokens": usage.get("prompt"),
               "output_tokens": usage.get("completion"), "estimated_cost_usd": round(c, 6),
               "cumulative_step_usd": round(self.spent(step) + c, 6), "cumulative_total_usd": round(self.spent() + c, 6),
               "logged_at": pd.Timestamp.now(tz="UTC").isoformat()}
        store.append_jsonl(self.path, row)
        return row

    def stop_message(self, step: str) -> str:
        return (f"COST STOP: {step} spent ${self.spent(step):.3f} of ${self.caps[step]:.2f}; total ${self.spent():.3f} of "
                f"${self.total_cap:.2f}. No automatic continuation: a further call needs a new written decision.")
