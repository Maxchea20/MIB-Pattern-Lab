"""Descriptive 'rediscovery' check: on the Stage A charts that were cited as supporting a setup and rated ACTIONABLE_NOW, did the frozen
detector see the setup (PRESENT at the chart's end candle) or FIRE on the last two candles? Reported per setup; it is not a gate and
changes nothing. Uses candles <= the chart's end only."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.brain import detectors as det
from src.setups import store


def supporting_ids(candidates_path: Path | None = None, attempts_path: Path | None = None) -> dict[str, list[str]]:
    d = json.loads(Path(candidates_path or store.CANDIDATES_FILE).read_text(encoding="utf-8"))
    by_name = {c["name"]: c["supporting_ids"] for c in d["candidates"]}
    out = {sid: list(by_name[n]) for sid, n in det.NAMES.items() if n in by_name}
    p = Path(attempts_path or (store.RUN_DIR / "stage_b_attempts.jsonl"))
    for r in store.load_jsonl(p):
        if r.get("kind") == "final" and r.get("accepted") and r.get("candidates"):
            for c in r["candidates"]:
                if c.get("name") == det.NAMES["S9"]:
                    out["S9"] = list(c.get("supporting_ids", []))
    return out


def check(df: pd.DataFrame, stage_a_rows: list[dict], support: dict[str, list[str]], fires: list[dict], thr: dict) -> dict:
    ts = df["ts"]
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    rows = {r["chart_id"]: r for r in stage_a_rows if r.get("error") is None and r["parsed"]["status"] == "ACTIONABLE_NOW"}
    fired = {(f["setup_id"], f["trigger_idx"]) for f in fires}
    out = {}
    for sid in det.IDS:
        ids = sorted(i for i in support.get(sid, []) if i in rows)
        per, pres_n, fire_n = {}, 0, 0
        for cid in ids:
            pos = int(ts.searchsorted(pd.Timestamp(rows[cid]["end_ts"])))
            if pos >= len(ts) or pos < det.WINDOW - 1:
                continue
            present = sid in det.evaluate(h[pos - 95:pos + 1], l[pos - 95:pos + 1], c[pos - 95:pos + 1], thr)
            f = any((sid, pos - k) in fired for k in range(2))
            per[cid] = {"end_ts": rows[cid]["end_ts"], "present_at_end": present, "fired_on_last_two_candles": f}
            pres_n += present
            fire_n += f
        out[sid] = {"cited_actionable_now_charts": len(per), "present_at_end": pres_n, "fired_on_last_two_candles": fire_n,
                    "either": sum(1 for v in per.values() if v["present_at_end"] or v["fired_on_last_two_candles"]), "per_chart": per}
    return out
