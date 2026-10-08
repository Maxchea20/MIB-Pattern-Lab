"""Price-only derivation of the recognizer threshold values (docs/setups/RECOGNIZER_PARAMETER_TABLE.md, section 4).

Computes the measured quantities of section 3 at every discovery position and writes their percentiles. It does NOT
recognise a setup, trigger anything, look at a future candle, or compute any outcome. Each position is measured from its
own 96-candle window only: `measures()` receives nothing else. Hold-out candles are removed before any computation.
Runs once: refuses to overwrite its own output.

    python -m src.setups.derive_params            # prints the table, writes results/setups/recognizer/derived_parameters.json
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

K = 3                      # swing confirmation candles (J-6)
EDGE = 24                  # right-edge zone length (J-7)
QUANTILES = (0.25, 0.33, 0.40, 0.60, 0.67, 0.75)
OUT = Path("results/setups/recognizer/derived_parameters.json")
NAN = float("nan")
KEYS = ("ZR", "EFF", "UP", "DN", "RET", "REB",
        "DT_C1", "DT_C2", "DF_C3", "DF_C4", "DF_C6", "DT_C7", "DF_C8")   # C5 is NOT CODEABLE: excluded


def swings(h, l):
    """Confirmed swing highs / lows (indices) inside one window. A swing at j needs K candles on each side inside the window."""
    n = len(h)
    sh, sl = [], []
    for j in range(K, n - K):
        if h[j] >= h[j - K:j].max() and h[j] > h[j + 1:j + 1 + K].max():
            sh.append(j)
        if l[j] <= l[j - K:j].min() and l[j] < l[j + 1:j + 1 + K].min():
            sl.append(j)
    return sh, sl


def measures(o, h, l, c) -> dict[str, float]:
    """Section-3 quantities for the decision candle = the LAST candle of the arrays (a 96-candle window). NaN = undefined."""
    h, l, c = (np.asarray(x, float) for x in (h, l, c))
    n = len(c)
    t = n - 1
    out = {k: NAN for k in KEYS}
    R = h.max() - l.min()
    if not R > 0:
        return out
    ez = slice(n - EDGE, n)
    zh, zl = h[ez].max(), l[ez].min()
    out["ZR"] = (zh - zl) / R
    steps = np.abs(np.diff(c[n - EDGE:]))
    out["EFF"] = abs(c[t] - c[t - (EDGE - 1)]) / steps.sum() if steps.sum() > 0 else 0.0
    out["DT_C7"] = (zh - c[t]) / R
    out["DF_C3"] = (c[t] - zl) / R
    sh, sl = swings(h, l)
    if sh:
        jH = sh[-1]
        hH = h[jH]
        pbl = l[jH:].min()
        out["DF_C6"] = (c[t] - pbl) / R
        in_e = jH >= n - EDGE
        res1 = zh if (not in_e or hH < c[t]) else min(zh, hH)
        out["DT_C1"] = (res1 - c[t]) / R
        before = [j for j in sl if j < jH]
        if before and hH > l[before[-1]]:
            lB = l[before[-1]]
            out["UP"] = (hH - lB) / R
            out["RET"] = (hH - pbl) / (hH - lB)
    if sl:
        jL = sl[-1]
        lL = l[jL]
        rh = h[jL:].max()
        out["REB"] = (rh - lL) / R
        out["DT_C2"] = (rh - c[t]) / R
        if c[t] >= lL:
            out["DF_C8"] = (c[t] - lL) / R
        before = [j for j in sh if j < jL]
        if before and h[before[-1]] > lL:
            out["DN"] = (h[before[-1]] - lL) / R
    # C4: the broken swing low with the most recent first break; LL* = latest swing low after that break
    best = None
    for jS in sl:
        lS = l[jS]
        brk = next((b for b in range(jS + 1, n) if c[b] < lS), None)
        if brk is not None and (best is None or (brk, lS) > (best[0], best[1])):
            best = (brk, lS)
    if best is not None:
        after = [j for j in sl if j > best[0]]
        if after and c[t] >= l[after[-1]]:
            out["DF_C4"] = (c[t] - l[after[-1]]) / R
    return out


def percentiles(values: dict[str, list[float]]) -> dict:
    res = {}
    for k in KEYS:
        v = np.array([x for x in values[k] if math.isfinite(x)], float)
        res[k] = ({"n_defined": int(len(v)), "min": float(v.min()), "max": float(v.max()),
                   **{f"q{int(round(q * 100)):02d}": float(np.quantile(v, q)) for q in QUANTILES}}
                  if len(v) else {"n_defined": 0})
    return res


def derive(df) -> dict:
    """df = closed candles (any period). Hold-out candles are physically removed first."""
    cutoff = np.datetime64(params.DISCOVERY_END.replace("Z", ""))
    d = df[df["ts"].dt.tz_localize(None) < cutoff].reset_index(drop=True)
    idx = valid_end_indices(d, params.TIMEFRAME, params.LOOKBACK)
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    cols = {k: [] for k in KEYS}
    for i in idx:
        s = slice(i - params.LOOKBACK + 1, i + 1)
        m = measures(o[s], h[s], l[s], c[s])
        for k in KEYS:
            cols[k].append(m[k])
    return {"n_positions": int(len(idx)), "n_candles_before_cutoff": int(len(d)),
            "last_decision_candle": str(d["ts"].iloc[idx[-1]]) if len(idx) else None,
            "quantities": percentiles(cols)}


def render(res: dict) -> str:
    rows = ["| quantity | n defined | q25 | q33 | q40 | q60 | q67 | q75 | min | max |", "|---|---|---|---|---|---|---|---|---|---|"]
    for k, v in res["quantities"].items():
        if v["n_defined"]:
            rows.append(f"| {k} | {v['n_defined']} | " + " | ".join(f"{v[x]:.4f}" for x in
                        ("q25", "q33", "q40", "q60", "q67", "q75", "min", "max")) + " |")
        else:
            rows.append(f"| {k} | 0 | undefined |")
    return "\n".join(rows)


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
    db_meta = lock.verify_database(db)
    cs = load_candles(db, params.SYMBOL, params.TIMEFRAME)
    cs = discovery_candles(cs, end=params.DISCOVERY_END)
    res = derive(cs.df)
    res.update({"discovery_end": params.DISCOVERY_END, "database": db_meta, "window": params.LOOKBACK, "K": K,
                "right_edge": EDGE, "quantiles": list(QUANTILES), "excluded": "C5 (NOT CODEABLE, J-5 declined)",
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"positions measured: {res['n_positions']} (candles before cutoff: {res['n_candles_before_cutoff']})")
    print(render(res))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
