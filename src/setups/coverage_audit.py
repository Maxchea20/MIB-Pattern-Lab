"""READ-ONLY data audit for the planned 15M setup-discovery experiment (docs/SETUP_DISCOVERY_DESIGN.md).

    python -m src.setups.coverage_audit [--db data/market_Data_Clean.db] [--out docs/setups/COVERAGE_15M_REPORT.json]

Checks, for 15m / 5m / 1m: candle counts, earliest/latest, gaps, duplicates, malformed candles, timestamp alignment,
usable candles after the loader, database hash; whether each 15m candle is made of complete 5m (and 1m) children and
whether its OHLC equals the aggregate of those children; and whether the discovery period and the planned hold-out
(>= the cutoff) contain enough usable 15m candles. It opens the database read-only and never computes a forward return,
a label or any outcome; it makes no network call. It judges nothing: it reports facts and warnings.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import config
from src.data.loader import DataError, connect_readonly, discover_sources, load_candles, tf_to_seconds
from src.exp5m import coverage as cov

SYMBOL = "BTC/USDT"
SIGNAL_TF, FINE_TFS = "15m", ("5m", "1m")
CUTOFF = "2026-06-01T00:00:00Z"                 # proposed discovery / hold-out boundary (design section 16)
LOOKBACK, FORWARD, MIN_GAP = 96, 24, 32         # design: 96-candle chart, 24-candle longest horizon, 32-candle spacing
RTOL = 1e-9


def _sec(df: pd.DataFrame) -> np.ndarray:
    return df["ts"].dt.as_unit("s").astype("int64").to_numpy()


def children_check(parent: pd.DataFrame, child: pd.DataFrame, parent_step: int, child_step: int) -> dict:
    """Does every parent candle consist of complete children, and does the parent OHLC equal their aggregate?"""
    k = parent_step // child_step
    p, c = _sec(parent), _sec(child)
    out = {"children_per_parent": k, "parents": int(len(p)), "parents_off_grid": int((p % parent_step != 0).sum())}
    if not len(p) or not len(c):
        return {**out, "parents_with_complete_children": 0, "note": "empty series"}
    offs = np.arange(k) * child_step
    idx = np.searchsorted(c, p)
    room = idx + k <= len(c)
    gather = np.clip(idx[:, None] + np.arange(k)[None, :], 0, len(c) - 1)
    complete = room & (c[gather] == p[:, None] + offs[None, :]).all(axis=1)
    out["parents_with_complete_children"] = int(complete.sum())
    out["parents_without_complete_children"] = int((~complete).sum())
    out["share_complete"] = float(complete.mean())
    out["first_incomplete"] = [pd.Timestamp(int(x), unit="s", tz="UTC").isoformat() for x in p[~complete][:10]]
    g = gather[complete]
    po = {f: parent[f].to_numpy(float)[complete] for f in ("open", "high", "low", "close")}
    co = {f: child[f].to_numpy(float) for f in ("open", "high", "low", "close")}
    agg = {"open": co["open"][g[:, 0]], "close": co["close"][g[:, -1]],
           "high": co["high"][g].max(axis=1), "low": co["low"][g].min(axis=1)}
    out["aggregate_mismatch"] = {}
    for f in ("open", "high", "low", "close"):
        rel = np.abs(po[f] - agg[f]) / np.maximum(np.abs(po[f]), 1e-12)
        out["aggregate_mismatch"][f] = {"mismatching_parents": int((rel > RTOL).sum()), "max_relative_diff": float(rel.max()) if len(rel) else 0.0}
    # open-time convention: parent.open should equal the FIRST child's open at the same label; if parent labels were
    # close times it would match the child one parent-step earlier.
    same = np.isin(p, c)
    j = np.searchsorted(c, p)
    ok_same = same & (np.clip(j, 0, len(c) - 1) < len(c))
    om = parent["open"].to_numpy(float)
    at_label = float(np.mean(np.abs(om[ok_same] - co["open"][np.clip(j, 0, len(c) - 1)][ok_same]) <= RTOL * np.abs(om[ok_same]))) if ok_same.any() else None
    q = p - parent_step
    j2 = np.clip(np.searchsorted(c, q), 0, len(c) - 1)
    ok2 = c[j2] == q
    at_prev = float(np.mean(np.abs(om[ok2] - co["open"][j2][ok2]) <= RTOL * np.abs(om[ok2]))) if ok2.any() else None
    out["open_time_check"] = {"parent_open_equals_child_open_at_same_label": at_label,
                              "parent_open_equals_child_open_one_parent_step_earlier": at_prev}
    return out


def feasibility(df: pd.DataFrame, step: int, cutoff: str, lookback: int, forward: int, min_gap: int) -> dict:
    """Counts only (no prices after any time are used): how many usable 15m candle positions exist on each side of the cutoff."""
    t = _sec(df)
    cut = int(pd.Timestamp(cutoff).tz_convert("UTC").timestamp()) if pd.Timestamp(cutoff).tzinfo else int(pd.Timestamp(cutoff, tz="UTC").timestamp())
    n = len(t)
    pos = np.arange(n)
    back_ok = pos >= lookback - 1
    back_ok[lookback - 1:] = (t[lookback - 1:] - t[:n - lookback + 1]) == (lookback - 1) * step
    fwd_ok = np.zeros(n, bool)
    if n > forward:
        fwd_ok[:n - forward] = (t[forward:] - t[:n - forward]) == forward * step
    before = t < cut
    disc = back_ok & fwd_ok & before & (np.append(t[forward:], [10**12] * forward) < cut)
    hold = back_ok & fwd_ok & ~before
    months = pd.Series(df["ts"].dt.strftime("%Y-%m")).value_counts().sort_index()
    return {"cutoff": cutoff, "lookback": lookback, "forward": forward, "step_seconds": step,
            "usable_candles_total": int(n), "usable_candles_before_cutoff": int(before.sum()),
            "usable_candles_from_cutoff": int((~before).sum()),
            "first_usable": df["ts"].iloc[0].isoformat() if n else None, "last_usable": df["ts"].iloc[-1].isoformat() if n else None,
            "holdout_days_of_data": float(((~before).sum() * step) / 86400.0),
            "discovery_positions_with_full_lookback_and_forward_path": int(disc.sum()),
            "holdout_positions_with_full_lookback_and_forward_path": int(hold.sum()),
            f"discovery_max_windows_at_spacing_{min_gap}_upper_bound": int(disc.sum() // min_gap),
            "usable_candles_per_month": {k: int(v) for k, v in months.items()}}


def _series_report(db: str, symbol: str, tf: str) -> dict:
    try:
        return {"available": True, **cov.coverage(db, symbol, tf)}
    except (DataError, ValueError, KeyError, SystemExit) as e:
        return {"available": False, "error": f"{type(e).__name__}: {e}"}


def audit(db_path, symbol: str = SYMBOL, cutoff: str = CUTOFF, lookback: int = LOOKBACK, forward: int = FORWARD,
          min_gap: int = MIN_GAP) -> dict:
    conn = connect_readonly(db_path)
    try:
        sources = [s.label() for s in discover_sources(conn)]
    finally:
        conn.close()
    series = {tf: _series_report(str(db_path), symbol, tf) for tf in (SIGNAL_TF, *FINE_TFS)}
    loaded: dict[str, pd.DataFrame] = {}
    notes: list[str] = []
    for tf, rep in series.items():
        if not rep.get("available"):
            continue
        try:
            loaded[tf] = load_candles(db_path, symbol, tf).df
        except DataError as e:
            notes.append(f"{tf}: loader refused the series ({e}); cross-checks involving it were skipped")
    step15 = tf_to_seconds(SIGNAL_TF)
    cross = {}
    for tf in FINE_TFS:
        if SIGNAL_TF in loaded and tf in loaded:
            cross[f"{SIGNAL_TF}_vs_{tf}"] = children_check(loaded[SIGNAL_TF], loaded[tf], step15, tf_to_seconds(tf))
    feas = feasibility(loaded[SIGNAL_TF], step15, cutoff, lookback, forward, min_gap) if SIGNAL_TF in loaded else None
    warnings = []
    for tf, rep in series.items():
        if not rep.get("available"):
            warnings.append(f"{tf}: series not found in the database")
            continue
        if rep["gap_count"]:
            warnings.append(f"{tf}: {rep['gap_count']} gaps ({rep['missing_candles_total']} candles missing; largest {rep['largest_gap_candles']})")
        for key in ("duplicate_timestamps", "off_grid_timestamps", "invalid_ohlc_rows", "intervals_shorter_than_step"):
            if rep[key]:
                warnings.append(f"{tf}: {key} = {rep[key]}")
        if "error" in rep.get("loader", {}):
            warnings.append(f"{tf}: loader error: {rep['loader']['error']}")
    for name, c in cross.items():
        if c.get("parents_without_complete_children"):
            warnings.append(f"{name}: {c['parents_without_complete_children']} parent candles lack complete children")
        bad = {f: m["mismatching_parents"] for f, m in c.get("aggregate_mismatch", {}).items() if m["mismatching_parents"]}
        if bad:
            warnings.append(f"{name}: parent OHLC differs from the aggregate of its children: {bad}")
    warnings += notes
    first = next((r["database_sha256"] for r in series.values() if r.get("available")), None)
    p = Path(db_path)
    return {"purpose": "read-only feasibility audit for the planned 15M setup-discovery experiment; no outcome computed",
            "database_file": p.name, "database_bytes": p.stat().st_size, "database_sha256": first, "symbol": symbol,
            "sources_found_in_database": sources, "series": series, "child_candle_cross_checks": cross,
            "discovery_holdout_feasibility": feas, "warnings": warnings}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=str(config.DB_PATH))
    ap.add_argument("--out", default=str(config.ROOT / "docs" / "setups" / "COVERAGE_15M_REPORT.json"))
    ap.add_argument("--cutoff", default=CUTOFF)
    a = ap.parse_args(argv)
    rep = audit(a.db, cutoff=a.cutoff)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rep, indent=2, default=str) + "\n", encoding="utf-8")
    print("sources:", *rep["sources_found_in_database"], sep="\n  ")
    for tf, r in rep["series"].items():
        if not r["available"]:
            print(f"{tf}: NOT AVAILABLE ({r['error']})")
            continue
        ld = r["loader"]
        print(f"{tf}: rows {r['rows']} unique {r['unique_timestamps']} | {r['earliest']} .. {r['latest']} | gaps {r['gap_count']} "
              f"(missing {r['missing_candles_total']}) dup {r['duplicate_timestamps']} off-grid {r['off_grid_timestamps']} "
              f"invalid {r['invalid_ohlc_rows']} | usable {ld.get('rows_usable_after_loader', 'ERR')}")
    for name, c in rep["child_candle_cross_checks"].items():
        print(f"{name}: complete children {c['parents_with_complete_children']}/{c['parents']}; "
              f"open-time check {c.get('open_time_check')}")
    f = rep["discovery_holdout_feasibility"]
    if f:
        print(f"15m before {f['cutoff']}: {f['usable_candles_before_cutoff']} | from cutoff: {f['usable_candles_from_cutoff']} "
              f"({f['holdout_days_of_data']:.1f} days) | positions discovery {f['discovery_positions_with_full_lookback_and_forward_path']} "
              f"hold-out {f['holdout_positions_with_full_lookback_and_forward_path']}")
    print("warnings:", *(rep["warnings"] or ["none"]), sep="\n  ")
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
