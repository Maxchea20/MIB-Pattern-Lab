"""One scan of Setup Brain v2 (S1 v2 + the unchanged v1 S2-S9) over the canonical Binance 15m candles into results/brain_v2/.

    python -m src.brain.scan_v2

Refuses unless the v1 freeze AND the v2 freeze verify. Replay == batch and the S2-S9 fires == the v1 fires must hold exactly or the run aborts.
Descriptive output only; no fill, no trade; bad recognitions are reported, not patched.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import config
from src.brain import detectors_v2 as d2
from src.brain import freeze, freeze_v2, rediscovery, s1v2_report, scan
from src.brain.brain_v2 import SetupBrainV2
from src.setups import params, store

OUT = Path(config.ROOT) / "results" / "brain_v2"


def thresholds_v2(root: Path = Path(config.ROOT)) -> dict:
    derived = json.loads((root / "results/brain_v2/derived_s1v2.json").read_bytes())
    return d2.with_s1v2_thresholds(scan.load_thresholds(root), derived)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=None)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    out = Path(a.out)
    import pandas as pd

    from src.data.loader import load_candles
    from src.setups import lock
    freeze.verify()
    rec = freeze_v2.verify()
    db = Path(a.db) if a.db else lock.CANONICAL_DB
    meta = lock.verify_database(db)
    marker = out / scan.SCAN_MARKER
    if marker.exists() and json.loads(marker.read_text(encoding="utf-8"))["detector_version_sha256"] != rec["detector_version_sha256"]:
        raise SystemExit("a v2 scan already started with a different detector version: no detector change after the first scan")
    out.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"detector_version_sha256": rec["detector_version_sha256"], "database": meta}, indent=2), encoding="utf-8")
    df = load_candles(db, params.SYMBOL, params.TIMEFRAME).df
    thr = thresholds_v2()
    stage_a = store.load_jsonl(store.RUN_DIR / "stage_a.jsonl")
    res = scan.run_scan(df, thr, rec["detector_version_sha256"], out, stage_a_rows=stage_a, support=rediscovery.supporting_ids(),
                        brain_factory=lambda t, v: SetupBrainV2(t, v, evaluate=d2.evaluate), evaluate_fn=d2.evaluate, cross_skip=("S1",))
    rows = [json.loads(x) for x in (out / "fires.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    v1 = [json.loads(x) for x in (Path(config.ROOT) / "results/brain/fires.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    cmp_ = s1v2_report.compare_v1_v2(v1, rows)
    if not cmp_["s2_s9_identical"]:
        (out / "MISMATCH_vs_v1.json").write_text(json.dumps(cmp_, indent=2))
        raise SystemExit("BUG: S2-S9 fires differ from v1. Aborted; nothing was edited.")
    ts = df["ts"].dt.as_unit("ns").astype("int64").to_numpy()
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    cited = s1v2_report.cited12(df, stage_a, rediscovery.supporting_ids()["S1"], thr, rows)
    ex = s1v2_report.unseen_examples(rows, {r["trigger_idx"] for r in v1 if r["setup_id"] == "S1"}, ts, o, h, l, c, thr, out / "examples_s1v2")
    (out / "s1v2_report.json").write_text(json.dumps({"compare": cmp_, "cited12": cited, "examples": ex}, indent=2, default=float), encoding="utf-8")
    (out / "S1_V2_REPORT.md").write_text(s1v2_report.render(cmp_, cited, ex), encoding="utf-8")
    print(json.dumps({"fires": res["fires"], "replay_equals_batch": res["replay_equals_batch"], "s2_s9_identical_to_v1": cmp_["s2_s9_identical"], "s1": cmp_["s1"]}, indent=1))
    print((out / "S1_V2_REPORT.md").read_text(encoding="utf-8")[:5000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
