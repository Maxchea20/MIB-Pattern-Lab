"""Price-only derivation of the two thresholds S1 v2 needs: UPnet (net up-leg) and DT_S1v2 (distance to the pause high), each in units of the
96-candle range, at every discovery position where it is defined. Same procedure as derive_s5 / derive_params: discovery candles only, each
position measured from its own window, percentiles q25..q75. No outcome, no future price, no setup recognition. Runs once; refuses to overwrite.

    python -m src.brain.derive_s1v2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from src.brain import s1_v2
from src.charts.windows import valid_end_indices
from src.data.loader import load_candles
from src.discovery.discover import discovery_candles
from src.setups import params
from src.setups.derive_params import QUANTILES

OUT = Path("results/brain_v2/derived_s1v2.json")


def derive(df) -> dict:
    cutoff = np.datetime64(params.DISCOVERY_END.replace("Z", ""))
    d = df[df["ts"].dt.tz_localize(None) < cutoff].reset_index(drop=True)
    idx = valid_end_indices(d, params.TIMEFRAME, params.LOOKBACK)
    h, l, c = (d[k].to_numpy(float) for k in ("high", "low", "close"))
    cols = {k: [] for k in s1_v2.KEYS}
    for i in idx:
        s = slice(i - params.LOOKBACK + 1, i + 1)
        q = s1_v2.quantities(h[s], l[s], c[s])
        for k in s1_v2.KEYS:
            cols[k].append(q[k])
    res = {}
    for k in s1_v2.KEYS:
        v = np.array([x for x in cols[k] if math.isfinite(x)], float)
        res[k] = ({"n_defined": int(len(v)), "min": float(v.min()), "max": float(v.max()),
                   **{f"q{int(round(p * 100)):02d}": float(np.quantile(v, p)) for p in QUANTILES}} if len(v) else {"n_defined": 0})
    return {"n_positions": int(len(idx)), "quantities": res}


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
                "definitions": {"UPnet": "(hH - lowest low before jH in the window)/R, hH = latest confirmed swing high, defined when hH exceeds that low",
                                "DT_S1v2": "(highest high from max(jH+1, t-23) to t - close)/R, defined when a confirmed swing high exists"},
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"positions {res['n_positions']}; " + "; ".join(f"{k} defined {v['n_defined']} q33 {v['q33']:.4f} q67 {v['q67']:.4f}" for k, v in res["quantities"].items()) + f"; wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
