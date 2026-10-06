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
