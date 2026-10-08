"""Run the frozen Setup Brain over the canonical Binance BTC/USDT 15m candles and write what it saw.

    python -m src.brain.scan --confirm-design-sha <12>      # needs the DB; refuses unless the detector freeze verifies

Live-like replay (one completed candle at a time) and an independent chronological batch scan must agree exactly, and the seven
Experiment 3 detectors must agree with the Experiment 3 recognizer's raw triggers; any difference aborts the run as a bug.
Outputs: every FIRE with descriptive forward observation, invalidations, overlap, rediscovery check, examples and a plain report.
No pass/fail, no gate, no fill: a FIRE is a signal and every forward number is measured from the analytical reference price.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import config
from src.brain import detectors as det
from src.brain import examples as ex
from src.brain import forward, freeze, rediscovery, replay
from src.brain.brain import SetupBrain
from src.setups import params, store
from src.setups import recognizer as rz

OUT = Path(config.ROOT) / "results" / "brain"
SCAN_MARKER = "scan_started.json"


def load_thresholds(root: Path = Path(config.ROOT)) -> dict:
    derived = json.loads((root / "results/setups/recognizer/derived_parameters.json").read_bytes())
    s5 = json.loads((root / "results/brain/derived_s5.json").read_bytes())
    return det.with_s5_threshold(rz.thresholds_from(derived), s5)


def cross_check_experiment3(ts, o, h, l, c, thr, fires: list[dict]) -> dict:
    """The seven imported detectors must fire on exactly the candles on which the Experiment 3 recognizer logged a raw trigger."""
    old = {(k, e["trigger_idx"]) for e in rz.recognize(ts, o, h, l, c, thr) for k in [e["cand"]]}
    inv = {v: k for k, v in det.RZ_KEY.items()}
    new = {(det.RZ_KEY[f["setup_id"]], f["trigger_idx"]) for f in fires if f["setup_id"] in det.RZ_KEY}
    return {"experiment3_raw_triggers": len(old), "brain_fires_same_setups": len(new), "identical": old == new,
            "only_in_experiment3": sorted(old - new)[:10], "only_in_brain": sorted(new - old)[:10]}


def run_scan(df: pd.DataFrame, thr: dict, version: str, out_dir: Path, cutoff: str = params.DISCOVERY_END, stage_a_rows=None,
             support=None, examples: bool = True) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = df["ts"].dt.as_unit("ns").astype("int64").to_numpy()
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    cutoff_ns = int(pd.Timestamp(cutoff).as_unit("ns").value)
    card = replay.dataset_card(df)
    brain = SetupBrain(thr, version)
    events = replay.replay(replay.candle_stream(df), brain, out_dir / "replay_log.jsonl")           # live-like: one candle at a time
    batch = replay.batch_scan(ts, o, h, l, c, thr, version)                                           # independent chronological scan
    equal = replay.comparable(events) == replay.comparable(batch)
    if not equal:
        (out_dir / "MISMATCH_replay_vs_batch.json").write_text(json.dumps({"replay": len(events), "batch": len(batch)}))
        raise SystemExit("BUG: incremental replay and batch scan differ. The run is aborted; the detectors are not edited to hide it.")
    fires = [e for e in events if e["event"] == "FIRE"]
    invs = [e for e in events if e["event"] == "INVALIDATED"]
    x3 = cross_check_experiment3(ts, o, h, l, c, thr, fires)
    if not x3["identical"]:
        (out_dir / "MISMATCH_vs_experiment3.json").write_text(json.dumps(x3, indent=2))
        raise SystemExit("BUG: the imported detectors disagree with the Experiment 3 recognizer. Aborted; nothing was edited.")
    rows = forward.observe(fires, invs, ts, o, h, l, c, cutoff_ns)
    summary = forward.summarize(rows)
    ov = forward.overlap(rows, brain.presence_pairs, brain.presence_candles)
    (out_dir / "fires.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + ("\n" if rows else ""), encoding="utf-8")
    redisc = rediscovery.check(df, stage_a_rows, support, fires, thr) if stage_a_rows is not None and support else None
    idx = ex.make_examples(rows, ts, o, h, l, c, out_dir / "examples") if examples else []
    result = {"detector_version_sha256": version, "dataset_card": card, "cutoff": cutoff, "events": len(events), "fires": len(fires),
              "invalidations": len(invs), "replay_equals_batch": equal, "cross_check_experiment3": x3,
              "rejected_incomplete_candles": brain.rejected_incomplete, "gaps_seen_by_brain": brain.gaps,
              "evaluated_candles": brain.evaluated_candles, "presence_candles": brain.presence_candles,
              "summary": summary, "overlap": ov, "rediscovery": redisc, "examples": idx,
              "final_input_digest": brain.digest.hexdigest(), "interpretations": det.INTERPRETATIONS}
    (out_dir / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True, default=float) + "\n", encoding="utf-8")
    (out_dir / "SETUP_BRAIN_REPORT.md").write_text(render_report(result, rows), encoding="utf-8")
    return result


def _f(v, nd=3):
    return "-" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:.{nd}f}"


def render_report(r: dict, rows: list[dict]) -> str:
    S = r["summary"]
    L = ["## SETUP BRAIN RESULT", "", f"Detector version `{r['detector_version_sha256']}`. A FIRE is a signal, not a trade or a fill.", "",
         "| Setup | Fires | Long | Short | In-sample | Unseen |", "|---|---:|---:|---:|---:|---:|"]
    for sid in det.IDS:
        a = S[sid]["ALL"]
        L.append(f"| {sid} | {a['fires']} | {a['long']} | {a['short']} | {S[sid]['IN_SAMPLE']['fires']} | {S[sid]['UNSEEN']['fires']} |")
    L += ["", f"Total fires: **{r['fires']}** (invalidation events: {r['invalidations']}). Replay == batch scan: **{r['replay_equals_batch']}**. "
          f"Imported detectors identical to the Experiment 3 recognizer's raw triggers: **{r['cross_check_experiment3']['identical']}**.", "",
          "### Earliest / latest fire", "", "| Setup | Earliest | Latest |", "|---|---|---|"]
    for sid in det.IDS:
        t = [x["trigger_ts"] for x in rows if x["setup_id"] == sid]
        L.append(f"| {sid} | {min(t) if t else '-'} | {max(t) if t else '-'} |")
    L += ["", "### Overlap (same-candle fires | presence Jaccard)", "", "| pair | same-candle fires | fire Jaccard | presence both | presence Jaccard |", "|---|---:|---:|---:|---:|"]
    for k, v in r["overlap"].items():
        if v["same_candle_fires"] or v["presence_both"]:
            L.append(f"| {k} | {v['same_candle_fires']} | {_f(v['fire_jaccard'])} | {v['presence_both']} | {_f(v['presence_jaccard'])} |")
    L += ["", "### Forward descriptive statistics (direction-signed % from the analytical reference price = next candle open; NOT fills)", "",
          "| Setup | Period | Rows | mean ret h1 | mean ret h6 | mean ret h24 | median MFE | median MAE | share ret h6 > 0 |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for sid in det.IDS:
        for p in ("IN_SAMPLE", "UNSEEN"):
            a = S[sid][p]
            fr = a["forward_return_pct"]
            L.append(f"| {sid} | {p} | {a['forward_rows_used']} | {_f(fr['h1'].get('mean'))} | {_f(fr['h6'].get('mean'))} | {_f(fr['h24'].get('mean'))} | "
                     f"{_f(a['mfe_pct'].get('median'))} | {_f(a['mae_pct'].get('median'))} | {_f(fr['h6'].get('share_positive'))} |")
    L += ["", "### Consecutive fires and invalidation", "", "| Setup | fires | first-in-streak | max streak position | invalidated within 24 | never invalidated by data end | median candles to invalidation |", "|---|---:|---:|---:|---:|---:|---:|"]
    for sid in det.IDS:
        a = S[sid]["ALL"]
        L.append(f"| {sid} | {a['fires']} | {a['first_in_streak']} | {a['max_streak_position']} | {a['invalidated_within_24']} | {a['never_invalidated_by_end_of_data']} | {_f(a['candles_to_invalidation'].get('median'), 1)} |")
    if r["rediscovery"]:
        L += ["", "### Rediscovery check (descriptive): charts the AI cited for the setup and rated ACTIONABLE_NOW", "", "| Setup | cited charts | PRESENT at end | FIRED on last 2 candles | either |", "|---|---:|---:|---:|---:|"]
        for sid in det.IDS:
            q = r["rediscovery"][sid]
            L.append(f"| {sid} | {q['cited_actionable_now_charts']} | {q['present_at_end']} | {q['fired_on_last_two_candles']} | {q['either']} |")
    L += ["", "### Examples (charts in `examples/`)", ""]
    for e in r["examples"]:
        L.append(f"* **{e['setup_id']} #{e['n']}** `{e['chart']}` - {e['trigger_ts']} ({e['period']}). {e['condition']} After: {json.dumps(e['after'], default=float)}")
    L += ["", "### Translation notes and data quality", "", f"Dataset: {json.dumps(r['dataset_card'])}.",
          f"Incomplete candles refused by the brain: {r['rejected_incomplete_candles']}; gaps seen: {r['gaps_seen_by_brain']}."]
    for k, v in r["interpretations"].items():
        L.append(f"* {k}: {v}")
    L += ["", "No pass/fail is stated: nothing here is gated. Forward return, future high/low, MFE and MAE are descriptive statistics of the price series and are not "
          "trading results; where the order of two events inside one 15m candle is unknown it is flagged, never assumed."]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=None)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    out = Path(a.out)
    from src.data.loader import load_candles
    from src.setups import lock
    rec = freeze.verify()                                       # detectors and thresholds must still be the frozen ones
    db = Path(a.db) if a.db else lock.CANONICAL_DB
    db_meta = lock.verify_database(db)
    marker = out / SCAN_MARKER
    if marker.exists():
        prev = json.loads(marker.read_text(encoding="utf-8"))
        if prev["detector_version_sha256"] != rec["detector_version_sha256"]:
            raise SystemExit("a scan already started with a different detector version: no detector change after the first scan")
    out.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"detector_version_sha256": rec["detector_version_sha256"], "database": db_meta}, indent=2), encoding="utf-8")
    cs = load_candles(db, params.SYMBOL, params.TIMEFRAME)      # closed, valid, de-duplicated; the still-forming candle is dropped
    thr = load_thresholds()
    stage_a = store.load_jsonl(store.RUN_DIR / "stage_a.jsonl")
    res = run_scan(cs.df, thr, rec["detector_version_sha256"], out, stage_a_rows=stage_a, support=rediscovery.supporting_ids())
    res_card = {k: res[k] for k in ("fires", "invalidations", "replay_equals_batch")}
    print(json.dumps(res_card, indent=2))
    print((out / "SETUP_BRAIN_REPORT.md").read_text(encoding="utf-8")[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
