"""Lock the discovery sample + pre-registration BEFORE any outcome is computed.

    python -m src.discovery.lock --timeframe 1h            # verify + print the lock record
    python -m src.discovery.lock --timeframe 1h --write    # also write docs/PREREG_LOCK.json

Refuses to lock unless every discovery window has both tagging passes without errors, windows are
non-overlapping and inside the discovery period, one chart style was used, and one model/prompt/vocab
produced all tags. The record contains the sha256 of the pre-registration, family definitions, vocabulary,
prompts, window list and tag file. The outcome module (built after locking) must check this record.
No outcome data is read or needed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

import config
from src.data.loader import tf_to_seconds
from src.discovery import families, vocab
from src.discovery.audit import stable_tags
from src.discovery.retag import load_rows
from src.discovery.tagset import default_run_dir, file_sha256, load_windows

PREREG = config.ROOT / "docs" / "PREREGISTRATION.md"
LOCK_FILE = config.ROOT / "docs" / "PREREG_LOCK.json"


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def build_lock(run_dir: Path, timeframe: str, passes: int = config.RETAG_PASSES) -> dict:
    windows = load_windows(run_dir)
    if not windows:
        raise SystemExit(f"No windows.jsonl in {run_dir}")
    rows = load_rows(run_dir / "retags.jsonl")
    cutoff = pd.Timestamp(config.discovery_end(timeframe))
    gap = pd.Timedelta(seconds=tf_to_seconds(timeframe) * config.LOOKBACK)

    problems = []
    ends = sorted(pd.Timestamp(w["end_ts"]) for w in windows)
    if len(set(ends)) != len(ends):
        problems.append("duplicate window end timestamps")
    if ends[-1] >= cutoff:
        problems.append(f"window ends at/after discovery cutoff {cutoff}")
    if any(b - a < gap for a, b in zip(ends, ends[1:])):
        problems.append("overlapping windows (closer than one full window)")
    styles = {w["chart_style_sha256"] for w in windows}
    if len(styles) != 1:
        problems.append(f"{len(styles)} different chart styles in the sample")

    good = {}
    for r in rows:
        if r.get("error") is None:
            good.setdefault(r["end_ts"], {})[r["pass"]] = r
    missing = [w["end_ts"] for w in windows
               if not all(p in good.get(w["end_ts"], {}) for p in range(1, passes + 1))]
    if missing:
        problems.append(f"{len(missing)} windows lack a clean tagging pass (e.g. {missing[0]}); finish tagging first")
    used = [r for r in rows if r.get("error") is None and r["end_ts"] in {w["end_ts"] for w in windows}]
    for key in ("model", "retag_version", "vocab_version", "vocab_sha256"):
        vals = {r.get(key) for r in used}
        if len(vals) > 1:
            problems.append(f"mixed {key} values in tag file: {sorted(map(str, vals))}")
    if any(r.get("vocab_sha256") not in (None, vocab.VOCAB_SHA256) for r in used):
        problems.append("tag file was produced with a different vocabulary than the current code")
    if problems:
        raise SystemExit("CANNOT LOCK:\n  - " + "\n  - ".join(problems))

    stable = stable_tags(rows, passes)
    stable = {k: v for k, v in stable.items() if k in {w["end_ts"] for w in windows}}
    mem = families.membership(stable)
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config.ROOT, capture_output=True,
                                text=True, check=True).stdout.strip()
    except Exception:
        commit = "unknown"
    model = next(iter({r.get("model") for r in used}))
    return {
        "locked_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "hash_method": "sha256 over file bytes with CRLF normalised to LF",
        "git_commit": commit, "timeframe": timeframe, "discovery_end": str(cutoff),
        "run_dir": str(run_dir.name), "n_windows": len(windows), "n_windows_with_stable_tag":
            sum(1 for v in stable.values() if v),
        "sha256": {"preregistration": file_sha256(PREREG), "families_py": file_sha256(Path(families.__file__)),
                   "vocab": vocab.VOCAB_SHA256, "windows_jsonl": file_sha256(run_dir / "windows.jsonl"),
                   "retags_jsonl": file_sha256(run_dir / "retags.jsonl"),
                   "prompt_system": _h(vocab.RETAG_SYSTEM), "prompt_user_pass1": _h(vocab.retag_user(False)),
                   "prompt_user_pass2": _h(vocab.retag_user(True))},
        "model": model, "retag_version": vocab.RETAG_VERSION, "vocab_version": vocab.VOCAB_VERSION,
        "passes": passes, "chart_style_sha256": next(iter(styles)),
        "primary_families": list(families.PRIMARY),
        "family_window_counts": {f: len(mem[f]) for f in families.FAMILIES},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--timeframe", default="1h")
    ap.add_argument("--run-dir")
    ap.add_argument("--write", action="store_true", help=f"write {LOCK_FILE.relative_to(config.ROOT)}")
    a = ap.parse_args(argv)
    run = Path(a.run_dir) if a.run_dir else default_run_dir(a.timeframe)
    rec = build_lock(run, a.timeframe)
    text = json.dumps(rec, indent=2)
    print(text)
    if a.write:
        LOCK_FILE.write_text(text + "\n", encoding="utf-8")
        print(f"\nwrote {LOCK_FILE}. Send me this output / commit the file. NO outcome has been computed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
