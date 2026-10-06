import hashlib
import json

import pytest

import config
from src.discovery import vocab, vocab_report
from src.discovery.retag import load_rows, run_retag
from tests.test_discovery import FakeDescriber, cs_long  # noqa: F401  (fixture helpers)


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


def test_audit_features_use_window_only_and_are_sane(cs_long):
    from src.charts.windows import build_window as bw
    from src.discovery import audit
    T = cs_long.df["ts"].iloc[300]
    w = bw(cs_long, T, 60)
    f = audit.window_features(w.raw)
    fut = cs_long.df.copy()
    fut.loc[fut["ts"] > T, ["open", "high", "low", "close"]] = 1e9
    assert audit.window_features(bw(type(cs_long)(fut, "BTC/USDT", "5m", "x"), T, 60).raw) == f
    assert 0 <= f["eff"] <= 1 and 0 <= f["hi_pos"] <= 1 and f["range_pct"] > 0
    tags = {T.isoformat(): ["drift_up"], cs_long.df["ts"].iloc[500].isoformat(): ["sideways_range"]}
    rows = []
    for ts, tg in tags.items():
        for p in (1, 2):
            rows.append({"end_ts": ts, "pass": p, "tags": tg, "error": None})
    st = audit.stable_tags(rows)
    assert st == {k: v for k, v in tags.items()}
    table = audit.summarise(audit.build_table(cs_long, st))
    assert table["tag"].tolist()[0] == "ALL WINDOWS" and set(table["tag"]) >= {"drift_up", "sideways_range"}


def test_pick_spacing_scales_with_timeframe_and_run_dirs():
    import numpy as np
    import pandas as pd
    from src.discovery.tagset import default_run_dir, pick
    idx = pd.date_range("2026-01-01", periods=20000, freq="15min", tz="UTC")
    r = pd.Series(np.random.default_rng(2).uniform(0.2, 3, 20000), index=idx)
    ts = sorted(t for t, _ in pick(r, idx, 60, "stratified", timeframe="15m"))
    assert len(ts) == 60 and min(b - x for x, b in zip(ts, ts[1:])) >= pd.Timedelta(minutes=15 * 60)
    assert default_run_dir("5m").name == config.TAGSET_RUN
    assert default_run_dir("15m").name == config.TAGSET_RUN + "_15m" != default_run_dir("1h").name
