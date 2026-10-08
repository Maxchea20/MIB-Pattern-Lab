"""Setup Brain tests: causality, replay, equivalence, determinism, independence. Constructed series only."""
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from src.brain import detectors as det
from src.brain import replay as rp
from src.brain import scan
from src.brain.brain import SetupBrain, STEP_NS
from src.setups import recognizer as rz
from tests.test_brain_detectors import S5_PATH, THR, s9_path
from tests.test_setups_recognizer import PATHS, walk

E = 0.3
START_NS = int(pd.Timestamp("2025-10-01T00:00:00Z").value)


def arrays(c, e=E, gap_at=None):
    c = np.asarray(c, float)
    ts = START_NS + np.arange(len(c), dtype=np.int64) * STEP_NS
    if gap_at is not None:
        ts[gap_at:] += STEP_NS
    return ts, c, c + e, c - e, c


def stream(ts, o, h, l, c):
    for i in range(len(c)):
        yield {"ts": int(ts[i]), "open": o[i], "high": h[i], "low": l[i], "close": c[i], "closed": True}


def run_series(c, e=E, thr=THR, gap_at=None):
    ts, o, h, l, cc = arrays(c, e, gap_at)
    return rp.replay(stream(ts, o, h, l, cc), SetupBrain(thr, "test"))


def fires(events, sid=None):
    return [e for e in events if e["event"] == "FIRE" and (sid is None or e["setup_id"] == sid)]


def test_first_valid_trigger_is_the_next_closing_candle_after_presence():
    c = PATHS["C7"]
    level = rz.window_state(c + E, c - E, c, THR)["C7"][0]
    assert fires(run_series(c)) == [] or all(f["trigger_idx"] > 95 for f in fires(run_series(c)))
    ev = fires(run_series(np.r_[c, level + 1.0]), "S7")
    assert len(ev) == 1
    f = ev[0]
    assert f["trigger_idx"] == 96 and f["presence_len"] >= 1 and f["direction"] == "up"
    assert f["operative_level"] == pytest.approx(level) and f["trigger_candle"]["close"] == pytest.approx(level + 1.0)
    assert pd.Timestamp(f["presence_start_ts"]) <= pd.Timestamp(f["trigger_ts"])
    assert f["detector_version_sha256"] == "test" and f["timeframe"] == "15m"
    assert not fires(run_series(np.r_[c, level - 0.1]), "S7")                      # inside the level: no fire


def test_touching_the_level_without_a_close_beyond_it_does_not_fire():
    c = PATHS["C7"]
    level = rz.window_state(c + E, c - E, c, THR)["C7"][0]
    series = np.r_[c, level - 0.1]
    ts, o, h, l, cc = arrays(series)
    h[-1] = level + 5                                                               # the wick pokes through, the close does not
    assert not fires(rp.replay(stream(ts, o, h, l, cc), SetupBrain(THR, "t")), "S7")


def test_simultaneous_fires_are_recorded_independently_without_voting_or_veto():
    c = PATHS["C7"]                                                                 # S2 and S7 are both present on this window
    level = rz.window_state(c + E, c - E, c, THR)["C7"][0]
    ev = fires(run_series(np.r_[c, level + 1.0]))
    got = {f["setup_id"] for f in ev if f["trigger_idx"] == 96}
    assert {"S2", "S7"} <= got and len([f for f in ev if f["trigger_idx"] == 96]) == len(got)
    assert len({f["fire_id"] for f in ev}) == len(ev)                               # separate events, separate ids


def test_s9_fires_in_both_directions_decided_at_the_trigger():
    c = s9_path()
    h = c + E
    l = c - E
    up = fires(run_series(np.r_[c, h[72:].max() + 1.0]), "S9")
    dn = fires(run_series(np.r_[c, l[72:].min() - 1.0]), "S9")
    assert [f["direction"] for f in up] == ["up"] and [f["direction"] for f in dn] == ["down"]
    assert up[0]["operative_level"] == pytest.approx(h[72:].max()) and dn[0]["operative_level"] == pytest.approx(l[72:].min())


def test_consecutive_fires_are_all_kept_and_labelled():
    c = PATHS["C7"]
    level = rz.window_state(c + E, c - E, c, THR)["C7"][0]
    ev = fires(run_series(np.r_[c, level + 1.0, level + 2.5, level + 4.5]), "S7")
    pos = [(f["trigger_idx"], f["streak_position"]) for f in ev]
    assert pos[0] == (96, 0)
    for (i, s), (j, t) in zip(pos, pos[1:]):
        assert t == (s + 1 if j == i + 1 else 0)


def test_invalidation_event_follows_the_fire_and_never_precedes_it():
    c = PATHS["C7"]
    level = rz.window_state(c + E, c - E, c, THR)["C7"][0]
    events = run_series(np.r_[c, level + 1.0, -1000.0])
    f = fires(events, "S7")[0]
    inv = [e for e in events if e["event"] == "INVALIDATED" and e["fire_id"] == f["fire_id"]]
    assert len(inv) == 1 and inv[0]["invalidation_idx"] == 97 and inv[0]["candles_after_trigger"] == 1
    assert events.index(inv[0]) > events.index(f)


def test_incomplete_candle_is_refused_and_out_of_order_input_raises():
    ts, o, h, l, c = arrays(PATHS["C7"])
    b = SetupBrain(THR, "t")
    for i in range(len(c)):
        b.on_candle({"ts": int(ts[i]), "open": o[i], "high": h[i], "low": l[i], "close": c[i]})
    n = b.idx
    assert b.on_candle({"ts": int(ts[-1] + STEP_NS), "open": 1, "high": 2, "low": 0, "close": 1, "closed": False}) == []
    assert b.rejected_incomplete == 1 and b.idx == n
    with pytest.raises(ValueError):
        b.on_candle({"ts": int(ts[-1]), "open": 1, "high": 2, "low": 0, "close": 1})


def test_gap_resets_the_window_and_blocks_fires_across_it():
    c = PATHS["C7"]
    level = rz.window_state(c + E, c - E, c, THR)["C7"][0]
    series = np.r_[c, level + 1.0]
    assert fires(run_series(series, gap_at=60), "S7") == []                         # a missing candle inside the 96-candle window
    ts, o, h, l, cc = arrays(series, gap_at=96)                                      # gap exactly before the trigger candle
    assert fires(rp.replay(stream(ts, o, h, l, cc), SetupBrain(THR, "t")), "S7") == []


def test_brain_cannot_see_the_future_prefix_noise_and_lazy_source():
    c = walk(3000, 4)
    thr = THR
    full = fires(run_series(c, thr=thr))
    assert len(full) > 10 and len({f["setup_id"] for f in full}) >= 3

    def key(ev, m):
        return [{k: v for k, v in e.items() if k != "input_digest"} for e in ev if e["trigger_idx"] < m]

    for m in (400, 1200, 2500):
        assert key(fires(run_series(c[:m], thr=thr)), m) == key(full, m)
        noisy = c.copy()
        noisy[m:] = np.random.default_rng(m).uniform(10, 900, len(c) - m)
        assert key(fires(run_series(noisy, thr=thr)), m) == key(full, m)
    pulled = []
    ts, o, h, l, cc = arrays(c)

    def lazy():
        for cd in stream(ts, o, h, l, cc):
            pulled.append(cd["ts"])
            yield cd
            if len(pulled) == 1500:
                raise RuntimeError("the source ends here: nothing later may be requested")
    b = SetupBrain(thr, "test")
    got = []
    with pytest.raises(RuntimeError):
        for cd in lazy():
            got += b.on_candle(cd)
    assert len(pulled) == 1500 and key(fires(got), 1500) == key(full, 1500)


def test_input_digest_covers_only_candles_up_to_the_fire():
    c = PATHS["C7"]
    level = rz.window_state(c + E, c - E, c, THR)["C7"][0]
    series = np.r_[c, level + 1.0, 5.0, 6.0]
    ts, o, h, l, cc = arrays(series)
    f = fires(rp.replay(stream(ts, o, h, l, cc), SetupBrain(THR, "t")), "S7")[0]
    hh = hashlib.sha256()
    for i in range(f["trigger_idx"] + 1):
        hh.update(f"{int(ts[i])},{float(o[i])!r},{float(h[i])!r},{float(l[i])!r},{float(cc[i])!r};".encode())
    assert f["input_digest"] == hh.hexdigest()


@pytest.mark.parametrize("seed,gap", [(4, None), (9, 700), (21, 1500)])
def test_incremental_replay_equals_chronological_batch_scan(seed, gap):
    c = walk(2500, seed)
    ts, o, h, l, cc = arrays(c, gap_at=gap)
    a = rp.replay(stream(ts, o, h, l, cc), SetupBrain(THR, "v"))
    b = rp.batch_scan(ts, o, h, l, cc, THR, "v")
    assert len(fires(a)) > 10
    assert rp.comparable(a) == rp.comparable(b)


def test_imported_detectors_agree_with_the_experiment3_recognizer_raw_triggers():
    c = walk(3000, 11)
    ts, o, h, l, cc = arrays(c)
    events = rp.replay(stream(ts, o, h, l, cc), SetupBrain(THR, "v"))
    r = scan.cross_check_experiment3(ts, o, h, l, cc, THR, fires(events))
    assert r["identical"] and r["experiment3_raw_triggers"] > 10


def test_output_is_deterministic_and_s5_s9_are_active():
    c = walk(2000, 2)
    assert run_series(c) == run_series(c.copy())
    seen = {f["setup_id"] for f in fires(run_series(walk(6000, 31)))}
    assert len(seen) >= 4


def test_presence_pairs_and_overlap_counts():
    c = PATHS["C7"]
    b = SetupBrain(THR, "t")
    ts, o, h, l, cc = arrays(c)
    for cd in stream(ts, o, h, l, cc):
        b.on_candle(cd)
    assert b.presence_candles["S7"] == 1 and b.presence_pairs.get(("S2", "S7")) == 1
    from src.brain import forward
    rows = [{"setup_id": "S2", "trigger_idx": 5}, {"setup_id": "S7", "trigger_idx": 5}, {"setup_id": "S7", "trigger_idx": 9}]
    m = forward.overlap(rows, b.presence_pairs, b.presence_candles)
    assert m["S2/S7"]["same_candle_fires"] == 1 and m["S2/S7"]["fire_jaccard"] == pytest.approx(0.5)
    assert m["S1/S3"]["same_candle_fires"] == 0
