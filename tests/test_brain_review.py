import json

import numpy as np
import pandas as pd
import pytest

from src.brain import detectors as det
from src.brain import review, scan
from tests.test_brain_brain import arrays
from tests.test_brain_detectors import THR
from tests.test_setups_recognizer import walk


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    c = walk(5000, 17)
    ts, o, h, l, cc = arrays(c)
    df = pd.DataFrame({"ts": pd.to_datetime(ts, unit="ns", utc=True), "open": o, "high": h, "low": l, "close": cc})
    cutoff = pd.Timestamp(int(ts[3500]), tz="UTC").isoformat()
    out = tmp_path_factory.mktemp("scan")
    res = scan.run_scan(df, THR, "v", out, cutoff=cutoff, examples=False)
    rows = [json.loads(x) for x in (out / "fires.jsonl").read_text().splitlines()]
    return df, rows, int(pd.Timestamp(cutoff).as_unit("ns").value), res


def test_hand_check_of_fires_agrees_with_the_brain_on_every_check(run):
    df, rows, _, _ = run
    checks = review.fire_checks(df, rows, THR)
    n = 0
    for sid, sheets in checks.items():
        for s in sheets:
            n += 1
            assert all(s["checks"].values()), (sid, s["fire_id"], s["checks"])
    assert n >= 20 and sum(1 for s in checks.values() if s) >= 6


def test_baseline_uses_the_same_measurement_as_fires_and_is_split_by_period(run):
    df, rows, cutoff_ns, _ = run
    b = review.baseline(df, rows, cutoff_ns)
    assert set(b["baseline"]) == {"up/IN_SAMPLE", "up/UNSEEN", "down/IN_SAMPLE", "down/UNSEEN"}
    up, down = b["baseline"]["up/IN_SAMPLE"], b["baseline"]["down/IN_SAMPLE"]
    assert up["h6"]["mean"] == pytest.approx(-down["h6"]["mean"], abs=1e-9)          # direction-signed: mirror images
    assert up["n"] > 1000 and b["setups"]
    k = next(iter(b["setups"]))
    assert "h6" in b["setups"][k] and "volatility_matched_baseline_mean" in b["setups"][k]["h6"]


def test_cited_review_reports_failing_conditions_without_changing_anything(run):
    df, rows, _, res = run
    ts = df["ts"]
    stage_a = [{"chart_id": f"S{i:04d}", "end_ts": ts.iloc[300 + 40 * i].isoformat(), "error": None,
                "parsed": {"status": "ACTIONABLE_NOW", "visible_summary": "x", "context": "c", "location": "l", "development": "d", "trigger": "t", "direction": "up"}} for i in range(30)]
    support = {sid: [r["chart_id"] for r in stage_a] for sid in det.IDS}
    out = review.cited_review(df, stage_a, support, rows, THR)
    assert all(out[s]["n"] == 30 for s in det.IDS)
    for sid in det.IDS:
        for it in out[sid]["charts"]:
            assert it["present_at_T"] == (sid in det.evaluate(*review._win(df, int(df["ts"].searchsorted(pd.Timestamp(it["end_ts"])))), THR))
    txt = review.render(out, review.fire_checks(df, rows, THR), review.baseline(df, rows, int(pd.Timestamp(res["cutoff"]).as_unit("ns").value)))
    assert set(txt) == {"cited_review.md", "fire_checks.md", "baseline_comparison.md"}
    assert " 0 MISMATCH" in txt["fire_checks.md"]
