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
DESIGN_LOCK = config.ROOT / "docs" / "PREREG_SETUPS_DESIGN_LOCK.json"
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


def verify_design_lock(lock_path: Path | None = None) -> dict:
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
    ap.add_argument("--db", default=str(CANONICAL_DB))
    a = ap.parse_args(argv)
    db = verify_database(a.db)                                   # the lock is only written for the exact canonical file
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
