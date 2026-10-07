"""READ-ONLY verification that the rendered Stage A charts correspond EXACTLY to the frozen sample record.

    python -m src.setups.verify_charts --confirm-design-sha <12 chars>

Run on the charts already rendered by `src.setups.sampling --build`. All 12 checks must pass; ANY difference is a
failure (no tolerance, no "close enough"): the report says FAIL, the exit code is 1.

  1 exactly 558 PNGs                          2 names S0001..S0558, each exactly once
  3 every chart maps to exactly one row       4 every row maps to exactly one chart
  5 PNG SHA-256 == recorded image_sha256      6 one chart_style_sha256 everywhere, equal to the code's
  7 no leakage in names / PNG metadata / bytes / send order
  8 every chart ends at its registered end_ts (and a byte-for-byte re-render from the database matches)
  9 exactly 96 gap-free candles ending at end_ts
 10 no candle after end_ts is visible (the chart is byte-identical when the future is altered; a leakage test only)
 11 dataset == F0 lock                        12 selection / send-order hashes and metadata unchanged

Charts are re-rendered from the database into a temporary folder and compared byte for byte. Nothing in the repository
is modified except the small report file. No API call, no outcome, no lock or sampler change. A helper OUTSIDE the F0 lock.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import struct
import tempfile
from pathlib import Path

import pandas as pd

from src.charts.renderer import render_window
from src.charts.windows import build_window
from src.data.loader import CandleSet, load_candles, tf_to_seconds
from src.discovery.tagset import file_sha256
from src.setups import params, sampling, store

EXPECTED_N = 558                      # accepted outcome of the sampler review (commit 6015fdb)
ALLOWED_CHUNKS = {"IHDR", "pHYs", "IDAT", "IEND"}
LEAK_BYTES = (b"BTC", b"USDT", b"15m", b"2025", b"2026", b"Matplotlib", b"matplotlib", b"Software")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def png_chunks(data: bytes) -> list[tuple[str, bytes]]:
    """[(chunk type, payload)] of a PNG; a non-PNG gives [("NOT_A_PNG", b"")]."""
    if data[:8] != PNG_MAGIC:
        return [("NOT_A_PNG", b"")]
    i, out = 8, []
    while i + 8 <= len(data):
        n, = struct.unpack(">I", data[i:i + 4])
        out.append((data[i + 4:i + 8].decode("latin1"), data[i + 8:i + 8 + n]))
        i += 12 + n
    return out


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _chk(passed: bool, detail) -> dict:
    return {"passed": bool(passed), "detail": detail}


def verify_charts(df: pd.DataFrame, run_dir: Path, expected_n: int | None = EXPECTED_N, future_every: int = 10) -> dict:
    """df = all closed candles of the canonical series. Returns {check: {passed, detail}}. Reads files, writes none."""
    run_dir = Path(run_dir)
    rows = store.load_jsonl(run_dir / "windows_setups.jsonl")
    meta = json.loads((run_dir / "sample_meta.json").read_text(encoding="utf-8"))
    charts = run_dir / "charts"
    pngs = sorted(p.name for p in charts.glob("*")) if charts.exists() else []
    n = len(rows)
    res: dict[str, dict] = {}

    res["1_png_count"] = _chk(len(pngs) == n and (expected_n is None or n == expected_n) and all(p.endswith(".png") for p in pngs),
                              {"pngs": len(pngs), "rows": n, "expected": expected_n})
    want = [f"S{i:04d}.png" for i in range(1, n + 1)]
    res["2_names_exactly_S0001_to_SN_once"] = _chk(pngs == want and len(set(pngs)) == len(pngs),
                                                   {"missing": sorted(set(want) - set(pngs))[:10], "extra": sorted(set(pngs) - set(want))[:10]})
    row_files = [r["chart"] for r in rows]
    res["3_every_chart_maps_to_exactly_one_row"] = _chk(sorted(row_files) == pngs and len(set(row_files)) == len(row_files),
                                                       {"charts_without_row": sorted(set(pngs) - set(row_files))[:10],
                                                        "duplicate_rows": len(row_files) - len(set(row_files))})
    res["4_every_row_maps_to_exactly_one_chart"] = _chk(set(row_files) <= set(pngs) and len({r["chart_id"] for r in rows}) == n
                                                       and all(r["chart"] == r["chart_id"] + ".png" for r in rows),
                                                       {"rows_without_chart": sorted(set(row_files) - set(pngs))[:10]})
    bad_sha = [r["chart"] for r in rows if not (charts / r["chart"]).exists() or _sha((charts / r["chart"]).read_bytes()) != r["image_sha256"]]
    res["5_image_sha256_matches_record"] = _chk(not bad_sha, {"n_mismatch": len(bad_sha), "mismatches": bad_sha[:10]})
    styles = {r["chart_style_sha256"] for r in rows}
    res["6_single_chart_style"] = _chk(styles == {meta["chart_style_sha256"]} and meta["chart_style_sha256"] == sampling.style_sha(),
                                       {"styles_in_rows": sorted(styles), "meta": meta["chart_style_sha256"], "code": sampling.style_sha()})

    # 7 leakage: neutral names, PNG chunks limited to the allowed set, no identifying strings in the non-image chunks
    leaks, chunk_bad = [], set()
    for r in rows:
        f = charts / r["chart"]
        if not re.fullmatch(r"S\d{4}\.png", r["chart"]):
            leaks.append(f"{r['chart']}: non-neutral file name")
        if not f.exists():
            continue
        for kind, payload in png_chunks(f.read_bytes()):
            if kind not in ALLOWED_CHUNKS:
                chunk_bad.add(kind)
            if kind != "IDAT":                                    # compressed pixels are not searched (random bytes)
                leaks += [f"{r['chart']}: {kind} contains {s!r}" for s in LEAK_BYTES if s in payload]
    t_ns = [pd.Timestamp(r["end_ts"]).value for r in rows]
    rho = float(pd.Series(range(n)).corr(pd.Series(t_ns).rank())) if n > 2 else 0.0      # Spearman = Pearson of ranks (no scipy)
    rho_limit = 4.0 / (max(n - 1, 1) ** 0.5)                       # 4 standard errors of a random shuffle (0.17 for 558 charts)
    res["7_no_leakage_in_names_metadata_bytes"] = _chk(not leaks and not chunk_bad and abs(rho) < rho_limit,
                                                       {"leaks": leaks[:10], "unexpected_png_chunks": sorted(chunk_bad), "allowed": sorted(ALLOWED_CHUNKS),
                                                        "spearman_chart_id_vs_time": round(rho, 4), "max_abs_spearman_allowed": round(rho_limit, 4)})

    # 8 / 9 / 10: rebuild every window from candles <= end_ts only, re-render, compare byte for byte
    cutoff = pd.Timestamp(params.DISCOVERY_END)
    d = df[df["ts"] < cutoff].reset_index(drop=True)
    cs = CandleSet(d, params.SYMBOL, params.TIMEFRAME, "setups")
    step = pd.Timedelta(seconds=tf_to_seconds(params.TIMEFRAME))
    end_bad, lb_bad, render_bad, future_bad, built = [], [], [], [], 0
    tmp = Path(tempfile.mkdtemp(prefix="verify_charts_"))
    for k, r in enumerate(rows):
        t = pd.Timestamp(r["end_ts"])
        try:
            w = build_window(cs, t, params.LOOKBACK)          # raises unless a closed candle with ts == t exists
            built += 1
            raw = w.raw
            if raw["ts"].iloc[-1] != t or not t < cutoff:
                end_bad.append(r["chart_id"])
            if (len(raw) != params.LOOKBACK or not bool((raw["ts"].diff().dropna() == step).all())
                    or raw["ts"].iloc[0] != t - step * (params.LOOKBACK - 1)):
                lb_bad.append(r["chart_id"])
            p = render_window(w, tmp / r["chart"], sampling.chart_style())
            if p.read_bytes() != (charts / r["chart"]).read_bytes() or _sha(p.read_bytes()) != r["image_sha256"]:
                render_bad.append(r["chart_id"])
            if future_every and k % future_every == 0:       # leakage test: change every candle after T
                alt = d.copy()
                later = alt["ts"] > t
                alt.loc[later, ["open", "high", "low", "close"]] = alt.loc[later, ["open", "high", "low", "close"]] * 3.0
                w2 = build_window(CandleSet(alt, params.SYMBOL, params.TIMEFRAME, "setups"), t, params.LOOKBACK)
                p2 = render_window(w2, tmp / ("alt_" + r["chart"]), sampling.chart_style())
                if p2.read_bytes() != p.read_bytes() or not w2.raw.equals(raw):
                    future_bad.append(r["chart_id"])
        except Exception as e:                                # any exception is a failure, never skipped
            end_bad.append(f"{r['chart_id']}: {type(e).__name__}: {e}")
    res["8_end_ts_and_byte_identical_rerender"] = _chk(not end_bad and not render_bad and built == n,
                                                       {"windows_rebuilt": built, "bad_end_ts": end_bad[:10], "rerender_mismatches": render_bad[:10]})
    res["9_96_candle_gap_free_lookback"] = _chk(not lb_bad and built == n, {"lookback": params.LOOKBACK, "bad": lb_bad[:10]})
    res["10_no_candle_after_end_ts_visible"] = _chk(not future_bad and built == n,
                                                    {"future_altered_for_every_nth_chart": future_every, "bad": future_bad[:10]})

    # 12 selection / send order / metadata unchanged: recomputed from the database, compared with the record
    meta2, _ = sampling.build(df, run_dir, render=False)
    listing = sorted((r["end_ts"], r["stratum"]) for r in rows)
    order = list(range(len(listing)))
    random.Random(params.SEED_ORDER).shuffle(order)
    sel_sha = _sha(json.dumps([list(x) for x in listing], sort_keys=True).encode())
    send_sha = _sha(json.dumps([list(listing[i]) for i in order], sort_keys=True).encode())
    keys = ("funnel", "feature_cutpoints_terciles", "n_selected", "per_stratum", "shortfall", "first_window_end", "last_window_end",
            "chart_style_sha256", "seed_order", "min_gap_candles", "discovery_end", "lookback", "timeframe", "n_target")
    same_meta = {k: meta.get(k) == json.loads(json.dumps(meta2.get(k))) for k in keys}
    same_order = [[r["end_ts"], r["stratum"]] for r in rows] == [list(listing[i]) for i in order]
    # the recomputed selection itself must equal the recorded rows (not only the metadata)
    cand, _, _ = sampling.candidates(df)
    picks, _, _ = sampling.select(cand, sampling.cutpoints(cand))
    same_sel = sorted((t.isoformat(), s) for t, s, _ in picks) == listing
    res["12_selection_send_order_and_metadata_unchanged"] = _chk(
        all(same_meta.values()) and same_order and same_sel and file_sha256(run_dir / "windows_setups.jsonl") == meta["windows_setups_jsonl_sha256"],
        {"metadata_equal": same_meta, "file_order_equals_seeded_shuffle": same_order, "recomputed_selection_equals_record": same_sel,
         "selection_sha256": sel_sha, "send_order_sha256": send_sha, "windows_jsonl_sha_matches_meta": file_sha256(run_dir / "windows_setups.jsonl") == meta["windows_setups_jsonl_sha256"]})
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--confirm-design-sha", required=True)
    ap.add_argument("--run-dir", default=str(store.RUN_DIR))
    ap.add_argument("--db", default=None)
    ap.add_argument("--out", default=None, help="default: <run-dir>/chart_verification.json")
    a = ap.parse_args(argv)
    from src.setups import lock
    lk = lock.require_design_lock(a.confirm_design_sha)               # refuses unless the F0 lock is intact
    db_path = Path(a.db) if a.db else lock.CANONICAL_DB
    db = lock.verify_database(db_path)
    cs = load_candles(db_path, params.SYMBOL, params.TIMEFRAME)
    run_dir = Path(a.run_dir)
    try:
        res = verify_charts(cs.df, run_dir)
    except Exception as e:
        res = {"0_verification_could_run": _chk(False, f"{type(e).__name__}: {e}")}
    res["11_dataset_matches_f0_lock"] = _chk(db["sha256"] == lk["dataset"]["sha256"] and db["bytes"] == lk["dataset"]["bytes"], db)
    present = {int(re.match(r"\d+", k).group()) for k in res}
    ok = all(v["passed"] for v in res.values()) and set(range(1, 13)) <= present      # all 12 checks must exist AND pass
    rep = {"all_passed": ok, "design_lock_verified": True, "n_rows": len(store.load_jsonl(run_dir / "windows_setups.jsonl")),
           "checks": dict(sorted(res.items(), key=lambda kv: (int(re.match(r"\d+", kv[0]).group()), kv[0])))}
    out = Path(a.out) if a.out else run_dir / "chart_verification.json"
    out.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    for k, v in rep["checks"].items():
        print(("PASS  " if v["passed"] else "FAIL  ") + k + ("" if v["passed"] else "   " + json.dumps(v["detail"])[:300]))
    print(("ALL 12 CHECKS PASSED" if ok else "DISCREPANCY FOUND - do not proceed") + f"  -> {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
