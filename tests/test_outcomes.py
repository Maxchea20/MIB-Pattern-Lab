import json
import math

import numpy as np
import pandas as pd
import pytest

import config
from src.data.loader import CandleSet, build_candles
from src.discovery import families as fam
from src.discovery.discover import discovery_candles
from src.outcomes import analyze as an
from src.outcomes import stats
from src.outcomes.forward import HORIZONS, forward_outcomes
from tests.conftest import make_ohlc

H1 = 3600
T0 = pd.Timestamp("2024-01-01T00:00:00Z")


def candles(n=60, closes=None, highs=None, lows=None):
    ts = pd.date_range(T0, periods=n, freq="1h", tz="UTC")
    c = np.array(closes if closes is not None else np.arange(100.0, 100.0 + n))
    h = np.array(highs if highs is not None else c + 1.0)
    l = np.array(lows if lows is not None else c - 1.0)
    return pd.DataFrame({"ts": ts, "open": c, "high": h, "low": l, "close": c})


# ------------------------------------------------------------- forward outcomes ------
def test_forward_outcomes_hand_checked():
    closes = [100.0, 101, 99, 102, 98, 103, 97, 104, 96, 105] + [100.0] * 30
    highs = [c + 2 for c in closes]
    lows = [c - 3 for c in closes]
    df = candles(40, closes, highs, lows)
    out, ex = forward_outcomes(df, [df["ts"][0]], H1)
    r = out.iloc[0]
    assert sum(ex.values()) == 0 and r["entry_close"] == 100.0           # entry = close of T (not next open)
    assert r["ret_1"] == pytest.approx(1.0) and r["ret_3"] == pytest.approx(2.0)
    assert r["ret_6"] == pytest.approx(-3.0)
    assert r["fh_3"] == 104 and r["fl_3"] == 96                           # candles 1..3: highs 103,101,104 / lows 98,96,99
    assert r["mfe_3"] == pytest.approx(4.0) and r["mae_3"] == pytest.approx(-4.0)
    assert r["fh_1"] == 103 and r["fl_1"] == 98
    assert (out[[f"mfe_{h}" for h in HORIZONS]] >= 0).all().all() and (out[[f"mae_{h}" for h in HORIZONS]] <= 0).all().all()


def test_forward_exclusions_counted():
    df = candles(40)
    out, ex = forward_outcomes(df, [df["ts"][0], df["ts"][20], T0 + pd.Timedelta(minutes=30)], H1)
    assert len(out) == 1 and ex["insufficient_forward_candles"] == 1 and ex["end_candle_missing"] == 1
    gapped = df.drop(index=10).reset_index(drop=True)
    out2, ex2 = forward_outcomes(gapped, [gapped["ts"][0]], H1)
    assert len(out2) == 0 and ex2["gap_in_forward_path"] == 1


def test_forward_uses_only_next_24_candles():
    df = candles(80)
    base, _ = forward_outcomes(df, [df["ts"][5]], H1)
    far = df.copy(); far.loc[40:, ["open", "high", "low", "close"]] = 1e9      # beyond T+24
    assert forward_outcomes(far, [far["ts"][5]], H1)[0].equals(base)
    near = df.copy(); near.loc[10, ["high", "low", "close", "open"]] = 1e9     # inside T+1..T+24
    assert not forward_outcomes(near, [near["ts"][5]], H1)[0].equals(base)


def test_discovery_cut_removes_holdout_candles_and_excludes_crossing_windows(monkeypatch):
    raw = make_ohlc(400, start_ms=int(T0.timestamp() * 1000), step_ms=3_600_000)
    cs = build_candles(raw, "BTC/USDT", "1h", "x", as_of="2100-01-01")
    cut = (T0 + pd.Timedelta(hours=300)).isoformat()
    monkeypatch.setattr(config, "DISCOVERY_END_BY_TF", {"1h": cut})
    d = discovery_candles(cs)
    assert d.df["ts"].max() < pd.Timestamp(cut)
    ends = [d.df["ts"].iloc[100], d.df["ts"].iloc[-10]]                      # 2nd one's forward path crosses the cut
    out, ex = forward_outcomes(d.df, ends, H1)
    assert len(out) == 1 and ex["insufficient_forward_candles"] == 1
    poisoned = cs.df.copy(); poisoned.loc[poisoned["ts"] >= pd.Timestamp(cut), ["open", "high", "low", "close"]] = 1e9
    d2 = discovery_candles(CandleSet(poisoned, "BTC/USDT", "1h", "x"))
    assert forward_outcomes(d2.df, ends, H1)[0].equals(out)                   # hold-out data cannot influence anything


# --------------------------------------------------------------------- statistics ----
def test_welch_cohen_mde_match_hand_computation():
    x = np.array([1.0, 2, 3, 4, 5]); y = np.array([2.0, 2, 3, 3, 3, 9])
    t, df, p = stats.welch(x, y)
    se = math.sqrt(x.var(ddof=1) / 5 + y.var(ddof=1) / 6)
    assert t == pytest.approx((x.mean() - y.mean()) / se) and 0 < p < 1 and df > 0
    sp = math.sqrt((4 * x.var(ddof=1) + 5 * y.var(ddof=1)) / 9)
    assert stats.cohens_d(x, y) == pytest.approx((x.mean() - y.mean()) / sp)
    assert stats.mde(x, y, m_cells=15) == pytest.approx((stats.z(1 - 0.05 / 30) + stats.z(0.8)) * sp * math.sqrt(1 / 5 + 1 / 6))


@pytest.mark.parametrize("t,df", [(12.706, 1), (4.303, 2), (2.571, 5), (2.228, 10), (2.086, 20), (2.042, 30), (1.984, 100)])
def test_t_distribution_matches_textbook_critical_values(t, df):
    assert stats.t_two_sided_p(t, df) == pytest.approx(0.05, abs=2e-4)


def test_ols_hc3_recovers_planted_coefficients():
    rng = np.random.default_rng(3)
    n = 600
    X = np.column_stack([np.ones(n), rng.normal(size=n), rng.normal(size=n), (rng.random(n) < 0.3).astype(float)])
    y = 0.5 + 2.0 * X[:, 1] - 1.0 * X[:, 2] + 1.5 * X[:, 3] + rng.normal(size=n)
    r = stats.ols_hc3(y, X)
    assert np.allclose(r["coef"], [0.5, 2.0, -1.0, 1.5], atol=0.25) and r["p"][3] < 1e-6
    y0 = 2.0 * X[:, 1] + rng.normal(size=n)                                   # dummy truly irrelevant
    assert stats.ols_hc3(y0, X)["p"][3] > 0.01


def test_bootstrap_ci_deterministic_and_covers_true_difference():
    rng = np.random.default_rng(5)
    x, y = rng.normal(1.0, 1, 80), rng.normal(0.0, 1, 300)
    ix = np.random.default_rng(1).integers(0, 80, (2000, 80)); iy = np.random.default_rng(2).integers(0, 300, (2000, 300))
    lo, hi = stats.bootstrap_diff_ci(x, y, ix, iy)
    assert lo < 1.0 < hi and lo == stats.bootstrap_diff_ci(x, y, ix, iy)[0]


# ------------------------------------------------------------ analysis / categories --
PRIMARY = fam.PRIMARY


def make_obs(n, seed):
    rng = np.random.default_rng(seed)
    cols = {f"{k}_{h}": rng.normal(size=n) for k in ("ret", "mfe", "mae") for h in HORIZONS}
    df = pd.DataFrame(cols)
    df["end_ts"] = [t.isoformat() for t in pd.date_range("2021-01-01", periods=n, freq="3D", tz="UTC")]
    df["net_pct"] = rng.normal(size=n); df["range_pct"] = np.abs(rng.normal(size=n)) + 1; df["eff"] = rng.random(n)
    return df


def members(obs, spec):
    return {name: set(obs["end_ts"].iloc[idx]) for name, idx in spec.items()}


def run(obs, spec, Bp=399, Bb=200):
    return an.analyze(obs, members(obs, spec), primary=PRIMARY, B_perm=Bp, B_boot=Bb)


def test_null_labels_rarely_pass_familywise():
    hits = 0
    for s in range(40):
        obs = make_obs(300, 1000 + s)
        perm = np.random.default_rng(s).permutation(300)
        spec = {"sideways_range": perm[:150], "drift_up": perm[150:210], "drift_down": perm[210:270], "stair_step_up": perm[270:290]}
        table, cats = run(obs, spec, Bp=199, Bb=100)
        hits += any(c["category"] == an.CATEGORY_PASS for c in cats.values())
        adj = table.loc[table["primary"], "adj_p"].dropna()
        assert (adj >= 1 / 200).all() and (adj <= 1).all()
    assert hits <= 6                                                            # nominal 5% of 40 = 2


def test_planted_effect_passes_and_exploratory_family_gets_no_category():
    obs = make_obs(300, 11)
    obs.loc[:59, [f"ret_{h}" for h in HORIZONS]] += 0.9
    spec = {"sideways_range": np.arange(0, 60), "drift_up": np.arange(60, 150), "drift_down": np.arange(150, 240),
            "stair_step_up": np.arange(240, 270)}
    table, cats = run(obs, spec, Bp=999, Bb=500)
    assert cats["sideways_range"]["category"] == an.CATEGORY_PASS and cats["sideways_range"]["frozen_horizon"] in HORIZONS
    # design property (family vs NON-family population): the other families are compared against a population that
    # contains the shifted sideways windows, so they show a MIRRORED (opposite-sign) difference
    assert table[(table.family == "drift_up") & (table.horizon == 6)].iloc[0]["mean_diff"] < 0
    assert "stair_step_up" not in cats
    row = table[(table.family == "sideways_range") & (table.horizon == 6)].iloc[0]
    assert row["mean_diff"] == pytest.approx(0.9, abs=0.35) and row["ci_lo"] > 0 and row["reg_coef"] > 0
    ex = table[(table.family == "stair_step_up")].iloc[0]
    assert pd.isna(ex["adj_p"])                                                 # exploratory: unadjusted only


def test_effect_explained_by_simple_features_does_not_pass():
    """Family = windows with the highest net_pct; returns are just net_pct + noise. Raw effect is huge, but the
    control regression shows the family adds nothing beyond the simple feature -> must not PASS."""
    obs = make_obs(300, 21)
    rng = np.random.default_rng(22)
    for h in HORIZONS:
        obs[f"ret_{h}"] = obs["net_pct"] * 1.0 + rng.normal(0, 0.3, 300)
    top = np.argsort(-obs["net_pct"].to_numpy())[:60]
    spec = {"sideways_range": np.setdiff1d(np.arange(300), top)[:100], "drift_up": top, "drift_down": np.argsort(obs["net_pct"].to_numpy())[:60]}
    table, cats = run(obs, spec, Bp=499, Bb=300)
    r = table[(table.family == "drift_up") & (table.horizon == 6)].iloc[0]
    assert r["mean_diff"] > 1 and r["ci_lo"] > 0 and r["adj_p"] < 0.05           # looks great on its own ...
    assert cats["drift_up"]["category"] != an.CATEGORY_PASS                       # ... but the control regression disagrees


def test_does_not_pass_requires_ci_inside_mde_and_low_n_is_inconclusive():
    base = make_obs(200, 31)
    obs = pd.concat([base, base.assign(end_ts=[t.isoformat() for t in pd.date_range("2022-01-01", periods=200, freq="3D", tz="UTC")])],
                    ignore_index=True)                                         # non-family rows are exact copies
    spec = {"sideways_range": np.arange(0, 200), "drift_up": np.arange(0, 10), "drift_down": np.arange(200, 230)}
    table, cats = run(obs, spec, Bp=299, Bb=300)
    assert cats["sideways_range"]["category"] == an.CATEGORY_NOT                  # zero effect, CI well inside +/-MDE
    assert cats["drift_up"]["category"] == an.CATEGORY_INCONCLUSIVE and "N=10" in cats["drift_up"]["reason"]
    assert cats["drift_down"]["category"] in (an.CATEGORY_NOT, an.CATEGORY_INCONCLUSIVE)


def test_permutation_machinery_preserves_outcomes_and_is_reproducible():
    obs = make_obs(120, 41)
    spec = {"sideways_range": np.arange(40), "drift_up": np.arange(40, 80), "drift_down": np.arange(80, 100)}
    t1, c1 = run(obs, spec, Bp=99, Bb=50)
    t2, c2 = run(obs, spec, Bp=99, Bb=50)
    pd.testing.assert_frame_equal(t1, t2)
    assert c1 == c2
    # permuting rows relative to membership leaves each column's multiset unchanged by construction
    Y = obs[[f"ret_{h}" for h in HORIZONS]].to_numpy()
    M = np.zeros((120, 1), bool); M[:40] = True
    ot, null = stats.permutation_null(Y, M, 20, 1)
    assert null.shape == (20, 1, 5) and np.isfinite(null).all()


# ------------------------------------------------------------- guards / end-to-end ---
def test_outcomes_module_not_imported_by_tagging_code():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1] / "src"
    for pkg in ("discovery", "charts", "data", "validation"):
        for f in (root / pkg).rglob("*.py"):
            assert "src.outcomes" not in f.read_text(encoding="utf-8"), f


def test_verify_lock_detects_any_tampering(tmp_path, monkeypatch):
    from src.discovery.tagset import file_sha256
    prereg = tmp_path / "PREREG.md"; prereg.write_text("frozen\n")
    monkeypatch.setattr(an, "PREREG", prereg)
    run_dir = tmp_path / "run"; run_dir.mkdir()
    (run_dir / "windows.jsonl").write_text("{}\n"); (run_dir / "retags.jsonl").write_text("{}\n")
    import hashlib
    from src.discovery import vocab
    h = lambda t: hashlib.sha256(t.encode()).hexdigest()
    lock = {"sha256": {"preregistration": file_sha256(prereg), "families_py": file_sha256(__import__("pathlib").Path(fam.__file__)),
                       "vocab": vocab.VOCAB_SHA256, "windows_jsonl": file_sha256(run_dir / "windows.jsonl"),
                       "retags_jsonl": file_sha256(run_dir / "retags.jsonl"), "prompt_system": h(vocab.RETAG_SYSTEM),
                       "prompt_user_pass1": h(vocab.retag_user(False)), "prompt_user_pass2": h(vocab.retag_user(True))}}
    an.verify_lock(lock, run_dir)                                               # untouched -> fine
    for f, name in [(prereg, "preregistration"), (run_dir / "windows.jsonl", "windows_jsonl"), (run_dir / "retags.jsonl", "retags_jsonl")]:
        old = f.read_text(); f.write_text(old + "x")
        with pytest.raises(SystemExit, match=name):
            an.verify_lock(lock, run_dir)
        f.write_text(old)
    (run_dir / "windows.jsonl").write_bytes(b"{}\r\n")                           # CRLF checkout must still verify
    an.verify_lock(lock, run_dir)


def test_end_to_end_cli_runs_once_and_refuses_changes(tmp_path, monkeypatch):
    import sqlite3
    from src.discovery import lock as lockmod, tagset
    from src.discovery.retag import run_retag
    from tests.test_vocab import Tagger
    freeze = tmp_path / "freeze.json"
    monkeypatch.setattr(an, "FREEZE", freeze)
    db = tmp_path / "m.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE candles (symbol TEXT, timeframe TEXT, ts INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL)")
    d = make_ohlc(3000, start_ms=int(T0.timestamp() * 1000), step_ms=3_600_000)
    con.executemany("INSERT INTO candles VALUES ('BTC_USDT','1h',?,?,?,?,?,1)",
                    [(int(r.timestamp // 1000), r.open, r.high, r.low, r.close) for r in d.itertuples()])
    con.commit(); con.close()
    cut = (T0 + pd.Timedelta(hours=2000)).isoformat()
    monkeypatch.setattr(config, "DISCOVERY_END_BY_TF", {"1h": cut})
    from src.data.loader import load_candles
    cs = load_candles(db, timeframe="1h")
    run_dir = tmp_path / "run"
    _, _, windows = tagset.prepare(cs, run_dir, 20, "stratified")
    names = ["sideways_range", "drift_up", "drift_down", "stair_step_up"]
    run_retag(run_dir, Tagger(lambda png, n: {"tags": [names[((n - 1) // 2) % 4]]}), passes=2, charts=windows)
    lock = lockmod.build_lock(run_dir, "1h")
    lock_path = tmp_path / "lock.json"; lock_path.write_text(json.dumps(lock))
    out = tmp_path / "out"
    args = ["--db", str(db), "--timeframe", "1h", "--lock", str(lock_path), "--run-dir", str(run_dir), "--out", str(out),
            "--permutations", "99", "--bootstrap", "50"]
    sha12 = lock["sha256"]["preregistration"][:12]
    with pytest.raises(SystemExit, match="not been frozen"):                    # no freeze record -> refuse
        an.main(args + ["--confirm-prereg-sha", sha12])
    assert an.main(["--write-freeze"]) == 0 and freeze.exists()
    with pytest.raises(SystemExit, match="already exists"):
        an.main(["--write-freeze"])
    with pytest.raises(SystemExit, match="confirm-prereg-sha"):
        an.main(args + ["--confirm-prereg-sha", "000000000000"])
    assert not out.exists()                                                      # nothing written without the right sha
    assert an.main(args + ["--confirm-prereg-sha", sha12]) == 0
    s = json.loads((out / "summary.json").read_text())
    assert set(s["categories"]) == set(fam.PRIMARY) and s["n_valid"] <= s["n_windows"] == len(windows)
    assert (out / "observations.csv").exists() and (out / "family_stats.csv").exists() and "Primary-family verdicts" in (out / "report.md").read_text()
    obs = pd.read_csv(out / "observations.csv")
    assert (pd.to_datetime(obs["end_ts"]) + pd.Timedelta(hours=24) < pd.Timestamp(cut)).all()   # forward path inside discovery
    with pytest.raises(SystemExit, match="already completed"):
        an.main(args + ["--confirm-prereg-sha", sha12])
    assert an.main(args + ["--confirm-prereg-sha", sha12, "--rerun-identical"]) == 0
    monkeypatch.setattr(an, "code_sha256", lambda: "changed")
    with pytest.raises(SystemExit, match="changed since it was frozen"):
        an.main(args + ["--confirm-prereg-sha", sha12, "--rerun-identical"])
    (run_dir / "retags.jsonl").write_text((run_dir / "retags.jsonl").read_text() + "\n")   # tamper with frozen sample
    monkeypatch.undo()
    with pytest.raises(SystemExit):
        an.main(args + ["--confirm-prereg-sha", sha12, "--rerun-identical"])
