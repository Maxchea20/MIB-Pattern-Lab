"""Reporting for the one S1 v2 scan: v1 vs v2, the 12 cited charts at T..T-6, and ~10 unseen-period fires drawn for inspection.
Descriptive only. Bad recognitions are listed, never patched; no detector, threshold or rule is changed here."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.brain import detectors as det
from src.brain import detectors_v2 as d2
from src.brain import examples as exm
from src.brain import s1_v2

SAME_KEYS = ("fire_id", "setup_id", "direction", "trigger_idx", "operative_level", "presence_len", "presence_start_ts", "streak_position", "invalidation_rules")


def _key(r):
    return tuple(json.dumps(r[k], sort_keys=True, default=float) for k in SAME_KEYS)


def compare_v1_v2(v1: list[dict], v2: list[dict]) -> dict:
    out = {"s2_s9_identical": True, "per_setup": {}}
    for sid in det.IDS:
        a = sorted((_key(r) for r in v1 if r["setup_id"] == sid))
        b = sorted((_key(r) for r in v2 if r["setup_id"] == sid))
        out["per_setup"][sid] = {"v1": len(a), "v2": len(b), "identical": a == b}
        if sid != "S1" and a != b:
            out["s2_s9_identical"] = False
    s1a = {r["trigger_idx"] for r in v1 if r["setup_id"] == "S1"}
    s1b = {r["trigger_idx"] for r in v2 if r["setup_id"] == "S1"}
    out["s1"] = {"v1_fires": len(s1a), "v2_fires": len(s1b), "same_candle": len(s1a & s1b), "v1_only": len(s1a - s1b), "v2_only": len(s1b - s1a),
                 "jaccard": len(s1a & s1b) / len(s1a | s1b) if (s1a | s1b) else 0.0,
                 "v1_by_period": {p: sum(1 for r in v1 if r["setup_id"] == "S1" and r["period"] == p) for p in ("IN_SAMPLE", "UNSEEN")},
                 "v2_by_period": {p: sum(1 for r in v2 if r["setup_id"] == "S1" and r["period"] == p) for p in ("IN_SAMPLE", "UNSEEN")}}
    return out


def cited12(df: pd.DataFrame, stage_a: list[dict], support_s1: list[str], thr: dict, v2: list[dict], lookback: int = 6) -> list[dict]:
    rows = {r["chart_id"]: r for r in stage_a if r.get("error") is None and r["parsed"]["status"] == "ACTIONABLE_NOW"}
    fired = {r["trigger_idx"] for r in v2 if r["setup_id"] == "S1"}
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    out = []
    for cid in sorted(i for i in support_s1 if i in rows):
        pos = int(df["ts"].searchsorted(pd.Timestamp(rows[cid]["end_ts"])))
        steps = []
        for k in range(lookback + 1):
            i = pos - k
            if i < 95:
                steps.append({"k": k, "present": False, "fired": False, "first_failure": "not enough history"})
                continue
            e = s1_v2.explain_s1_v2(h[i - 95:i + 1], l[i - 95:i + 1], c[i - 95:i + 1], thr)
            steps.append({"k": k, "present": e["present"], "fired": i in fired,
                          "first_failure": next((x["condition"] for x in e["conditions"] if not x["ok"]), None)})
        out.append({"chart_id": cid, "end_ts": rows[cid]["end_ts"], "steps": steps,
                    "fired_any_T_to_T_minus_6": any(s["fired"] for s in steps), "present_any": any(s["present"] for s in steps)})
    return out


def unseen_examples(rows: list[dict], v1_idx: set, ts, o, h, l, c, thr: dict, out_dir: Path, n: int = 10) -> list[dict]:
    pool = [r for r in rows if r["setup_id"] == "S1" and r["period"] == "UNSEEN" and r["streak_position"] == 0]
    pick = [pool[i] for i in sorted({int(x) for x in np.linspace(0, len(pool) - 1, min(n, len(pool))).round()})] if pool else []
    out = []
    for k, f in enumerate(pick, 1):
        t = f["trigger_idx"]
        p = exm.draw(f, ts, o, h, l, c, out_dir / f"S1v2_unseen_{k:02d}.png")
        e = s1_v2.explain_s1_v2(h[t - 96:t], l[t - 96:t], c[t - 96:t], thr)            # window ending on the previous candle (presence)
        out.append({"n": k, "chart": p.name, "fire_id": f["fire_id"], "trigger_ts": f["trigger_ts"], "also_a_v1_fire": t in v1_idx,
                    "condition": exm.condition_text(f), "previous_candle_conditions": e["conditions"]})
    return out


def render(cmp_: dict, cited: list[dict], ex: list[dict]) -> str:
    L = ["# S1 v2 scan report (S1 only; S2-S9 are the v1 functions)", "", "Descriptive. Bad recognitions are to be listed by the reviewer, not patched. No fill, no trade.", "",
         "## v1 vs v2", "", f"S2-S9 fires identical to v1: **{cmp_['s2_s9_identical']}**", "", "| setup | v1 fires | v2 fires | identical |", "|---|---:|---:|---|"]
    L += [f"| {s} | {v['v1']} | {v['v2']} | {v['identical']} |" for s, v in cmp_["per_setup"].items()]
    s = cmp_["s1"]
    L += ["", f"S1: v1 {s['v1_fires']} fires, v2 {s['v2_fires']}; same candle {s['same_candle']}; v1 only {s['v1_only']}; v2 only {s['v2_only']}; Jaccard {s['jaccard']:.3f}.",
          f"By period: v1 {s['v1_by_period']}, v2 {s['v2_by_period']}.", "", "## The 12 cited charts, v2 at T .. T-6 (a consistency check, not a recall target)", "",
          "| chart | end | fired in T..T-6 | present in T..T-6 | per candle (k: P=present F=fired .=neither; failing condition) |", "|---|---|---|---|---|"]
    for c in cited:
        cells = " ".join(f"{x['k']}:{'P' if x['present'] else '.'}{'F' if x['fired'] else ''}" for x in c["steps"])
        L.append(f"| {c['chart_id']} | {c['end_ts']} | {c['fired_any_T_to_T_minus_6']} | {c['present_any']} | {cells}; at T: {c['steps'][0]['first_failure']} |")
    L += ["", "## Ten unseen-period v2 fires for inspection (evenly spaced, deterministic; first fire of each run)", ""]
    for e in ex:
        L += [f"### {e['n']}. {e['fire_id']} {e['trigger_ts']} (also a v1 fire: {e['also_a_v1_fire']})", f"![{e['chart']}](examples_s1v2/{e['chart']})", "", e["condition"], "",
              "| previous-candle condition | ok | detail |", "|---|---|---|"] + [f"| {k['condition']} | {'ok' if k['ok'] else 'NO'} | {k['detail']} |" for k in e["previous_candle_conditions"]] + [""]
    return "\n".join(L) + "\n"
