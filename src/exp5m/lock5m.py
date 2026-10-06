"""Design lock for the 5M experiment: hashes of everything that defines the discovery design, written BEFORE the
discovery sample is generated and before any AI call or outcome exists.

    python -m src.exp5m.lock5m --write          # after the pre-registration is final and coverage was verified
    python -m src.exp5m.lock5m                  # verify only

Also proves the archived 1H experiment is untouched (its pre-registration, family and code hashes must still match
its own lock/freeze records).
"""
from __future__ import annotations

import argparse
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
DESIGN_FILES = ("src/exp5m/params.py", "src/exp5m/sampling.py", "src/exp5m/prompts5m.py", "src/exp5m/coverage.py")


def archive_1h_intact() -> dict:
    """The archived 1H experiment must be byte-identical to what its own lock/freeze recorded."""
    lock = json.loads((config.ROOT / "docs" / "PREREG_LOCK.json").read_text(encoding="utf-8"))
    from src.discovery import families
    out = {"preregistration_1h": file_sha256(config.ROOT / "docs" / "PREREGISTRATION.md") == lock["sha256"]["preregistration"],
           "families_1h": file_sha256(Path(families.__file__)) == lock["sha256"]["families_py"]}
    # Recompute the 1H code-freeze hash straight from the files (same formula as the archived module) so that this
    # module never imports the outcome code.
    import hashlib
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


def require_design_lock(confirm_sha12: str | None) -> dict:
    """Used by sampling --build: the design must be locked and unchanged, and the caller must name it."""
    if not DESIGN_LOCK.exists():
        raise SystemExit("docs/PREREG_5M_DESIGN_LOCK.json is missing: the 5M design is not frozen yet.")
    lock = json.loads(DESIGN_LOCK.read_text(encoding="utf-8"))
    now = current_record()
    changed = [k for k, v in lock["sha256"].items() if now["sha256"].get(k) != v]
    changed += [k for k, v in lock["prompt_template_sha256"].items() if now["prompt_template_sha256"].get(k) != v]
    if changed or lock["parameters"] != now["parameters"]:
        raise SystemExit(f"DESIGN LOCK MISMATCH - the frozen 5M design changed: {changed or 'parameters'}")
    sha = lock["sha256"]["preregistration_5m"]
    if not confirm_sha12 or len(confirm_sha12) < 12 or not sha.startswith(confirm_sha12.lower()):
        raise SystemExit("--confirm-design-sha missing or does not match the design lock (first 12 chars of "
                         f"preregistration_5m sha256: {sha[:12]}).")
    return lock


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
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
