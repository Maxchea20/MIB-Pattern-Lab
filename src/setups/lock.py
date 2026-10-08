"""Design lock (F0) for the Setup Discovery experiment: hashes of everything that defines the discovery design, written
BEFORE the sample is generated and before any AI call or outcome exists.

    python -m src.setups.lock                 # verify the current state / show the record
    python -m src.setups.lock --write         # write docs/PREREG_SETUPS_DESIGN_LOCK.json (once)

Also proves that the canonical dataset is the expected file (name, bytes, SHA-256) and that the archived 1H and 5M
experiments are untouched. This module never imports outcome code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

import config
from src.discovery.tagset import file_sha256
from src.setups import params, prompts

CANONICAL_DB = config.ROOT / "data" / params.DB_NAME
PREREG = config.ROOT / "docs" / "PREREGISTRATION_SETUPS.md"
DESIGN_DOC = config.ROOT / "docs" / "SETUP_DISCOVERY_DESIGN.md"
POLICY = config.ROOT / "docs" / "REAL_FILLS_POLICY.md"
COVERAGE = config.ROOT / "docs" / "setups" / "COVERAGE_RESEARCH_BINANCE_REPORT.json"
DESIGN_LOCK = config.ROOT / "docs" / "PREREG_SETUPS_DESIGN_LOCK.json"          # F0 (original; never modified)
F0B_LOCK = config.ROOT / "docs" / "PREREG_SETUPS_DESIGN_LOCK_F0B.json"        # F0b: F0 + the Stage B citation amendment
F0C_LOCK = config.ROOT / "docs" / "PREREG_SETUPS_DESIGN_LOCK_F0C.json"        # F0c: F0b + the final-merge rule order
AMENDMENT_F0C = config.ROOT / "docs" / "setups" / "AMENDMENT_F0C.md"
F1_LOCK = config.ROOT / "docs" / "PREREG_SETUPS_F1_LOCK.json"                  # F1: the setup definitions are frozen; no AI step after this
CANDIDATES = config.ROOT / "docs" / "setups" / "SETUP_CANDIDATES.json"
F1_RUN_FILES = ("windows_setups.jsonl", "sample_meta.json", "stage_a.jsonl", "chart_verification.json",
                "stage_b_attempts.jsonl", "cost_log.jsonl")                       # whole files: after F1 nothing may be appended
_REAL_DESIGN_LOCK = DESIGN_LOCK                                                  # the guard below applies to the real pipeline only
AMENDMENT = config.ROOT / "docs" / "setups" / "AMENDMENT_F0B.md"
F0B_AMENDED = ("src/setups/prompts.py", "src/setups/discover.py")             # the ONLY locked files F0b may change
RUN_DIR = config.ROOT / "results" / "setups" / "discovery"
F0B_PRESERVED = ("windows_setups.jsonl", "sample_meta.json", "stage_a.jsonl", "chart_verification.json")
F0B_PREFIX_FILES = ("stage_b_attempts.jsonl", "cost_log.jsonl")                # append-only: the existing lines are preserved
DOCS = {"preregistration_setups": PREREG, "design_doc": DESIGN_DOC, "real_fills_policy": POLICY, "coverage_report": COVERAGE}
# Code and archived modules the discovery design depends on (archived ones are used UNCHANGED; any edit blocks the run).
DESIGN_FILES = ("src/setups/params.py", "src/setups/store.py", "src/setups/costlog.py", "src/setups/prompts.py",
                "src/setups/sampling.py", "src/setups/discover.py", "src/setups/audit.py", "src/setups/coverage_audit.py",
                "src/charts/renderer.py", "src/charts/windows.py", "src/charts/normalize.py", "src/data/loader.py",
                "src/validation/window_validation.py", "src/discovery/audit.py", "src/discovery/discover.py",
                "src/discovery/cost.py", "src/discovery/tagset.py")


def sha256_file_bytes(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_database(path) -> dict:
    """The canonical dataset: right file name, exact byte size and SHA-256. Refuses anything else."""
    p = Path(path)
    if p.name.lower() in params.FORBIDDEN_DB_NAMES:
        raise SystemExit(f"{p.name} is NOT the dataset of the Setup Discovery experiment and must not be used.")
    if p.name.lower() != params.DB_NAME:
        raise SystemExit(f"The canonical dataset is data/{params.DB_NAME}; got {p.name}.")
    if not p.exists():
        raise SystemExit(f"database not found: {p}")
    size, sha = p.stat().st_size, sha256_file_bytes(p)
    if size != params.EXPECTED_DB_BYTES or sha != params.EXPECTED_DB_SHA256:
        raise SystemExit(f"{p.name} is not the dataset that was pre-registered (bytes {size}, sha256 {sha}).")
    return {"file": p.name, "bytes": size, "sha256": sha}


def archive_intact() -> dict:
    """Archived 1H and 5M experiments are byte-identical to their own lock/freeze records."""
    from src.exp5m import lock5m
    out = dict(lock5m.archive_1h_intact())
    lock5m.verify_design_lock()                                   # 5M design lock still matches (raises otherwise)
    out["design_5m"] = True
    for k, rel in (("discovery_lock_5m", "docs/PREREG_5M_DISCOVERY_LOCK.json"),
                   ("outcome_freeze_5m", "docs/OUTCOME5M_CODE_FREEZE.json")):
        out[k] = (config.ROOT / rel).exists()
    return out


def config_snapshot() -> dict:
    from src.setups import sampling
    return {"chart_style_sha256": sampling.style_sha(), "openai_price_usd_per_m": dict(config.OPENAI_PRICE_USD_PER_M)}


def current_record() -> dict:
    for f in DOCS.values():
        if not f.exists():
            raise SystemExit(f"missing {f.relative_to(config.ROOT)}")
    bad = {k: v for k, v in prompts.lint_templates().items() if v}
    if bad:
        raise SystemExit(f"prompt templates contain forbidden words: {bad}")
    arch = archive_intact()
    if not all(arch.values()):
        raise SystemExit(f"an archived experiment changed: {arch}")
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config.ROOT, capture_output=True, text=True,
                                check=True).stdout.strip()
    except Exception:
        commit = "unknown"
    return {"experiment": params.EXPERIMENT, "git_commit": commit,
            "hash_method": "sha256 over file bytes with CRLF normalised to LF",
            "dataset": {"file": f"data/{params.DB_NAME}", "bytes": params.EXPECTED_DB_BYTES, "sha256": params.EXPECTED_DB_SHA256,
                        "statement": f"data/{params.DB_NAME} is the canonical dataset for the Setup Discovery experiment."},
            "sha256": {**{k: file_sha256(v) for k, v in DOCS.items()}, **{f: file_sha256(config.ROOT / f) for f in DESIGN_FILES}},
            "prompt_template_sha256": prompts.template_hashes(),
            "config": config_snapshot(),
            "parameters": json.loads(json.dumps({k: v for k, v in vars(params).items() if k.isupper()})),
            "archive_intact": arch}


def _verify_f0(lock_path: Path | None = None) -> dict:
    p = Path(lock_path or DESIGN_LOCK)
    if not p.exists():
        raise SystemExit("docs/PREREG_SETUPS_DESIGN_LOCK.json is missing: the Setup Discovery design is not frozen yet.")
    lock = json.loads(p.read_text(encoding="utf-8"))
    now = current_record()
    changed = [k for k, v in lock["sha256"].items() if now["sha256"].get(k) != v]
    changed += [k for k, v in lock["prompt_template_sha256"].items() if now["prompt_template_sha256"].get(k) != v]
    changed += [k for k in ("config", "dataset") if lock[k] != now[k]]
    if changed or lock["parameters"] != now["parameters"]:
        raise SystemExit(f"DESIGN LOCK MISMATCH - the frozen design changed: {changed or 'parameters'}")
    return lock


def _lines_sha(path: Path, n: int | None = None) -> dict:
    lines = Path(path).read_bytes().replace(b"\r\n", b"\n").split(b"\n")
    lines = [l for l in lines if l.strip()]
    lines = lines if n is None else lines[:n]
    return {"lines": len(lines), "sha256_of_these_lines": hashlib.sha256(b"\n".join(lines) + b"\n").hexdigest()}


def f0b_record(run_dir: Path | None = None, f0_lock_path: Path | None = None) -> dict:
    """What F0b will freeze, computed from the current files. Fails unless the ONLY locked files that differ from the original
    F0 lock are exactly F0B_AMENDED, and everything else the F0 lock froze is byte-identical."""
    run_dir = Path(run_dir or RUN_DIR)
    f0p = Path(f0_lock_path or DESIGN_LOCK)
    if not f0p.exists() or not AMENDMENT.exists():
        raise SystemExit("F0b needs the original F0 lock and docs/setups/AMENDMENT_F0B.md.")
    f0 = json.loads(f0p.read_text(encoding="utf-8"))
    now = current_record()
    changed = sorted(k for k, v in f0["sha256"].items() if now["sha256"].get(k) != v)
    if changed != sorted(F0B_AMENDED):
        raise SystemExit(f"F0b may change exactly {sorted(F0B_AMENDED)}; files differing from the F0 lock: {changed}")
    for k in ("prompt_template_sha256", "parameters", "config", "dataset"):
        if f0[k] != now[k]:
            raise SystemExit(f"F0b must not change {k}")
    preserved = {n: {"sha256": file_sha256(run_dir / n)} for n in F0B_PRESERVED}
    prefixes = {n: _lines_sha(run_dir / n) for n in F0B_PREFIX_FILES}
    tests = {str(p.relative_to(config.ROOT).as_posix()): file_sha256(p) for p in sorted((config.ROOT / "tests").glob("test_setups_*.py"))}
    return {"amendment": {"id": "F0b", "rule": "Stage B: unknown supporting ids are dropped and audited; support = distinct VERIFIED ids",
                          "document": "docs/setups/AMENDMENT_F0B.md", "document_sha256": file_sha256(AMENDMENT)},
            "original_f0_lock": {"file": str(f0p.relative_to(config.ROOT).as_posix()) if f0p.is_relative_to(config.ROOT) else f0p.name,
                                 "file_sha256": file_sha256(f0p), "git_commit": f0["git_commit"], "locked_at": f0["locked_at"]},
            "amended_files": {k: {"f0_sha256": f0["sha256"][k], "f0b_sha256": now["sha256"][k]} for k in F0B_AMENDED},
            "unchanged_since_f0_sha256": {k: v for k, v in f0["sha256"].items() if k not in F0B_AMENDED},
            "tests_sha256": tests, "preserved_records": preserved, "preserved_append_only_prefixes": prefixes,
            "dataset": now["dataset"], "git_commit": now["git_commit"]}


def verify_f0b(f0b_path: Path | None = None, run_dir: Path | None = None, f0_lock_path: Path | None = None) -> dict:
    """F0b holds iff: the original F0 lock file is byte-identical; every file F0 froze is unchanged except the two amended
    files, which equal their F0b hashes; the amendment, tests, Stage A record, chart verification and the existing lines of
    the append-only Stage B / cost files are unchanged; templates, parameters, config and dataset are unchanged."""
    run_dir = Path(run_dir or RUN_DIR)
    p = Path(f0b_path or F0B_LOCK)
    if not p.exists():
        raise SystemExit("docs/PREREG_SETUPS_DESIGN_LOCK_F0B.json is missing: the amended design is not frozen yet.")
    f0b = json.loads(p.read_text(encoding="utf-8"))
    f0p = Path(f0_lock_path or DESIGN_LOCK)
    f0 = json.loads(f0p.read_text(encoding="utf-8"))
    bad = []
    if file_sha256(f0p) != f0b["original_f0_lock"]["file_sha256"]:
        bad.append("original_f0_lock")
    now = current_record()
    for k, v in f0b["unchanged_since_f0_sha256"].items():
        if now["sha256"].get(k) != v or f0["sha256"].get(k) != v:
            bad.append(k)
    for k, v in f0b["amended_files"].items():
        if k not in F0B_AMENDED or f0["sha256"].get(k) != v["f0_sha256"] or now["sha256"].get(k) != v["f0b_sha256"]:
            bad.append(k)
    if set(f0b["amended_files"]) != set(F0B_AMENDED) or set(f0b["amended_files"]) | set(f0b["unchanged_since_f0_sha256"]) != set(f0["sha256"]):
        bad.append("file_set")
    if file_sha256(AMENDMENT) != f0b["amendment"]["document_sha256"]:
        bad.append("amendment_document")
    for k, v in f0b["tests_sha256"].items():
        if file_sha256(config.ROOT / k) != v:
            bad.append(k)
    for n, v in f0b["preserved_records"].items():
        if file_sha256(run_dir / n) != v["sha256"]:
            bad.append(n)
    for n, v in f0b["preserved_append_only_prefixes"].items():
        if _lines_sha(run_dir / n, v["lines"]) != v:
            bad.append(n + " (existing lines)")
    for k in ("prompt_template_sha256", "parameters", "config", "dataset"):
        if f0[k] != now[k]:
            bad.append(k)
    if bad:
        raise SystemExit(f"F0b LOCK MISMATCH - the amended design changed: {sorted(set(bad))}")
    return {**f0, "f0b": f0b}


def f0c_record(run_dir: Path | None = None, f0_lock_path: Path | None = None, f0b_lock_path: Path | None = None) -> dict:
    """What F0c will freeze. Both earlier lock files stay byte-identical; the files that differ from the F0 lock are again exactly
    F0B_AMENDED (now at their F0c hashes); everything else F0 froze is unchanged; the preserved records and the append-only files
    are recorded as they are now (the three F0 attempts, the F0b attempts, and the cost lines so far)."""
    run_dir = Path(run_dir or RUN_DIR)
    f0p, f0bp = Path(f0_lock_path or DESIGN_LOCK), Path(f0b_lock_path or F0B_LOCK)
    for need in (f0p, f0bp, AMENDMENT, AMENDMENT_F0C):
        if not Path(need).exists():
            raise SystemExit(f"F0c needs {Path(need).name} (the F0 lock, the F0b lock and both amendment documents).")
    f0, f0b = json.loads(f0p.read_text(encoding="utf-8")), json.loads(f0bp.read_text(encoding="utf-8"))
    now = current_record()
    changed = sorted(k for k, v in f0["sha256"].items() if now["sha256"].get(k) != v)
    if changed != sorted(F0B_AMENDED):
        raise SystemExit(f"F0c may change exactly {sorted(F0B_AMENDED)} relative to F0; files differing from the F0 lock: {changed}")
    for k in ("prompt_template_sha256", "parameters", "config", "dataset"):
        if f0[k] != now[k]:
            raise SystemExit(f"F0c must not change {k}")
    return {"amendment": {"id": "F0c", "rule": "Stage B final merge: verify citations, set aside candidates with < 15 verified ids by count, then require <= 8 survivors",
                          "document": "docs/setups/AMENDMENT_F0C.md", "document_sha256": file_sha256(AMENDMENT_F0C)},
            "earlier_amendment_f0b": {"document_sha256": file_sha256(AMENDMENT), "lock_file_sha256": file_sha256(f0bp),
                                      "git_commit": f0b["git_commit"], "locked_at": f0b["locked_at"]},
            "original_f0_lock": {"file_sha256": file_sha256(f0p), "git_commit": f0["git_commit"], "locked_at": f0["locked_at"]},
            "amended_files": {k: {"f0_sha256": f0["sha256"][k], "f0b_sha256": f0b["amended_files"][k]["f0b_sha256"],
                                  "f0c_sha256": now["sha256"][k]} for k in F0B_AMENDED},
            "unchanged_since_f0_sha256": {k: v for k, v in f0["sha256"].items() if k not in F0B_AMENDED},
            "tests_sha256": {str(p.relative_to(config.ROOT).as_posix()): file_sha256(p) for p in sorted((config.ROOT / "tests").glob("test_setups_*.py"))},
            "preserved_records": {n: {"sha256": file_sha256(run_dir / n)} for n in F0B_PRESERVED},
            "preserved_append_only_prefixes": {n: _lines_sha(run_dir / n) for n in F0B_PREFIX_FILES},
            "earlier_prefixes_still_intact": {n: f0b["preserved_append_only_prefixes"][n] for n in F0B_PREFIX_FILES},
            "dataset": now["dataset"], "git_commit": now["git_commit"]}


def verify_f0c(f0c_path: Path | None = None, run_dir: Path | None = None, f0_lock_path: Path | None = None,
               f0b_lock_path: Path | None = None) -> dict:
    run_dir = Path(run_dir or RUN_DIR)
    p = Path(f0c_path or F0C_LOCK)
    if not p.exists():
        raise SystemExit("docs/PREREG_SETUPS_DESIGN_LOCK_F0C.json is missing: the amended design is not frozen yet.")
    f0c = json.loads(p.read_text(encoding="utf-8"))
    f0p, f0bp = Path(f0_lock_path or DESIGN_LOCK), Path(f0b_lock_path or F0B_LOCK)
    f0, f0b = json.loads(f0p.read_text(encoding="utf-8")), json.loads(f0bp.read_text(encoding="utf-8"))
    bad = []
    if file_sha256(f0p) != f0c["original_f0_lock"]["file_sha256"]:
        bad.append("original_f0_lock")
    if file_sha256(f0bp) != f0c["earlier_amendment_f0b"]["lock_file_sha256"]:
        bad.append("f0b_lock")
    if file_sha256(AMENDMENT) != f0c["earlier_amendment_f0b"]["document_sha256"]:
        bad.append("amendment_f0b_document")
    if file_sha256(AMENDMENT_F0C) != f0c["amendment"]["document_sha256"]:
        bad.append("amendment_f0c_document")
    now = current_record()
    for k, v in f0c["unchanged_since_f0_sha256"].items():
        if now["sha256"].get(k) != v or f0["sha256"].get(k) != v:
            bad.append(k)
    for k, v in f0c["amended_files"].items():
        if (k not in F0B_AMENDED or f0["sha256"].get(k) != v["f0_sha256"] or f0b["amended_files"][k]["f0b_sha256"] != v["f0b_sha256"]
                or now["sha256"].get(k) != v["f0c_sha256"]):
            bad.append(k)
    if set(f0c["amended_files"]) != set(F0B_AMENDED) or set(f0c["amended_files"]) | set(f0c["unchanged_since_f0_sha256"]) != set(f0["sha256"]):
        bad.append("file_set")
    for k, v in f0c["tests_sha256"].items():
        if file_sha256(config.ROOT / k) != v:
            bad.append(k)
    for n, v in f0c["preserved_records"].items():
        if file_sha256(run_dir / n) != v["sha256"]:
            bad.append(n)
    for n, v in f0c["preserved_append_only_prefixes"].items():
        if _lines_sha(run_dir / n, v["lines"]) != v:
            bad.append(n + " (existing lines)")
    for n, v in f0c["earlier_prefixes_still_intact"].items():
        if _lines_sha(run_dir / n, v["lines"]) != v:
            bad.append(n + " (F0b lines)")
    for k in ("prompt_template_sha256", "parameters", "config", "dataset"):
        if f0[k] != now[k]:
            bad.append(k)
    if bad:
        raise SystemExit(f"F0c LOCK MISMATCH - the amended design changed: {sorted(set(bad))}")
    return {**f0, "f0b": f0b, "f0c": f0c}


def verify_design_lock(lock_path: Path | None = None) -> dict:
    """With an explicit path: verify that single (F0-format) record. Otherwise the latest lock that exists governs: F0c, else F0b, else F0."""
    if lock_path is not None:
        return _verify_f0(lock_path)
    if F0C_LOCK.exists():
        return verify_f0c()
    return verify_f0b() if F0B_LOCK.exists() else _verify_f0()


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def f1_record(run_dir: Path | None = None, candidates_path: Path | None = None) -> dict:
    """A malformed or tampered file is a loud, clean failure (SystemExit), never a silent pass or a stray KeyError."""
    try:
        return _f1_record(run_dir, candidates_path)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as e:
        raise SystemExit(f"F1: a frozen file is malformed or was changed ({type(e).__name__}: {e})")


def _f1_record(run_dir: Path | None = None, candidates_path: Path | None = None) -> dict:
    """What F1 freezes: the setup definitions (SETUP_CANDIDATES.json), every final Stage A description, every Stage B attempt
    (including the rejected F0 / F0b ones), the accepted final response, the cost log, and the three design locks with their
    amendments. Refuses unless the F0c design lock verifies and the candidate file is exactly what the accepted final response
    produced under the rules: at most MAX_CANDIDATES, each with >= MIN_SUPPORT verified supporting descriptions, structurally valid."""
    from src.setups import prompts
    run_dir = Path(run_dir or RUN_DIR)
    cpath = Path(candidates_path or CANDIDATES)
    verify_design_lock()                                              # F0 -> F0b -> F0c chain must hold
    for need in (cpath, F0B_LOCK, F0C_LOCK, DESIGN_LOCK, AMENDMENT, AMENDMENT_F0C, *[run_dir / n for n in F1_RUN_FILES]):
        if not Path(need).exists():
            raise SystemExit(f"F1 needs {Path(need).name}")
    cand = json.loads(cpath.read_text(encoding="utf-8"))
    problems = []
    keep = cand["candidates"]
    if len(keep) > params.MAX_CANDIDATES or not keep:
        problems.append(f"{len(keep)} candidates (1..{params.MAX_CANDIDATES} allowed)")
    if len({c["name"] for c in keep}) != len(keep):
        problems.append("candidate names are not unique")
    for c in keep:
        base = {k: c[k] for k in prompts.B_KEYS}
        if prompts.validate_candidate(base):
            problems.append(f"{c['name']}: {prompts.validate_candidate(base)}")
        if len(set(c["supporting_ids"])) < params.MIN_SUPPORT or len(c["supporting_ids"]) != len(set(c["supporting_ids"])):
            problems.append(f"{c['name']}: fewer than {params.MIN_SUPPORT} distinct verified supporting descriptions")
    attempts = [json.loads(l) for l in (run_dir / "stage_b_attempts.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    finals = [r for r in attempts if r["kind"] == "final" and r.get("rule") == cand.get("rule") and r["accepted"]]
    if len(finals) != 1:
        problems.append("expected exactly one accepted final response under the rule recorded in the candidate file")
    else:
        survivors = [c for c in finals[0]["candidates"] if len(c["supporting_ids"]) >= params.MIN_SUPPORT]
        if _canon(survivors) != _canon(keep):
            problems.append("SETUP_CANDIDATES.json is not exactly the survivors of the accepted final response")
        if _canon([d["name"] for d in cand["dropped"]]) != _canon([c["name"] for c in finals[0]["candidates"] if len(c["supporting_ids"]) < params.MIN_SUPPORT]):
            problems.append("the dropped list is not exactly the candidates set aside by count")
    a_rows = [json.loads(l) for l in (run_dir / "stage_a.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    windows = [json.loads(l) for l in (run_dir / "windows_setups.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    final_a = {}
    for r in a_rows:
        if r.get("error") is None:
            final_a[r["chart_id"]] = r
    if sorted(final_a) != sorted(w["chart_id"] for w in windows):
        problems.append("not every chart has a clean final Stage A description")
    if problems:
        raise SystemExit("CANNOT FREEZE F1:\n  - " + "\n  - ".join(problems))
    status_counts: dict[str, int] = {}
    for r in final_a.values():
        status_counts[r["parsed"]["status"]] = status_counts.get(r["parsed"]["status"], 0) + 1
    desc = [f"{cid}:{_h(_canon(final_a[cid]['parsed']))}" for cid in sorted(final_a)]
    cost_lines = [l for l in (run_dir / "cost_log.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return {
        "id": "F1",
        "principle": "The setup definitions are frozen exactly as the model returned them. No AI step follows: no merging, splitting, "
                     "renaming, trigger or lookback changes, and no removal of examples.",
        "candidates_file": {"path": "docs/setups/SETUP_CANDIDATES.json", "sha256": file_sha256(cpath), "rule": cand["rule"],
                            "n_candidates": len(keep), "n_dropped": len(cand["dropped"])},
        "candidates": [{"name": c["name"], "direction": c["direction"], "verified_supporting_descriptions": len(c["supporting_ids"]),
                        "definition_sha256": _h(_canon({k: c[k] for k in prompts.B_KEYS}))} for c in keep],
        "dropped": [{"name": d["name"], "verified": d["verified_distinct_supporting_descriptions"]} for d in cand["dropped"]],
        "stage_a": {"n_descriptions": len(final_a), "status_counts": dict(sorted(status_counts.items())),
                    "final_descriptions_sha256": _h("\n".join(desc)), "rows_in_file": len(a_rows)},
        "stage_b": {"attempt_rows": len(attempts),
                    "rows": [{"rule": r.get("rule", "F0"), "kind": r["kind"], "index": r["index"], "attempt": r["attempt"], "accepted": r["accepted"],
                              "raw_sha256": _h(r["raw"])} for r in attempts],
                    "accepted_final_raw_sha256": _h(finals[0]["raw"])},
        "cost": {"lines": len(cost_lines), "total_usd": round(sum(json.loads(l)["estimated_cost_usd"] for l in cost_lines), 6)},
        "files_sha256": {n: file_sha256(run_dir / n) for n in F1_RUN_FILES},
        "locks_sha256": {"f0": file_sha256(DESIGN_LOCK), "f0b": file_sha256(F0B_LOCK), "f0c": file_sha256(F0C_LOCK),
                         "amendment_f0b": file_sha256(AMENDMENT), "amendment_f0c": file_sha256(AMENDMENT_F0C)},
        "dataset": current_record()["dataset"],
    }


_F1_COMPARE = ("candidates_file", "candidates", "dropped", "stage_a", "stage_b", "cost", "files_sha256", "locks_sha256", "dataset")


def verify_f1(f1_path: Path | None = None, run_dir: Path | None = None, candidates_path: Path | None = None) -> dict:
    p = Path(f1_path or F1_LOCK)
    if not p.exists():
        raise SystemExit("docs/PREREG_SETUPS_F1_LOCK.json is missing: the setup definitions are not frozen yet.")
    stored = json.loads(p.read_text(encoding="utf-8"))
    now = f1_record(run_dir, candidates_path)
    bad = [k for k in _F1_COMPARE if stored[k] != now[k]]
    if bad:
        raise SystemExit(f"F1 MISMATCH - the frozen setup definitions or their record changed: {bad}")
    return stored


def require_f1(confirm_sha12: str | None) -> dict:
    """For every step after discovery (recognizer, fidelity, outcomes): F0 -> F0b -> F0c -> F1 must all hold."""
    lock = verify_design_lock()
    verify_f1()
    sha = lock["sha256"]["preregistration_setups"]
    if not confirm_sha12 or len(confirm_sha12) < 12 or not sha.startswith(confirm_sha12.lower()):
        raise SystemExit(f"--confirm-design-sha missing or does not match (first 12 chars: {sha[:12]}).")
    return lock


def require_design_lock(confirm_sha12: str | None, lock_path: Path | None = None) -> dict:
    """Used by every discovery step: the design must be locked and unchanged, and the caller must name it.
    Once F1 exists the discovery AI steps (Stage A, Stage B, sampling) are CLOSED for the real pipeline: they are refused here."""
    if lock_path is None and F1_LOCK.exists() and DESIGN_LOCK == _REAL_DESIGN_LOCK:
        raise SystemExit("F1 is written: the setup definitions are frozen and the discovery steps (sampling, Stage A, Stage B) are closed. "
                         "Use require_f1 for later stages.")
    lock = verify_design_lock(lock_path)
    sha = lock["sha256"]["preregistration_setups"]
    if not confirm_sha12 or len(confirm_sha12) < 12 or not sha.startswith(confirm_sha12.lower()):
        raise SystemExit("--confirm-design-sha missing or does not match the design lock (first 12 chars of "
                         f"preregistration_setups sha256: {sha[:12]}).")
    return lock


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--write-f1", action="store_true", help="write docs/PREREG_SETUPS_F1_LOCK.json (once): freeze the setup definitions")
    ap.add_argument("--write-f0c", action="store_true", help="write docs/PREREG_SETUPS_DESIGN_LOCK_F0C.json (once), after amendment F0c is approved")
    ap.add_argument("--write-f0b", action="store_true", help="write docs/PREREG_SETUPS_DESIGN_LOCK_F0B.json (once), after the amendment is approved")
    ap.add_argument("--db", default=str(CANONICAL_DB))
    a = ap.parse_args(argv)
    db = verify_database(a.db)                                   # the lock is only written for the exact canonical file
    if a.write_f1:
        if F1_LOCK.exists():
            raise SystemExit("F1 lock already exists; it is written once.")
        rec = {"locked_at": pd.Timestamp.now(tz="UTC").isoformat(), "git_commit": current_record()["git_commit"], "database_verified": db, **f1_record()}
        F1_LOCK.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {F1_LOCK}\n" + json.dumps({k: rec[k] for k in ("id", "candidates_file", "candidates", "dropped", "stage_a", "cost")}, indent=2))
        return 0
    if a.write_f0c:
        if F0C_LOCK.exists():
            raise SystemExit("F0c lock already exists; it is written once.")
        rec = {"locked_at": pd.Timestamp.now(tz="UTC").isoformat(), "database_verified": db, **f0c_record()}
        F0C_LOCK.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {F0C_LOCK}\n" + json.dumps(rec, indent=2))
        return 0
    if a.write_f0b:
        if F0B_LOCK.exists():
            raise SystemExit("F0b lock already exists; it is written once.")
        rec = {"locked_at": pd.Timestamp.now(tz="UTC").isoformat(), "database_verified": db, **f0b_record()}
        F0B_LOCK.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {F0B_LOCK}\n" + json.dumps(rec, indent=2))
        return 0
    rec = current_record()
    if a.write:
        if DESIGN_LOCK.exists():
            raise SystemExit("design lock already exists; it is written once.")
        rec = {"locked_at": pd.Timestamp.now(tz="UTC").isoformat(), "database_verified": db, **rec}
        DESIGN_LOCK.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {DESIGN_LOCK}")
    print(json.dumps(rec, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
