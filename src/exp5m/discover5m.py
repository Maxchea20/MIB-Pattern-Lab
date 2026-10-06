"""Outcome-blind AI discovery for the 5M experiment: D1 description -> D2 vocabulary -> D3 classification.

    python -m src.exp5m.discover5m d1 --confirm-design-sha <12> [--budget-usd 1.5] [--dry-run]
    python -m src.exp5m.discover5m d2 --confirm-design-sha <12>
    python -m src.exp5m.discover5m d3 --confirm-design-sha <12> [--budget-usd 2.5] [--dry-run]

Every step refuses to run unless the design lock is intact. The model sees only chart images (D1, D3) or text derived
from them (D2): never prices after T, never an outcome. All calls are resumable, hash-recorded and cost-capped.
Nothing here imports or can reach the outcome code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path

import pandas as pd

import config
from src.discovery import cost
from src.discovery.discover import OpenAIDescriber, load_env, parse_response
from src.exp5m import io5m, lock5m, params, prompts5m


# ------------------------------------------------------------------------ shared ------------------
def _png(run_dir: Path, w: dict) -> bytes:
    data = (run_dir / "charts" / w["chart"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != w["image_sha256"]:
        raise SystemExit(f"chart {w['chart']} does not match the hash in windows5m.jsonl")
    return data


def _spent(rows: list[dict]) -> float:
    return cost.total_cost(rows)


def _stop(spent: float, avg: float, budget) -> bool:
    return budget is not None and spent + 1.2 * avg > budget


# ------------------------------------------------------------------------ D1 -------------------
def run_d1(run_dir: Path, describer, budget_usd=None) -> list[dict]:
    windows = [w for w in io5m.load_jsonl(run_dir / "windows5m.jsonl") if w["description_stage"]]
    out = run_dir / "d1_descriptions.jsonl"
    done = io5m.clean_rows(io5m.load_jsonl(out))
    spent = _spent(io5m.load_jsonl(out))
    n_done = len(done)
    for i, w in enumerate(windows, 1):
        if w["end_ts"] in done:
            continue
        avg = spent / n_done if n_done else 0.01
        if _stop(spent, avg, budget_usd):
            print(f"BUDGET STOP at ${spent:.3f} of ${budget_usd:.2f} ({i - 1}/{len(windows)} processed); re-run to continue.")
            break
        rec = {"end_ts": w["end_ts"], "chart": w["chart"], "image_sha256": w["image_sha256"], "step": "D1",
               "model": getattr(describer, "model", None), "prompt_user_sha256": hashlib.sha256(prompts5m.D1_USER.encode()).hexdigest(),
               "requested_at": pd.Timestamp.now(tz="UTC").isoformat(), "parsed": None, "raw": None, "usage": None, "error": None}
        try:
            r = describer.describe(_png(run_dir, w))
            rec["raw"], rec["usage"] = r["text"], r.get("usage")
            obj, err = parse_response(r["text"])
            if err is None and not (isinstance(obj.get("summary"), str) and isinstance(obj.get("shape_tags"), list)):
                err = "response lacks 'summary' (str) or 'shape_tags' (list)"
            rec["parsed"], rec["error"] = (obj if err is None else None), err
        except Exception as e:                                           # keep going; failed rows are retried next run
            rec["error"] = f"{type(e).__name__}: {e}"
        io5m.append_jsonl(out, rec)
        spent += cost.call_cost(rec["usage"])
        n_done += rec["error"] is None
        print(f"[D1 {i}/{len(windows)}] {w['end_ts']} {'OK' if rec['error'] is None else 'ERROR ' + rec['error']}  spent ${spent:.3f}")
    return io5m.load_jsonl(out)


# ------------------------------------------------------------------------ D2 -------------------
def normalise_tag(t: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(t).lower())).strip("_")


def build_d2_input(d1_rows: list[dict], top_names: int = 80, n_summaries: int = 40, seed: int = 12345):
    good = sorted(io5m.clean_rows(d1_rows).values(), key=lambda r: r["end_ts"])
    counts = Counter(normalise_tag(t) for r in good for t in r["parsed"]["shape_tags"] if normalise_tag(t))
    table = "\n".join(f"{n}: {c}" for n, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top_names])
    pick = random.Random(seed).sample(good, min(n_summaries, len(good)))
    summ = "\n".join("- " + str(r["parsed"]["summary"])[:300].replace("\n", " ") for r in sorted(pick, key=lambda r: r["end_ts"]))
    return len(good), table, summ


class TextCaller:
    """Text-only JSON call (D2). Same client/key handling as the image describer."""

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
        return {"text": r.choices[0].message.content or "", "usage": {"prompt": getattr(u, "prompt_tokens", None),
                                                                      "completion": getattr(u, "completion_tokens", None)}}


def run_d2(run_dir: Path, caller, vocab_path: Path | None = None) -> prompts5m.Vocabulary:
    vocab_path = vocab_path or io5m.VOCAB_FILE
    if vocab_path.exists():
        raise SystemExit(f"{vocab_path.name} already exists: the vocabulary is written once and frozen.")
    d1 = io5m.load_jsonl(run_dir / "d1_descriptions.jsonl")
    windows = [w for w in io5m.load_jsonl(run_dir / "windows5m.jsonl") if w["description_stage"]]
    clean = io5m.clean_rows(d1)
    missing = [w["end_ts"] for w in windows if w["end_ts"] not in clean]
    if missing:
        raise SystemExit(f"D1 is incomplete ({len(missing)} windows without a clean description); finish D1 first.")
    n, table, summ = build_d2_input(d1)
    user = prompts5m.D2_USER_TEMPLATE.format(n_charts=n, tag_table=table, summaries=summ,
                                             k_min=params.VOCAB_MIN, k_max=params.VOCAB_MAX)
    attempts_file = run_dir / "d2_attempts.jsonl"
    problems_prev: list[str] = []
    for attempt in range(1, params.D2_MAX_ATTEMPTS + 1):
        prompt = user + (prompts5m.RETRY_SUFFIX.format(problems="; ".join(problems_prev)) if problems_prev else "")
        r = caller.call(prompts5m.D2_SYSTEM, prompt)
        obj, err = parse_response(r["text"])
        fams, problems = (prompts5m.validate_families(obj) if err is None else (None, [err]))
        io5m.append_jsonl(attempts_file, {"attempt": attempt, "model": getattr(caller, "model", None),
                                          "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "raw": r["text"],
                                          "usage": r.get("usage"), "problems": problems, "accepted": fams is not None,
                                          "requested_at": pd.Timestamp.now(tz="UTC").isoformat()})
        print(f"[D2 attempt {attempt}] {'ACCEPTED' if fams else 'rejected: ' + '; '.join(problems)}")
        if fams:
            vocab = prompts5m.Vocabulary(fams)
            vocab_path.parent.mkdir(parents=True, exist_ok=True)
            vocab_path.write_text(json.dumps({
                "experiment": params.EXPERIMENT, "model": getattr(caller, "model", None), "attempt_accepted": attempt,
                "created_at": pd.Timestamp.now(tz="UTC").isoformat(), "families": vocab.families,
                "member_names": {f["name"]: f["member_names"] for f in fams}, "sha256": vocab.sha256,
                "d2_template_sha256": prompts5m.template_hashes()["D2_USER_TEMPLATE"]}, indent=2) + "\n", encoding="utf-8")
            return vocab
        problems_prev = problems
    raise SystemExit("D2 failed all attempts; nothing is fixed by hand. Report this and stop.")


def load_vocabulary(vocab_path: Path | None = None) -> prompts5m.Vocabulary:
    p = vocab_path or io5m.VOCAB_FILE
    if not p.exists():
        raise SystemExit(f"{p} is missing: run d2 first.")
    rec = json.loads(p.read_text(encoding="utf-8"))
    v = prompts5m.Vocabulary(rec["families"])
    if v.sha256 != rec["sha256"]:
        raise SystemExit("vocabulary file does not match its recorded hash")
    return v


# ------------------------------------------------------------------------ D3 -------------------
def run_d3(run_dir: Path, describer_factory, vocab: prompts5m.Vocabulary, budget_usd=None) -> list[dict]:
    windows = io5m.load_jsonl(run_dir / "windows5m.jsonl")
    out = run_dir / "tags5m.jsonl"
    done = io5m.clean_rows(io5m.load_jsonl(out))
    users = {p: vocab.user_prompt(p % 2 == 0) for p in range(1, params.PASSES + 1)}
    ds = {p: describer_factory(users[p]) for p in users}
    spent = _spent(io5m.load_jsonl(out))
    n_charts = len({k[0] for k in done})
    for i, w in enumerate(windows, 1):
        todo = [p for p in range(1, params.PASSES + 1) if (w["end_ts"], p) not in done]
        if not todo:
            continue
        avg = spent / n_charts if n_charts else 0.01 * params.PASSES
        if _stop(spent, avg, budget_usd):
            print(f"BUDGET STOP at ${spent:.3f} of ${budget_usd:.2f} ({i - 1}/{len(windows)} windows); re-run to continue.")
            break
        png = _png(run_dir, w)
        for p in todo:
            rec = {"end_ts": w["end_ts"], "chart": w["chart"], "pass": p, "reversed_order": p % 2 == 0, "step": "D3",
                   "model": getattr(ds[p], "model", None), "vocab_sha256": vocab.sha256,
                   "prompt_user_sha256": hashlib.sha256(users[p].encode()).hexdigest(), "image_sha256": w["image_sha256"],
                   "stratum": w["stratum"], "requested_at": pd.Timestamp.now(tz="UTC").isoformat(),
                   "tags": None, "primary": None, "raw": None, "usage": None, "error": None}
            try:
                r = ds[p].describe(png)
                rec["raw"], rec["usage"] = r["text"], r.get("usage")
                obj, err = parse_response(r["text"])
                if err is None:
                    rec["tags"], rec["primary"], err = vocab.validate_tags(obj)
                rec["error"] = err
            except Exception as e:
                rec["error"] = f"{type(e).__name__}: {e}"
            io5m.append_jsonl(out, rec)
            spent += cost.call_cost(rec["usage"])
            print(f"[D3 {i}/{len(windows)} p{p}] {w['end_ts']} {'OK ' + str(rec['tags']) if rec['error'] is None else 'ERROR ' + rec['error']}  spent ${spent:.3f}")
        n_charts += 1
    return io5m.load_jsonl(out)


# ------------------------------------------------------------------------ CLI -------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("step", choices=["d1", "d2", "d3"])
    ap.add_argument("--confirm-design-sha", required=True)
    ap.add_argument("--run-dir", default=str(io5m.RUN_DIR))
    ap.add_argument("--budget-usd", type=float, default=2.0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    lock5m.require_design_lock(a.confirm_design_sha)
    run_dir = Path(a.run_dir)
    windows = io5m.load_jsonl(run_dir / "windows5m.jsonl")
    if not windows:
        raise SystemExit("no windows5m.jsonl: generate the sample first (sampling --build).")
    if a.step == "d1":
        n = sum(w["description_stage"] for w in windows)
        if a.dry_run:
            print(f"D1: {n} windows, model {params.MODEL}, budget ${a.budget_usd:.2f}\n--- system ---\n{prompts5m.D1_SYSTEM}\n--- user ---\n{prompts5m.D1_USER}")
            return 0
        run_d1(run_dir, OpenAIDescriber(params.MODEL, prompts5m.D1_SYSTEM, prompts5m.D1_USER), a.budget_usd)
    elif a.step == "d2":
        n, table, summ = build_d2_input(io5m.load_jsonl(run_dir / "d1_descriptions.jsonl"))
        if a.dry_run:
            print(f"D2 input: {n} described charts\n--- shape names ---\n{table}\n--- sample summaries ---\n{summ}")
            return 0
        run_d2(run_dir, TextCaller(params.MODEL))
    else:
        vocab = load_vocabulary()
        if a.dry_run:
            print(f"D3: {len(windows)} windows x {params.PASSES} passes = {len(windows) * params.PASSES} calls; vocabulary {vocab.names}\n{vocab.user_prompt(False)}")
            return 0
        run_d3(run_dir, lambda user: OpenAIDescriber(params.MODEL, prompts5m.D3_SYSTEM, user), vocab, a.budget_usd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
