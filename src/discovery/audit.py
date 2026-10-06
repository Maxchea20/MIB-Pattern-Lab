"""Label audit (no API, no outcomes): do the AI shape tags match simple measurable chart features?

    python -m src.discovery.audit [--run-dir results/discovery/tagset_v1]

For each tagged window, computes features from the WINDOW ONLY (never later candles):
  net_pct      close_T vs first open, %          range_pct   (max high - min low) / close_T, %
  eff          |net| / total path length (1 = straight line, ~0 = pure chop)
  max_rise5 / max_fall5   largest 5-candle rise / fall, %
  hi_pos / lo_pos         where the window high / low sits, 0 = left edge, 1 = right edge
  last10_pct   move over the last 10 candles, %
Then reports mean features per STABLE tag vs. all windows. If a tag does not differ from the baseline
in the way its name says (e.g. drift_down with positive net_pct), the label is unreliable. If the tags
are fully explained by net_pct/range_pct, the AI adds nothing beyond trivial features.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import config
from src.charts.windows import build_window
from src.data.loader import load_candles
from src.discovery.discover import discovery_candles
from src.discovery.retag import load_rows

FEATURES = ["net_pct", "range_pct", "eff", "max_rise5", "max_fall5", "hi_pos", "lo_pos", "last10_pct"]


def window_features(raw: pd.DataFrame) -> dict:
    o, h, l, c = (raw[k].to_numpy(float) for k in ["open", "high", "low", "close"])
    ref = c[-1]
    path = np.abs(np.diff(c)).sum() + abs(c[0] - o[0])
    k = 5
    roll = c[k:] - c[:-k]
    return {"net_pct": (c[-1] / o[0] - 1) * 100, "range_pct": (h.max() - l.min()) / ref * 100,
            "eff": abs(c[-1] - o[0]) / path if path else 0.0,
            "max_rise5": roll.max() / ref * 100, "max_fall5": roll.min() / ref * 100,
            "hi_pos": int(h.argmax()) / (len(h) - 1), "lo_pos": int(l.argmin()) / (len(l) - 1),
            "last10_pct": (c[-1] / c[-11] - 1) * 100}


def stable_tags(rows: list[dict], passes: int = 2) -> dict[str, list[str]]:
    by = {}
    for r in rows:
        if r.get("error") is None:
            by.setdefault(r["end_ts"], {})[r["pass"]] = set(r["tags"])
    return {k: sorted(set.intersection(*v.values())) for k, v in by.items()
            if all(p in v for p in range(1, passes + 1))}


def build_table(cs, tags: dict[str, list[str]]) -> pd.DataFrame:
    dcs = discovery_candles(cs)
    recs = []
    for end_ts, tg in tags.items():
        w = build_window(dcs, pd.Timestamp(end_ts), config.LOOKBACK)
        recs.append({"end_ts": end_ts, "tags": tg, **window_features(w.raw)})
    return pd.DataFrame(recs)


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    rows = [{"tag": "ALL WINDOWS", "n": len(df), **df[FEATURES].mean().round(3).to_dict()}]
    for t in sorted({t for tg in df["tags"] for t in tg}):
        sub = df[df["tags"].map(lambda tg, t=t: t in tg)]
        rows.append({"tag": t, "n": len(sub), **sub[FEATURES].mean().round(3).to_dict()})
    return pd.DataFrame(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=str(config.DB_PATH))
    ap.add_argument("--timeframe", default=config.TIMEFRAME)
    ap.add_argument("--run-dir", help="default: results/discovery/tagset_v1[_<timeframe>]")
    a = ap.parse_args(argv)
    from src.discovery.tagset import default_run_dir
    run = Path(a.run_dir) if a.run_dir else default_run_dir(a.timeframe)
    tags = stable_tags(load_rows(run / "retags.jsonl"))
    df = build_table(load_candles(a.db, timeframe=a.timeframe), tags)
    summ = summarise(df)
    pd.set_option("display.width", 200)
    print(summ.to_string(index=False))
    summ.to_csv(run / "audit_by_tag.csv", index=False)
    d = df[df["tags"].map(lambda t: "drift_down" in t)]
    u = df[df["tags"].map(lambda t: "drift_up" in t)]
    print(f"\ndrift_down windows with net_pct < 0: {(d['net_pct'] < 0).mean():.0%} (n={len(d)})"
          f" | drift_up windows with net_pct > 0: {(u['net_pct'] > 0).mean():.0%} (n={len(u)})")
    print(f"saved {run / 'audit_by_tag.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
