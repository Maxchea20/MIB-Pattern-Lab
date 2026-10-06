"""Stage 3a: re-tag the already-rendered discovery charts against the FROZEN vocabulary.

    python -m src.discovery.retag --dry-run
    python -m src.discovery.retag                      # RETAG_PASSES passes over every chart in the run

Reads <run>/descriptions.jsonl (for the chart list + image hashes) and <run>/charts/*.png.
Needs no database. Each pass is independent and image-only (the earlier free-text description is NOT
shown). Even-numbered passes list the vocabulary in reverse order, to expose order bias.
Output: <run>/retags.jsonl (resumable; invalid / unknown tags are errors and are retried).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

import config
from src.discovery import vocab
from src.discovery.discover import OpenAIDescriber, build_messages, load_results, parse_response


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def done_keys(path: Path) -> set[tuple[str, int]]:
    return {(r["end_ts"], r["pass"]) for r in load_rows(path) if r.get("error") is None}


def run_retag(run_dir: Path, describer, passes: int, limit: int | None = None) -> list[dict]:
    charts = [r for r in load_results(run_dir / "descriptions.jsonl") if r["error"] is None]
    if limit:
        charts = charts[:limit]
    if not charts:
        raise SystemExit(f"No successful discovery rows in {run_dir / 'descriptions.jsonl'}")
    out = run_dir / "retags.jsonl"
    done = done_keys(out)
    for p in range(1, passes + 1):
        reverse = p % 2 == 0
        user = vocab.retag_user(reverse)
        d = describer(user) if callable(describer) else describer
        for i, c in enumerate(charts, 1):
            if (c["end_ts"], p) in done:
                continue
            png_path = run_dir / "charts" / c["chart"]
            png = png_path.read_bytes()
            rec = {"end_ts": c["end_ts"], "chart": c["chart"], "pass": p, "reversed_order": reverse,
                   "model": getattr(d, "model", None), "retag_version": vocab.RETAG_VERSION,
                   "vocab_version": vocab.VOCAB_VERSION, "vocab_sha256": vocab.VOCAB_SHA256,
                   "image_sha256": hashlib.sha256(png).hexdigest(),
                   "requested_at": pd.Timestamp.now(tz="UTC").isoformat(),
                   "tags": None, "primary": None, "raw": None, "usage": None, "error": None}
            if rec["image_sha256"] != c["image_sha256"]:
                rec["error"] = "chart PNG does not match the hash recorded at discovery time"
            else:
                try:
                    r = d.describe(png)
                    rec["raw"], rec["usage"] = r["text"], r.get("usage")
                    obj, err = parse_response(r["text"])
                    if err is None:
                        rec["tags"], rec["primary"], err = vocab.validate_tags(obj)
                    rec["error"] = err
                except Exception as e:
                    rec["error"] = f"{type(e).__name__}: {e}"
            with open(out, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            print(f"[pass {p}/{passes}] [{i}/{len(charts)}] {c['end_ts']} "
                  f"{'OK ' + str(rec['tags']) if rec['error'] is None else 'ERROR ' + rec['error']}")
    return load_rows(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--run-dir", default=str(config.DISCOVERY_DIR / config.DISCOVERY_RUN))
    ap.add_argument("--passes", type=int, default=config.RETAG_PASSES)
    ap.add_argument("--model", default=config.OPENAI_MODEL)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    if a.dry_run:
        n = len([r for r in load_results(run_dir / "descriptions.jsonl") if r["error"] is None])
        print(f"run dir: {run_dir}\ncharts: {n} x {a.passes} passes = {n * a.passes} API calls, model {a.model}\n"
              f"vocab {vocab.VOCAB_VERSION} ({len(vocab.NAMES)} names) sha {vocab.VOCAB_SHA256[:12]}\n"
              f"--- system ---\n{vocab.RETAG_SYSTEM}\n--- user (pass 1) ---\n{vocab.retag_user(False)}")
        return 0
    factory = lambda user: OpenAIDescriber(a.model, vocab.RETAG_SYSTEM, user)   # noqa: E731
    run_retag(run_dir, factory, a.passes, a.limit)
    print("next: python -m src.discovery.vocab_report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
