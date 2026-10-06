"""Stage 3b: how often does each frozen shape actually recur (and is tagging even reliable)?

    python -m src.discovery.vocab_report

A chart's STABLE tags are the tags present in EVERY pass; its stable primary is the primary tag only
if all passes agree. Only stable tags are counted, so one-off model noise cannot create "patterns".
A shape is "recurring" only if stable on >= MIN_SUPPORT_N charts AND >= MIN_SUPPORT_FRAC of charts.
No market outcomes are used anywhere here.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from html import escape
from itertools import combinations
from pathlib import Path

import config
from src.discovery import vocab
from src.discovery.retag import load_rows


def analyse(rows: list[dict], passes: int) -> dict:
    by = defaultdict(dict)
    for r in rows:
        if r.get("error") is None:
            by[r["end_ts"]][r["pass"]] = r          # last good row per (chart, pass)
    complete = {k: v for k, v in by.items() if all(p in v for p in range(1, passes + 1))}
    n = len(complete)
    if n == 0:
        raise SystemExit("No chart has all passes completed.")
    stable, prim_ok, jac = {}, 0, []
    for k, v in complete.items():
        sets = [set(v[p]["tags"]) for p in range(1, passes + 1)]
        prims = {v[p]["primary"] for p in range(1, passes + 1)}
        stable[k] = {"tags": sorted(set.intersection(*sets)),
                     "primary": next(iter(prims)) if len(prims) == 1 else None,
                     "chart": v[1]["chart"], "all": [v[p]["tags"] for p in range(1, passes + 1)]}
        prim_ok += len(prims) == 1
        jac += [len(a & b) / len(a | b) for a, b in combinations(sets, 2)]
    need = max(config.MIN_SUPPORT_N, math.ceil(config.MIN_SUPPORT_FRAC * n))
    counts = {}
    for name in vocab.NAMES:
        any_ = [k for k, s in stable.items() if name in s["tags"]]
        pri = [k for k, s in stable.items() if s["primary"] == name]
        counts[name] = {"stable_charts": len(any_), "stable_primary": len(pri),
                        "share": round(len(any_) / n, 3), "recurring": len(any_) >= need,
                        "examples": [stable[k]["chart"] for k in any_[:4]]}
    no_stable = sum(1 for s in stable.values() if not s["tags"])
    return {"charts": n, "passes": passes, "support_needed": need,
            "primary_agreement": round(prim_ok / n, 3),
            "mean_tag_jaccard": round(sum(jac) / len(jac), 3) if jac else None,
            "charts_with_no_stable_tag": no_stable, "counts": counts,
            "vocab_version": vocab.VOCAB_VERSION, "vocab_sha256": vocab.VOCAB_SHA256}


def sampling_note(run_dir: Path) -> str:
    w = run_dir / "scale.json"
    if w.exists() and json.loads(w.read_text(encoding="utf-8")).get("sampling") == "stratified":
        return ("<p><b>Note:</b> this sample is stratified by window range (equal counts per quartile), so "
                "shares are NOT population frequencies; active windows are over-represented.</p>")
    return ""


def write_report(run_dir: Path, res: dict) -> Path:
    (run_dir / "pattern_counts.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    rows = []
    for name, c in sorted(res["counts"].items(), key=lambda kv: -kv[1]["stable_charts"]):
        imgs = "".join(f"<a href='charts/{escape(e)}'><img src='charts/{escape(e)}' width='150'></a>"
                       for e in c["examples"])
        rows.append(f"<tr><td><b>{escape(name)}</b></td><td>{c['stable_charts']}</td><td>{c['share']:.0%}</td>"
                    f"<td>{c['stable_primary']}</td><td>{'YES' if c['recurring'] else 'no'}</td><td>{imgs}</td></tr>")
    p = run_dir / "vocab_report.html"
    p.write_text(
        "<!doctype html><meta charset='utf-8'><title>Shape recurrence</title>"
        "<style>body{font-family:sans-serif;margin:20px}td,th{padding:6px 10px;border-bottom:1px solid #ddd;"
        "font-size:13px;vertical-align:top;text-align:left}</style>"
        f"<h1>Shape recurrence ({res['charts']} charts, {res['passes']} passes)</h1>"
        f"<p>vocab {res['vocab_version']} · primary-tag agreement between passes <b>{res['primary_agreement']:.0%}</b> · "
        f"mean tag overlap <b>{res['mean_tag_jaccard']}</b> · charts with no stable tag {res['charts_with_no_stable_tag']} · "
        f"recurring = stable on ≥ {res['support_needed']} charts</p>" + sampling_note(run_dir) +
        "<table><tr><th>shape</th><th>stable charts</th><th>share</th><th>stable primary</th><th>recurring?</th>"
        f"<th>examples</th></tr>{''.join(rows)}</table>", encoding="utf-8")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--run-dir", default=str(config.DISCOVERY_DIR / config.DISCOVERY_RUN))
    ap.add_argument("--passes", type=int, default=config.RETAG_PASSES)
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    res = analyse(load_rows(run_dir / "retags.jsonl"), a.passes)
    print(f"charts: {res['charts']} | passes: {res['passes']} | primary-tag agreement: {res['primary_agreement']:.0%} "
          f"| mean tag overlap: {res['mean_tag_jaccard']} | no stable tag: {res['charts_with_no_stable_tag']}")
    print(f"recurring = stable on >= {res['support_needed']} charts")
    for name, c in sorted(res["counts"].items(), key=lambda kv: -kv[1]["stable_charts"]):
        print(f"  {name:22s} stable on {c['stable_charts']:3d} charts ({c['share']:.0%})  primary {c['stable_primary']:3d}"
              f"  {'RECURRING' if c['recurring'] else ''}")
    print(f"report: {write_report(run_dir, res)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
