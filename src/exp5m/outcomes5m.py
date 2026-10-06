"""Pre-registered 5M DISCOVERY outcome analysis (docs/PREREGISTRATION_5M.md).

    python -m src.exp5m.outcomes5m --write-freeze                      # once, after review, BEFORE the analysis
    python -m src.exp5m.outcomes5m --confirm-design-sha <12 chars>     # the single analysis run

The statistics are the archived 1H code imported UNCHANGED (src.outcomes.analyze / stats / forward). This module only
wires the 5M sample, the frozen vocabulary and the discovery lock into them. It refuses to run unless
  * the 5M design lock, the 5M discovery lock and the 5M outcome-code freeze all match the files on disk,
  * the archived 1H experiment is untouched,
  * hold-out candles (>= 2026-06-01) were physically removed before any candle is read.
The analysis can be completed only once (RUN_COMPLETE.json). Outcomes are DESCRIPTIVE statistics of the historical
price series, not fills; there is no entry, exit, stop, target, cost or position anywhere in this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd

import config
from src.data.loader import load_candles, tf_to_seconds
from src.discovery.discover import discovery_candles
from src.discovery.tagset import file_sha256
from src.exp5m import io5m, lock5m, params, prompts5m
from src.outcomes import analyze as arch                         # archived, frozen statistics (imported, not copied)
from src.outcomes import stats as arch_stats                     # noqa: F401  (part of the frozen code hash)

FREEZE = config.ROOT / "docs" / "OUTCOME5M_CODE_FREEZE.json"
OUT_DIR = config.ROOT / "results" / "exp5m" / "outcomes"
POLICY = config.ROOT / "docs" / "REAL_FILLS_POLICY.md"

REAL_FILLS_SENTENCE = (
    "Forward return, future high, future low, MFE and MAE are descriptive statistics of the historical price series, "
    "measured from the close of the last candle of each visual window. They are not trade fills, they were not shown "
    "to be executable prices, and they must not be read as realized trades.")
NO_PASS_STATEMENT = "No robust predictive visual family was established in the 5M discovery sample."
SCOPE_NOTE = ("Scope: this report covers the 5M DISCOVERY sample only (windows ending before "
              f"{params.DISCOVERY_END}). It does not revisit the archived 1H experiment.")

_EXTRA_FILES = ("src/exp5m/outcomes5m.py", "src/exp5m/params.py", "src/exp5m/prompts5m.py", "src/exp5m/io5m.py",
                "src/exp5m/lock5m.py")


# --------------------------------------------------------------------------- guards ---
def frozen_files() -> list[str]:
    """Everything the 5M outcome analysis depends on: this wrapper, the archived 1H outcome code and its
    dependencies (exactly the set the 1H freeze covers) and the 5M parameter / prompt / lock modules."""
    one_h = sorted(f"src/outcomes/{p.name}" for p in (config.ROOT / "src" / "outcomes").glob("*.py"))
    return sorted(set(one_h) | set(arch._DEPENDENCIES) | set(_EXTRA_FILES))


def code_sha256() -> str:
    h = hashlib.sha256()
    for rel in frozen_files():
        h.update(rel.encode() + (config.ROOT / rel).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def write_freeze(path: Path = FREEZE) -> dict:
    if path.exists():
        raise SystemExit(f"{path.name} already exists; the freeze is written once.")
    rec = {"code_sha256": code_sha256(), "files": frozen_files(),
           "frozen_at": pd.Timestamp.now(tz="UTC").isoformat(),
           "note": "Written after the discovery lock and BEFORE any 5M outcome was computed. Any change to these "
                   "files blocks the analysis."}
    path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec


def check_freeze(path: Path = FREEZE) -> dict:
    if not path.exists():
        raise SystemExit(f"{path.name} is missing: the 5M outcome code has not been frozen yet (--write-freeze).")
    rec = json.loads(path.read_text(encoding="utf-8"))
    if rec["code_sha256"] != code_sha256() or rec["files"] != frozen_files():
        raise SystemExit("The 5M outcome code (or a dependency) changed since it was frozen. No changes are allowed "
                         "once the analysis may begin.")
    return rec


def require_required_statements(policy: Path = POLICY) -> str:
    """The required real-fills sentence must exist verbatim in the policy document, and the sample must carry the
    limitation statement; otherwise nothing is written."""
    text = re.sub(r"\s+", " ", re.sub(r"(?m)^>\s?", "", policy.read_text(encoding="utf-8"))).strip()
    if REAL_FILLS_SENTENCE not in text:
        raise SystemExit("REAL_FILLS_POLICY.md does not contain the required descriptive-statistics sentence verbatim.")
    return REAL_FILLS_SENTENCE


def verify_discovery_lock(run_dir: Path, lock_path: Path = lock5m.DISCOVERY_LOCK) -> dict:
    """Every file the discovery lock recorded must be byte-identical, and the confirmatory set must be the one
    that the tag counts of the locked files produce."""
    if not lock_path.exists():
        raise SystemExit("docs/PREREG_5M_DISCOVERY_LOCK.json is missing: discovery is not locked.")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    files = {"windows5m_jsonl": "windows5m.jsonl", "sample_meta_json": "sample_meta.json", "tags5m_jsonl": "tags5m.jsonl",
             "d1_descriptions_jsonl": "d1_descriptions.jsonl", "d2_attempts_jsonl": "d2_attempts.jsonl"}
    bad = [k for k, f in files.items() if file_sha256(run_dir / f) != lock["sha256"][k]]
    if file_sha256(io5m.VOCAB_FILE) != lock["vocabulary"]["file_sha256"]:
        bad.append("vocabulary_file")
    vocab = prompts5m.Vocabulary(lock["vocabulary"]["families"])
    if vocab.sha256 != lock["vocabulary"]["sha256"]:
        bad.append("vocabulary_sha256")
    for k, rev in (("d3_user_prompt_pass1", False), ("d3_user_prompt_pass2", True)):
        if hashlib.sha256(vocab.user_prompt(rev).encode()).hexdigest() != lock["sha256"][k]:
            bad.append(k)
    if file_sha256(lock5m.DESIGN_LOCK) != lock["design_lock_sha256"]:
        bad.append("design_lock")
    if bad:
        raise SystemExit("DISCOVERY LOCK MISMATCH - the frozen discovery changed: " + ", ".join(bad))
    stable = io5m.stable_tags(io5m.load_jsonl(run_dir / "tags5m.jsonl"), params.PASSES)
    counts = {f["name"]: sum(1 for t in stable.values() if f["name"] in t) for f in vocab.families}
    conf = sorted([f for f, n in counts.items() if n >= params.N_MIN], key=lambda f: (-counts[f], f))
    if counts != lock["family_window_counts"] or conf != lock["confirmatory_families"]:
        raise SystemExit("DISCOVERY LOCK MISMATCH - tag counts or the confirmatory set differ from the lock.")
    return lock


def assert_same_statistics() -> None:
    """The statistics are the archived ones; the 5M parameters must agree with them exactly."""
    ok = (tuple(arch.HORIZONS) == tuple(params.HORIZONS) and arch.N_MIN == params.N_MIN and arch.ALPHA == params.ALPHA
          and (arch.SEED_PERM, arch.SEED_BOOT) == (params.SEED_PERM, params.SEED_BOOT))
    if not ok:
        raise SystemExit("5M statistical parameters differ from the archived statistics code.")


# ------------------------------------------------------------------------ analysis ---
def membership_from_tags(tags: list[dict], family_names: list[str]) -> dict[str, set]:
    """{family: {end_ts}} using STABLE tags only (a family tag present in every pass); `none` is not a family."""
    stable = io5m.stable_tags(tags, params.PASSES)
    mem = {f: set() for f in family_names}
    for e, ts in stable.items():
        for t in ts:
            if t in mem:
                mem[t].add(pd.Timestamp(e).isoformat())
    return mem


def run_analysis(dcs, windows: list[dict], tags: list[dict], family_names: list[str], confirmatory: list[str],
                 B_perm: int = params.B_PERM, B_boot: int = params.B_BOOT):
    obs, excluded = arch.build_observations(dcs, windows, params.TIMEFRAME)
    membership = membership_from_tags(tags, family_names)
    table, cats = arch.analyze(obs, membership, primary=confirmatory, horizons=params.HORIZONS,
                               B_perm=B_perm, B_boot=B_boot, seed_perm=params.SEED_PERM, seed_boot=params.SEED_BOOT)
    return obs, excluded, membership, table, cats


def final_statement(cats: dict) -> str:
    passed = [f for f, c in cats.items() if c["category"] == arch.CATEGORY_PASS]
    if not passed:
        return NO_PASS_STATEMENT
    return (f"{len(passed)} discovery family(ies) passed: {', '.join(passed)}. Each is only a candidate; "
            "it must still be confirmed once on the untouched hold-out.")


# ----------------------------------------------------------------------- reporting ---
def render_report(table: pd.DataFrame, cats: dict, meta: dict, counts: dict) -> str:
    fmt = arch._fmt
    L = ["# 5M discovery outcome analysis (pre-registered)", "", SCOPE_NOTE, "",
         f"**Limitation.** {meta['limitation_statement']}", "",
         f"**Descriptive statistics only.** {meta['real_fills_statement']}", "",
         f"Design lock prereg sha256 `{meta['design_prereg_sha256']}` | discovery lock sha256 `{meta['discovery_lock_sha256']}`",
         f"Outcome code sha256 `{meta['code_sha256']}` | seeds perm={params.SEED_PERM} boot={params.SEED_BOOT} | "
         f"B_perm={meta['B_perm']} B_boot={meta['B_boot']}", "",
         f"Windows tagged: {meta['n_windows']} | with valid forward path: {meta['n_valid']} | excluded: {meta['excluded']}",
         "", "Outcomes: forward close return, MFE and MAE (% from the close of the last candle, T) at 1/3/6/12/24 candles "
         "(5-minute candles). Effects are mean differences in percentage points against the non-family population.", "",
         "**Reading note:** the non-family population contains the other families. A real effect in one family can "
         "appear as an opposite-signed (mirrored) difference in another; PASS in several families may reflect a single "
         "contrast. The maxT correction accounts for this dependence.", "",
         "## Stable-tag window counts", "", "| family | stable windows | confirmatory (N>=30) |", "|---|---|---|"]
    for f, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        L.append(f"| {f} | {n} | {'yes' if f in cats else 'no (exploratory)'} |")
    L += ["", "## Confirmatory-family verdicts (discovery)", ""]
    if cats:
        L += ["| family | N | category | frozen hold-out horizon | note |", "|---|---|---|---|---|"]
        for f, c in cats.items():
            L.append(f"| {f} | {c['N']} | **{c['category']}** | {c['frozen_horizon'] or ''} | {c['reason']} |")
    else:
        L.append("No family reached the minimum of 30 stable windows, so there is no confirmatory family.")
    L += ["", "A DOES NOT PASS means effects at least as large as the MDE are not supported by the data; it does NOT "
          "mean no edge exists. INCONCLUSIVE / LOW POWER means the data cannot support a reliable conclusion.", "",
          f"**Conclusion:** {meta['final_statement']}", ""]
    cols = ["horizon", "N", "mean", "median", "win_pct", "mfe_mean", "mae_mean", "mean_diff", "cohens_d", "ci_lo",
            "ci_hi", "welch_p", "perm_p", "adj_p", "reg_coef", "reg_p", "mde", "ci_within_mde"]
    for f in cats:
        L += [f"### {f}", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for _, r in table[table["family"] == f].iterrows():
            L.append("| " + " | ".join(fmt(r.get(c)) for c in cols) + " |")
        L.append("")
    L += ["## Exploratory families (N < 30; descriptive only; unadjusted p; no claims)", ""]
    ecols = ["family", "horizon", "N", "mean", "median", "win_pct", "mfe_mean", "mae_mean", "mean_diff", "ci_lo", "ci_hi", "perm_p"]
    L += ["| " + " | ".join(ecols) + " |", "|" + "---|" * len(ecols)]
    if not table.empty:
        for _, r in table[~table["primary"] & (table["N"] > 0)].iterrows():
            L.append("| " + " | ".join(fmt(r.get(c)) for c in ecols) + " |")
    else:
        L.append("| (no statistics were computed: no family reached N>=30) |" + " |" * (len(ecols) - 1))
    L += ["", "---", REAL_FILLS_SENTENCE, ""]
    return "\n".join(L) + "\n"


def execute(db: str, run_dir: Path, out: Path, confirm: str | None, B_perm: int = params.B_PERM,
            B_boot: int = params.B_BOOT, rerun_identical: bool = False) -> dict:
    """Guards, the single analysis, the files. Returns the summary dict."""
    design = lock5m.require_design_lock(confirm)
    check_freeze()
    assert_same_statistics()
    sentence = require_required_statements()
    lock = verify_discovery_lock(run_dir)
    meta_sample = json.loads((run_dir / "sample_meta.json").read_text(encoding="utf-8"))
    limitation = meta_sample.get("limitation_statement")
    if not limitation:
        raise SystemExit("sample_meta.json carries no limitation_statement; refusing to produce a report without it.")
    marker = out / "RUN_COMPLETE.json"
    code = code_sha256()
    if marker.exists():
        prev = json.loads(marker.read_text(encoding="utf-8"))
        if not (rerun_identical and prev["code_sha256"] == code):
            raise SystemExit("The 5M discovery analysis was already completed. Re-running is allowed only with "
                             "--rerun-identical and unchanged code.")
    t0 = time.time()
    cs = load_candles(db, params.SYMBOL, params.TIMEFRAME)
    dcs = discovery_candles(cs, end=params.DISCOVERY_END)             # hold-out candles physically removed here
    assert dcs.df["ts"].max() < pd.Timestamp(params.DISCOVERY_END), "hold-out candle present"
    windows = io5m.load_jsonl(run_dir / "windows5m.jsonl")
    tags = io5m.load_jsonl(run_dir / "tags5m.jsonl")
    names = [f["name"] for f in lock["vocabulary"]["families"]]
    confirmatory = list(lock["confirmatory_families"])
    out.mkdir(parents=True, exist_ok=True)
    counts = lock["family_window_counts"]
    if confirmatory:
        obs, excluded, membership, table, cats = run_analysis(dcs, windows, tags, names, confirmatory, B_perm, B_boot)
        obs.to_csv(out / "observations.csv", index=False)
        table.to_csv(out / "family_stats.csv", index=False)
    else:
        excluded, table, cats = {}, pd.DataFrame(), {}
        obs = pd.DataFrame()
    n_pass = sum(1 for c in cats.values() if c["category"] == arch.CATEGORY_PASS)
    meta = {"design_prereg_sha256": design["sha256"]["preregistration_5m"],
            "discovery_lock_sha256": file_sha256(lock5m.DISCOVERY_LOCK), "code_sha256": code, "B_perm": B_perm,
            "B_boot": B_boot, "n_windows": len(windows), "n_valid": len(obs), "excluded": excluded,
            "limitation_statement": limitation, "real_fills_statement": sentence,
            "final_statement": final_statement(cats)}
    (out / "report.md").write_text(render_report(table, cats, meta, counts), encoding="utf-8")
    summary = {**meta, "experiment": params.EXPERIMENT, "confirmatory_families": confirmatory,
               "family_window_counts": counts, "categories": cats, "any_pass": n_pass > 0,
               "holdout_allowed": n_pass > 0, "alpha_holdout": (params.ALPHA / n_pass) if n_pass else None,
               "python": platform.python_version(), "numpy": np.__version__, "seconds": round(time.time() - t0, 1),
               "completed_at": pd.Timestamp.now(tz="UTC").isoformat()}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    marker.write_text(json.dumps({"code_sha256": code, "completed_at": summary["completed_at"]}, indent=2), encoding="utf-8")
    return summary


# ----------------------------------------------------------------------------- CLI ---
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=str(config.DB_PATH))
    ap.add_argument("--run-dir", default=str(io5m.RUN_DIR))
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--write-freeze", action="store_true",
                    help="record the sha256 of the outcome code in docs/OUTCOME5M_CODE_FREEZE.json and exit (no data is read)")
    ap.add_argument("--confirm-design-sha", help="first 12 characters of the preregistration sha256 in the design lock")
    ap.add_argument("--permutations", type=int, default=params.B_PERM)
    ap.add_argument("--bootstrap", type=int, default=params.B_BOOT)
    ap.add_argument("--rerun-identical", action="store_true")
    a = ap.parse_args(argv)
    if a.write_freeze:
        lock5m.verify_design_lock()
        verify_discovery_lock(Path(a.run_dir))
        rec = write_freeze()
        print(f"wrote {FREEZE}\ncode_sha256 {rec['code_sha256']}")
        return 0
    s = execute(a.db, Path(a.run_dir), Path(a.out), a.confirm_design_sha, a.permutations, a.bootstrap, a.rerun_identical)
    print((Path(a.out) / "report.md").read_text(encoding="utf-8"))
    print(f"wrote {a.out}  | {s['final_statement']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
