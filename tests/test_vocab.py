import hashlib
import json

import pytest

import config
from src.discovery import vocab, vocab_report
from src.discovery.retag import load_rows, run_retag
from tests.test_discovery import FakeDescriber  # noqa: F401  (fixture helpers)


def _png(tmp_path, name, content):
    (tmp_path / "charts").mkdir(exist_ok=True)
    (tmp_path / "charts" / name).write_bytes(content)
    return hashlib.sha256(content).hexdigest()


@pytest.fixture
def run_dir(tmp_path):
    rows = []
    for i in range(6):
        name = f"c{i}.png"
        sha = _png(tmp_path, name, f"png{i}".encode())
        rows.append({"end_ts": f"2026-01-0{i + 1}T00:00:00+00:00", "chart": name, "image_sha256": sha,
                     "error": None, "parsed": {}})
    (tmp_path / "descriptions.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return tmp_path


class Tagger:
    model = "fake"

    def __init__(self, plan):             # plan: callable(png_bytes, call_no) -> dict
        self.plan, self.n = plan, 0

    def describe(self, png):
        self.n += 1
        return {"text": json.dumps(self.plan(png, self.n)), "usage": None}


def test_vocab_is_outcome_blind_and_unique():
    blob = (vocab.RETAG_SYSTEM + vocab.retag_user() + vocab.retag_user(True)).lower()
    for w in ["buy", "sell", "profit", "favorable", "outcome", "trade", "long", "short", "bullish",
              "bearish", "forecast", "predict the"]:
        assert w not in blob, w
    assert len(set(vocab.NAMES)) == len(vocab.NAMES) and vocab.NAMES[-1] == vocab.NONE_TAG


def test_reverse_order_changes_prompt_not_vocab():
    assert vocab.retag_user(False) != vocab.retag_user(True)
    assert sorted(n for n, _ in vocab.ordered_vocab(True)) == sorted(vocab.NAMES)
    assert vocab.ordered_vocab(True)[-1][0] == vocab.NONE_TAG


@pytest.mark.parametrize("obj,ok", [
    ({"tags": ["sharp_drop"], "primary": "sharp_drop"}, True),
    ({"tags": ["sharp_drop", "v_reversal"]}, True),
    ({"tags": ["sharp_drop_ish"]}, False),                      # unknown name
    ({"tags": ["none", "sharp_drop"]}, False),                  # none must be alone
    ({"tags": ["sharp_drop"], "primary": "rounded_top"}, False),
    ({"tags": []}, False),
    ({"tags": ["a", "b", "c", "d"]}, False),
    ({"nope": 1}, False),
])
def test_validate_tags(obj, ok):
    tags, primary, err = vocab.validate_tags(obj)
    assert (err is None) == ok


def test_retag_resumable_and_rejects_unknown_tags(run_dir):
    bad_once = Tagger(lambda png, n: {"tags": ["made_up"]} if n == 2 else {"tags": ["sideways_range"]})
    rows = run_retag(run_dir, bad_once, passes=1)
    assert sum(1 for r in rows if r["error"]) == 1 and len(rows) == 6
    good = Tagger(lambda png, n: {"tags": ["sideways_range"]})
    run_retag(run_dir, good, passes=1)
    assert good.n == 1                                          # only the failed chart is redone


def test_retag_refuses_changed_image(run_dir):
    (run_dir / "charts" / "c0.png").write_bytes(b"tampered")
    t = Tagger(lambda png, n: {"tags": ["sideways_range"]})
    rows = run_retag(run_dir, t, passes=1)
    assert [r for r in rows if "does not match" in (r["error"] or "")] and t.n == 5


def test_stable_tags_and_recurrence(run_dir):
    def plan(png, n):                     # call order (chart-outer): c0p1 c0p2 c1p1 c1p2 ...
        i, pas = (n - 1) // 2, (n - 1) % 2 + 1
        if i < 4:
            return {"tags": ["sideways_range"]}                # always agrees -> recurring
        if i == 4:
            return {"tags": ["sharp_drop"] if pas == 1 else ["v_reversal"]}   # passes disagree -> unstable
        return {"tags": ["rounded_top"]}                       # only 1 chart -> below support
    run_retag(run_dir, Tagger(plan), passes=2)
    res = vocab_report.analyse(load_rows(run_dir / "retags.jsonl"), 2)
    c = res["counts"]
    assert res["charts"] == 6 and res["support_needed"] == 3
    assert c["sideways_range"]["stable_charts"] == 4 and c["sideways_range"]["recurring"]
    assert c["sharp_drop"]["stable_charts"] == 0 and c["v_reversal"]["stable_charts"] == 0
    assert c["rounded_top"]["stable_charts"] == 1 and not c["rounded_top"]["recurring"]
    assert res["primary_agreement"] == pytest.approx(5 / 6, abs=1e-3) and res["charts_with_no_stable_tag"] == 1
    assert vocab_report.write_report(run_dir, res).exists()


def test_budget_stop_leaves_no_half_tagged_charts(run_dir):
    class Costly(Tagger):
        def describe(self, png):
            r = super().describe(png)
            r["usage"] = {"prompt": 100_000, "completion": 0}          # $0.075 per call at default prices
            return r
    t = Costly(lambda png, n: {"tags": ["sideways_range"]})
    rows = run_retag(run_dir, t, passes=2, budget_usd=0.40)
    per_chart = {}
    for r in rows:
        per_chart.setdefault(r["end_ts"], set()).add(r["pass"])
    assert 0 < len(per_chart) < 6 and all(v == {1, 2} for v in per_chart.values())
    from src.discovery import cost
    assert cost.total_cost(rows) <= 0.40
    assert cost.call_cost({"prompt": 1_000_000, "completion": 1_000_000}) == pytest.approx(5.25)


def test_stratified_pick_balanced_deterministic_and_unique():
    import numpy as np
    import pandas as pd
    from src.discovery.tagset import pick
    idx = pd.date_range("2026-01-01", periods=20000, freq="5min", tz="UTC")
    r = pd.Series(np.random.default_rng(1).uniform(0.2, 3, 20000), index=idx)
    a = pick(r, idx, 100, "stratified")
    assert a == pick(r, idx, 100, "stratified") and len(a) == 100 and len({t for t, _ in a}) == 100
    assert [s for _, s in a].count("Q4_active") == 25 and [s for _, s in a].count("Q1_quiet") == 25
    q1 = [r.loc[t] for t, s in a if s == "Q1_quiet"]; q4 = [r.loc[t] for t, s in a if s == "Q4_active"]
    assert max(q1) < min(q4)
    ts = sorted(t for t, _ in a)
    assert min(b - x for x, b in zip(ts, ts[1:])) >= pd.Timedelta(minutes=300)    # windows never overlap
    ev = pick(r, idx, 50, "even")
    assert len(ev) == 50
    # clustered high-range region cannot produce overlapping picks
    r2 = pd.Series(np.where(np.arange(20000) < 300, 5.0, 0.3), index=idx)
    c = sorted(t for t, _ in pick(r2, idx, 40, "stratified"))
    assert min(b - x for x, b in zip(c, c[1:])) >= pd.Timedelta(minutes=300)
    with pytest.raises(ValueError):
        pick(r, idx, 5, "bogus")
