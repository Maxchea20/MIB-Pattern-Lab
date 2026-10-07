"""Fidelity audit and recognizer sanity rules (pre-registration section 7). Outcome-blind: nothing here reads a return.

The audit asks whether a deterministic recognizer represents what the AI described. It is NOT profitability. The rules
below are pure functions so that the minimum-evidence requirements are mechanically enforced:

* precision >= 70 %, evaluated ONLY if at least 10 recognizer trigger cases were audited;
* recall   >= 50 %, evaluated ONLY if at least 10 eligible supporting ACTIONABLE_NOW charts exist;
* otherwise the candidate is "insufficient evidence -> NOT CODEABLE FAITHFULLY" (a tiny sample can never pass);
* a recognizer that triggers on < 0.2 % or > 10 % of discovery candles is NOT CODEABLE / NOT SELECTIVE.

An UNCLEAR judgement counts as NOT present (conservative: it can never raise precision).
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import pandas as pd

from src.discovery.discover import parse_response
from src.setups import costlog, params, prompts, store

INSUFFICIENT = "insufficient evidence -> NOT CODEABLE FAITHFULLY"


def precision_gate(n_audited_trigger: int, n_judged_present: int) -> dict:
    if n_audited_trigger < params.MIN_TRIGGER_CASES:
        return {"evaluated": False, "n": n_audited_trigger, "value": None, "passed": False, "classification": INSUFFICIENT}
    v = n_judged_present / n_audited_trigger
    return {"evaluated": True, "n": n_audited_trigger, "value": v, "passed": v >= params.PRECISION_MIN, "classification": None}


def eligible_supporting_charts(stage_a_rows, supporting_ids) -> list[str]:
    """E_K: Stage A charts with status ACTIONABLE_NOW whose chart id is in the candidate's supporting_ids."""
    sup = set(supporting_ids)
    return sorted({r["chart_id"] for r in stage_a_rows if r.get("error") is None and r["parsed"]["status"] == "ACTIONABLE_NOW"
                   and r["chart_id"] in sup})


def recall_gate(eligible: list[str], recognized: set[str]) -> dict:
    """recognized = chart ids on which the frozen recognizer of the candidate is PRESENT, or TRIGGERED within the last
    RECALL_WINDOW_CANDLES candles, at the chart's end T (evaluated on candles <= T only)."""
    den = len(eligible)
    if den < params.MIN_RECALL_CHARTS:
        return {"evaluated": False, "denominator": den, "numerator": None, "value": None, "passed": False,
                "classification": INSUFFICIENT}
    num = len(set(eligible) & set(recognized))
    return {"evaluated": True, "denominator": den, "numerator": num, "value": num / den, "passed": num / den >= params.RECALL_MIN,
            "classification": None}


def fidelity_verdict(precision: dict, recall: dict) -> dict:
    ok = precision["passed"] and recall["passed"]
    insufficient = (not precision["evaluated"]) or (not recall["evaluated"])
    return {"precision": precision, "recall": recall, "passed": ok,
            "classification": INSUFFICIENT if insufficient else (None if ok else "NOT CODEABLE FAITHFULLY")}


def frequency_gate(n_triggers: int, n_candles: int) -> dict:
    share = n_triggers / n_candles if n_candles else 0.0
    ok = params.FREQ_MIN <= share <= params.FREQ_MAX
    return {"triggers": n_triggers, "candles": n_candles, "share": share, "passed": ok,
            "classification": None if ok else "NOT CODEABLE / NOT SELECTIVE"}


def select_cases(pool: list[tuple[str, str]], n: int, seed: int = params.SEED_AUDIT) -> list[str]:
    """Stratified, seeded, deterministic pick of up to n case ids from pool = [(case_id, stratum)]: round-robin over the
    strata so that every stratum is represented as evenly as possible (like the Stage A sample)."""
    rng = random.Random(seed)
    groups: dict[str, list[str]] = {}
    for cid, st in sorted(pool):
        groups.setdefault(st, []).append(cid)
    for g in groups.values():
        rng.shuffle(g)
    out, names = [], sorted(groups)
    while len(out) < n and any(groups[k] for k in names):
        for k in names:
            if groups[k] and len(out) < n:
                out.append(groups[k].pop())
    return out


def run_judgements(cases: list[dict], describer, definition: str, out_path: Path, log: costlog.CostLog) -> list[dict]:
    """cases: [{"case_id", "kind": "trigger"|"non_trigger", "png": bytes}]. One call per case, resumable, cost-capped.
    The model sees the frozen definition text and the chart only."""
    user = prompts.AUDIT_USER_TEMPLATE.replace("{DEFINITION}", definition)
    done = store.clean_rows(store.load_jsonl(out_path), key="case_id")
    for c in cases:
        if c["case_id"] in done:
            continue
        if not log.allow("audit"):
            print(log.stop_message("audit"))
            break
        rec = {"case_id": c["case_id"], "kind": c["kind"], "step": "audit", "model": getattr(describer, "model", None),
               "prompt_user_sha256": hashlib.sha256(user.encode()).hexdigest(), "judgement": None, "reason": None,
               "raw": None, "usage": None, "error": None, "requested_at": pd.Timestamp.now(tz="UTC").isoformat()}
        try:
            r = describer.describe(c["png"])
            rec["raw"], rec["usage"] = r["text"], r.get("usage")
            obj, err = parse_response(r["text"])
            if err is None:
                problems = prompts.validate_audit(obj)
                err = "; ".join(problems) if problems else None
            if err is None:
                rec["judgement"], rec["reason"] = obj["judgement"], obj["reason"]
            rec["error"] = err
        except Exception as e:
            rec["error"] = f"{type(e).__name__}: {e}"
        store.append_jsonl(out_path, rec)
        log.record("audit", rec["model"], rec["usage"])
    return store.load_jsonl(out_path)


def precision_from_judgements(rows: list[dict]) -> dict:
    """Precision over the audited TRIGGER cases (errors are not audited cases); UNCLEAR counts as not present."""
    t = [r for r in store.clean_rows(rows, key="case_id").values() if r["kind"] == "trigger"]
    return precision_gate(len(t), sum(1 for r in t if r["judgement"] == "PRESENT"))
