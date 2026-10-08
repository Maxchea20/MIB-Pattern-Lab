"""Design lock (F0) for the Setup Discovery experiment: hashes of everything that defines the discovery design, written
BEFORE the sample is generated and before any AI call or outcome exists.

    python -m src.setups.lock                 # verify the current state / show the record
    python -m src.setups.lock --write         # write docs/PREREG_SETUPS_DESIGN_LOCK.json (once)

Also proves that the canonical dataset is the expected file (name, bytes, SHA-256) and that the archived 1H and 5M
experiments are untouched. This module never imports outcome code.
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
from src.setups import params, prompts

CANONICAL_DB = config.ROOT / "data" / params.DB_NAME
PREREG = config.ROOT / "docs" / "PREREGISTRATION_SETUPS.md"
DESIGN_DOC = config.ROOT / "docs" / "SETUP_DISCOVERY_DESIGN.md"
POLICY = config.ROOT / "docs" / "REAL_FILLS_POLICY.md"
COVERAGE = config.ROOT / "docs" / "setups" / "COVERAGE_RESEARCH_BINANCE_REPORT.json"
DESIGN_LOCK = config.ROOT / "docs" / "PREREG_SETUPS_DESIGN_LOCK.json"          # F0 (original; never modified)
F0B_LOCK = config.ROOT / "docs" / "PREREG_SETUPS_DESIGN_LOCK_F0B.json"        # F0b: F0 + the Stage B citation amendment
AMENDMENT = config.ROOT / "docs" / "setups" / "AMENDMENT_F0B.md"
F0B_AMENDED = ("src/setups/prompts.py", "src/setups/discover.py")             # the ONLY locked files F0b may change
RUN_DIR = config.ROOT / "results" / "setups" / "discovery"
F0B_PRESERVED = ("windows_setups.jsonl", "sample_meta.json", "stage_a.jsonl", "chart_verification.json")
F0B_PREFIX_FILES = ("stage_b_attempts.jsonl", "cost_log.jsonl")                # append-only: the existing lines are preserved
DOCS = {"preregistration_setups": PREREG, "design_doc": DESIGN_DOC, "real_fills_policy": POLICY, "coverage_report": COVERAGE}
# Code and archived modules the discovery design depends on (archived ones are used UNCHANGED; any edit blocks the run).
DESIGN_FILES = ("src/setups/params.py", "src/setups/store.py", "src/setups/costlog.py", "src/setups/prompts.py",
                "src/setups/sampling.py", "src/setups/discover.py", "src/setups/audit.py", "src/setups/coverage_audit.py",
                "src/charts/renderer.py", "src/charts/windows.py", "src/charts/normalize.py", "src/data/loader.py",
                "src/validation/window_validation.py", "src/discovery/audit.py", "src/discovery/discover.py",
                "src/discovery/cost.py", "src/discovery/tagset.py")


def sha256_file_bytes(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_database(path) -> dict:
    """The canonical dataset: right file name, exact byte size and SHA-256. Refuses anything else."""
    p = Path(path)
    if p.name.lower() in params.FORBIDDEN_DB_NAMES:
        raise SystemExit(f"{p.name} is NOT the dataset of the Setup Discovery experiment and must not be used.")
    if p.name.lower() != params.DB_NAME:
        raise SystemExit(f"The canonical dataset is data/{params.DB_NAME}; got {p.name}.")
    if not p.exists():
        raise SystemExit(f"database not found: {p}")
    size, sha = p.stat().st_size, sha256_file_bytes(p)
    if size != params.EXPECTED_DB_BYTES or sha != params.EXPECTED_DB_SHA256:
        raise SystemExit(f"{p.name} is not the dataset that was pre-registered (bytes {size}, sha256 {sha}).")
    return {"file": p.name, "bytes": size, "sha256": sha}


def archive_intact() -> dict:
    """Archived 1H and 5M experiments are byte-identical to their own lock/freeze records."""
    from src.exp5m import lock5m
    out = dict(lock5m.archive_1h_intact())
    lock5m.verify_design_lock()                                   # 5M design lock still matches (raises otherwise)
    out["design_5m"] = True
    for k, rel in (("discovery_lock_5m", "docs/PREREG_5M_DISCOVERY_LOCK.json"),
                   ("outcome_freeze_5m", "docs/OUTCOME5M_CODE_FREEZE.json")):
        out[k] = (config.ROOT / rel).exists()
    return out


def config_snapshot() -> dict:
    from src.setups import sampling
    return {"chart_style_sha256": sampling.style_sha(), "openai_price_usd_per_m": dict(config.OPENAI_PRICE_USD_PER_M)}


def current_record() -> dict:
    for f in DOCS.values():
        if not f.exists():
            raise SystemExit(f"missing {f.relative_to(config.ROOT)}")
    bad = {k: v for k, v in prompts.lint_templates().items() if v}
    if bad:
        raise SystemExit(f"prompt templates contain forbidden words: {bad}")
    arch = archive_intact()
    if not all(arch.values()):
        raise SystemExit(f"an archived experiment changed: {arch}")
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config.ROOT, capture_output=True, text=True,
                                check=True).stdout.strip()
    except Exception:
        commit = "unknown"
    return {"experiment": params.EXPERIMENT, "git_commit": commit,
            "hash_method": "sha256 over file bytes with CRLF normalised to LF",
            "dataset": {"file": f"data/{params.DB_NAME}", "bytes": params.EXPECTED_DB_BYTES, "sha256": params.EXPECTED_DB_SHA256,
                        "statement": f"data/{params.DB_NAME} is the canonical dataset for the Setup Discovery experiment."},
            "sha256": {**{k: file_sha256(v) for k, v in DOCS.items()}, **{f: file_sha256(config.ROOT / f) for f in DESIGN_FILES}},
            "prompt_template_sha256": prompts.template_hashes(),
            "config": config_snapshot(),
            "parameters": json.loads(json.dumps({k: v for k, v in vars(params).items() if k.isupper()})),
            "archive_intact": arch}


def _verify_f0(lock_path: Path | None = None) -> dict:
    p = Path(lock_path or DESIGN_LOCK)
    if not p.exists():
        raise SystemExit("docs/PREREG_SETUPS_DESIGN_LOCK.json is missing: the Setup Discovery design is not frozen yet.")
    lock = json.loads(p.read_text(encoding="utf-8"))
    now = current_record()
    changed = [k for k, v in lock["sha256"].items() if now["sha256"].get(k) != v]
    changed += [k for k, v in lock["prompt_template_sha256"].items() if now["prompt_template_sha256"].get(k) != v]
    changed += [k for k in ("config", "dataset") if lock[k] != now[k]]
    if changed or lock["parameters"] != now["parameters"]:
        raise SystemExit(f"DESIGN LOCK MISMATCH - the frozen design changed: {changed or 'parameters'}")
    return lock


def _lines_sha(path: Path, n: int | None = None) -> dict:
    lines = Path(path).read_bytes().replace(b"\r\n", b"\n").split(b"\n")
    lines = [l for l in lines if l.strip()]
    lines = lines if n is None else lines[:n]
    return {"lines": len(lines), "sha256_of_these_lines": hashlib.sha256(b"\n".join(lines) + b"\n").hexdigest()}


def f0b_record(run_dir: Path | None = None, f0_lock_path: Path | None = None) -> dict:
    """What F0b will freeze, computed from the current files. Fails unless the ONLY locked files that differ from the original
    F0 lock are exactly F0B_AMENDED, and everything else the F0 lock froze is byte-identical."""
    run_dir = Path(run_dir or RUN_DIR)
    f0p = Path(f0_lock_path or DESIGN_LOCK)
    if not f0p.exists() or not AMENDMENT.exists():
        raise SystemExit("F0b needs the original F0 lock and docs/setups/AMENDMENT_F0B.md.")
    f0 = json.loads(f0p.read_text(encoding="utf-8"))
    now = current_record()
    changed = sorted(k for k, v in f0["sha256"].items() if now["sha256"].get(k) != v)
    if changed != sorted(F0B_AMENDED):
        raise SystemExit(f"F0b may change exactly {sorted(F0B_AMENDED)}; files differing from the F0 lock: {changed}")
    for k in ("prompt_template_sha256", "parameters", "config", "dataset"):
        if f0[k] != now[k]:
            raise SystemExit(f"F0b must not change {k}")
    preserved = {n: {"sha256": file_sha256(run_dir / n)} for n in F0B_PRESERVED}
    prefixes = {n: _lines_sha(run_dir / n) for n in F0B_PREFIX_FILES}
    tests = {str(p.relative_to(config.ROOT).as_posix()): file_sha256(p) for p in sorted((config.ROOT / "tests").glob("test_setups_*.py"))}
    return {"amendment": {"id": "F0b", "rule": "Stage B: unknown supporting ids are dropped and audited; support = distinct VERIFIED ids",
                          "document": "docs/setups/AMENDMENT_F0B.md", "document_sha256": file_sha256(AMENDMENT)},
            "original_f0_lock": {"file": str(f0p.relative_to(config.ROOT).as_posix()) if f0p.is_relative_to(config.ROOT) else f0p.name,
                                 "file_sha256": file_sha256(f0p), "git_commit": f0["git_commit"], "locked_at": f0["locked_at"]},
            "amended_files": {k: {"f0_sha256": f0["sha256"][k], "f0b_sha256": now["sha256"][k]} for k in F0B_AMENDED},
            "unchanged_since_f0_sha256": {k: v for k, v in f0["sha256"].items() if k not in F0B_AMENDED},
            "tests_sha256": tests, "preserved_records": preserved, "preserved_append_only_prefixes": prefixes,
            "dataset": now["dataset"], "git_commit": now["git_commit"]}


def verify_f0b(f0b_path: Path | None = None, run_dir: Path | None = None, f0_lock_path: Path | None = None) -> dict:
    """F0b holds iff: the original F0 lock file is byte-identical; every file F0 froze is unchanged except the two amended
    files, which equal their F0b hashes; the amendment, tests, Stage A record, chart verification and the existing lines of
    the append-only Stage B / cost files are unchanged; templates, parameters, config and dataset are unchanged."""
    run_dir = Path(run_dir or RUN_DIR)
    p = Path(f0b_path or F0B_LOCK)
    if not p.exists():
        raise SystemExit("docs/PREREG_SETUPS_DESIGN_LOCK_F0B.json is missing: the amended design is not frozen yet.")
    f0b = json.loads(p.read_text(encoding="utf-8"))
    f0p = Path(f0_lock_path or DESIGN_LOCK)
    f0 = json.loads(f0p.read_text(encoding="utf-8"))
    bad = []
    if file_sha256(f0p) != f0b["original_f0_lock"]["file_sha256"]:
        bad.append("original_f0_lock")
    now = current_record()
    for k, v in f0b["unchanged_since_f0_sha256"].items():
        if now["sha256"].get(k) != v or f0["sha256"].get(k) != v:
            bad.append(k)
    for k, v in f0b["amended_files"].items():
        if k not in F0B_AMENDED or f0["sha256"].get(k) != v["f0_sha256"] or now["sha256"].get(k) != v["f0b_sha256"]:
            bad.append(k)
    if set(f0b["amended_files"]) != set(F0B_AMENDED) or set(f0b["amended_files"]) | set(f0b["unchanged_since_f0_sha256"]) != set(f0["sha256"]):
        bad.append("file_set")
    if file_sha256(AMENDMENT) != f0b["amendment"]["document_sha256"]:
        bad.append("amendment_document")
    for k, v in f0b["tests_sha256"].items():
        if file_sha256(config.ROOT / k) != v:
            bad.append(k)
    for n, v in f0b["preserved_records"].items():
        if file_sha256(run_dir / n) != v["sha256"]:
            bad.append(n)
    for n, v in f0b["preserved_append_only_prefixes"].items():
        if _lines_sha(run_dir / n, v["lines"]) != v:
            bad.append(n + " (existing lines)")
    for k in ("prompt_template_sha256", "parameters", "config", "dataset"):
        if f0[k] != now[k]:
            bad.append(k)
    if bad:
        raise SystemExit(f"F0b LOCK MISMATCH - the amended design changed: {sorted(set(bad))}")
    return {**f0, "f0b": f0b}


def verify_design_lock(lock_path: Path | None = None) -> dict:
    """With an explicit path: verify that single (F0-format) record. Otherwise F0b governs once it exists; before that F0."""
    if lock_path is not None:
        return _verify_f0(lock_path)
    return verify_f0b() if F0B_LOCK.exists() else _verify_f0()


def require_design_lock(confirm_sha12: str | None, lock_path: Path | None = None) -> dict:
    """Used by every pipeline step: the design must be locked and unchanged, and the caller must name it."""
    lock = verify_design_lock(lock_path)
    sha = lock["sha256"]["preregistration_setups"]
    if not confirm_sha12 or len(confirm_sha12) < 12 or not sha.startswith(confirm_sha12.lower()):
        raise SystemExit("--confirm-design-sha missing or does not match the design lock (first 12 chars of "
                         f"preregistration_setups sha256: {sha[:12]}).")
    return lock


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--write-f0b", action="store_true", help="write docs/PREREG_SETUPS_DESIGN_LOCK_F0B.json (once), after the amendment is approved")
    ap.add_argument("--db", default=str(CANONICAL_DB))
    a = ap.parse_args(argv)
    db = verify_database(a.db)                                   # the lock is only written for the exact canonical file
    if a.write_f0b:
        if F0B_LOCK.exists():
            raise SystemExit("F0b lock already exists; it is written once.")
        rec = {"locked_at": pd.Timestamp.now(tz="UTC").isoformat(), "database_verified": db, **f0b_record()}
        F0B_LOCK.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {F0B_LOCK}\n" + json.dumps(rec, indent=2))
        return 0
    rec = current_record()
    if a.write:
        if DESIGN_LOCK.exists():
            raise SystemExit("design lock already exists; it is written once.")
        rec = {"locked_at": pd.Timestamp.now(tz="UTC").isoformat(), "database_verified": db, **rec}
        DESIGN_LOCK.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {DESIGN_LOCK}")
    print(json.dumps(rec, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
