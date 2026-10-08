"""Price-only derivation of the one threshold S5 needs that Experiment 3 never derived: DT_C5 = (spike high - close) / 96-candle range,
measured at every discovery position where a confirmed swing high exists and the close is not above it. Same procedure as
src/setups/derive_params.py (discovery candles only, each position measured from its own 96-candle window, percentiles q25..q75).
No outcome, no future price, no setup recognition. Runs once: refuses to overwrite its output.

    python -m src.brain.derive_s5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from src.charts.windows import valid_end_indices
from src.data.loader import load_candles
from src.discovery.discover import discovery_candles
from src.setups import params
from src.setups.derive_params import QUANTILES, swings

OUT = Path("results/brain/derived_s5.json")


def measure_dt_c5(h, l, c) -> float:
    h, l, c = (np.asarray(x, float) for x in (h, l, c))
    R = h.max() - l.min()
    if not R > 0:
        return float("nan")
    sh, _ = swings(h, l)
    if not sh:
        return float("nan")
    hH = h[sh[-1]]
    return float((hH - c[-1]) / R) if hH >= c[-1] else float("nan")


def derive(df) -> dict:
    cutoff = np.datetime64(params.DISCOVERY_END.replace("Z", ""))
    d = df[df["ts"].dt.tz_localize(None) < cutoff].reset_index(drop=True)
    idx = valid_end_indices(d, params.TIMEFRAME, params.LOOKBACK)
    h, l, c = (d[k].to_numpy(float) for k in ("high", "low", "close"))
    vals = []
    for i in idx:
        s = slice(i - params.LOOKBACK + 1, i + 1)
        vals.append(measure_dt_c5(h[s], l[s], c[s]))
    v = np.array([x for x in vals if math.isfinite(x)], float)
    q = {"n_defined": int(len(v)), "min": float(v.min()), "max": float(v.max()),
         **{f"q{int(round(p * 100)):02d}": float(np.quantile(v, p)) for p in QUANTILES}} if len(v) else {"n_defined": 0}
    return {"n_positions": int(len(idx)), "quantities": {"DT_C5": q}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=None)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    out = Path(a.out)
    if out.exists():
        raise SystemExit(f"{out} exists: the derivation runs once. Refusing to overwrite.")
    from src.setups import lock
    db = Path(a.db) if a.db else lock.CANONICAL_DB
    meta = lock.verify_database(db)
    cs = discovery_candles(load_candles(db, params.SYMBOL, params.TIMEFRAME), end=params.DISCOVERY_END)
    res = derive(cs.df)
    res.update({"discovery_end": params.DISCOVERY_END, "database": meta, "window": params.LOOKBACK, "K": 3,
                "definition": "DT_C5 = (hH - c_t)/R where hH = latest confirmed swing high in the 96-candle window and hH >= c_t",
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    q = res["quantities"]["DT_C5"]
    print(f"positions {res['n_positions']}; DT_C5 defined {q['n_defined']}; q33 {q['q33']:.4f} q67 {q['q67']:.4f}; wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
