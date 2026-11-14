"""Event study of the written trend + RSI rules on a folder of downloaded candles. Descriptive only: no order, no fill, no trade."""
from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

import numpy as np

from src.trendrsi import indicators as ind
from src.trendrsi import params as P
from src.trendrsi import signals as sg

STEP = {"15m": 900_000, "4h": 14_400_000, "1d": 86_400_000}


def load_csv(path: Path) -> dict:
    with gzip.open(path, "rt") as f:
        rows = list(csv.reader(f))[1:]
    a = np.array(rows, float)
    return {"ts": a[:, 0].astype(np.int64), "o": a[:, 1], "h": a[:, 2], "l": a[:, 3], "c": a[:, 4]}


def prepare(data_dir: Path) -> dict:
    d15, d4, d1 = (load_csv(Path(data_dir) / f"BTCUSDT-{iv}.csv.gz") for iv in ("15m", "4h", "1d"))
    ts, n = d15["ts"], len(d15["ts"])
    close_ms = ts + STEP["15m"]
    rsi = ind.rsi_wilder(d15["c"])
    p4 = ind.htf_pack(d4["ts"], d4["c"], P.EMA_4H, P.EMA_4H_SLOPE_BARS, STEP["4h"])
    p1 = ind.htf_pack(d1["ts"], d1["c"], P.EMA_1D, P.EMA_1D_SLOPE_BARS, STEP["1d"])
    bear, bull = ind.htf_bias(close_ms, p4, p1)
    valid = np.ones(n, bool)
    valid[:P.WARMUP_DAYS * 96] = False
    for g in np.flatnonzero(np.diff(ts) != STEP["15m"]) + 1:                   # a data gap before candle g
        valid[max(0, g - P.GAP_GUARD_BARS_BEFORE):g + P.GAP_GUARD_BARS_AFTER] = False
    return {**d15, "rsi": rsi, "bear": bear, "bull": bull, "valid": valid, "n": n}


def run(data_dir: Path) -> dict:
    x = prepare(data_dir)
    out = {}
    for mode in ("with_trend", "counter_trend"):
        bs, bl = (x["bear"], x["bull"]) if mode == "with_trend" else (x["bull"], x["bear"])     # counter: shorts in a bull bias, longs in a bear bias
        sigs = sg.find_signals(x["o"], x["h"], x["l"], x["c"], x["rsi"], bs, bl, x["valid"])
        out[mode] = [sg.outcome(s, x["o"], x["h"], x["l"], x["c"], x["rsi"], x["valid"]) for s in sigs]
    return {"x": x, "records": out}


def _stats(v: list[float]) -> dict:
    a = np.array(v, float)
    return {"n": int(len(a))} if not len(a) else {"n": int(len(a)), "mean": float(a.mean()), "median": float(np.median(a)), "share_positive": float((a > 0).mean())}


def summarize(records: list[dict], ts: np.ndarray) -> dict:
    ok = [r for r in records if r["status"] == "OK"]
    exc: dict = {}
    for r in records:
        if r["status"] != "OK":
            exc[r["status"]] = exc.get(r["status"], 0) + 1
    half = int(np.datetime64(P.HALF_SPLIT).astype("datetime64[ms]").astype(np.int64))
    def block(rs):
        return {"n": len(rs), "gross_R": _stats([r["gross_R"] for r in rs]),
                **{f"net_R_slip{s}": _stats([r[f"net_R_slip{s}"] for r in rs]) for s in P.SLIP_SENSITIVITY_PCT},
                "exit_reasons": {k: sum(1 for r in rs if r["exit_reason"] == k) for k in ("risk_level", "rsi", "time")},
                "median_risk_pct": float(np.median([r["risk_pct"] for r in rs])) if rs else None,
                "median_bars_held": float(np.median([r["bars_held"] for r in rs])) if rs else None,
                "mean_mfe_R": float(np.mean([r["mfe_R"] for r in rs])) if rs else None, "mean_mae_R": float(np.mean([r["mae_R"] for r in rs])) if rs else None}
    res = {"signals": len(records), "ok": len(ok), "excluded": exc, "all": block(ok), "long": block([r for r in ok if r["side"] == "long"]),
           "short": block([r for r in ok if r["side"] == "short"]),
           "first_half": block([r for r in ok if ts[r["t"]] < half]), "second_half": block([r for r in ok if ts[r["t"]] >= half]),
           "by_year": {}}
    for y in sorted({int(np.datetime64(int(ts[r["t"]]), "ms").astype("datetime64[Y]").astype(int)) + 1970 for r in ok}):
        res["by_year"][str(y)] = block([r for r in ok if int(np.datetime64(int(ts[r["t"]]), "ms").astype("datetime64[Y]").astype(int)) + 1970 == y])
    return res


def stop_rule(s: dict) -> dict:
    """The charter's stop rule (section 6) applied mechanically at the judged slippage."""
    key = f"net_R_slip{P.JUDGE_SLIP_PCT}"
    m = lambda b: b[key].get("mean")                                           # noqa: E731
    excl = s["signals"] - s["ok"]
    crit = {"1_mean_net_R_above_zero": bool(m(s["all"]) is not None and m(s["all"]) > 0),
            "2_at_least_100_signals": s["ok"] >= P.MIN_SIGNALS,
            "3_positive_in_both_halves": bool(m(s["first_half"]) is not None and m(s["second_half"]) is not None and m(s["first_half"]) > 0 and m(s["second_half"]) > 0),
            "4_excluded_share_at_most_20pct": (excl / s["signals"] <= P.MAX_AMBIGUOUS_SHARE) if s["signals"] else False}
    return {"criteria": crit, "all_met": all(crit.values()), "excluded_share": (excl / s["signals"]) if s["signals"] else None}


def report(data_dir: Path) -> dict:
    r = run(data_dir)
    ts = r["x"]["ts"]
    out = {"data_dir": str(data_dir), "candles_15m": int(r["x"]["n"]), "first_utc": str(np.datetime64(int(ts[0]), "ms")), "last_utc": str(np.datetime64(int(ts[-1]), "ms")),
           "valid_candles": int(r["x"]["valid"].sum()), "bear_candles": int((r["x"]["bear"] & r["x"]["valid"]).sum()), "bull_candles": int((r["x"]["bull"] & r["x"]["valid"]).sum())}
    for mode, recs in r["records"].items():
        out[mode] = summarize(recs, ts)
    out["with_trend"]["stop_rule"] = stop_rule(out["with_trend"])
    out["records"] = r["records"]
    return out
