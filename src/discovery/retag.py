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
from src.discovery import cost, vocab
from src.discovery.discover import OpenAIDescriber, build_messages, load_results, parse_response


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def done_keys(path: Path) -> set[tuple[str, int]]:
    return {(r["end_ts"], r["pass"]) for r in load_rows(path) if r.get("error") is None}


def charts_from_descriptions(run_dir: Path) -> list[dict]:
    return [r for r in load_results(run_dir / "descriptions.jsonl") if r["error"] is None]


def run_retag(run_dir: Path, describer, passes: int, limit: int | None = None, charts: list[dict] | None = None,
              budget_usd: float | None = None, price: dict | None = None) -> list[dict]:
    """Chart-outer loop (every chart finishes all passes before the next starts, so a budget stop
    never leaves half-tagged charts). `describer`: object, or factory(user_prompt)."""
    charts = charts if charts is not None else charts_from_descriptions(run_dir)
    if limit:
        charts = charts[:limit]
    if not charts:
        raise SystemExit(f"No charts to tag in {run_dir}")
    out = run_dir / "retags.jsonl"
    done = done_keys(out)
    users = {p: vocab.retag_user(p % 2 == 0) for p in range(1, passes + 1)}
    ds = {p: (describer(users[p]) if callable(describer) else describer) for p in range(1, passes + 1)}
    spent = cost.total_cost(load_rows(out), price)
    tagged = len({r["end_ts"] for r in load_rows(out) if r["error"] is None})
    for i, c in enumerate(charts, 1):
        todo = [p for p in range(1, passes + 1) if (c["end_ts"], p) not in done]
        if not todo:
            continue
        avg = spent / tagged if tagged else 0.01 * passes          # conservative before we have data
        if budget_usd is not None and spent + 1.2 * avg > budget_usd:
            print(f"BUDGET STOP: spent ${spent:.3f} of ${budget_usd:.2f}; next chart est ${avg:.4f}. "
                  f"{i - 1}/{len(charts)} charts processed. Re-run to continue after raising the budget.")
            break
        png = (run_dir / "charts" / c["chart"]).read_bytes()
        for p in todo:
            rec = {"end_ts": c["end_ts"], "chart": c["chart"], "pass": p, "reversed_order": p % 2 == 0,
                   "model": getattr(ds[p], "model", None), "retag_version": vocab.RETAG_VERSION,
                   "vocab_version": vocab.VOCAB_VERSION, "vocab_sha256": vocab.VOCAB_SHA256,
                   "image_sha256": hashlib.sha256(png).hexdigest(), "stratum": c.get("stratum"),
                   "requested_at": pd.Timestamp.now(tz="UTC").isoformat(),
                   "tags": None, "primary": None, "raw": None, "usage": None, "error": None}
            if rec["image_sha256"] != c["image_sha256"]:
                rec["error"] = "chart PNG does not match the hash recorded at discovery time"
            else:
                try:
                    r = ds[p].describe(png)
                    rec["raw"], rec["usage"] = r["text"], r.get("usage")
                    obj, err = parse_response(r["text"])
                    if err is None:
                        rec["tags"], rec["primary"], err = vocab.validate_tags(obj)
                    rec["error"] = err
                except Exception as e:
                    rec["error"] = f"{type(e).__name__}: {e}"
            spent += cost.call_cost(rec["usage"], price)
            with open(out, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            print(f"[{i}/{len(charts)} p{p}] {c['end_ts']} "
                  f"{'OK ' + str(rec['tags']) if rec['error'] is None else 'ERROR ' + rec['error']}  spent ${spent:.3f}")
        tagged += 1
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
