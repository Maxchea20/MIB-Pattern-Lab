"""Freeze of the written rules BEFORE the untouched data is analysed: hashes of the code, the charter and the exact data files.

    python -m src.trendrsi.freeze --data-dir data/ext_old --write    # once
    python -m src.trendrsi.freeze --data-dir data/ext_old            # verify
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "docs" / "trend_rsi" / "FREEZE.json"
CODE = ("src/trendrsi/params.py", "src/trendrsi/indicators.py", "src/trendrsi/signals.py", "src/trendrsi/study.py", "src/trendrsi/run.py",
        "docs/trend_rsi/CHARTER_DRAFT.md")
DATA = ("BTCUSDT-15m.csv.gz", "BTCUSDT-4h.csv.gz", "BTCUSDT-1d.csv.gz")


def _sha(p: Path) -> str:
    b = gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes()      # gzip headers carry a timestamp: hash the CONTENT
    return hashlib.sha256(b.replace(b"\r\n", b"\n") if p.suffix in (".py", ".md") else b).hexdigest()


def record(data_dir: Path, root: Path = ROOT) -> dict:
    missing = [n for n in CODE if not (root / n).exists()] + [n for n in DATA if not (Path(data_dir) / n).exists()]
    if missing:
        raise SystemExit(f"cannot freeze/verify: missing {missing}")
    code = {n: _sha(root / n) for n in CODE}
    data = {n: _sha(Path(data_dir) / n) for n in DATA}
    return {"experiment": "trend_rsi_v1", "code_and_charter_sha256": code, "data_files_sha256": data,
            "version_sha256": hashlib.sha256(json.dumps([code, data], sort_keys=True).encode()).hexdigest(),
            "rules": ["rules and numbers fixed before the untouched data is analysed; none is tuned",
                      "the untouched data is analysed once; the stop rule of the charter is applied mechanically",
                      "event study only: no order, no fill, no trade (REAL FILLS ONLY)"]}


def write(data_dir: Path, root: Path = ROOT, path: Path = FREEZE) -> dict:
    if path.exists():
        raise SystemExit(f"{path} exists: the freeze is written once.")
    rec = record(data_dir, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rec


def verify(data_dir: Path, root: Path = ROOT, path: Path = FREEZE) -> dict:
    if not Path(path).exists():
        raise SystemExit("docs/trend_rsi/FREEZE.json is missing: the rules are not frozen, so the untouched data may not be analysed.")
    stored = json.loads(Path(path).read_text(encoding="utf-8"))
    now = record(data_dir, root)
    bad = [k for k in ("code_and_charter_sha256", "data_files_sha256", "version_sha256") if stored[k] != now[k]]
    if bad:
        raise SystemExit(f"FREEZE MISMATCH - the frozen rules, charter or data changed: {bad}")
    return stored


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    rec = write(Path(a.data_dir)) if a.write else verify(Path(a.data_dir))
    print(json.dumps({"version_sha256": rec["version_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
