import json
import shutil

import pandas as pd
import pytest

from src.setups import params, sampling, verify_charts as vc
from tests.test_setups_sampling import series, small  # noqa: F401  (fixtures/helpers)


@pytest.fixture
def built(small, tmp_path, monkeypatch):                 # noqa: F811
    monkeypatch.setattr(params, "PER_STRATUM", 4)         # fewer, shorter: every test re-renders every chart
    monkeypatch.setattr(params, "DISCOVERY_END", (pd.Timestamp("2025-10-01T00:00:00Z") + pd.Timedelta(days=40)).isoformat())
    df = series(4500)
    meta, rows = sampling.build(df, tmp_path)
    return df, tmp_path, rows


def run(df, d, n, **kw):
    return vc.verify_charts(df, d, expected_n=n, future_every=kw.pop("future_every", 4), **kw)


def failed(res):
    return sorted(k for k, v in res.items() if not v["passed"])


def test_clean_build_passes_every_check(built):
    df, d, rows = built
    res = run(df, d, len(rows))
    assert failed(res) == [], {k: v for k, v in res.items() if not v["passed"]}
    assert {int(k.split("_")[0]) for k in res} == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12}      # 11 (dataset) is added by the CLI
    assert res["8_end_ts_and_byte_identical_rerender"]["detail"]["windows_rebuilt"] == len(rows)


def test_png_contains_no_metadata_beyond_the_minimum(built):
    _, d, rows = built
    kinds = [k for k, _ in vc.png_chunks((d / "charts" / rows[0]["chart"]).read_bytes())]
    assert kinds == ["IHDR", "pHYs", "IDAT", "IEND"] and set(kinds) <= vc.ALLOWED_CHUNKS


def test_one_changed_pixel_fails_loudly(built):
    df, d, rows = built
    f = d / "charts" / "S0003.png"
    good = f.read_bytes()
    f.write_bytes(good[:-30] + bytes([good[-30] ^ 1]) + good[-29:])
    bad = failed(run(df, d, len(rows)))
    assert "5_image_sha256_matches_record" in bad and "8_end_ts_and_byte_identical_rerender" in bad


def test_missing_extra_and_misnamed_charts_fail(built):
    df, d, rows = built
    (d / "charts" / "S0002.png").rename(d / "charts" / "renamed.png")
    bad = failed(run(df, d, len(rows)))
    assert {"1_png_count", "2_names_exactly_S0001_to_SN_once", "3_every_chart_maps_to_exactly_one_row",
            "4_every_row_maps_to_exactly_one_chart", "5_image_sha256_matches_record"} <= set(bad) or \
           {"2_names_exactly_S0001_to_SN_once", "4_every_row_maps_to_exactly_one_chart", "5_image_sha256_matches_record"} <= set(bad)
    (d / "charts" / "renamed.png").rename(d / "charts" / "S0002.png")
    shutil.copy(d / "charts" / "S0001.png", d / "charts" / "extra.png")
    bad = failed(run(df, d, len(rows)))
    assert "1_png_count" in bad and "2_names_exactly_S0001_to_SN_once" in bad and "3_every_chart_maps_to_exactly_one_row" in bad


def test_wrong_expected_count_fails(built):
    df, d, rows = built
    assert "1_png_count" in failed(run(df, d, len(rows) + 1))
    assert "1_png_count" in failed(run(df, d, len(rows) - 1))


def test_tampered_end_ts_fails_even_if_a_valid_candle_exists_there(built):
    df, d, rows = built
    jl = d / "windows_setups.jsonl"
    recs = [json.loads(l) for l in jl.read_text().splitlines()]
    recs[0]["end_ts"] = (pd.Timestamp(recs[0]["end_ts"]) + pd.Timedelta(minutes=15)).isoformat()   # a real candle, wrong window
    jl.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    bad = failed(run(df, d, len(rows)))
    assert "8_end_ts_and_byte_identical_rerender" in bad and "12_selection_send_order_and_metadata_unchanged" in bad


def test_end_ts_with_no_candle_fails(built):
    df, d, rows = built
    jl = d / "windows_setups.jsonl"
    recs = [json.loads(l) for l in jl.read_text().splitlines()]
    recs[1]["end_ts"] = "2030-01-01T00:00:00+00:00"
    jl.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    assert "8_end_ts_and_byte_identical_rerender" in failed(run(df, d, len(rows)))


def test_wrong_style_hash_in_a_row_or_the_metadata_fails(built):
    df, d, rows = built
    jl = d / "windows_setups.jsonl"
    recs = [json.loads(l) for l in jl.read_text().splitlines()]
    recs[0]["chart_style_sha256"] = "0" * 64
    jl.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    assert "6_single_chart_style" in failed(run(df, d, len(rows)))


def test_reordered_send_order_or_changed_metadata_fails(built):
    df, d, rows = built
    jl = d / "windows_setups.jsonl"
    recs = [json.loads(l) for l in jl.read_text().splitlines()]
    recs[0], recs[1] = recs[1], recs[0]                     # swap two records: chart ids no longer follow the seeded order
    jl.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    assert "12_selection_send_order_and_metadata_unchanged" in failed(run(df, d, len(rows)))


def test_metadata_change_fails(built):
    df, d, rows = built
    m = json.loads((d / "sample_meta.json").read_text())
    m["per_stratum"]["S1_directional"] += 1
    (d / "sample_meta.json").write_text(json.dumps(m))
    assert "12_selection_send_order_and_metadata_unchanged" in failed(run(df, d, len(rows)))


def test_a_chart_that_leaks_the_future_would_be_caught(built, monkeypatch):
    df, d, rows = built
    real = vc.build_window

    def leaky(cs, t, lookback):                              # simulate a renderer/window builder that sees one future candle
        w = real(cs, t, lookback)
        w.raw.iloc[-1, w.raw.columns.get_loc("close")] *= 1.0
        return w

    monkeypatch.setattr(vc, "build_window", leaky)
    assert failed(run(df, d, len(rows))) == []               # benign wrapper: still clean
    calls = {"n": 0}

    def future_peek(cs, t, lookback):
        calls["n"] += 1
        w = real(cs, t, lookback)
        if calls["n"] % 2 == 0:                              # the 'altered future' build differs from the real build
            w.raw.iloc[-1, w.raw.columns.get_loc("close")] *= 1.001
            w.norm.iloc[-1, w.norm.columns.get_loc("close")] *= 1.001
        return w

    monkeypatch.setattr(vc, "build_window", future_peek)
    assert "10_no_candle_after_end_ts_visible" in failed(run(df, d, len(rows), future_every=1))


def test_leaky_metadata_is_caught(built):
    df, d, rows = built
    f = d / "charts" / "S0001.png"
    data = f.read_bytes()
    i = data.index(b"IDAT") - 4                              # insert a text chunk with an identifying string before IDAT
    payload = b"Comment\x00BTCUSDT 15m 2025-09-02"
    import struct, zlib
    chunk = struct.pack(">I", len(payload)) + b"tEXt" + payload + struct.pack(">I", zlib.crc32(b"tEXt" + payload))
    f.write_bytes(data[:i] + chunk + data[i:])
    bad = failed(run(df, d, len(rows)))
    assert "7_no_leakage_in_names_metadata_bytes" in bad and "5_image_sha256_matches_record" in bad


def test_cli_exit_code_is_nonzero_on_any_failure(built, monkeypatch, tmp_path):
    df, d, rows = built
    from src.data import loader
    from src.setups import lock
    monkeypatch.setattr(lock, "require_design_lock", lambda c: {"dataset": {"sha256": "x", "bytes": 1}})
    monkeypatch.setattr(lock, "verify_database", lambda p: {"file": "research_binance.db", "bytes": 1, "sha256": "x"})
    monkeypatch.setattr(vc, "load_candles", lambda *a, **k: type("C", (), {"df": df})())
    out = tmp_path / "report.json"
    assert vc.main(["--confirm-design-sha", "x", "--run-dir", str(d), "--out", str(out)]) == 1     # expected_n (558) != this sample
    rep = json.loads(out.read_text())
    assert rep["all_passed"] is False and not rep["checks"]["1_png_count"]["passed"] and rep["checks"]["11_dataset_matches_f0_lock"]["passed"]
