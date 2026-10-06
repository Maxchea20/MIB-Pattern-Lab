import base64
import json

import pandas as pd
import pytest

import config
from src.charts.renderer import render_window
from src.charts.windows import build_window
from src.data.loader import CandleSet
from src.discovery import discover, prompts

L = 60
CUT = "2026-06-01T00:00:00Z"


@pytest.fixture
def cs_long(monkeypatch):
    from src.data.loader import build_candles
    from tests.conftest import make_ohlc
    start = int(pd.Timestamp("2026-05-30T00:00:00Z").timestamp() * 1000)
    raw = make_ohlc(1000, start_ms=start)                 # spans well past the cutoff
    monkeypatch.setattr(config, "DISCOVERY_END", CUT)
    return build_candles(raw, "BTC/USDT", "5m", "synthetic", as_of="2100-01-01")


class FakeDescriber:
    model = "fake"

    def __init__(self, fail_on=None):
        self.calls, self.fail_on = [], fail_on

    def describe(self, png):
        self.calls.append(png)
        if self.fail_on == len(self.calls):
            raise RuntimeError("boom")
        return {"text": json.dumps({"summary": "s", "structure": ["a"], "pattern_tags": ["t"],
                                    "notable_features": [], "clarity": 3}),
                "usage": {"prompt": 1, "completion": 1}, "model_served": "fake"}


def test_discovery_candles_cut_at_cutoff(cs_long):
    d = discover.discovery_candles(cs_long)
    assert d.df["ts"].max() < pd.Timestamp(CUT) and len(d.df) < len(cs_long.df)


def test_all_sampled_windows_inside_discovery_period(cs_long, tmp_path):
    fake = FakeDescriber()
    res = discover.run(cs_long, fake, tmp_path, count=8)
    assert len(res) == 8 and all(pd.Timestamp(r["end_ts"]) < pd.Timestamp(CUT) for r in res)


def test_request_contains_only_prompt_and_image(cs_long, tmp_path):
    w = build_window(cs_long, cs_long.df["ts"].iloc[100], L)
    png = render_window(w, tmp_path / "x.png").read_bytes()
    msgs = discover.build_messages(png)
    text = json.dumps([m["content"] if isinstance(m["content"], str) else
                       [p for p in m["content"] if p["type"] == "text"] for m in msgs])
    assert str(w.end_ts.year) not in text and "x.png" not in text and "BTC" not in text
    parts = msgs[1]["content"]
    assert [p["type"] for p in parts] == ["text", "image_url"]
    assert base64.b64decode(parts[1]["image_url"]["url"].split(",", 1)[1]) == png


def test_prompt_is_outcome_blind():
    blob = (prompts.SYSTEM_PROMPT + prompts.USER_PROMPT).lower()
    for word in ["buy", "sell", "profit", "favorable", "outcome", "trade", "long", "short",
                 "bullish", "bearish", "forecast", "predict the"]:
        assert word not in blob, word


def test_run_is_resumable_and_retries_errors(cs_long, tmp_path):
    f1 = FakeDescriber(fail_on=2)
    r1 = discover.run(cs_long, f1, tmp_path, count=4)
    assert sum(1 for r in r1 if r["error"]) == 1 and len(f1.calls) == 4
    f2 = FakeDescriber()
    r2 = discover.run(cs_long, f2, tmp_path, count=4)
    assert len(f2.calls) == 1 and all(r["error"] is None for r in r2)   # only the failed one redone
    rec = r2[0]
    assert rec["prompt_version"] == prompts.PROMPT_VERSION and len(rec["image_sha256"]) == 64
    assert discover.write_report(tmp_path, r2).exists()


def test_bad_json_recorded_not_crashing(cs_long, tmp_path):
    class Bad(FakeDescriber):
        def describe(self, png):
            return {"text": "not json", "usage": None}
    res = discover.run(cs_long, Bad(), tmp_path, count=2)
    assert all(r["parsed"] is None and "invalid JSON" in r["error"] for r in res)


def test_env_loader_does_not_override(tmp_path, monkeypatch):
    p = tmp_path / ".env"
    p.write_text("# c\nOPENAI_API_KEY=abc\nOTHER='x'\n")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OTHER", "keep")
    discover.load_env(p)
    import os
    assert os.environ["OPENAI_API_KEY"] == "abc" and os.environ["OTHER"] == "keep"


# ---- fixed scale / anonymised axes -------------------------------------------------------
from src.charts.renderer import compute_ylim, xtick_labels
from src.discovery import scale


def test_fixed_span_same_for_every_window(cs_long):
    a = build_window(cs_long, cs_long.df["ts"].iloc[100], L)
    b = build_window(cs_long, cs_long.df["ts"].iloc[700], L)
    st = {**config.CHART_STYLE, "y_span_pct": 8.0}
    for w in (a, b):
        lo, hi = compute_ylim(w.norm, st)
        assert hi - lo == pytest.approx(8.0)
        assert lo <= w.norm["low"].min() and hi >= w.norm["high"].max()   # window fits when range <= span


def test_span_from_discovery_period_only_and_eligibility(cs_long):
    d = discover.discovery_candles(cs_long)
    r = scale.window_ranges_pct(d.df, "5m", L)
    assert r.index.max() < pd.Timestamp(CUT)
    span = scale.choose_span(r)
    assert span >= r.quantile(0.99)
    assert (span / config.SPAN_STEP_PCT) == pytest.approx(round(span / config.SPAN_STEP_PCT))
    elig = scale.eligible_ends(r, span)
    assert 0 < len(elig) <= len(r) and (r.loc[elig] <= span).all()
    # tiny window is excluded from the sample, never clipped
    assert len(scale.eligible_ends(r, r.min() / 2)) == 0


def test_range_uses_only_window_data(cs_long):
    d = cs_long.df
    r1 = scale.window_ranges_pct(d, "5m", L)
    f = d.copy()
    f.loc[500:, ["open", "high", "low", "close"]] = 1e9          # change the future
    r2 = scale.window_ranges_pct(f, "5m", L)
    t = d["ts"].iloc[400]
    assert r1.loc[t] == r2.loc[t]


def test_relative_time_labels_hide_dates(cs_long):
    w = build_window(cs_long, cs_long.df["ts"].iloc[300], L)
    st = {**config.CHART_STYLE, **config.DISCOVERY_CHART_STYLE}
    labels = xtick_labels(w.norm, list(range(59, -1, -10))[::-1], st)
    assert labels[-1] == "T" and labels[0] == "T-50" and not any("-0" in x or ":" in x for x in labels)
    assert st["axis_labels"] == "pct"


def test_run_writes_scale_style_hash_and_tags_run(cs_long, tmp_path):
    res = discover.run(cs_long, FakeDescriber(), tmp_path, count=3)
    assert (tmp_path / "scale.json").exists()
    assert all(r["run"] == config.DISCOVERY_RUN and len(r["chart_style_sha256"]) == 64 for r in res)


def test_per_timeframe_cutoff_and_run_dir(cs_long, monkeypatch):
    monkeypatch.setattr(config, "DISCOVERY_END_BY_TF", {"1h": "2026-05-31T12:00:00Z"})
    assert config.discovery_end("1H") == "2026-05-31T12:00:00Z" and config.discovery_end("5m") == CUT
    from src.discovery.tagset import default_run_dir
    assert default_run_dir("1h").name.endswith("_cut20260531") and "cut" not in default_run_dir("5m").name
    cs1h = CandleSet(cs_long.df, "BTC/USDT", "1h", "x")
    d = discover.discovery_candles(cs1h)
    assert d.df["ts"].max() < pd.Timestamp("2026-05-31T12:00:00Z") and d.stats["discovery_cutoff"].startswith("2026-05-31T12")
