"""Outcome-blind AI discovery of setups: Stage A (open discovery on charts) -> Stage B (consolidation of the TEXT).

    python -m src.setups.discover stage-a --confirm-design-sha <12> [--dry-run]
    python -m src.setups.discover stage-b --confirm-design-sha <12> [--dry-run]

Every step refuses to run unless the design lock is intact and the dataset hash is the canonical one. The model sees only
chart images (Stage A) or text derived from them (Stage B): never a price after T, a timestamp, a stratum or an outcome.
All calls are resumable, hash-recorded, and capped by src.setups.costlog (hard stop, no continuation, no override).
Nothing here imports or can reach outcome code. A setup definition is produced here and then FROZEN (F1); it is never
edited, merged or split afterwards.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import pandas as pd

from src.discovery.discover import OpenAIDescriber, load_env, parse_response
from src.setups import costlog, params, prompts, store

STAGE_A_FILE = "stage_a.jsonl"
STAGE_B_FILE = "stage_b_attempts.jsonl"
COST_FILE = "cost_log.jsonl"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _png(run_dir: Path, w: dict) -> bytes:
    data = (run_dir / "charts" / w["chart"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != w["image_sha256"]:
        raise SystemExit(f"chart {w['chart']} does not match the hash in windows_setups.jsonl")
    return data


# --------------------------------------------------------------------------------------------- Stage A ----
def run_stage_a(run_dir: Path, describer, log: costlog.CostLog | None = None) -> list[dict]:
    """One call per chart, in the stored (shuffled) order. A rejected response is an error row; it is not retried inside
    the run (a re-run tries it again). Stops at the first cost refusal."""
    log = log or costlog.CostLog(run_dir / COST_FILE)
    windows = store.load_jsonl(run_dir / "windows_setups.jsonl")
    out = run_dir / STAGE_A_FILE
    done = store.clean_rows(store.load_jsonl(out))
    for i, w in enumerate(windows, 1):
        if w["chart_id"] in done:
            continue
        if not log.allow("stage_a"):
            print(log.stop_message("stage_a"))
            break
        rec = {"chart_id": w["chart_id"], "end_ts": w["end_ts"], "chart": w["chart"], "stratum": w["stratum"],
               "image_sha256": w["image_sha256"], "step": "A", "model": getattr(describer, "model", None),
               "prompt_user_sha256": _sha(prompts.A_USER), "requested_at": pd.Timestamp.now(tz="UTC").isoformat(),
               "parsed": None, "raw": None, "usage": None, "error": None}
        try:
            r = describer.describe(_png(run_dir, w))
            rec["raw"], rec["usage"] = r["text"], r.get("usage")
            obj, err = parse_response(r["text"])
            if err is None:
                problems = prompts.validate_stage_a(obj)
                err = "; ".join(problems) if problems else None
            rec["parsed"], rec["error"] = (obj if err is None else None), err
        except Exception as e:                                           # keep going; failed rows are retried next run
            rec["error"] = f"{type(e).__name__}: {e}"
        store.append_jsonl(out, rec)
        if rec["usage"] is not None or rec["error"] is None:
            log.record("stage_a", rec["model"], rec["usage"])
        print(f"[A {i}/{len(windows)}] {w['chart_id']} {'OK ' + rec['parsed']['status'] if rec['error'] is None else 'ERROR ' + rec['error']}"
              f"  spent ${log.spent('stage_a'):.3f}")
    return store.load_jsonl(out)


# --------------------------------------------------------------------------------------------- Stage B ----
class TextCaller:
    """Text-only JSON call (Stage B). Same client/key handling as the image describer."""

    def __init__(self, model: str):
        load_env()
        import os
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise SystemExit("OPENAI_API_KEY not set (see .env.example).")
        from openai import OpenAI
        self.client, self.model = OpenAI(api_key=key), model

    def call(self, system: str, user: str) -> dict:
        r = self.client.chat.completions.create(model=self.model, response_format={"type": "json_object"},
                                                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        u = r.usage
        return {"text": r.choices[0].message.content or "",
                "usage": {"prompt": getattr(u, "prompt_tokens", None), "completion": getattr(u, "completion_tokens", None)}}


def stage_a_complete(run_dir: Path) -> tuple[list[dict], dict]:
    windows = store.load_jsonl(run_dir / "windows_setups.jsonl")
    clean = store.clean_rows(store.load_jsonl(run_dir / STAGE_A_FILE))
    missing = [w["chart_id"] for w in windows if w["chart_id"] not in clean]
    if missing:
        raise SystemExit(f"Stage A is incomplete ({len(missing)} charts without a clean description); finish Stage A first.")
    return windows, clean


def make_chunks(clean: dict) -> list[list[dict]]:
    """Descriptions with status != NONE, chart-id order, seeded shuffle, chunks of CHUNK_SIZE. Chunk membership depends on
    nothing but the (frozen) Stage A text and the seed."""
    items = sorted((r for r in clean.values() if r["parsed"]["status"] != "NONE"), key=lambda r: r["chart_id"])
    random.Random(params.SEED_CHUNK).shuffle(items)
    return [items[i:i + params.CHUNK_SIZE] for i in range(0, len(items), params.CHUNK_SIZE)]


def _call_validated(caller, log, attempts_file, kind, index, system, user, allowed_ids):
    """Up to MAX_ATTEMPTS attempts with the problems appended; accepted attempts are cached so a re-run never pays twice."""
    prior = [r for r in store.load_jsonl(attempts_file) if r["kind"] == kind and r["index"] == index]
    for r in prior:
        if r["accepted"]:
            return r["candidates"]
    problems_prev: list[str] = []
    for attempt in range(len(prior) + 1, params.MAX_ATTEMPTS + 1):
        if not log.allow("stage_b"):
            print(log.stop_message("stage_b"))
            return None
        prompt = user + (prompts.RETRY_SUFFIX.format(problems="; ".join(problems_prev)) if problems_prev else "")
        r = caller.call(system, prompt)
        log.record("stage_b", getattr(caller, "model", None), r.get("usage"))
        obj, err = parse_response(r["text"])
        cands, problems = (prompts.validate_stage_b(obj, allowed_ids) if err is None else (None, [err]))
        store.append_jsonl(attempts_file, {"kind": kind, "index": index, "attempt": attempt, "model": getattr(caller, "model", None),
                                           "prompt_sha256": _sha(prompt), "raw": r["text"], "usage": r.get("usage"),
                                           "problems": problems, "accepted": cands is not None, "candidates": cands,
                                           "requested_at": pd.Timestamp.now(tz="UTC").isoformat()})
        print(f"[B {kind} {index} attempt {attempt}] {'ACCEPTED' if cands is not None else 'rejected: ' + '; '.join(problems)}")
        if cands is not None:
            return cands
        problems_prev = problems
    raise SystemExit(f"Stage B ({kind} {index}) failed all attempts; nothing is fixed by hand. Report this and stop.")


def run_stage_b(run_dir: Path, caller, log: costlog.CostLog | None = None, candidates_path: Path | None = None) -> dict | None:
    """Chunk calls, then ONE final consolidation call. Writes the candidate file once (it becomes the F1 record)."""
    candidates_path = candidates_path or store.CANDIDATES_FILE
    if candidates_path.exists():
        raise SystemExit(f"{candidates_path.name} already exists: the setup definitions are written once and then frozen (F1).")
    log = log or costlog.CostLog(run_dir / COST_FILE)
    windows, clean = stage_a_complete(run_dir)
    status_counts = pd.Series([r["parsed"]["status"] for r in clean.values()]).value_counts().to_dict()
    chunks = make_chunks(clean)
    if not chunks:
        rec = {"experiment": params.EXPERIMENT, "created_at": pd.Timestamp.now(tz="UTC").isoformat(), "candidates": [],
               "dropped": [], "stage_a_status_counts": status_counts, "note": "no recurring setup recognised: no description had status other than NONE"}
        candidates_path.parent.mkdir(parents=True, exist_ok=True)
        candidates_path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        return rec
    attempts = run_dir / STAGE_B_FILE
    chunk_out = []
    for k, chunk in enumerate(chunks, 1):
        ids = {r["chart_id"] for r in chunk}
        user = prompts.B_CHUNK_USER_TEMPLATE.replace("{DESCRIPTIONS}", "\n\n".join(prompts.render_description(r) for r in chunk))
        c = _call_validated(caller, log, attempts, "chunk", k, prompts.B_SYSTEM, user, ids)
        if c is None:
            return None
        chunk_out += c
    all_ids = {r["chart_id"] for ch in chunks for r in ch}
    user = prompts.B_FINAL_USER_TEMPLATE.replace("{CANDIDATES}", prompts.render_candidates(chunk_out))
    final = _call_validated(caller, log, attempts, "final", 0, prompts.B_SYSTEM, user, all_ids)
    if final is None:
        return None
    kept, dropped = [], []
    for c in final:
        n = len(set(c["supporting_ids"]))
        c = {**c, "supporting_ids": sorted(set(c["supporting_ids"]))}
        if n >= params.MIN_SUPPORT:
            kept.append(c)
        else:
            dropped.append({"name": c["name"], "distinct_supporting_descriptions": n,
                            "reason": f"fewer than {params.MIN_SUPPORT} distinct supporting descriptions (dropped on count alone)"})
    rec = {"experiment": params.EXPERIMENT, "model": getattr(caller, "model", None), "created_at": pd.Timestamp.now(tz="UTC").isoformat(),
           "stage_a_status_counts": status_counts, "n_chunks": len(chunks), "chunk_size": params.CHUNK_SIZE,
           "candidates": kept, "dropped": dropped,
           "template_hashes": {k: v for k, v in prompts.template_hashes().items() if k.startswith("B_")},
           "note": "" if kept else "no recurring setup recognised"}
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    candidates_path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec


# ------------------------------------------------------------------------------------------------ CLI ----
def dry_run_a(run_dir: Path) -> None:
    windows = store.load_jsonl(run_dir / "windows_setups.jsonl")
    tin, tout = params.DRY_RUN_TOKENS["stage_a"]
    import config
    price = config.OPENAI_PRICE_USD_PER_M
    per = (tin * price["input"] + tout * price["output"]) / 1e6
    print(f"Stage A: {len(windows)} charts, model {params.MODEL}, cap ${params.CAP_STAGE_A:.2f} (total cap ${params.CAP_TOTAL:.2f})")
    print(f"estimate: ~{tin} input + ~{tout} output tokens per call => ~${per:.4f}/call, ~${per * len(windows):.2f} total (estimate only)")
    print("--- system ---\n" + prompts.A_SYSTEM + "\n--- user ---\n" + prompts.A_USER)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("step", choices=["stage-a", "stage-b"])
    ap.add_argument("--confirm-design-sha", required=True)
    ap.add_argument("--run-dir", default=str(store.RUN_DIR))
    ap.add_argument("--db", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    from src.setups import lock
    lock.require_design_lock(a.confirm_design_sha)
    lock.verify_database(Path(a.db) if a.db else lock.CANONICAL_DB)
    run_dir = Path(a.run_dir)
    if a.step == "stage-a":
        if a.dry_run:
            dry_run_a(run_dir)
            return 0
        run_stage_a(run_dir, OpenAIDescriber(params.MODEL, system=prompts.A_SYSTEM, user=prompts.A_USER))
        return 0
    if a.dry_run:
        windows, clean = stage_a_complete(run_dir)
        chunks = make_chunks(clean)
        print(f"Stage B: {sum(len(c) for c in chunks)} non-NONE descriptions in {len(chunks)} chunks of <= {params.CHUNK_SIZE}; "
              f"{len(chunks) + 1} calls minimum, cap ${params.CAP_STAGE_B:.2f}")
        print("--- system ---\n" + prompts.B_SYSTEM + "\n--- chunk user template ---\n" + prompts.B_CHUNK_USER_TEMPLATE)
        return 0
    run_stage_b(run_dir, TextCaller(params.MODEL))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
