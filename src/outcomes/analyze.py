"""Pre-registered DISCOVERY outcome analysis (docs/PREREGISTRATION.md sections 4-8).

    python -m src.outcomes.analyze --confirm-prereg-sha <first 12 chars of the lock's preregistration sha>

Refuses to run unless docs/PREREG_LOCK.json matches the files on disk (pre-registration, families, vocabulary,
prompts, window list, tag file). Hold-out candles are physically removed before anything is read. The analysis can
be completed only once: a RUN_COMPLETE.json marker stores the code hash and blocks changed re-runs.
Nothing here defines or uses trading rules (no TP/SL), and no family is merged or renamed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd

import config
from src.charts.windows import build_window
from src.data.loader import load_candles, tf_to_seconds
from src.discovery import families as fam
from src.discovery import vocab
from src.discovery.audit import stable_tags, window_features
from src.discovery.discover import discovery_candles
from src.discovery.retag import load_rows
from src.discovery.tagset import file_sha256, load_windows
from src.outcomes import stats
from src.outcomes.forward import HORIZONS, forward_outcomes

PREREG = config.ROOT / "docs" / "PREREGISTRATION.md"
LOCK = config.ROOT / "docs" / "PREREG_LOCK.json"
N_MIN = 30
ALPHA = 0.05
SEED_PERM, SEED_BOOT = 12345, 20240601
CATEGORY_PASS, CATEGORY_NOT, CATEGORY_INCONCLUSIVE = "PASS", "DOES NOT PASS", "INCONCLUSIVE / LOW POWER"


# --------------------------------------------------------------------------- guards ---
FREEZE = config.ROOT / "docs" / "OUTCOME_CODE_FREEZE.json"
# Everything the discovery analysis depends on (besides the data and the lock record).
_DEPENDENCIES = ("src/discovery/audit.py", "src/discovery/discover.py", "src/discovery/families.py",
                 "src/discovery/retag.py", "src/discovery/tagset.py", "src/discovery/vocab.py",
                 "src/charts/windows.py", "src/data/loader.py", "src/validation/window_validation.py")


def code_sha256() -> str:
    """sha256 over src/outcomes/*.py and its dependencies (CRLF-normalised, path-labelled)."""
    files = sorted(Path(__file__).parent.glob("*.py")) + [config.ROOT / d for d in _DEPENDENCIES]
    h = hashlib.sha256()
    for f in sorted(files, key=lambda p: p.relative_to(config.ROOT).as_posix()):
        h.update(f.relative_to(config.ROOT).as_posix().encode() + f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def check_freeze() -> None:
    if not FREEZE.exists():
        raise SystemExit(f"{FREEZE.name} is missing: the outcome code has not been frozen yet "
                         "(it is written once, after the code is reviewed: --write-freeze).")
    rec = json.loads(FREEZE.read_text(encoding="utf-8"))
    if rec["code_sha256"] != code_sha256():
        raise SystemExit("The outcome code (or a dependency) changed since it was frozen. "
                         "No changes are allowed once the analysis may begin.")


def verify_lock(lock: dict, run_dir: Path) -> None:
    now = {"preregistration": file_sha256(PREREG), "families_py": file_sha256(Path(fam.__file__)),
           "vocab": vocab.VOCAB_SHA256, "windows_jsonl": file_sha256(run_dir / "windows.jsonl"),
           "retags_jsonl": file_sha256(run_dir / "retags.jsonl"),
           "prompt_system": hashlib.sha256(vocab.RETAG_SYSTEM.encode()).hexdigest(),
           "prompt_user_pass1": hashlib.sha256(vocab.retag_user(False).encode()).hexdigest(),
           "prompt_user_pass2": hashlib.sha256(vocab.retag_user(True).encode()).hexdigest()}
    bad = [k for k, v in lock["sha256"].items() if now.get(k) != v]
    if bad:
        raise SystemExit("LOCK MISMATCH - the frozen specification or sample changed: " + ", ".join(bad))


# ------------------------------------------------------------------- observations ---
def build_observations(dcs, windows: list[dict], timeframe: str):
    """One row per window with valid forward outcomes + window-only control features."""
    fwd, excluded = forward_outcomes(dcs.df, [w["end_ts"] for w in windows], tf_to_seconds(timeframe))
    feats = []
    for e in fwd["end_ts"]:
        raw = build_window(dcs, pd.Timestamp(e), config.LOOKBACK).raw
        f = window_features(raw)
        feats.append({"net_pct": f["net_pct"], "range_pct": f["range_pct"], "eff": f["eff"]})
    obs = pd.concat([fwd.reset_index(drop=True), pd.DataFrame(feats)], axis=1)
    strat = {w["end_ts"]: w.get("stratum") for w in windows}
    obs["stratum"] = [strat.get(pd.Timestamp(e).isoformat(), strat.get(e)) for e in obs["end_ts"]]
    return obs, excluded


# ------------------------------------------------------------------------ analysis ---
def analyze(obs: pd.DataFrame, membership: dict[str, set], primary=fam.PRIMARY, horizons=HORIZONS,
            B_perm: int = 10_000, B_boot: int = 10_000, seed_perm: int = SEED_PERM, seed_boot: int = SEED_BOOT):
    names = list(membership)
    n = len(obs)
    pos = {e: i for i, e in enumerate(obs["end_ts"])}
    M = np.zeros((n, len(names)), bool)
    for j, f in enumerate(names):
        for e in membership[f]:
            if e in pos:
                M[pos[e], j] = True
    cols = [f"{k}_{h}" for k in ("ret", "mfe", "mae") for h in horizons]
    col = {c: i for i, c in enumerate(cols)}
    Y = obs[cols].to_numpy(float)

    obs_t, null = stats.permutation_null(Y, M, B_perm, seed_perm)
    perm_p = stats.permutation_p(obs_t, null)
    prim_j = [names.index(f) for f in primary]
    ret_k = [col[f"ret_{h}"] for h in horizons]
    adj = stats.maxt_adjusted_p(np.array([obs_t[j, k] for j in prim_j for k in ret_k]),
                                null[:, prim_j][:, :, ret_k].reshape(B_perm, -1))
    adj_map = {(primary[a], horizons[b]): adj[a * len(horizons) + b]
               for a in range(len(primary)) for b in range(len(horizons))}
    m_cells = len(primary) * len(horizons)

    rng = np.random.default_rng(seed_boot)
    X0 = np.column_stack([np.ones(n), obs[["net_pct", "range_pct", "eff"]].to_numpy(float)])
    rows = []
    for j, f in enumerate(names):
        mask = M[:, j]
        nf, nn = int(mask.sum()), int((~mask).sum())
        bi_x = rng.integers(0, nf, (B_boot, nf)) if nf >= 2 else None
        bi_y = rng.integers(0, nn, (B_boot, nn)) if nf >= 2 and nn >= 2 else None
        for h in horizons:
            kr, km, ka = col[f"ret_{h}"], col[f"mfe_{h}"], col[f"mae_{h}"]
            x, y = Y[mask, kr], Y[~mask, kr]
            r = {"family": f, "primary": f in primary, "horizon": h, "N": nf, "nonfamily_N": nn}
            if nf >= 1:
                r.update(mean=x.mean(), median=float(np.median(x)), win_pct=100.0 * float((x > 0).mean()),
                         mfe_mean=Y[mask, km].mean(), mfe_median=float(np.median(Y[mask, km])),
                         mae_mean=Y[mask, ka].mean(), mae_median=float(np.median(Y[mask, ka])))
            if nn >= 1:
                r.update(nonfamily_mean=y.mean(), nonfamily_median=float(np.median(y)))
            if nf >= 2 and nn >= 2:
                lo, hi = stats.bootstrap_diff_ci(x, y, bi_x, bi_y)
                t, dfree, p = stats.welch(x, y)
                reg = stats.ols_hc3(Y[:, kr], np.column_stack([X0, mask.astype(float)]))
                r.update(mean_diff=x.mean() - y.mean(), cohens_d=stats.cohens_d(x, y), ci_lo=lo, ci_hi=hi,
                         welch_t=t, welch_p=p, perm_t=obs_t[j, kr], perm_p=perm_p[j, kr],
                         null_p025=float(np.nanpercentile(null[:, j, kr], 2.5)),
                         null_p50=float(np.nanpercentile(null[:, j, kr], 50)),
                         null_p975=float(np.nanpercentile(null[:, j, kr], 97.5)),
                         adj_p=adj_map.get((f, h)), reg_coef=float(reg["coef"][-1]), reg_p=float(reg["p"][-1]),
                         mde=stats.mde(x, y, m_cells=m_cells),
                         mfe_diff=Y[mask, km].mean() - Y[~mask, km].mean(), mfe_perm_p=perm_p[j, km],
                         mae_diff=Y[mask, ka].mean() - Y[~mask, ka].mean(), mae_perm_p=perm_p[j, ka])
                r["ci_within_mde"] = bool(abs(lo) <= r["mde"] and abs(hi) <= r["mde"])
            rows.append(r)
    table = pd.DataFrame(rows)
    return table, {f: categorize(table[table["family"] == f], horizons) for f in primary}


def categorize(rows: pd.DataFrame, horizons=HORIZONS) -> dict:
    """Pre-registration section 8. All three conditions must hold at a horizon for PASS."""
    n = int(rows["N"].iloc[0])
    out = {"N": n, "passing_horizons": [], "frozen_horizon": None}
    if n < N_MIN:
        return {**out, "category": CATEGORY_INCONCLUSIVE, "reason": f"N={n} < {N_MIN}"}
    for _, r in rows.iterrows():
        ok = (r.get("adj_p", np.nan) < ALPHA and r.get("ci_lo", np.nan) * r.get("ci_hi", np.nan) > 0
              and r.get("reg_p", np.nan) < ALPHA and np.sign(r.get("reg_coef", np.nan)) == np.sign(r.get("mean_diff", np.nan))
              and r.get("mean_diff", 0) != 0)
        if ok:
            out["passing_horizons"].append((int(r["horizon"]), float(r["adj_p"])))
    if out["passing_horizons"]:
        best = sorted(out["passing_horizons"], key=lambda t: (t[1], t[0]))[0][0]      # smallest adj p, ties shorter
        return {**out, "category": CATEGORY_PASS, "frozen_horizon": best,
                "reason": "all three conditions hold at the listed horizons"}
    if bool(rows["ci_within_mde"].fillna(False).all()) and len(rows) == len(horizons):
        return {**out, "category": CATEGORY_NOT,
                "reason": "at every horizon the 95% CI lies within +/-MDE: effects at least that large are not supported"}
    return {**out, "category": CATEGORY_INCONCLUSIVE,
            "reason": "criteria not met and the data cannot exclude effects of MDE size at every horizon"}


# ----------------------------------------------------------------------- reporting ---
def _fmt(v, nd=3):
    return "" if v is None or (isinstance(v, float) and not np.isfinite(v)) else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def render_report(table: pd.DataFrame, cats: dict, meta: dict) -> str:
    L = ["# Discovery outcome analysis (pre-registered)", "",
         f"Lock record: prereg sha256 `{meta['lock_prereg_sha256']}` | windows sha256 `{meta['lock_windows_sha256']}`",
         f"Outcome code sha256 `{meta['code_sha256']}` | seeds perm={SEED_PERM} boot={SEED_BOOT} | "
         f"B_perm={meta['B_perm']} B_boot={meta['B_boot']}", "",
         f"Windows tagged: {meta['n_windows']} | with valid 24h forward path: {meta['n_valid']} | excluded: {meta['excluded']}",
         "", "Outcomes: forward close return, MFE, MAE (% from the close of T) at 1/3/6/12/24 candles (hours). "
         "No TP/SL, no costs, no trading rules. Effects are mean differences in percentage points vs the non-family "
         "population. Exploratory families carry no confirmatory claim.", "",
         "**Reading note:** the non-family population contains the other families. A real effect in one family can "
         "therefore appear as an opposite-signed (mirrored) difference in another; PASS in several families may reflect "
         "a single contrast. The maxT correction accounts for this dependence.", "",
         "## Primary-family verdicts (discovery)", "", "| family | N | category | frozen hold-out horizon | note |", "|---|---|---|---|---|"]
    for f, c in cats.items():
        L.append(f"| {f} | {c['N']} | **{c['category']}** | {c['frozen_horizon'] or ''} | {c['reason']} |")
    L += ["", "A DOES NOT PASS means effects at least as large as the MDE are not supported by the data; it does NOT "
          "mean no edge exists. INCONCLUSIVE / LOW POWER means the data cannot support a reliable conclusion.", ""]
    cols = ["horizon", "N", "mean", "median", "win_pct", "mfe_mean", "mae_mean", "mean_diff", "cohens_d", "ci_lo",
            "ci_hi", "welch_p", "perm_p", "adj_p", "reg_coef", "reg_p", "mde", "ci_within_mde"]
    for f in cats:
        L += [f"### {f}", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for _, r in table[table["family"] == f].iterrows():
            L.append("| " + " | ".join(_fmt(r.get(c)) for c in cols) + " |")
        L.append("")
    L += ["## Exploratory families (descriptive only; unadjusted p; no claims)", ""]
    ecols = ["family", "horizon", "N", "mean", "median", "win_pct", "mfe_mean", "mae_mean", "mean_diff", "ci_lo", "ci_hi", "perm_p"]
    L += ["| " + " | ".join(ecols) + " |", "|" + "---|" * len(ecols)]
    for _, r in table[~table["primary"] & (table["N"] > 0)].iterrows():
        L.append("| " + " | ".join(_fmt(r.get(c)) for c in ecols) + " |")
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- CLI ---
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=str(config.DB_PATH))
    ap.add_argument("--timeframe", default="1h")
    ap.add_argument("--lock", default=str(LOCK))
    ap.add_argument("--run-dir", help="tagging run folder (default: the locked 1h folder)")
    ap.add_argument("--out", default=str(config.ROOT / "results" / "outcomes" / "discovery_1h"))
    ap.add_argument("--write-freeze", action="store_true",
                    help="record the sha256 of the outcome code in docs/OUTCOME_CODE_FREEZE.json and exit (no data is read)")
    ap.add_argument("--confirm-prereg-sha", help="first 12 characters of the lock's preregistration sha256")
    ap.add_argument("--permutations", type=int, default=10_000)
    ap.add_argument("--bootstrap", type=int, default=10_000)
    ap.add_argument("--rerun-identical", action="store_true", help="re-run with IDENTICAL code after a completed run")
    a = ap.parse_args(argv)

    if a.write_freeze:
        if FREEZE.exists():
            raise SystemExit(f"{FREEZE.name} already exists; the freeze is written once.")
        FREEZE.write_text(json.dumps({"code_sha256": code_sha256(), "files": sorted(
            [f"src/outcomes/{p.name}" for p in Path(__file__).parent.glob("*.py")] + list(_DEPENDENCIES)),
            "frozen_at": pd.Timestamp.now(tz="UTC").isoformat()}, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {FREEZE}")
        return 0
    if not a.confirm_prereg_sha:
        raise SystemExit("--confirm-prereg-sha is required")
    check_freeze()
    lock = json.loads(Path(a.lock).read_text(encoding="utf-8"))
    if not lock["sha256"]["preregistration"].startswith(a.confirm_prereg_sha.strip().lower()) or len(a.confirm_prereg_sha.strip()) < 12:
        raise SystemExit("--confirm-prereg-sha does not match the lock record (need the first 12 characters).")
    from src.discovery.tagset import default_run_dir
    run_dir = Path(a.run_dir) if a.run_dir else default_run_dir(a.timeframe)
    verify_lock(lock, run_dir)
    out = Path(a.out)
    marker = out / "RUN_COMPLETE.json"
    code = code_sha256()
    if marker.exists():
        prev = json.loads(marker.read_text(encoding="utf-8"))
        if not (a.rerun_identical and prev["code_sha256"] == code):
            raise SystemExit("The pre-registered discovery analysis was already completed. Re-running is allowed only "
                             "with --rerun-identical and unchanged outcome code.")
    t0 = time.time()
    cs = load_candles(a.db, timeframe=a.timeframe)
    dcs = discovery_candles(cs)                                   # hold-out candles physically removed here
    assert dcs.df["ts"].max() < pd.Timestamp(config.discovery_end(a.timeframe)), "hold-out candle present"
    windows = load_windows(run_dir)
    stable = stable_tags(load_rows(run_dir / "retags.jsonl"))
    obs, excluded = build_observations(dcs, windows, a.timeframe)
    stable_ok = {pd.Timestamp(k).isoformat(): v for k, v in stable.items()}
    membership = fam.membership(stable_ok)
    table, cats = analyze(obs, membership, B_perm=a.permutations, B_boot=a.bootstrap)

    out.mkdir(parents=True, exist_ok=True)
    obs.to_csv(out / "observations.csv", index=False)
    table.to_csv(out / "family_stats.csv", index=False)
    meta = {"lock_prereg_sha256": lock["sha256"]["preregistration"], "lock_windows_sha256": lock["sha256"]["windows_jsonl"],
            "code_sha256": code, "B_perm": a.permutations, "B_boot": a.bootstrap, "n_windows": len(windows),
            "n_valid": len(obs), "excluded": excluded}
    (out / "report.md").write_text(render_report(table, cats, meta), encoding="utf-8")
    summary = {**meta, "categories": cats, "python": platform.python_version(), "numpy": np.__version__,
               "seconds": round(time.time() - t0, 1), "completed_at": pd.Timestamp.now(tz="UTC").isoformat()}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    marker.write_text(json.dumps({"code_sha256": code, "completed_at": summary["completed_at"]}, indent=2), encoding="utf-8")
    print((out / "report.md").read_text(encoding="utf-8"))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
