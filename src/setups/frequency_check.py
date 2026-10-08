"""Discovery-period frequency check of the recognizer (pre-registration section 4: 0.2 %-10 % of discovery candles).

Price-only. Reads the recognizer and the derived thresholds exactly as committed; changes no rule; computes no return,
excursion, outcome or R; never touches a hold-out candle. A candidate outside the band gets the preregistered classification,
not a different parameterization. Runs once: refuses to overwrite its own report.

    python -m src.setups.frequency_check
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

from src.data.loader import load_candles
from src.discovery.discover import discovery_candles
from src.setups import audit, params
from src.setups import recognizer as rz

DERIVED = Path("results/setups/recognizer/derived_parameters.json")
OUT = Path("results/setups/recognizer/frequency_report.json")
LONG_LOCK = 480                      # candles (= 5 days): reporting bucket only, not a rule


def jaccard(a: set, b: set) -> float:
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def _runs(flag: np.ndarray) -> list[int]:
    out, n = [], 0
    for f in flag:
        if f:
            n += 1
        elif n:
            out.append(n)
            n = 0
    if n:
        out.append(n)
    return out


def _dist(v: list[float]) -> dict:
    if not v:
        return {"n": 0}
    a = np.array(v, float)
    return {"n": int(len(a)), "min": float(a.min()), "median": float(np.median(a)), "mean": float(a.mean()),
            "p90": float(np.quantile(a, 0.9)), "max": float(a.max())}


def check(ts, o, h, l, c, thr: dict) -> dict:
    n = len(c)
    presence = {k: np.zeros(n, bool) for k in rz.ORDER}
    evaluated = np.zeros(n, bool)

    def observe(t, ok, state):
        evaluated[t] = ok
        for k in rz.ORDER:
            if state[k] is not None:
                presence[k][t] = True

    events = rz.recognize(ts, o, h, l, c, thr, on_state=observe)
    n_eval = int(evaluated.sum())
    per, trig_sets, counted_sets = {}, {}, {}
    for k in rz.ORDER:
        ev = [e for e in events if e["cand"] == k]
        counted = [e for e in ev if e["counted"]]
        supp = [e for e in ev if not e["counted"]]
        raw_gate = audit.frequency_gate(len(ev), n_eval)
        cnt_gate = audit.frequency_gate(len(counted), n_eval)
        end = n - 1
        lock_len, never_inv, long_lock = [], 0, 0
        for e in counted:
            inv = e["invalidation_idx"]
            if inv is None:
                never_inv += 1
                lock_len.append(end - e["trigger_idx"])               # still active when the data ends (lower bound)
            else:
                lock_len.append(max(inv, e["trigger_idx"] + rz.LOCKOUT) - e["trigger_idx"])
            long_lock += lock_len[-1] > LONG_LOCK
        locked_candles = sum(lock_len)
        per[k] = {
            "name": rz.NAMES[k], "direction": rz.DIRECTION[k],
            "presence_candles": int(presence[k].sum()),
            "presence_share_of_evaluated": float(presence[k].sum() / n_eval) if n_eval else 0.0,
            "presence_runs": _dist(_runs(presence[k])),
            "raw_triggers": len(ev), "counted_triggers": len(counted), "suppressed_triggers": len(supp),
            "frequency_raw": raw_gate, "frequency_counted": cnt_gate,
            "g1_counted_ge_100": len(counted) >= params.N_MIN_DISCOVERY,
            "trigger_presence_run_length": _dist([e["presence_len"] for e in ev]),
            "lockout": {
                "occurrences_never_invalidated_by_end_of_data": never_inv,
                "lock_length_candles": _dist(lock_len),
                f"locks_longer_than_{LONG_LOCK}_candles": int(long_lock),
                "candles_under_lock_total": int(locked_candles),
                "share_of_evaluated_under_lock_upper_bound": float(locked_candles / n_eval) if n_eval else 0.0,
                "suppressed_per_counted": float(len(supp) / len(counted)) if counted else None,
            },
        }
        trig_sets[k] = {e["trigger_idx"] for e in ev}
        counted_sets[k] = {e["trigger_idx"] for e in counted}
    pairs = {}
    for a, b in itertools.combinations(rz.ORDER, 2):
        pairs[f"{a}/{b}"] = {
            "presence_both": int((presence[a] & presence[b]).sum()),
            "presence_jaccard": jaccard(set(np.flatnonzero(presence[a])), set(np.flatnonzero(presence[b]))),
            "raw_trigger_same_candle": len(trig_sets[a] & trig_sets[b]),
            "raw_trigger_jaccard": jaccard(trig_sets[a], trig_sets[b]),
            "counted_trigger_same_candle": len(counted_sets[a] & counted_sets[b]),
        }
    return {"n_candles": int(n), "n_evaluated_candles": n_eval, "candidates": per, "pairs": pairs}


def render(rep: dict) -> str:
    L = [f"candles: {rep['n_candles']}  evaluated (96 gap-free): {rep['n_evaluated_candles']}  band {params.FREQ_MIN:.1%}-{params.FREQ_MAX:.0%}", "",
         "| cand | presence candles | pres. runs (n/median/max) | raw trig | counted | suppressed | raw share | counted share | band (raw) | band (counted) | counted>=100 |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, v in rep["candidates"].items():
        r = v["presence_runs"]
        L.append(f"| {k} | {v['presence_candles']} | {r.get('n', 0)}/{r.get('median', 0):.0f}/{r.get('max', 0):.0f} | {v['raw_triggers']} | "
                 f"{v['counted_triggers']} | {v['suppressed_triggers']} | {v['frequency_raw']['share']:.3%} | {v['frequency_counted']['share']:.3%} | "
                 f"{'in' if v['frequency_raw']['passed'] else 'OUT'} | {'in' if v['frequency_counted']['passed'] else 'OUT'} | "
                 f"{'yes' if v['g1_counted_ge_100'] else 'no'} |")
    L += ["", "| cand | never invalidated by data end | lock length median/p90/max | locks > 480 | candles under lock (share) | suppressed per counted |", "|---|---|---|---|---|---|"]
    for k, v in rep["candidates"].items():
        lk = v["lockout"]
        d = lk["lock_length_candles"]
        L.append(f"| {k} | {lk['occurrences_never_invalidated_by_end_of_data']} | "
                 + (f"{d['median']:.0f}/{d['p90']:.0f}/{d['max']:.0f}" if d["n"] else "-") +
                 f" | {lk[f'locks_longer_than_{LONG_LOCK}_candles']} | {lk['candles_under_lock_total']} ({lk['share_of_evaluated_under_lock_upper_bound']:.1%}) | "
                 + (f"{lk['suppressed_per_counted']:.2f}" if lk["suppressed_per_counted"] is not None else "-") + " |")
    L += ["", "| pair | presence both | presence Jaccard | raw trigger same candle | raw trigger Jaccard | counted same candle |", "|---|---|---|---|---|---|"]
    for k, v in rep["pairs"].items():
        L.append(f"| {k} | {v['presence_both']} | {v['presence_jaccard']:.3f} | {v['raw_trigger_same_candle']} | {v['raw_trigger_jaccard']:.3f} | {v['counted_trigger_same_candle']} |")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=None)
    ap.add_argument("--derived", default=str(DERIVED))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    out = Path(a.out)
    if out.exists():
        raise SystemExit(f"{out} exists: the frequency check runs once. Refusing to overwrite.")
    from src.setups import lock
    db = Path(a.db) if a.db else lock.CANONICAL_DB
    db_meta = lock.verify_database(db)
    dpath = Path(a.derived)
    raw_bytes = dpath.read_bytes()
    derived = json.loads(raw_bytes)
    thr = rz.thresholds_from(derived)
    cs = discovery_candles(load_candles(db, params.SYMBOL, params.TIMEFRAME), end=params.DISCOVERY_END)
    d = cs.df
    ts = d["ts"].dt.as_unit("ns").astype("int64").to_numpy()
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    rep = check(ts, o, h, l, c, thr)
    rep.update({"discovery_end": params.DISCOVERY_END, "database": db_meta,
                "derived_parameters_sha256": hashlib.sha256(raw_bytes.replace(b"\r\n", b"\n")).hexdigest(),
                "recognizer_sha256": hashlib.sha256(Path(rz.__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
                "note": "Price-only. No return, outcome, MFE, MAE or R. No parameter or rule was changed. Both the raw-trigger and the "
                        "counted-trigger share are shown against the band; the preregistration says 'triggers on' without naming which."})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2, sort_keys=True, default=float) + "\n", encoding="utf-8")
    print(render(rep))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
