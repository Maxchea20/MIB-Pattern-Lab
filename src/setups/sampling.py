"""Deterministic, outcome-blind Stage A sample and clean 15M chart windows (pre-registration section 5).

    python -m src.setups.sampling --dry-run                                     # funnel + plan; nothing rendered
    python -m src.setups.sampling --build --confirm-design-sha <12 chars>       # renders 600 charts

Candidates are 96-candle gap-free windows ending before the discovery cutoff that also have FORWARD_MAX gap-free
following candles before the cutoff (existence of candles only: no price after T is read). Chart-only features of the
96 candles define six strata (directional, sideways, expansion, compression, sharp, slow) by terciles taken over all
candidates (disclosed hindsight about the distribution of CHART features, never about outcomes). 100 windows per stratum,
strata processed in a fixed order, a window belongs to the first stratum that accepts it, never closer than
MIN_GAP_CANDLES to an accepted window. The charts are shuffled with a fixed seed and given neutral ids (S0001...), so
neither file names nor order reveal chronology. This module never imports the outcome code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

import config
from src.charts.renderer import render_window
from src.charts.windows import build_window, valid_end_indices
from src.data.loader import CandleSet, load_candles, tf_to_seconds
from src.discovery.audit import window_features
from src.discovery.discover import discovery_candles
from src.discovery.tagset import file_sha256
from src.setups import params, store

FEATURES = ("eff", "net_pct", "abs_net", "re", "sharp")


def chart_style() -> dict:
    return {"axis_labels": params.AXIS_LABELS, "time_labels": params.TIME_LABELS, "y_span_pct": params.Y_SPAN_PCT}


def style_sha() -> str:
    st = {**config.CHART_STYLE, **chart_style()}
    return hashlib.sha256(json.dumps(st, sort_keys=True, default=str).encode()).hexdigest()


def _spread(n_total: int, n: int) -> list[int]:
    """Visiting order: n evenly spaced indices first, then a denser even grid, then everything."""
    first = np.linspace(0, n_total - 1, n).round().astype(int).tolist() if n_total and n else []
    more = np.linspace(0, n_total - 1, min(n_total, 4 * max(n, 1))).round().astype(int).tolist() if n_total else []
    seen, order = set(), []
    for i in first + more + list(range(n_total)):
        if i not in seen:
            seen.add(i)
            order.append(i)
    return order


def chart_features(raw: pd.DataFrame) -> dict:
    """Chart-only features of one 96-candle window (rows <= T). `re` is NaN if the preceding 72 candles have zero range."""
    f = window_features(raw)
    h, l = raw["high"].to_numpy(float), raw["low"].to_numpy(float)
    n, k = len(raw), params.RE_RECENT
    r_recent = h[n - k:].max() - l[n - k:].min()
    r_prior = h[: n - k].max() - l[: n - k].min()
    return {"eff": float(f["eff"]), "net_pct": float(f["net_pct"]), "abs_net": abs(float(f["net_pct"])),
            "re": float(r_recent / r_prior) if r_prior > 0 else float("nan"),
            "sharp": float(max(f["max_rise5"], -f["max_fall5"]))}


def candidates(df: pd.DataFrame):
    """-> (candidate DataFrame[end_ts + features], funnel, discovery candles). df = all closed candles (any period)."""
    cutoff = pd.Timestamp(params.DISCOVERY_END)
    d = df[df["ts"] < cutoff].reset_index(drop=True)             # hold-out candles physically removed here
    step_ns = tf_to_seconds(params.TIMEFRAME) * 1_000_000_000
    ts = d["ts"].dt.as_unit("ns").astype("int64").to_numpy()
    idx = valid_end_indices(d, params.TIMEFRAME, params.LOOKBACK)
    funnel = {"closed_candles_before_cutoff": int(len(d)), "full_lookback_windows": int(len(idx))}
    ok = np.zeros(len(idx), bool)
    inside = idx + params.FORWARD_MAX < len(d)
    ok[inside] = (ts[idx[inside] + params.FORWARD_MAX] - ts[idx[inside]]) == params.FORWARD_MAX * step_ns
    funnel["excluded_no_complete_forward_path_before_cutoff"] = int((~ok).sum())
    idx = idx[ok]
    funnel["candidates"] = int(len(idx))
    ohlc = d[["open", "high", "low", "close"]]
    rows = [chart_features(ohlc.iloc[i - params.LOOKBACK + 1: i + 1]) for i in idx]
    cand = pd.DataFrame(rows, columns=list(FEATURES))
    cand.insert(0, "end_ts", pd.to_datetime(ts[idx], unit="ns", utc=True))
    return cand, funnel, d


def cutpoints(cand: pd.DataFrame) -> dict:
    """Terciles (lower, upper cut) of each feature over ALL candidates."""
    out = {}
    for f in ("eff", "abs_net", "re", "sharp"):
        v = cand[f].to_numpy(float)
        v = v[np.isfinite(v)]
        lo, hi = np.quantile(v, [1 / 3, 2 / 3])
        out[f] = [float(lo), float(hi)]
    return out


def stratum_masks(cand: pd.DataFrame, cuts: dict) -> dict[str, np.ndarray]:
    """Boolean eligibility per stratum (pre-registration table). NaN never qualifies."""
    eff, net, re, sh = (cand[c].to_numpy(float) for c in ("eff", "abs_net", "re", "sharp"))
    with np.errstate(invalid="ignore"):
        return {
            "S1_directional": (eff >= cuts["eff"][1]) & (net >= cuts["abs_net"][1]),
            "S2_sideways": (eff <= cuts["eff"][0]) & (net <= cuts["abs_net"][0]),
            "S3_expansion": re >= cuts["re"][1],
            "S4_compression": re <= cuts["re"][0],
            "S5_sharp": sh >= cuts["sharp"][1],
            "S6_slow": sh <= cuts["sharp"][0]}


def first_stratum(masks: dict[str, np.ndarray], i: int) -> str:
    for name in params.STRATA:
        if masks[name][i]:
            return name
    return "S0_other"


def select(cand: pd.DataFrame, cuts: dict):
    """-> (picks [(end_ts, stratum, row_index)], shortfall {stratum: missing}). Deterministic; no outcome is read."""
    gap_ns = tf_to_seconds(params.TIMEFRAME) * params.MIN_GAP_CANDLES * 1_000_000_000
    c = cand.sort_values("end_ts").reset_index(drop=True)
    masks = stratum_masks(c, cuts)
    ts = c["end_ts"].dt.as_unit("ns").astype("int64").to_numpy()
    taken: list[int] = []                                    # sorted ns of accepted windows
    picked: list[tuple[int, str]] = []
    shortfall = {}
    for name in params.STRATA:
        assigned = {p[0] for p in picked}
        pool = [i for i in np.where(masks[name])[0] if i not in assigned]
        got = 0
        for j in _spread(len(pool), min(params.PER_STRATUM, len(pool))):
            if got >= params.PER_STRATUM:
                break
            i = pool[j]
            t = int(ts[i])
            k = int(np.searchsorted(taken, t))
            if (k > 0 and t - taken[k - 1] < gap_ns) or (k < len(taken) and taken[k] - t < gap_ns):
                continue
            taken.insert(k, t)
            picked.append((i, name))
            got += 1
        if got < params.PER_STRATUM:
            shortfall[name] = params.PER_STRATUM - got
    picks = [(c["end_ts"].iloc[i], name, int(i)) for i, name in sorted(picked, key=lambda p: ts[p[0]])]
    return picks, shortfall, c


def build(df: pd.DataFrame, out_dir: Path, render: bool = True, db_meta: dict | None = None):
    cand, funnel, d = candidates(df)
    cuts = cutpoints(cand)
    picks, shortfall, c = select(cand, cuts)
    cutoff = pd.Timestamp(params.DISCOVERY_END)
    assert all(t < cutoff for t, _, _ in picks), "window beyond discovery cutoff"
    order = list(range(len(picks)))
    random.Random(params.SEED_ORDER).shuffle(order)               # neutral, chronology-free send order
    by = pd.Series([picks[i][1] for i in order]).value_counts().reindex(list(params.STRATA)).fillna(0).astype(int).to_dict()
    times = sorted(t for t, _, _ in picks)
    meta = {"experiment": params.EXPERIMENT, "timeframe": params.TIMEFRAME, "lookback": params.LOOKBACK,
            "discovery_end": params.DISCOVERY_END, "funnel": funnel, "feature_cutpoints_terciles": cuts,
            "n_target": params.N_STRATA * params.PER_STRATUM, "n_selected": len(picks), "per_stratum": by,
            "shortfall": shortfall, "first_window_end": times[0].isoformat() if times else None,
            "last_window_end": times[-1].isoformat() if times else None, "chart_style_sha256": style_sha(),
            "seed_order": params.SEED_ORDER, "min_gap_candles": params.MIN_GAP_CANDLES,
            "disclosure": ("Tercile cut-points use all discovery candidates (chart features only); no outcome is used "
                           "for selection. Forward-path existence is checked from timestamps only."),
            "database": db_meta}
    if not render:
        return meta, []
    cs = CandleSet(d, params.SYMBOL, params.TIMEFRAME, "setups")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for n, pos in enumerate(order, 1):
        t, stratum, ci = picks[pos]
        cid = f"S{n:04d}"
        w = build_window(cs, t, params.LOOKBACK)                  # validates: exactly 96 closed gap-free candles ending at T
        path = out_dir / "charts" / f"{cid}.png"
        render_window(w, path, chart_style())
        feats = {k: round(float(c[k].iloc[ci]), 6) for k in FEATURES}
        rows.append({"chart_id": cid, "end_ts": t.isoformat(), "chart": path.name, "stratum": stratum,
                     "image_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "chart_style_sha256": meta["chart_style_sha256"], "features": feats})
        if n % 100 == 0:
            print(f"rendered {n}/{len(picks)}")
    (out_dir / "windows_setups.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    meta["windows_setups_jsonl_sha256"] = file_sha256(out_dir / "windows_setups.jsonl")
    (out_dir / "sample_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta, rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=None, help="default: data/research_binance.db")
    ap.add_argument("--out", default=str(store.RUN_DIR))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--confirm-design-sha", help="first 12 chars of the preregistration sha256 in the design lock")
    a = ap.parse_args(argv)
    from src.setups import lock
    db = Path(a.db) if a.db else lock.CANONICAL_DB
    db_meta = lock.verify_database(db)                               # name, bytes and SHA-256 of the canonical dataset
    if a.build:
        lock.require_design_lock(a.confirm_design_sha)
    cs = load_candles(db, params.SYMBOL, params.TIMEFRAME)
    meta, rows = build(cs.df, Path(a.out), render=a.build and not a.dry_run, db_meta=db_meta)
    print(json.dumps(meta, indent=2))
    print(f"wrote {a.out}" if a.build and not a.dry_run else "dry-run: nothing rendered, nothing written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
