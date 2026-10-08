"""Detector freeze for the Setup Brain. Written ONCE, after the detectors and their tests are final and BEFORE any market scan.

The detector version is the SHA-256 of the exact detector sources and thresholds. The scan refuses to run unless the files on disk still
match the freeze record. After the first scan nothing in this list may change; if something is wrong it is documented, not edited.
The observation layer (forward statistics, examples, report) is deliberately NOT part of the detector hash.

    python -m src.brain.freeze            # verify / show
    python -m src.brain.freeze --write    # write docs/brain/BRAIN_FREEZE.json (once)
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import config

ROOT = Path(config.ROOT)
FREEZE = ROOT / "docs" / "brain" / "BRAIN_FREEZE.json"
DETECTOR_FILES = ("src/brain/detectors.py", "src/brain/brain.py", "src/setups/recognizer.py", "src/setups/derive_params.py",
                  "docs/brain/DETECTOR_TRANSLATIONS.md")
THRESHOLD_FILES = ("results/setups/recognizer/derived_parameters.json", "results/brain/derived_s5.json")
CONTEXT_FILES = ("docs/brain/EXPERIMENT4_PLAN.md", "docs/setups/SETUP_CANDIDATES.json", "docs/REAL_FILLS_POLICY.md")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def file_hashes(root: Path = ROOT, names=DETECTOR_FILES + THRESHOLD_FILES) -> dict:
    missing = [n for n in names if not (root / n).exists()]
    if missing:
        raise SystemExit(f"cannot freeze or verify: missing {missing}")
    return {n: _sha(root / n) for n in sorted(names)}


def detector_version(root: Path = ROOT) -> str:
    return hashlib.sha256(json.dumps(file_hashes(root), sort_keys=True).encode()).hexdigest()


def record(root: Path = ROOT) -> dict:
    from src.brain import detectors as det
    return {"experiment": "brain_15m_v1", "timeframe": "15m", "setups": list(det.IDS),
            "detector_files_and_thresholds_sha256": file_hashes(root),
            "detector_version_sha256": detector_version(root),
            "context_files_sha256": file_hashes(root, CONTEXT_FILES),
            "interpretations": det.INTERPRETATIONS,
            "rules": ["no voting, consensus, ranking, veto, merging, lockout, frequency/fidelity/profitability gate",
                      "detectors are frozen BEFORE any market scan; no detector change after the first scan",
                      "REAL FILLS ONLY: a FIRE is a signal; no entry, fill, stop or target is assumed anywhere"]}


def write(root: Path = ROOT, path: Path = FREEZE) -> dict:
    if path.exists():
        raise SystemExit(f"{path} exists: the detector freeze is written once.")
    rec = record(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rec


def verify(root: Path = ROOT, path: Path = FREEZE) -> dict:
    if not Path(path).exists():
        raise SystemExit("docs/brain/BRAIN_FREEZE.json is missing: the detectors are not frozen, so no scan may run.")
    stored = json.loads(Path(path).read_text(encoding="utf-8"))
    now = record(root)
    bad = [k for k in ("detector_files_and_thresholds_sha256", "detector_version_sha256", "setups") if stored[k] != now[k]]
    if bad:
        raise SystemExit(f"BRAIN FREEZE MISMATCH - the frozen detectors or thresholds changed: {bad}")
    return stored


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    rec = write() if a.write else verify()
    print(json.dumps({"detector_version_sha256": rec["detector_version_sha256"], "files": rec["detector_files_and_thresholds_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
