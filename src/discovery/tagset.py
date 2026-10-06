"""Stage 3 at scale: sample many discovery-period windows and tag them (no free-text step).

    python -m src.discovery.tagset --dry-run             # sampling plan, NO charts rendered, NO API
    python -m src.discovery.tagset                       # TAGSET_COUNT windows, RETAG_PASSES passes, budget-capped
    python -m src.discovery.tagset --count 300 --budget-usd 1.5

* Only candles before config.discovery_end(timeframe) are used (held-out data is never read).
* Same fixed-span, anonymised charts as the 50-chart run (style hash recorded).
* Sampling "stratified": equal numbers of windows from each quartile of window range, so quiet windows
  do not crowd out the rarer large-move shapes. It uses ONLY the window's own size - no outcomes.
  Shares in the report are therefore NOT population frequencies. "even": evenly spaced instead.
* HARD spending cap (--budget-usd): the run stops between charts; re-run resumes where it stopped.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import config
from src.charts.renderer import chart_filename, render_window
from src.charts.windows import build_window
from src.data.loader import load_candles, tf_to_seconds
from src.discovery import scale, vocab
from src.discovery.discover import OpenAIDescriber, discovery_candles
from src.discovery.retag import load_rows, run_retag


def _spread(n_total: int, n: int) -> list[int]:
    """Candidate order: n evenly spaced indices first, then the rest of a 4n evenly spaced set."""
    first = np.linspace(0, n_total - 1, n).round().astype(int).tolist()
    more = np.linspace(0, n_total - 1, min(n_total, 4 * n)).round().astype(int).tolist()
    seen, order = set(), []
    for i in first + more + list(range(n_total)):
        if i not in seen:
            seen.add(i); order.append(i)
    return order


def default_run_dir(timeframe: str) -> Path:
    """5m keeps the original folder name; other timeframes get their own folder."""
    tf = tf_to_seconds(timeframe)
    name = config.TAGSET_RUN if tf == tf_to_seconds(config.TIMEFRAME) else f"{config.TAGSET_RUN}_{timeframe}"
    if str(timeframe).strip().lower() in config.DISCOVERY_END_BY_TF:       # custom split -> its own folder
        name += "_cut" + pd.Timestamp(config.discovery_end(timeframe)).strftime("%Y%m%d")
    return config.DISCOVERY_DIR / name


def pick(ranges: pd.Series, eligible: pd.DatetimeIndex, count: int, mode: str,
         min_gap: pd.Timedelta | None = None, timeframe: str | None = None) -> list[tuple[pd.Timestamp, str]]:
    """-> [(end_ts, stratum)] sorted by time. Deterministic (no randomness). No two picks are closer
    than `min_gap` (default: one full window), so sampled windows never overlap and are not
    near-duplicates."""
    min_gap = min_gap or pd.Timedelta(seconds=tf_to_seconds(timeframe or config.TIMEFRAME) * config.LOOKBACK)
    r = ranges.loc[eligible]
    count = min(count, len(r))
    if mode == "even":
        groups = [("all", r, count)]
    elif mode == "stratified":
        q = pd.qcut(r.rank(method="first"), 4, labels=["Q1_quiet", "Q2", "Q3", "Q4_active"])
        per, extra = divmod(count, 4)
        groups = [(lab, r[q == lab], per + (1 if k < extra else 0))
                  for k, lab in enumerate(["Q1_quiet", "Q2", "Q3", "Q4_active"])]
    else:
        raise ValueError(f"unknown sampling mode {mode!r}")
    taken: list[pd.Timestamp] = []                     # sorted, for the spacing check
    out = []
    for lab, grp, n in groups:
        got = 0
        for i in _spread(len(grp), min(n, len(grp))):
            if got >= n:
                break
            t = grp.index[i]
            j = np.searchsorted(taken, t)
            near = (j > 0 and t - taken[j - 1] < min_gap) or (j < len(taken) and taken[j] - t < min_gap)
            if near:
                continue
            taken.insert(j, t)
            out.append((t, lab)); got += 1
    return sorted(out)


def prepare(cs, out_dir: Path, count: int, mode: str, render: bool = True):
    dcs = discovery_candles(cs)
    ranges = scale.window_ranges_pct(dcs.df, dcs.timeframe, config.LOOKBACK)
    span = scale.choose_span(ranges)
    elig = scale.eligible_ends(ranges, span)
    picks = pick(ranges, elig, count, mode, timeframe=dcs.timeframe)
    if len(picks) < count:
        print(f"WARNING: only {len(picks)} non-overlapping windows fit (requested {count}).")
    cutoff = config.discovery_end(dcs.timeframe)
    assert all(t < pd.Timestamp(cutoff) for t, _ in picks), "window beyond discovery cutoff"
    style = {**config.DISCOVERY_CHART_STYLE, "y_span_pct": span}
    info = {"span_pct": span, "windows_total": len(ranges), "windows_eligible": len(elig),
            "sampling": mode, "count": len(picks), "timeframe": dcs.timeframe, "discovery_end": cutoff,
            "chart_style": {**config.CHART_STYLE, **style}}
    info["chart_style_sha256"] = hashlib.sha256(
        json.dumps(info["chart_style"], sort_keys=True, default=str).encode()).hexdigest()
    if not render:
        return picks, info, []
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "scale.json").write_text(json.dumps(info, indent=2, default=str), encoding="utf-8")
    windows = []
    for i, (t, stratum) in enumerate(picks, 1):
        w = build_window(dcs, t, config.LOOKBACK)
        path = out_dir / "charts" / chart_filename(w)
        if not path.exists():
            render_window(w, path, style)
        windows.append({"end_ts": t.isoformat(), "chart": path.name, "stratum": stratum,
                        "range_pct": round(float(ranges.loc[t]), 4),
                        "image_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "chart_style_sha256": info["chart_style_sha256"]})
        if i % 100 == 0:
            print(f"rendered {i}/{len(picks)}")
    (out_dir / "windows.jsonl").write_text("\n".join(json.dumps(w) for w in windows), encoding="utf-8")
    return picks, info, windows


def load_windows(out_dir: Path) -> list[dict]:
    f = out_dir / "windows.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def _context(cs):
    dcs = discovery_candles(cs)
    ranges = scale.window_ranges_pct(dcs.df, dcs.timeframe, config.LOOKBACK)
    span = scale.choose_span(ranges)
    elig = scale.eligible_ends(ranges, span)
    style = {**config.DISCOVERY_CHART_STYLE, "y_span_pct": span}
    info = {"span_pct": span, "windows_total": len(ranges), "windows_eligible": len(elig),
            "timeframe": dcs.timeframe, "discovery_end": config.discovery_end(dcs.timeframe),
            "chart_style": {**config.CHART_STYLE, **style}}
    info["chart_style_sha256"] = hashlib.sha256(
        json.dumps(info["chart_style"], sort_keys=True, default=str).encode()).hexdigest()
    return dcs, ranges, elig, style, info


def _near(taken: list, t: pd.Timestamp, min_gap: pd.Timedelta) -> tuple[bool, int]:
    j = int(np.searchsorted(taken, t))
    return bool((j > 0 and t - taken[j - 1] < min_gap) or (j < len(taken) and taken[j] - t < min_gap)), j


def topup(cs, out_dir: Path, n: int, render: bool = True):
    """Add up to `n` MORE discovery-period windows to an existing sample (option C: fill the remaining
    non-overlapping capacity). New windows never overlap existing ones, stay before the discovery cutoff,
    and use the identical chart style (checked by hash). Existing windows are never changed.
    Returns (new_picks [(ts, stratum)], all_windows)."""
    existing = load_windows(out_dir)
    if not existing:
        raise SystemExit(f"--topup needs an existing sample ({out_dir / 'windows.jsonl'}). Run the base sampling first.")
    dcs, ranges, elig, style, info = _context(cs)
    bad = [w["end_ts"] for w in existing if w["chart_style_sha256"] != info["chart_style_sha256"]]
    if bad:
        raise SystemExit("Existing windows were rendered with a different chart style; refusing to mix them.")
    min_gap = pd.Timedelta(seconds=tf_to_seconds(dcs.timeframe) * config.LOOKBACK)
    taken = sorted(pd.Timestamp(w["end_ts"]) for w in existing)
    q = pd.qcut(ranges.loc[elig].rank(method="first"), 4, labels=["Q1_quiet", "Q2", "Q3", "Q4_active"])
    cand = [t for t in elig if not _near(taken, t, min_gap)[0]]
    new: list[tuple[pd.Timestamp, str]] = []
    for i in _spread(len(cand), min(n, len(cand))) if cand else []:
        if len(new) >= n:
            break
        t = cand[i]
        near, j = _near(taken, t, min_gap)
        if near:
            continue
        taken.insert(j, t)
        new.append((t, str(q.loc[t])))
    new.sort()
    cutoff = pd.Timestamp(info["discovery_end"])
    assert all(t < cutoff for t, _ in new), "window beyond discovery cutoff"
    if not render:
        return new, existing
    batch = f"topup{1 + len({w.get('batch') for w in existing if w.get('batch')})}"
    added = []
    for i, (t, stratum) in enumerate(new, 1):
        w = build_window(dcs, t, config.LOOKBACK)
        path = out_dir / "charts" / chart_filename(w)
        if not path.exists():
            render_window(w, path, style)
        added.append({"end_ts": t.isoformat(), "chart": path.name, "stratum": stratum,
                      "range_pct": round(float(ranges.loc[t]), 4),
                      "image_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "chart_style_sha256": info["chart_style_sha256"], "batch": batch})
        if i % 100 == 0:
            print(f"rendered {i}/{len(new)}")
    allw = sorted(existing + added, key=lambda w: w["end_ts"])
    (out_dir / "windows.jsonl").write_text("\n".join(json.dumps(w) for w in allw), encoding="utf-8")
    sj = out_dir / "scale.json"
    meta = json.loads(sj.read_text(encoding="utf-8")) if sj.exists() else {}
    meta.setdefault("topups", []).append({"batch": batch, "requested": n, "added": len(added),
                                         "at": pd.Timestamp.now(tz="UTC").isoformat()})
    sj.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    return new, allw


def file_sha256(path: Path) -> str:
    """sha256 of the file with CRLF normalised to LF, so the hash is identical on Windows and Linux/GitHub
    (git on Windows may check text files out with CRLF line endings)."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=str(config.DB_PATH))
    ap.add_argument("--count", type=int, default=config.TAGSET_COUNT)
    ap.add_argument("--passes", type=int, default=config.RETAG_PASSES)
    ap.add_argument("--budget-usd", type=float, default=config.TAGSET_BUDGET_USD)
    ap.add_argument("--sampling", choices=["stratified", "even"], default=config.TAGSET_SAMPLING)
    ap.add_argument("--model", default=config.OPENAI_MODEL)
    ap.add_argument("--timeframe", default=config.TIMEFRAME, help="e.g. 5m, 15m, 1h (default config.TIMEFRAME)")
    ap.add_argument("--out", help="run folder (default results/discovery/tagset_v1[_<timeframe>])")
    ap.add_argument("--topup", type=int, metavar="N",
                    help="ADD up to N more non-overlapping discovery windows to the existing sample (use a big\n"
                         "number, e.g. 999, to fill all remaining capacity). Existing windows are never changed.")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out) if a.out else default_run_dir(a.timeframe)
    cs = load_candles(a.db, timeframe=a.timeframe)
    if a.dry_run and a.topup is not None:
        new, existing = topup(cs, out, a.topup, render=False)
        by = pd.Series([s_ for _, s_ in new]).value_counts().sort_index() if new else pd.Series(dtype=int)
        print(f"run dir: {out}\nexisting windows: {len(existing)} | can add: {len(new)} (requested {a.topup})\n"
              + (f"new windows span {new[0][0]} -> {new[-1][0]} (cutoff {config.discovery_end(a.timeframe)})\n{by.to_string()}\n" if new else "")
              + f"API calls: {len(new) * a.passes} (about ${len(new) * a.passes * 0.0009:.2f} at the earlier rate); hard budget ${a.budget_usd:.2f}")
        return 0
    if a.dry_run:
        picks, info, _ = prepare(cs, out, a.count, a.sampling, render=False)
        by = pd.Series([s for _, s in picks]).value_counts().sort_index()
        print(f"run dir: {out}\ntimeframe {a.timeframe} ({config.LOOKBACK} candles/window)\nmodel {a.model} | vocab {vocab.VOCAB_VERSION} | passes {a.passes}\n"
              f"discovery cutoff {info['discovery_end']}; fixed span {info['span_pct']}% "
              f"(eligible {info['windows_eligible']}/{info['windows_total']} windows)\n"
              f"{len(picks)} windows ({a.sampling}): {picks[0][0]} -> {picks[-1][0]}\n{by.to_string()}\n"
              f"API calls: {len(picks) * a.passes}; hard budget ${a.budget_usd:.2f} "
              f"(prices: {config.OPENAI_PRICE_USD_PER_M} USD/1M tokens). No cost estimate before the first "
              f"calls: the run measures real token use and stops at the cap.")
        return 0
    if a.topup is not None:
        new, windows = topup(cs, out, a.topup)
        print(f"added {len(new)} windows (total {len(windows)})")
    elif load_windows(out):
        windows = load_windows(out)
        print(f"using the existing window list ({len(windows)} windows); --count/--sampling ignored. "
              f"Use --topup N to add windows.")
    else:
        picks, info, windows = prepare(cs, out, a.count, a.sampling)
    factory = lambda user: OpenAIDescriber(a.model, vocab.RETAG_SYSTEM, user)   # noqa: E731
    rows = run_retag(out, factory, a.passes, charts=windows, budget_usd=a.budget_usd)
    from src.discovery import cost
    print(f"windows.jsonl sha256: {file_sha256(out / 'windows.jsonl')}")
    print(f"total spent on this run folder: ${cost.total_cost(rows):.3f}\nnext: python -m src.discovery.vocab_report "
          f"--run-dir {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
