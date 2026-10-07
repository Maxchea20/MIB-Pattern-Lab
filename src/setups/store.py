"""Small shared helpers (JSONL, paths, hashing) for the Setup Discovery pipeline. No outcome code, no network."""
from __future__ import annotations

import json
from pathlib import Path

import config

RUN_DIR = config.ROOT / "results" / "setups" / "discovery"
CANDIDATES_FILE = config.ROOT / "docs" / "setups" / "SETUP_CANDIDATES.json"


def load_jsonl(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def append_jsonl(path: Path, row: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def clean_rows(rows: list[dict], key: str = "chart_id") -> dict:
    """Latest error-free row per key."""
    return {r[key]: r for r in rows if r.get("error") is None}
