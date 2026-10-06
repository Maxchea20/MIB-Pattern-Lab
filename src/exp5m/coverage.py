"""Verify the 5M data actually in the database (no assumptions). Read-only.

    python -m src.exp5m.coverage [--db data/market_Data_Clean.db] [--out docs/5m/COVERAGE_REPORT.json]

Reports earliest/latest timestamp, candle counts, gaps, duplicates, grid alignment, timezone/unit assumptions,
invalid OHLC rows, the open-time convention check (vs the 1h series) and what the loader keeps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import config
from src.data import inspect_db
from src.data.loader import (DataError, OHLC, connect_readonly, discover_sources, fetch_source, invalid_ohlc_mask,
                             load_candles, parse_timestamps, select_source, tf_to_seconds)
from src.exp5m import params

STEP = 300


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def coverage(db_path, symbol=None, timeframe=None) -> dict:
    symbol, timeframe = symbol or params.SYMBOL, timeframe or params.TIMEFRAME
    step = tf_to_seconds(timeframe)
    conn = connect_readonly(db_path)
    try:
        sources = discover_sources(conn)
        src = select_source(sources, symbol, timeframe)
        raw = fetch_source(conn, src)
        conv = inspect_db.convention_check(conn, sources)
    finally:
        conn.close()
    stored = raw["timestamp"]
    numeric = bool(pd.api.types.is_numeric_dtype(stored))
    mx = float(np.nanmax(np.abs(stored.to_numpy(float)))) if numeric and len(stored) else 0.0
    unit = ("milliseconds" if mx > 1e11 else "seconds") if numeric else "ISO string"
    ts_all = parse_timestamps(stored)
    ts = ts_all.sort_values().reset_index(drop=True)
    uniq = ts.drop_duplicates()
    sec = uniq.dt.as_unit("s").astype("int64").to_numpy()
    diffs = np.diff(sec)
    gaps = []
    for i in np.where(diffs > step)[0]:
        gaps.append({"after": pd.Timestamp(sec[i], unit="s", tz="UTC").isoformat(),
                     "resumes": pd.Timestamp(sec[i + 1], unit="s", tz="UTC").isoformat(),
                     "missing_candles": int(diffs[i] // step - 1)})
    expected = int((sec[-1] - sec[0]) // step + 1) if len(sec) else 0
    d = raw.copy()
    for k in OHLC:
        d[k] = pd.to_numeric(d[k], errors="coerce")
    bad = int(invalid_ohlc_mask(d).sum())
    try:
        cs = load_candles(db_path, symbol, timeframe)
        loader = {"rows_usable_after_loader": int(len(cs.df)), **cs.stats,
                  "DROP_LAST_CANDLES": int(getattr(config, "DROP_LAST_CANDLES", 0)),
                  "first_usable": cs.df["ts"].iloc[0].isoformat(), "last_usable": cs.df["ts"].iloc[-1].isoformat()}
    except DataError as e:                                   # e.g. duplicates: report them, do not crash
        loader = {"error": str(e)}
    monthly = uniq.dt.strftime("%Y-%m").value_counts().sort_index()
    p = Path(db_path)
    return {
        "database_file": p.name, "database_bytes": p.stat().st_size, "database_sha256": _sha256(p),
        "source": src.label(), "symbol": symbol, "timeframe": timeframe, "step_seconds": step,
        "stored_timestamp_type": "numeric epoch" if numeric else "string",
        "stored_timestamp_unit": unit, "timezone_assumption": "UTC (epoch is timezone-free; ISO strings parsed as UTC)",
        "rows": int(len(raw)), "unique_timestamps": int(len(uniq)),
        "earliest": uniq.iloc[0].isoformat() if len(uniq) else None,
        "latest": uniq.iloc[-1].isoformat() if len(uniq) else None,
        "expected_candles_on_grid": expected, "missing_candles_total": int(sum(g["missing_candles"] for g in gaps)),
        "gap_count": len(gaps), "largest_gap_candles": max([g["missing_candles"] for g in gaps], default=0), "gaps": gaps,
        "duplicate_timestamps": int(ts.duplicated().sum()),
        "rows_in_original_order_sorted": bool(ts_all.is_monotonic_increasing),
        "off_grid_timestamps": int((sec % step != 0).sum()),
        "intervals_shorter_than_step": int((diffs < step).sum()),
        "invalid_ohlc_rows": bad,
        "open_time_convention_check": conv,
        "loader": loader,
        "candles_per_month": {k: int(v) for k, v in monthly.items()},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=str(config.DB_PATH))
    ap.add_argument("--out", default=str(config.ROOT / "docs" / "5m" / "COVERAGE_REPORT.json"))
    a = ap.parse_args(argv)
    rep = coverage(a.db)
    text = json.dumps(rep, indent=2, default=str)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(text + "\n", encoding="utf-8")
    print(f"source: {rep['source']}\nrows {rep['rows']} | unique {rep['unique_timestamps']} | duplicates {rep['duplicate_timestamps']}")
    print(f"earliest {rep['earliest']}  latest {rep['latest']}  (UTC; stored as {rep['stored_timestamp_unit']})")
    print(f"expected on grid {rep['expected_candles_on_grid']} | missing {rep['missing_candles_total']} in {rep['gap_count']} gaps "
          f"(largest {rep['largest_gap_candles']}) | off-grid {rep['off_grid_timestamps']} | invalid OHLC {rep['invalid_ohlc_rows']}")
    ld = rep["loader"]
    print("loader: " + (f"ERROR {ld['error']}" if "error" in ld else
                        f"usable {ld['rows_usable_after_loader']} (last stored candle dropped: {ld['DROP_LAST_CANDLES']})"))
    print("\n".join(rep["open_time_convention_check"]))
    for g in rep["gaps"][:20]:
        print(f"  gap after {g['after']}: {g['missing_candles']} candles missing")
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
