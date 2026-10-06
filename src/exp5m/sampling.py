"""Deterministic, outcome-blind construction of the 5M discovery sample + clean chart windows.

    python -m src.exp5m.sampling --dry-run                       # funnel + plan, nothing rendered
    python -m src.exp5m.sampling --build --confirm-design-sha <12 chars of the design lock's prereg sha>

CAUSAL NORMALISATION. Each chart shows the 60 candles ending at T, as % relative to the close at T (price axis) with
relative time labels (T-50 .. T). The vertical SPAN is one fixed number for every chart, learned ONLY from the
calibration prefix (the first CALIBRATION_DAYS of data): 99th percentile of window ranges inside that prefix. Every
discovery window starts AFTER the prefix, so no window's chart uses any information from after its own end T
(not even a global constant). Windows wider than the span are excluded (counted), never clipped.

SAMPLING. Candidates are gap-free 60-candle windows that start after the calibration prefix, end before the discovery
cutoff, fit the span, and have FORWARD_MAX gap-free following candles before the cutoff (existence of candles only;
no price values are read for this). Candidates are split into equal-count quartiles of window range (a property of the
chart itself) and N_TARGET/4 windows are taken from each, evenly spread over time, never closer than MIN_GAP_CANDLES
(= no overlap, which is the de-duplication). Nothing about returns/outcomes is used.
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
from src.charts.windows import build_window, valid_end_indices
from src.data.loader import CandleSet, load_candles, tf_to_seconds
from src.discovery.scale import choose_span, window_ranges_pct
from src.discovery.tagset import file_sha256
from src.exp5m import params

OUT_DIR = config.ROOT / "results" / "exp5m" / "discovery"
LABELS = ["Q1_quiet", "Q2", "Q3", "Q4_active"]


def _spread(n_total: int, n: int) -> list[int]:
    """Candidate visiting order: n evenly spaced indices first, then a denser even grid, then everything."""
    first = np.linspace(0, n_total - 1, n).round().astype(int).tolist() if n_total and n else []
    more = np.linspace(0, n_total - 1, min(n_total, 4 * max(n, 1))).round().astype(int).tolist() if n_total else []
    seen, order = set(), []
    for i in first + more + list(range(n_total)):
        if i not in seen:
            seen.add(i)
            order.append(i)
    return order


def calibration_span(df: pd.DataFrame) -> tuple[float, pd.Timestamp, int]:
    """Fixed chart span from the calibration prefix ONLY (uses no candle at/after the prefix end)."""
    step = pd.Timedelta(seconds=tf_to_seconds(params.TIMEFRAME))
    cal_end = df["ts"].iloc[0] + pd.Timedelta(days=params.CALIBRATION_DAYS)
    cal = df[df["ts"] < cal_end].reset_index(drop=True)
    rng = window_ranges_pct(cal, params.TIMEFRAME, params.LOOKBACK)
    if len(rng) == 0:
        raise SystemExit("calibration prefix contains no complete window")
    return choose_span(rng, q=params.SPAN_QUANTILE, step=params.SPAN_STEP_PCT), cal_end, len(rng)


def candidates(df: pd.DataFrame):
    """-> (candidate DataFrame[end_ts, range_pct], span, cal_end, funnel). df = all closed candles (any period)."""
    cutoff = pd.Timestamp(params.DISCOVERY_END)
    span, cal_end, n_cal = calibration_span(df)
    d = df[df["ts"] < cutoff].reset_index(drop=True)              # hold-out candles physically removed here
    step_ns = tf_to_seconds(params.TIMEFRAME) * 1_000_000_000
    ts = d["ts"].dt.as_unit("ns").astype("int64").to_numpy()
    idx = valid_end_indices(d, params.TIMEFRAME, params.LOOKBACK)
    hi = d["high"].rolling(params.LOOKBACK).max().to_numpy()
    lo = d["low"].rolling(params.LOOKBACK).min().to_numpy()
    rng = (hi - lo) / d["close"].to_numpy() * 100.0
    funnel = {"closed_candles_before_cutoff": int(len(d)), "gap_free_windows": int(len(idx))}
    start_ok = ts[idx - (params.LOOKBACK - 1)] >= cal_end.as_unit("ns").value            # integer ns: no tz ambiguity
    idx1 = idx[start_ok]
    funnel["start_after_calibration"] = int(len(idx1))
    span_ok = rng[idx1] <= span
    funnel["excluded_wider_than_span"] = int((~span_ok).sum())
    idx2 = idx1[span_ok]
    fwd_ok = np.zeros(len(idx2), bool)
    inside = idx2 + params.FORWARD_MAX < len(d)
    fwd_ok[inside] = (ts[idx2[inside] + params.FORWARD_MAX] - ts[idx2[inside]]) == params.FORWARD_MAX * step_ns
    funnel["excluded_no_complete_forward_path_before_cutoff"] = int((~fwd_ok).sum())
    idx3 = idx2[fwd_ok]
    funnel["candidates"] = int(len(idx3))
    cand = pd.DataFrame({"end_ts": pd.to_datetime(ts[idx3], unit="ns", utc=True), "range_pct": rng[idx3]})
    return cand, span, cal_end, funnel, d


def select(cand: pd.DataFrame, n_target: int | None = None):
    """Deterministic stratified, time-spread, non-overlapping selection -> list of (end_ts, stratum) sorted by time."""
    n_target = params.N_TARGET if n_target is None else n_target
    gap = pd.Timedelta(seconds=tf_to_seconds(params.TIMEFRAME) * params.MIN_GAP_CANDLES)
    c = cand.sort_values("end_ts").reset_index(drop=True)
    q = pd.qcut(c["range_pct"].rank(method="first"), params.N_STRATA, labels=LABELS[:params.N_STRATA])
    c["stratum"] = q.astype(str)
    per, extra = divmod(n_target, params.N_STRATA)
    taken: list[pd.Timestamp] = []
    out = []
    for k, lab in enumerate(LABELS[:params.N_STRATA]):
        grp = c[c["stratum"] == lab].reset_index(drop=True)
        want, got = per + (1 if k < extra else 0), 0
        for i in _spread(len(grp), min(want, len(grp))):
            if got >= want:
                break
            t = grp["end_ts"].iloc[i]
            j = int(np.searchsorted(taken, t))
            if (j > 0 and t - taken[j - 1] < gap) or (j < len(taken) and taken[j] - t < gap):
                continue
            taken.insert(j, t)
            out.append((t, lab, float(grp["range_pct"].iloc[i])))
            got += 1
    return sorted(out, key=lambda r: r[0])


def chart_style(span: float) -> dict:
    return {"axis_labels": params.AXIS_LABELS, "time_labels": params.TIME_LABELS, "y_span_pct": span}


def style_sha(span: float) -> str:
    st = {**config.CHART_STYLE, **chart_style(span)}
    return hashlib.sha256(json.dumps(st, sort_keys=True, default=str).encode()).hexdigest()


def build(df: pd.DataFrame, out_dir: Path, render: bool = True):
    cand, span, cal_end, funnel, d = candidates(df)
    picks = select(cand)
    cutoff = pd.Timestamp(params.DISCOVERY_END)
    assert all(t < cutoff for t, _, _ in picks), "window beyond discovery cutoff"
    assert all(t - pd.Timedelta(seconds=tf_to_seconds(params.TIMEFRAME) * (params.LOOKBACK - 1)) >= cal_end for t, _, _ in picks)
    by = pd.Series([s for _, s, _ in picks]).value_counts().reindex(LABELS[:params.N_STRATA]).fillna(0).astype(int).to_dict()
    meta = {"experiment": params.EXPERIMENT, "timeframe": params.TIMEFRAME, "lookback": params.LOOKBACK,
            "calibration_days": params.CALIBRATION_DAYS, "calibration_end": cal_end.isoformat(),
            "span_pct": span, "span_quantile": params.SPAN_QUANTILE, "discovery_end": params.DISCOVERY_END,
            "funnel": funnel, "n_target": params.N_TARGET, "n_selected": len(picks), "per_stratum": by,
            "first_window_end": picks[0][0].isoformat() if picks else None,
            "last_window_end": picks[-1][0].isoformat() if picks else None, "chart_style_sha256": style_sha(span)}
    if not render:
        return meta, []
    cs = CandleSet(d, params.SYMBOL, params.TIMEFRAME, "exp5m")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, (t, lab, r) in enumerate(picks, 1):
        w = build_window(cs, t, params.LOOKBACK)                  # validates: exactly 60 closed gap-free candles ending at T
        path = out_dir / "charts" / chart_filename(w)
        render_window(w, path, chart_style(span))
        rows.append({"end_ts": t.isoformat(), "chart": path.name, "stratum": lab, "range_pct": round(r, 4),
                     "image_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "chart_style_sha256": meta["chart_style_sha256"],
                     "description_stage": (i - 1) % params.D1_EVERY == 0})
        if i % 100 == 0:
            print(f"rendered {i}/{len(picks)}")
    (out_dir / "windows5m.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    meta["windows5m_jsonl_sha256"] = file_sha256(out_dir / "windows5m.jsonl")
    meta["n_description_stage"] = sum(1 for r in rows if r["description_stage"])
    (out_dir / "sample_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta, rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=str(config.DB_PATH))
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--confirm-design-sha", help="first 12 chars of the preregistration sha256 in the design lock")
    a = ap.parse_args(argv)
    if a.build:
        from src.exp5m import lock5m
        lock5m.require_design_lock(a.confirm_design_sha)
    cs = load_candles(a.db, params.SYMBOL, params.TIMEFRAME)
    meta, rows = build(cs.df, Path(a.out), render=a.build and not a.dry_run)
    print(json.dumps(meta, indent=2))
    if a.build:
        print(f"wrote {a.out}  (windows5m.jsonl sha256 {meta['windows5m_jsonl_sha256']})")
    else:
        print("dry-run: nothing rendered, nothing written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
