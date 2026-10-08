"""Fidelity audit of the C7 recognizer (pre-registration section 7). Outcome-blind: no return, future high/low, MFE, MAE, R or
hold-out candle is read anywhere in this module.

    python -m src.setups.fidelity prepare  --confirm-design-sha <12>      # DB only: cases, charts, recall list. NO API call
    python -m src.setups.fidelity dry-run  --confirm-design-sha <12>      # shows counts, the exact prompt, the cost cap. NO API call
    python -m src.setups.fidelity run      --confirm-design-sha <12>      # the ONLY step that calls the model (<= $1.00, hard stop)
    python -m src.setups.fidelity report                                  # precision / recall / verdict from files. No DB, no API

What the model sees: the frozen C7 definition text, one chart ending at the case's candle, and the fixed question. It never
sees the recognizer's classification, the case kind, a timestamp, a stratum or anything after the last candle.
Cases: up to 100 COUNTED C7 triggers (stratified like the Stage A sample) and up to 100 non-trigger candles (C7 not present and
no C7 trigger on the last two candles, same strata, spaced like the Stage A sample); deterministic (seed 12345).
UNCLEAR counts as not present. The thresholds (precision >= 70 %, recall >= 50 %, minimum evidence) are src.setups.audit's.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

import config
from src.charts.renderer import render_window
from src.charts.windows import build_window, valid_end_indices
from src.data.loader import CandleSet, load_candles
from src.discovery.discover import OpenAIDescriber, discovery_candles
from src.setups import audit, costlog, params, prompts, sampling, store
from src.setups import recognizer as rz

CAND_NAME = "bullish_breakout_from_right_edge_range"
CAND_KEY = "C7"
FID_DIR = config.ROOT / "results" / "setups" / "fidelity"
RECOG_DIR = config.ROOT / "results" / "setups" / "recognizer"
CASES = "audit_cases.jsonl"
JUDGEMENTS = "audit_judgements.jsonl"
COST = "cost_log.jsonl"
RECALL = "recall.json"
REPORT = "fidelity_report.json"
GAP_CANDLES = params.MIN_GAP_CANDLES      # spacing between non-trigger cases (as in the Stage A sample)


# ------------------------------------------------------------------------------------------- definition ----
def load_candidate(path: Path | None = None, name: str = CAND_NAME) -> dict:
    d = json.loads(Path(path or store.CANDIDATES_FILE).read_text(encoding="utf-8"))
    hit = [c for c in d["candidates"] if c["name"] == name]
    if len(hit) != 1:
        raise SystemExit(f"candidate {name} not found exactly once in the frozen candidates file")
    return hit[0]


def definition_text(c: dict) -> str:
    """The frozen wording the model is shown: context, conditions, presence rule, trigger, invalidation. NOT the name, the
    direction label, the supporting ids or any property of the recognizer."""
    lines = [f"Context: {c['context_definition']}", "Conditions, in order:"]
    lines += [f"{i}. {s}" for i, s in enumerate(c["conditions_sequence"], 1)]
    lines += [f"Presence: {c['presence_rule']}", f"Trigger event: {c['trigger']}", f"Ends when: {c['invalidation']}"]
    return "\n".join(lines)


def user_prompt(c: dict) -> str:
    return prompts.AUDIT_USER_TEMPLATE.replace("{DEFINITION}", definition_text(c))


# ---------------------------------------------------------------------------------------------- recognizer ---
def run_c7(ts, o, h, l, c, thr: dict):
    """-> (presence bool array for C7, raw C7 trigger indices, counted C7 trigger indices). Reads the committed recognizer."""
    n = len(c)
    presence = np.zeros(n, bool)

    def observe(t, ok, state):
        if state[CAND_KEY] is not None:
            presence[t] = True

    ev = [e for e in rz.recognize(ts, o, h, l, c, thr, on_state=observe) if e["cand"] == CAND_KEY]
    return presence, {e["trigger_idx"] for e in ev}, sorted(e["trigger_idx"] for e in ev if e["counted"])


def discovery_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Hold-out candles physically removed before anything else is computed."""
    cutoff = pd.Timestamp(params.DISCOVERY_END)
    return df[df["ts"] < cutoff].reset_index(drop=True)


# ------------------------------------------------------------------------------------------- selection -----
def stratum_of(d: pd.DataFrame, i: int, cuts: dict) -> str:
    f = sampling.chart_features(d[["open", "high", "low", "close"]].iloc[i - params.LOOKBACK + 1: i + 1])
    row = pd.DataFrame([f], columns=list(sampling.FEATURES))
    return sampling.first_stratum(sampling.stratum_masks(row, cuts), 0)


def select_spaced(pool: list[tuple[int, str]], n: int, seed: int, gap: int = 0) -> list[tuple[int, str]]:
    """Deterministic, stratified round-robin pick of up to n (index, stratum); picks are >= gap candles apart."""
    rng = random.Random(seed)
    groups: dict[str, list[int]] = {}
    for i, s in sorted(pool):
        groups.setdefault(s, []).append(i)
    for s in sorted(groups):
        rng.shuffle(groups[s])
    out: list[tuple[int, str]] = []
    taken: list[int] = []
    names = sorted(groups)
    while len(out) < n and any(groups[k] for k in names):
        for k in names:
            while groups[k] and len(out) < n:
                i = groups[k].pop()
                if gap and any(abs(i - t) < gap for t in taken):
                    continue
                taken.append(i)
                out.append((i, k))
                break
    return out


def plan_cases(d: pd.DataFrame, thr: dict, cuts: dict, n_trig: int = params.AUDIT_N_TRIGGER,
               n_non: int = params.AUDIT_N_NONTRIGGER, seed: int = params.SEED_AUDIT) -> dict:
    """d = DISCOVERY candles only. Returns the case plan and the C7 recognizer arrays (reused for recall)."""
    ts = d["ts"].dt.as_unit("ns").astype("int64").to_numpy()
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    presence, raw, counted = run_c7(ts, o, h, l, c, thr)
    valid = valid_end_indices(d, params.TIMEFRAME, params.LOOKBACK)
    trig_pool = [(i, stratum_of(d, i, cuts)) for i in counted]
    non_pool = [(int(i), stratum_of(d, int(i), cuts)) for i in valid
                if not presence[i] and i not in raw and (i - 1) not in raw]
    trig = select_spaced(trig_pool, n_trig, seed)
    non = select_spaced(non_pool, n_non, seed + 1, gap=GAP_CANDLES)
    cases = [{"kind": "trigger", "idx": i, "stratum": s} for i, s in trig] + \
            [{"kind": "non_trigger", "idx": i, "stratum": s} for i, s in non]
    random.Random(seed + 2).shuffle(cases)                          # neutral order, kinds interleaved
    for n, cs_ in enumerate(cases, 1):
        cs_["case_id"] = f"A{n:04d}"
        cs_["end_ts"] = d["ts"].iloc[cs_["idx"]].isoformat()
    return {"cases": cases, "pools": {"counted_triggers": len(counted), "non_trigger_candidates": len(non_pool)},
            "presence": presence, "raw_triggers": raw, "counted": counted}


# -------------------------------------------------------------------------------------------------- recall ---
def recall_for(d: pd.DataFrame, stage_a_rows: list[dict], supporting_ids, presence, raw_triggers) -> dict:
    """E_K = Stage A ACTIONABLE_NOW charts cited as supporting. A chart is recognized if C7 is PRESENT at its end T or TRIGGERED
    (raw trigger, before any lockout) on T or the candle before it. Candles <= T only."""
    eligible = audit.eligible_supporting_charts(stage_a_rows, supporting_ids)
    end = {r["chart_id"]: pd.Timestamp(r["end_ts"]) for r in stage_a_rows if r.get("error") is None}
    ts = d["ts"]
    recognized, per = [], {}
    for cid in eligible:
        pos = int(ts.searchsorted(end[cid]))
        if pos >= len(ts) or ts.iloc[pos] != end[cid]:
            per[cid] = {"end_ts": end[cid].isoformat(), "present": None, "triggered": None, "recognized": False, "note": "candle not found"}
            continue
        pres = bool(presence[pos])
        trig = any((pos - k) in raw_triggers for k in range(params.RECALL_WINDOW_CANDLES))
        per[cid] = {"end_ts": end[cid].isoformat(), "present": pres, "triggered": trig, "recognized": pres or trig}
        if pres or trig:
            recognized.append(cid)
    return {"eligible": eligible, "recognized": recognized, "per_chart": per,
            "gate": audit.recall_gate(eligible, set(recognized))}


# -------------------------------------------------------------------------------------------- rendering -----
def render_cases(d: pd.DataFrame, cases: list[dict], out_dir: Path) -> list[dict]:
    cs = CandleSet(d, params.SYMBOL, params.TIMEFRAME, "setups")
    style_sha = sampling.style_sha()
    rows = []
    (out_dir / "charts").mkdir(parents=True, exist_ok=True)
    for c in cases:
        w = build_window(cs, pd.Timestamp(c["end_ts"]), params.LOOKBACK)          # 96 closed gap-free candles ending at T
        path = out_dir / "charts" / f"{c['case_id']}.png"
        render_window(w, path, sampling.chart_style())
        rows.append({**c, "chart": path.name, "image_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "chart_style_sha256": style_sha})
    return rows


# ---------------------------------------------------------------------------------------------- cost log ---
class AuditCostLog(costlog.CostLog):
    """Audit-step log in its own file (the F1-frozen discovery log is never written). The total cap still counts the
    earlier discovery spend, read-only."""

    def __init__(self, path: Path, baseline_path: Path):
        super().__init__(path)
        self.baseline = float(sum(r["estimated_cost_usd"] for r in store.load_jsonl(baseline_path)))

    def spent(self, step: str | None = None) -> float:
        return super().spent(step) + (self.baseline if step is None else 0.0)


# ------------------------------------------------------------------------------------------------ report ---
def build_report(cases: list[dict], judgements: list[dict], recall: dict, frequency: dict | None) -> dict:
    prec = audit.precision_from_judgements(judgements)
    good = store.clean_rows(judgements, key="case_id")
    non = [r for r in good.values() if r["kind"] == "non_trigger"]
    trig = [r for r in good.values() if r["kind"] == "trigger"]
    by_stratum: dict[str, dict] = {}
    stratum = {c["case_id"]: c["stratum"] for c in cases}
    for r in trig:
        s = by_stratum.setdefault(stratum.get(r["case_id"], "?"), {"audited": 0, "present": 0})
        s["audited"] += 1
        s["present"] += r["judgement"] == "PRESENT"
    verdict = audit.fidelity_verdict(prec, recall["gate"])
    return {
        "candidate": CAND_NAME, "verdict": verdict,
        "cases_planned": {"trigger": sum(c["kind"] == "trigger" for c in cases), "non_trigger": sum(c["kind"] == "non_trigger" for c in cases)},
        "judged": {"trigger": len(trig), "non_trigger": len(non), "errors_unjudged": len(cases) - len(good)},
        "trigger_judgement_counts": {k: sum(r["judgement"] == k for r in trig) for k in prompts.AUDIT_JUDGEMENTS},
        "non_trigger_judgement_counts": {k: sum(r["judgement"] == k for r in non) for k in prompts.AUDIT_JUDGEMENTS},
        "non_trigger_present_share": (sum(r["judgement"] == "PRESENT" for r in non) / len(non)) if non else None,
        "trigger_precision_by_stratum": by_stratum,
        "recall": {"eligible": len(recall["eligible"]), "recognized": len(recall["recognized"])},
        "frequency_reference": (frequency or {}).get("candidates", {}).get(CAND_KEY),
        "note": ("Descriptive and outcome-blind. UNCLEAR counts as not present. The non-trigger present share is reported for context and "
                 "is not a gate. Fidelity is not profitability."),
    }


def _png(out_dir: Path, row: dict) -> bytes:
    data = (out_dir / "charts" / row["chart"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != row["image_sha256"]:
        raise SystemExit(f"chart {row['chart']} does not match the hash in {CASES}")
    return data


def run_audit(out_dir: Path, describer, definition: str, log: costlog.CostLog) -> list[dict]:
    rows = store.load_jsonl(out_dir / CASES)
    cases = [{"case_id": r["case_id"], "kind": r["kind"], "png": _png(out_dir, r)} for r in rows]
    return audit.run_judgements(cases, describer, definition, out_dir / JUDGEMENTS, log)


# ------------------------------------------------------------------------------------------------- main ----
def _load_inputs(db):
    from src.setups import lock
    lock.verify_database(db)
    cs = discovery_candles(load_candles(db, params.SYMBOL, params.TIMEFRAME), end=params.DISCOVERY_END)
    derived = json.loads((RECOG_DIR / "derived_parameters.json").read_bytes())
    meta = json.loads((store.RUN_DIR / "sample_meta.json").read_text(encoding="utf-8"))
    return cs.df, rz.thresholds_from(derived), meta["feature_cutpoints_terciles"], derived


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("step", choices=["prepare", "dry-run", "run", "report"])
    ap.add_argument("--confirm-design-sha")
    ap.add_argument("--db", default=None)
    ap.add_argument("--out", default=str(FID_DIR))
    a = ap.parse_args(argv)
    out = Path(a.out)
    from src.setups import lock
    cand = load_candidate()
    if a.step != "report":
        lock.require_f1(a.confirm_design_sha)
    if a.step == "prepare":
        if (out / CASES).exists():
            raise SystemExit(f"{out / CASES} exists: the case list is fixed once made. Refusing to rebuild.")
        db = Path(a.db) if a.db else lock.CANONICAL_DB
        d, thr, cuts, derived = _load_inputs(db)
        plan = plan_cases(d, thr, cuts)
        rows = render_cases(d, plan["cases"], out)
        stage_a = store.load_jsonl(store.RUN_DIR / "stage_a.jsonl")
        recall = recall_for(d, stage_a, cand["supporting_ids"], plan["presence"], plan["raw_triggers"])
        recall["recognizer_sha256"] = hashlib.sha256(Path(rz.__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        recall["derived_parameters_sha256"] = hashlib.sha256((RECOG_DIR / "derived_parameters.json").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        recall["pools"] = plan["pools"]
        (out / RECALL).write_text(json.dumps(recall, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (out / CASES).write_text("\n".join(json.dumps({k: v for k, v in r.items()}) for r in rows) + "\n", encoding="utf-8")
        print(json.dumps({"pools": plan["pools"], "cases": len(rows), "recall_eligible": len(recall["eligible"]),
                          "recall_recognized": len(recall["recognized"])}, indent=2))
        return 0
    rows = store.load_jsonl(out / CASES)
    if a.step == "dry-run":
        by = pd.DataFrame(rows).groupby(["kind", "stratum"]).size() if rows else "none"
        print(f"cases: {len(rows)}\n{by}\n--- system ---\n{prompts.AUDIT_SYSTEM}\n--- user (with the frozen definition) ---\n{user_prompt(cand)}")
        log = AuditCostLog(out / COST, store.RUN_DIR / "cost_log.jsonl")
        print(f"\nstep cap ${params.CAP_AUDIT:.2f}; total cap ${params.CAP_TOTAL:.2f}; already spent ${log.spent():.4f}; model {params.MODEL}; "
              f"the model is shown the chart and the text above only")
        return 0
    if a.step == "run":
        log = AuditCostLog(out / COST, store.RUN_DIR / "cost_log.jsonl")
        run_audit(out, OpenAIDescriber(params.MODEL, system=prompts.AUDIT_SYSTEM, user=user_prompt(cand)), definition_text(cand), log)
        print(f"audit spent ${log.spent('audit'):.4f}; total ${log.spent():.4f}")
        return 0
    recall = json.loads((out / RECALL).read_text(encoding="utf-8"))
    freq_p = RECOG_DIR / "frequency_report.json"
    freq = json.loads(freq_p.read_text(encoding="utf-8")) if freq_p.exists() else None
    rep = build_report(rows, store.load_jsonl(out / JUDGEMENTS), recall, freq)
    (out / REPORT).write_text(json.dumps(rep, indent=2, sort_keys=True, default=float) + "\n", encoding="utf-8")
    print(json.dumps(rep, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
