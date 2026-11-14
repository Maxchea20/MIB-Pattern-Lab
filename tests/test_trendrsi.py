"""Written-rule tests on constructed data only. No market data, no network, no order, no fill."""
import ast
import csv
import gzip
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

import config
from src.trendrsi import freeze, indicators as ind, params as P, run as runmod, signals as sg, study
from tests import policy_guard

ROOT = Path(config.ROOT)


def base(n=160):
    o = np.full(n, 100.0); c = o.copy(); h = np.full(n, 100.5); l = np.full(n, 99.5)
    return o, h, l, c


def test_rsi_matches_a_hand_computed_wilder_example_and_is_causal():
    r = ind.rsi_wilder([1, 2, 3, 2, 3], n=3)
    assert np.isnan(r[:3]).all() and r[3] == pytest.approx(66.6667, abs=1e-3) and r[4] == pytest.approx(77.7778, abs=1e-3)
    assert ind.rsi_wilder(np.arange(1, 40.0))[-1] == 100.0
    x = np.random.default_rng(1).normal(0, 1, 200).cumsum() + 100
    y = x.copy(); y[150:] = 5
    assert np.allclose(ind.rsi_wilder(x)[:150], ind.rsi_wilder(y)[:150], equal_nan=True)


def test_ema_recurrence():
    e = ind.ema([10, 20, 30], 3)
    assert e[0] == 10 and e[1] == pytest.approx(15) and e[2] == pytest.approx(22.5)


def test_higher_timeframe_values_are_used_only_after_that_candle_has_closed():
    step4 = 4 * 3_600_000
    open4 = np.arange(0, 10 * step4, step4)
    close4 = np.linspace(100, 90, 10)
    p4 = ind.htf_pack(open4, close4, 3, 1, step4)
    p1 = ind.htf_pack(np.arange(0, 10) * 86_400_000, np.linspace(100, 90, 10), 3, 1, 86_400_000)
    ts15_close = np.array([5 * step4 - 1, 5 * step4, 5 * step4 + 900_000])
    k = np.searchsorted(open4 + step4, ts15_close, side="right") - 1
    assert list(k) == [3, 4, 4]                                              # the candle closing exactly at 5*step4 is usable only from that close on
    bear_before, _ = ind.htf_bias(np.array([1.0]), p4, p1)
    assert not bear_before[0]                                                # nothing closed yet: no bias


def test_swings_are_known_only_k_candles_after_they_form():
    o, h, l, c = base(60)
    l[20] = 98.0
    sh, sl = ind.swings(h, l)
    assert sl[20] and sl.sum() == 1


def short_case(stop_hit=False, time_stop=False, rsi_exit=True):
    n = 260
    o, h, l, c = base(n)
    l[10] = 98.0                                      # confirmed swing low (known at candle 13)
    rsi = np.full(n, 50.0)
    rsi[20] = 70.0                                    # armed: almost overbought while the bias is bear
    h[22] = 105.0                                     # the bounce high = the risk level
    c[30], l[30], o[31] = 97.0, 96.5, 97.0            # CHoCH: a close below the swing low 98 -> signal at 30; reference = open of 31
    if stop_hit:
        h[33] = 105.2
    if rsi_exit:
        rsi[35] = 30.0
        o[36] = 95.0
    bias = np.ones(n, bool)
    valid = np.ones(n, bool)
    return o, h, l, c, rsi, bias, valid


def test_short_signal_risk_level_reference_and_rsi_exit_with_costs_in_R():
    o, h, l, c, rsi, bias, valid = short_case()
    sigs = sg.find_signals(o, h, l, c, rsi, bias, ~bias, valid)
    assert len(sigs) == 1 and (sigs[0]["side"], sigs[0]["t"], sigs[0]["arm_idx"], sigs[0]["risk_level"]) == ("short", 30, 20, 105.0)
    r = sg.outcome(sigs[0], o, h, l, c, rsi, valid)
    assert r["status"] == "OK" and r["exit_reason"] == "rsi" and r["ref_idx"] == 31 and r["ref_px"] == 97.0 and r["exit_ref"] == 95.0
    assert r["gross_R"] == pytest.approx((97.0 - 95.0) / (105.0 - 97.0))
    assert r["net_R_slip0.01"] == pytest.approx(0.25 - 2 * 0.05 / 100 * 97.0 / 8.0)
    assert r["net_R_slip0.0"] > r["net_R_slip0.01"] > r["net_R_slip0.03"]


def test_risk_level_reached_exits_at_the_level_and_is_a_loss_of_one_R():
    o, h, l, c, rsi, bias, valid = short_case(stop_hit=True, rsi_exit=False)
    r = sg.outcome(sg.find_signals(o, h, l, c, rsi, bias, ~bias, valid)[0], o, h, l, c, rsi, valid)
    assert r["exit_reason"] == "risk_level" and r["exit_idx"] == 33 and r["gross_R"] == pytest.approx(-1.0) and r["mae_R"] >= 1.0


def test_time_stop_closes_at_the_next_open_after_96_candles():
    o, h, l, c, rsi, bias, valid = short_case(rsi_exit=False)
    r = sg.outcome(sg.find_signals(o, h, l, c, rsi, bias, ~bias, valid)[0], o, h, l, c, rsi, valid)
    assert r["exit_reason"] == "time" and r["exit_idx"] == 31 + P.TIME_STOP_BARS and r["bars_held"] == P.TIME_STOP_BARS


def test_long_is_the_mirror_image():
    o, h, l, c = base(260)
    h[10] = 102.0
    rsi = np.full(260, 50.0); rsi[20] = 30.0
    l[22] = 95.0
    c[30], h[30], o[31] = 103.0, 103.5, 103.0
    rsi[35] = 70.0; o[36] = 105.0
    bias = np.ones(260, bool)
    sigs = sg.find_signals(o, h, l, c, rsi, ~bias, bias, np.ones(260, bool))
    assert len(sigs) == 1 and sigs[0]["side"] == "long" and sigs[0]["risk_level"] == 95.0
    r = sg.outcome(sigs[0], o, h, l, c, rsi, np.ones(260, bool))
    assert r["gross_R"] == pytest.approx((105.0 - 103.0) / (103.0 - 95.0))


def test_no_setup_without_the_bias_and_disarm_when_the_move_has_already_happened_or_expired():
    o, h, l, c, rsi, bias, valid = short_case()
    assert sg.find_signals(o, h, l, c, rsi, np.zeros(260, bool), np.zeros(260, bool), valid) == []
    rsi2 = rsi.copy(); rsi2[25] = 30.0                                          # almost oversold before the CHoCH: the setup is over
    assert sg.find_signals(o, h, l, c, rsi2, bias, ~bias, valid) == []
    b2 = bias.copy(); b2[24] = False                                            # the bias was lost in between
    assert sg.find_signals(o, h, l, c, rsi, b2, ~b2, valid) == []
    o3, h3, l3, c3, rsi3, bias3, valid3 = short_case()
    c3[30], l3[30] = 100.0, 99.5; c3[130], l3[130], o3[131] = 97.0, 96.5, 97.0  # the CHoCH comes after 110 candles: expired
    assert sg.find_signals(o3, h3, l3, c3, rsi3, bias3, ~bias3, valid3) == []


def test_exclusions_are_reported_not_resolved_favourably():
    o, h, l, c, rsi, bias, valid = short_case()
    sig = sg.find_signals(o, h, l, c, rsi, bias, ~bias, valid)[0]
    o2 = o.copy(); o2[31] = 106.0                                               # the reference already lies beyond the risk level
    assert sg.outcome(sig, o2, h, l, c, rsi, valid)["status"] == "EXCLUDED_RISK_NOT_POSITIVE"
    v2 = valid.copy(); v2[33] = False                                           # a data gap inside the path
    assert sg.outcome(sig, o, h, l, c, rsi, v2)["status"] == "EXCLUDED_DATA_GAP"
    assert sg.outcome({**sig, "t": 259}, o, h, l, c, rsi, valid)["status"] == "EXCLUDED_END_OF_DATA"


def test_signals_are_causal_prefix_invariant_on_random_data():
    rng = np.random.default_rng(5)
    n = 4000
    c = 100 + np.cumsum(rng.normal(0, 0.4, n))
    o = np.r_[c[0], c[:-1]]; h = np.maximum(o, c) + rng.uniform(0, 0.3, n); l = np.minimum(o, c) - rng.uniform(0, 0.3, n)
    rsi = ind.rsi_wilder(c)
    bear = (np.sin(np.arange(n) / 300.0) < 0)
    valid = np.ones(n, bool)
    full = sg.find_signals(o, h, l, c, rsi, bear, ~bear, valid)
    assert len(full) > 20
    for m in (800, 2000, 3500):
        part = sg.find_signals(o[:m], h[:m], l[:m], c[:m], ind.rsi_wilder(c[:m]), bear[:m], ~bear[:m], valid[:m])
        assert part == [s for s in full if s["t"] < m]
        o2, h2, l2, c2 = o.copy(), h.copy(), l.copy(), c.copy()                       # everything after m replaced by noise
        c2[m:] = 1.0 + rng.uniform(0, 50, n - m); o2[m:] = c2[m:]; h2[m:] = c2[m:] + 5; l2[m:] = c2[m:] - 5
        p2 = sg.find_signals(o2, h2, l2, c2, ind.rsi_wilder(c2), bear, ~bear, valid)
        assert [s_ for s_ in p2 if s_["t"] < m] == [s_ for s_ in full if s_["t"] < m]


def write_csv(path, rows):
    with gzip.open(path, "wt", newline="") as f:
        w = csv.writer(f); w.writerow(["ts_ms", "open", "high", "low", "close", "volume"]); w.writerows(rows)


def make_dir(tmp_path, gap=False, days=200):
    rng = np.random.default_rng(3)
    t0 = 1_672_531_200_000
    d = tmp_path / "data"; d.mkdir()
    c = 20000 + np.cumsum(rng.normal(0, 20, days * 96))
    for iv, step in (("15m", 900_000), ("4h", 14_400_000), ("1d", 86_400_000)):
        per = step // 900_000
        n = len(c) // per
        cc = c[: n * per].reshape(n, per)
        rows = [(t0 + i * step, cc[i, 0], cc[i].max() + 1, cc[i].min() - 1, cc[i, -1], 1) for i in range(n)]
        if gap and iv == "15m":
            rows = rows[:9000] + rows[9100:]
        write_csv(d / f"BTCUSDT-{iv}.csv.gz", rows)
    return d


def test_prepare_guards_warmup_and_data_gaps_and_the_study_runs_end_to_end(tmp_path):
    d = make_dir(tmp_path, gap=True)
    x = study.prepare(d)
    assert not x["valid"][:P.WARMUP_DAYS * 96].any()
    g = 9000
    assert not x["valid"][g - P.GAP_GUARD_BARS_BEFORE:g + P.GAP_GUARD_BARS_AFTER].any() and x["valid"][g + P.GAP_GUARD_BARS_AFTER + 5]
    rep = study.report(d)
    recs = rep.pop("records")
    assert rep["with_trend"]["signals"] == len(recs["with_trend"]) and "stop_rule" in rep["with_trend"]
    assert set(rep["with_trend"]["stop_rule"]["criteria"]) == {"1_mean_net_R_above_zero", "2_at_least_100_signals", "3_positive_in_both_halves", "4_excluded_share_at_most_20pct"}


def test_freeze_blocks_the_test_run_on_any_change_and_the_run_happens_once(tmp_path):
    d = make_dir(tmp_path)
    root = tmp_path / "repo"
    for n in freeze.CODE:
        p = root / n; p.parent.mkdir(parents=True, exist_ok=True); p.write_text((ROOT / n).read_text(encoding="utf-8"), encoding="utf-8")
    fp = tmp_path / "f.json"
    rec = freeze.write(d, root, fp)
    with pytest.raises(SystemExit):
        freeze.write(d, root, fp)
    assert freeze.verify(d, root, fp)["version_sha256"] == rec["version_sha256"]
    (root / "src/trendrsi/params.py").write_text((root / "src/trendrsi/params.py").read_text() + "\n# tweak\n")
    with pytest.raises(SystemExit):
        freeze.verify(d, root, fp)
    shutil.copy(ROOT / "src/trendrsi/params.py", root / "src/trendrsi/params.py")
    freeze.verify(d, root, fp)
    write_csv(d / "BTCUSDT-1d.csv.gz", [(1_672_531_200_000, 1, 2, 0.5, 1, 1)])          # the data files must be the frozen ones
    with pytest.raises(SystemExit):
        freeze.verify(d, root, fp)
    with pytest.raises(SystemExit):
        runmod.main(["--label", "test", "--data-dir", str(d), "--out", str(tmp_path / "o")])      # no freeze for this data/dir in the real repo


def test_no_execution_code_or_order_fields_and_policy_firewall():
    findings, problems = policy_guard.check_repo(ROOT)
    assert findings == [] and "src/trendrsi/" in policy_guard.PROTECTED_DIRS
    for f in (ROOT / "src/trendrsi").glob("*.py"):
        names = {n.id.lower() for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))) if isinstance(n, ast.Name)}
        assert not names & {"fill_price", "stop_loss", "take_profit", "entry_price", "exit_price", "slippage", "leverage", "pnl"}, f.name
