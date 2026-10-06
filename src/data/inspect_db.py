"""Read-only database inspection report.

    python -m src.data.inspect_db [--db data/market_Data_Clean.db] [--out results/db_inspection.txt]

The database is opened with SQLite ``mode=ro``; it is never modified.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

import config
from src.data.loader import (OHLC, connect_readonly, discover_sources, fetch_source,
                             invalid_ohlc_mask, list_tables, parse_timestamps, tf_to_seconds,
                             DataError)


def analyse_source(df: pd.DataFrame, tf_hint: str | None) -> dict:
    df = df.copy()
    df["ts"] = parse_timestamps(df["timestamp"])
    for k in OHLC:
        df[k] = pd.to_numeric(df[k], errors="coerce")
    df = df.sort_values("ts", kind="stable")
    res = {"rows": len(df)}
    if df.empty:
        return res
    res["start"], res["end"] = df["ts"].iloc[0], df["ts"].iloc[-1]
    res["duplicates"] = int(df["ts"].duplicated().sum())
    res["invalid_rows"] = int(invalid_ohlc_mask(df).sum())
    u = df["ts"].drop_duplicates()
    diffs = u.diff().dropna().dt.total_seconds()
    step = tf_to_seconds(tf_hint) if tf_hint else (int(diffs.median()) if len(diffs) else None)
    res["step_s"] = step
    if step and len(diffs):
        gaps = diffs[diffs > step]
        res["missing_candles"] = int(((gaps / step) - 1).round().sum())
        res["gap_count"] = len(gaps)
        res["largest_gap_candles"] = int(round(gaps.max() / step)) - 1 if len(gaps) else 0
        res["off_grid_intervals"] = int((diffs < step).sum())
    return res


def build_report(db_path) -> str:
    conn = connect_readonly(db_path)
    lines = [f"Database:\n{Path(db_path).name}\n"]
    try:
        tables = list_tables(conn)
        lines.append(f"Tables ({len(tables)}): {', '.join(tables)}\n")
        for t in tables:
            n = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            lines.append(f"== Table {t}  ({n} rows)")
            for cid, name, typ, notnull, dflt, pk in conn.execute(f'PRAGMA table_info("{t}")'):
                lines.append(f"   col {cid}: {name} {typ}{' PK' if pk else ''}{' NOT NULL' if notnull else ''}")
            idx = conn.execute(f'PRAGMA index_list("{t}")').fetchall()
            if idx:
                lines.append("   indexes: " + ", ".join(r[1] for r in idx))
        lines.append("")
        sources = discover_sources(conn)
        if not sources:
            lines.append("No table with detectable timestamp + OHLC columns found.")
        for s in sources:
            m = s.schema.mapping
            lines += [f"---- Source: {s.label()}",
                      "Detected fields: " + ", ".join(f"{k}={v}" for k, v in m.items() if v)
                      + (" | missing: " + ", ".join(k for k, v in m.items() if not v and k in ("symbol", "timeframe"))
                         if not (m["symbol"] and m["timeframe"]) else "")]
            try:
                tf_hint = s.timeframe_value
                if tf_hint:
                    tf_to_seconds(tf_hint)
            except DataError:
                tf_hint = None
            r = analyse_source(fetch_source(conn, s), tf_hint)
            lines += [f"Symbol:\n{s.symbol_value or '(no symbol column)'}", "",
                      f"Timeframe:\n{s.timeframe_value or '(no timeframe column; step inferred)'}", "",
                      f"Rows:\n{r['rows']}", ""]
            if r["rows"]:
                lines += [f"Start:\n{r['start']}", "", f"End:\n{r['end']}", "",
                          f"Duplicates:\n{r['duplicates']}", "",
                          f"Missing candles:\n{r.get('missing_candles', 'n/a')} "
                          f"(in {r.get('gap_count', 0)} gaps, largest {r.get('largest_gap_candles', 0)} candles, "
                          f"step {r.get('step_s')}s, off-grid intervals {r.get('off_grid_intervals', 0)})", "",
                          f"Invalid rows:\n{r['invalid_rows']}", ""]
    finally:
        conn.close()
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(config.DB_PATH))
    ap.add_argument("--out", help="also write the report to this file")
    a = ap.parse_args(argv)
    rep = build_report(a.db)
    print(rep)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(rep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
