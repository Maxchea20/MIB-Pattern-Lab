"""Small shared helpers for the 5M discovery pipeline (no outcome code, no network)."""
from __future__ import annotations

import json
from pathlib import Path

import config

RUN_DIR = config.ROOT / "results" / "exp5m" / "discovery"
VOCAB_FILE = config.ROOT / "docs" / "5m" / "VOCABULARY_5M.json"


def load_jsonl(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def append_jsonl(path: Path, row: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def clean_rows(rows: list[dict]) -> dict:
    """Latest error-free row per key. D1: {end_ts: row}; D3: {(end_ts, pass): row}."""
    out = {}
    for r in rows:
        if r.get("error") is None:
            out[(r["end_ts"], r["pass"]) if "pass" in r else r["end_ts"]] = r
    return out


def stable_tags(rows: list[dict], passes: int) -> dict[str, list[str]]:
    """{end_ts: tags present in EVERY pass} for windows with all passes clean."""
    good = clean_rows(rows)
    ends = {k[0] for k in good}
    out = {}
    for e in ends:
        if all((e, p) in good for p in range(1, passes + 1)):
            out[e] = sorted(set.intersection(*[set(good[(e, p)]["tags"]) for p in range(1, passes + 1)]))
    return out
