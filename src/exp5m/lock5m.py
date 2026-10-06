"""Design lock for the 5M experiment: hashes of everything that defines the discovery design, written BEFORE the
discovery sample is generated and before any AI call or outcome exists.

    python -m src.exp5m.lock5m --write          # after the pre-registration is final and coverage was verified
    python -m src.exp5m.lock5m                  # verify only

Also proves the archived 1H experiment is untouched (its pre-registration, family and code hashes must still match
its own lock/freeze records).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

import config
from src.discovery.tagset import file_sha256
from src.exp5m import params, prompts5m

PREREG = config.ROOT / "docs" / "PREREGISTRATION_5M.md"
COVERAGE = config.ROOT / "docs" / "5m" / "COVERAGE_REPORT.json"
DESIGN_LOCK = config.ROOT / "docs" / "PREREG_5M_DESIGN_LOCK.json"
DESIGN_FILES = ("src/exp5m/params.py", "src/exp5m/sampling.py", "src/exp5m/prompts5m.py", "src/exp5m/coverage.py",
                "src/exp5m/io5m.py", "src/exp5m/discover5m.py")
DISCOVERY_LOCK = config.ROOT / "docs" / "PREREG_5M_DISCOVERY_LOCK.json"


def archive_1h_intact() -> dict:
    """The archived 1H experiment must be byte-identical to what its own lock/freeze recorded."""
    lock = json.loads((config.ROOT / "docs" / "PREREG_LOCK.json").read_text(encoding="utf-8"))
    from src.discovery import families
    out = {"preregistration_1h": file_sha256(config.ROOT / "docs" / "PREREGISTRATION.md") == lock["sha256"]["preregistration"],
           "families_1h": file_sha256(Path(families.__file__)) == lock["sha256"]["families_py"]}
    # Recompute the 1H code-freeze hash straight from the files (same formula as the archived module) so that this
    # module never imports the outcome code.
    freeze = json.loads((config.ROOT / "docs" / "OUTCOME_CODE_FREEZE.json").read_text(encoding="utf-8"))
    h = hashlib.sha256()
    for rel in sorted(freeze["files"]):
        h.update(rel.encode() + (config.ROOT / rel).read_bytes().replace(b"\r\n", b"\n"))
    out["outcome_code_1h"] = h.hexdigest() == freeze["code_sha256"]
    return out


def current_record() -> dict:
    for f in (PREREG, COVERAGE):
        if not f.exists():
            raise SystemExit(f"missing {f.relative_to(config.ROOT)} (write the pre-registration / run coverage first)")
    bad = {k: v for k, v in prompts5m.lint_templates().items() if v}
    if bad:
        raise SystemExit(f"prompt templates contain forbidden words: {bad}")
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config.ROOT, capture_output=True, text=True,
                                check=True).stdout.strip()
    except Exception:
        commit = "unknown"
    arch = archive_1h_intact()
    if not all(arch.values()):
        raise SystemExit(f"the archived 1H experiment changed: {arch}")
    return {"experiment": params.EXPERIMENT, "git_commit": commit,
            "hash_method": "sha256 over file bytes with CRLF normalised to LF",
            "sha256": {"preregistration_5m": file_sha256(PREREG), "coverage_report": file_sha256(COVERAGE),
                       **{f: file_sha256(config.ROOT / f) for f in DESIGN_FILES}},
            "prompt_template_sha256": prompts5m.template_hashes(),
            "parameters": {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(params).items()
                           if k.isupper()},
            "archive_1h_intact": arch}


def verify_design_lock() -> dict:
    """The design lock must exist and every frozen file / parameter / prompt must still match it."""
    if not DESIGN_LOCK.exists():
        raise SystemExit("docs/PREREG_5M_DESIGN_LOCK.json is missing: the 5M design is not frozen yet.")
    lock = json.loads(DESIGN_LOCK.read_text(encoding="utf-8"))
    now = current_record()
    changed = [k for k, v in lock["sha256"].items() if now["sha256"].get(k) != v]
    changed += [k for k, v in lock["prompt_template_sha256"].items() if now["prompt_template_sha256"].get(k) != v]
    if changed or lock["parameters"] != now["parameters"]:
        raise SystemExit(f"DESIGN LOCK MISMATCH - the frozen 5M design changed: {changed or 'parameters'}")
    return lock


def require_design_lock(confirm_sha12: str | None) -> dict:
    """Used by every pipeline step: the design must be locked and unchanged, and the caller must name it."""
    lock = verify_design_lock()
    sha = lock["sha256"]["preregistration_5m"]
    if not confirm_sha12 or len(confirm_sha12) < 12 or not sha.startswith(confirm_sha12.lower()):
        raise SystemExit("--confirm-design-sha missing or does not match the design lock (first 12 chars of "
                         f"preregistration_5m sha256: {sha[:12]}).")
    return lock


def build_discovery_lock(run_dir: Path) -> dict:
    """Freeze the finished discovery (sample, vocabulary, tags) and fix the confirmatory set from TAG COUNTS only.
    Every sampled window already has a complete 24-candle forward path (a candidate rule), so valid N = stable N."""
    from src.exp5m import io5m
    design = verify_design_lock()
    windows = io5m.load_jsonl(run_dir / "windows5m.jsonl")
    tags = io5m.load_jsonl(run_dir / "tags5m.jsonl")
    if not windows or not io5m.VOCAB_FILE.exists():
        raise SystemExit("CANNOT LOCK: sample or vocabulary missing")
    vrec = json.loads(io5m.VOCAB_FILE.read_text(encoding="utf-8"))
    vocab = prompts5m.Vocabulary(vrec["families"])
    problems = []
    if vocab.sha256 != vrec["sha256"]:
        problems.append("vocabulary file does not match its recorded hash")
    meta = json.loads((run_dir / "sample_meta.json").read_text(encoding="utf-8"))
    if file_sha256(run_dir / "windows5m.jsonl") != meta["windows5m_jsonl_sha256"]:
        problems.append("windows5m.jsonl changed since the sample was built")
    if len({w["chart_style_sha256"] for w in windows}) != 1:
        problems.append("more than one chart style in the sample")
    good = io5m.clean_rows(tags)
    missing = [w["end_ts"] for w in windows if not all((w["end_ts"], p) in good for p in range(1, params.PASSES + 1))]
    if missing:
        problems.append(f"{len(missing)} windows lack a clean tagging pass (e.g. {missing[0]}); finish D3 first")
    used = [r for r in good.values() if r["end_ts"] in {w["end_ts"] for w in windows}]
    for key in ("model", "vocab_sha256"):
        vals = {r.get(key) for r in used}
        if len(vals) > 1:
            problems.append(f"mixed {key}: {sorted(map(str, vals))}")
    if any(r["vocab_sha256"] != vocab.sha256 for r in used):
        problems.append("tags were produced with a different vocabulary than the frozen file")
    attempts = io5m.load_jsonl(run_dir / "d2_attempts.jsonl")
    if not any(a["accepted"] for a in attempts):
        problems.append("no accepted D2 attempt on record")
    d1 = io5m.clean_rows(io5m.load_jsonl(run_dir / "d1_descriptions.jsonl"))
    need = [w["end_ts"] for w in windows if w["description_stage"]]
    if any(e not in d1 for e in need):
        problems.append("D1 descriptions incomplete")
    if problems:
        raise SystemExit("CANNOT LOCK:\n  - " + "\n  - ".join(problems))
    stable = io5m.stable_tags(tags, params.PASSES)
    counts = {f["name"]: sum(1 for t in stable.values() if f["name"] in t) for f in vocab.families}
    confirmatory = sorted([f for f, n in counts.items() if n >= params.N_MIN], key=lambda f: (-counts[f], f))
    return {"experiment": params.EXPERIMENT, "design_lock_sha256": file_sha256(DESIGN_LOCK),
            "design_lock_prereg_sha256": design["sha256"]["preregistration_5m"],
            "n_windows": len(windows), "n_windows_with_stable_tag": sum(1 for t in stable.values() if t),
            "model": next(iter({r["model"] for r in used})), "passes": params.PASSES,
            "vocabulary": {"families": vocab.families, "sha256": vocab.sha256, "file_sha256": file_sha256(io5m.VOCAB_FILE)},
            "sha256": {"windows5m_jsonl": file_sha256(run_dir / "windows5m.jsonl"),
                       "sample_meta_json": file_sha256(run_dir / "sample_meta.json"),
                       "tags5m_jsonl": file_sha256(run_dir / "tags5m.jsonl"),
                       "d1_descriptions_jsonl": file_sha256(run_dir / "d1_descriptions.jsonl"),
                       "d2_attempts_jsonl": file_sha256(run_dir / "d2_attempts.jsonl"),
                       "d3_user_prompt_pass1": hashlib.sha256(vocab.user_prompt(False).encode()).hexdigest(),
                       "d3_user_prompt_pass2": hashlib.sha256(vocab.user_prompt(True).encode()).hexdigest()},
            "family_window_counts": counts, "n_min": params.N_MIN, "confirmatory_families": confirmatory,
            "n_confirmatory_cells": len(confirmatory) * len(params.HORIZONS),
            "sample_meta": meta}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--stage", choices=["design", "discovery"], default="design")
    ap.add_argument("--run-dir")
    a = ap.parse_args(argv)
    if a.stage == "discovery":
        from src.exp5m import io5m
        rec = {"locked_at": pd.Timestamp.now(tz="UTC").isoformat(), **build_discovery_lock(Path(a.run_dir) if a.run_dir else io5m.RUN_DIR)}
        if a.write:
            if DISCOVERY_LOCK.exists():
                raise SystemExit("discovery lock already exists; it is written once.")
            DISCOVERY_LOCK.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
            print(f"wrote {DISCOVERY_LOCK}")
        print(json.dumps(rec, indent=2))
        return 0
    rec = current_record()
    if a.write:
        if DESIGN_LOCK.exists():
            raise SystemExit("design lock already exists; it is written once.")
        rec = {"locked_at": pd.Timestamp.now(tz="UTC").isoformat(), **rec}
        DESIGN_LOCK.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {DESIGN_LOCK}")
    print(json.dumps(rec, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
