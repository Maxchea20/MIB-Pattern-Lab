"""Generate clean chart windows.

    python -m src.charts.generate                         # SAMPLE_COUNT evenly spaced windows
    python -m src.charts.generate --count 20 --seed 1     # seeded random sample
    python -m src.charts.generate --timestamp 2025-03-01T12:00:00Z   # one exact, reproducible chart
"""
from __future__ import annotations

import argparse
import hashlib
import json
from html import escape
from pathlib import Path

import pandas as pd

import config
from src.charts.renderer import chart_filename, render_window
from src.charts.windows import build_window, sample_end_timestamps
from src.data.loader import load_candles


def parse_ts(s: str) -> pd.Timestamp:
    s = s.strip()
    t = pd.Timestamp(int(s), unit="ms" if len(s) > 11 else "s", tz="UTC") if s.isdigit() else pd.Timestamp(s)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_reports(out: Path, entries: list[dict], meta: dict) -> None:
    (out / "manifest.json").write_text(json.dumps({"meta": meta, "charts": entries}, indent=2), encoding="utf-8")
    head = (f"Symbol: {meta['symbol']} | Timeframe: {meta['timeframe']} | Window: {meta['lookback']} candles | "
            f"Normalization: {meta['normalization']}")
    md = ["# Sample chart QA report", "", head, "",
          f"Source: `{meta['source']}`  (db: `{meta['db_file']}`, sha256 `{meta['db_sha256'][:16]}…`)", ""]
    for e in entries:
        md += [f"## {e['end_ts']}", "",
               f"- symbol: {e['symbol']}\n- timeframe: {e['timeframe']}\n- window size: {e['lookback']}\n"
               f"- window: {e['start_ts']} → {e['end_ts']}", "", f"![{e['file']}]({e['file']})", ""]
    (out / "index.md").write_text("\n".join(md), encoding="utf-8")
    cards = "".join(
        f"<figure><img src='{escape(e['file'])}' width='640'><figcaption><b>{escape(e['end_ts'])}</b><br>"
        f"{escape(e['symbol'])} · {escape(e['timeframe'])} · {e['lookback']} candles<br>"
        f"window {escape(e['start_ts'])} → {escape(e['end_ts'])}</figcaption></figure>" for e in entries)
    (out / "index.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>Sample charts</title>"
        "<style>body{font-family:sans-serif;margin:20px}figure{display:inline-block;margin:10px;"
        "vertical-align:top}figcaption{font-size:12px}</style>"
        f"<h1>Sample chart QA</h1><p>{escape(head)}</p><p>Source: {escape(meta['source'])}</p>{cards}",
        encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=str(config.DB_PATH))
    ap.add_argument("--symbol", default=config.SYMBOL)
    ap.add_argument("--timeframe", default=config.TIMEFRAME)
    ap.add_argument("--lookback", type=int, default=config.LOOKBACK)
    ap.add_argument("--timestamp", help="window END candle open time T (ISO or epoch); single chart")
    ap.add_argument("--count", type=int, default=config.SAMPLE_COUNT)
    ap.add_argument("--seed", type=int, default=config.SAMPLE_SEED)
    ap.add_argument("--out", help="output directory")
    a = ap.parse_args(argv)

    cs = load_candles(a.db, a.symbol, a.timeframe)
    if a.timestamp:
        ends = [parse_ts(a.timestamp)]
        out = Path(a.out or config.SINGLE_DIR)
    else:
        ends = sample_end_timestamps(cs, a.lookback, a.count, a.seed)
        out = Path(a.out or config.SAMPLE_DIR)

    entries = []
    for t in ends:
        w = build_window(cs, t, a.lookback)
        p = render_window(w, out / chart_filename(w))
        entries.append({"file": p.name, "symbol": w.symbol, "timeframe": w.timeframe,
                        "lookback": w.lookback, "start_ts": w.raw["ts"].iloc[0].isoformat(),
                        "end_ts": w.end_ts.isoformat(), "png_sha256": sha256(p)})
        print(f"wrote {p}")
    meta = {"symbol": a.symbol, "timeframe": a.timeframe, "lookback": a.lookback,
            "normalization": "last_close_pct", "source": cs.source,
            "db_file": Path(a.db).name, "db_sha256": sha256(a.db), "load_stats": cs.stats}
    write_reports(out, entries, meta)
    print(f"report: {out / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
