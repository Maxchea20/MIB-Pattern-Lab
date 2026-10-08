"""Detector freeze for Setup Brain v2 (S1 replaced, S2-S9 unchanged). Separate record from v1 (docs/brain/BRAIN_FREEZE.json stays valid).
Written once, after the tests and the price-only derivation and BEFORE the v2 scan; the scan refuses to run if any listed file changed.

    python -m src.brain.freeze_v2            # verify / show
    python -m src.brain.freeze_v2 --write    # write docs/brain/BRAIN_V2_FREEZE.json (once)
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from src.brain import freeze as f1

ROOT = f1.ROOT
FREEZE = ROOT / "docs" / "brain" / "BRAIN_V2_FREEZE.json"
DETECTOR_FILES = f1.DETECTOR_FILES + ("src/brain/s1_v2.py", "src/brain/detectors_v2.py", "src/brain/brain_v2.py", "docs/brain/DETECTOR_TRANSLATIONS_V2.md")
THRESHOLD_FILES = f1.THRESHOLD_FILES + ("results/brain_v2/derived_s1v2.json",)
CONTEXT_FILES = f1.CONTEXT_FILES + ("docs/brain/S1_REVIEW_AND_PROPOSAL.md", "docs/brain/BRAIN_FREEZE.json")
NAMES = DETECTOR_FILES + THRESHOLD_FILES


def detector_version(root: Path = ROOT) -> str:
    return hashlib.sha256(json.dumps(f1.file_hashes(root, NAMES), sort_keys=True).encode()).hexdigest()


def record(root: Path = ROOT) -> dict:
    from src.brain import detectors_v2 as d2
    return {"experiment": "brain_15m_v2_s1", "timeframe": "15m", "setups": list(d2.IDS), "changed_setup": "S1 (S2-S9 are the v1 functions, unchanged)",
            "v1_detector_version_sha256": json.loads((root / "docs/brain/BRAIN_FREEZE.json").read_text(encoding="utf-8"))["detector_version_sha256"],
            "detector_files_and_thresholds_sha256": f1.file_hashes(root, NAMES), "detector_version_sha256": detector_version(root),
            "context_files_sha256": f1.file_hashes(root, CONTEXT_FILES), "interpretations": d2.INTERPRETATIONS,
            "rules": ["S1 v2 approved as translation corrections, not performance optimization",
                      "no detector change after the first v2 scan; bad recognitions are reported, not patched",
                      "no forward-return number was used to design S1 v2", "REAL FILLS ONLY: a FIRE is a signal; no entry, fill, stop or target is assumed"]}


def write(root: Path = ROOT, path: Path = FREEZE) -> dict:
    if path.exists():
        raise SystemExit(f"{path} exists: the v2 freeze is written once.")
    rec = record(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rec


def verify(root: Path = ROOT, path: Path = FREEZE) -> dict:
    if not Path(path).exists():
        raise SystemExit("docs/brain/BRAIN_V2_FREEZE.json is missing: v2 is not frozen, so no v2 scan may run.")
    stored = json.loads(Path(path).read_text(encoding="utf-8"))
    now = record(root)
    bad = [k for k in ("detector_files_and_thresholds_sha256", "detector_version_sha256", "setups", "v1_detector_version_sha256") if stored[k] != now[k]]
    if bad:
        raise SystemExit(f"BRAIN V2 FREEZE MISMATCH - the frozen detectors or thresholds changed: {bad}")
    return stored


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    rec = write() if a.write else verify()
    print(json.dumps({"detector_version_sha256": rec["detector_version_sha256"], "v1": rec["v1_detector_version_sha256"], "files": rec["detector_files_and_thresholds_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
