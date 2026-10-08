"""Read-only review packet for the question: are the detectors wrong, or was the AI's visual judgment too loose?
No detector, threshold or scan result is changed. Needs the DB and the local Stage A charts.

    python -m src.brain.review

1. cited charts: for every Stage A chart the AI rated ACTIONABLE_NOW and cited for a setup: AI description, the chart image, and the
   condition-by-condition reading of the frozen detector at that chart's last candle (which condition failed and by how much).
2. fire checks: five FIREs per setup re-verified from the raw Binance candles by the separately written explanation code.
3. baseline: the unconditional forward-return distribution of ALL candles measured exactly like a FIRE, per period and direction,
   next to each setup's numbers. Descriptive only; no significance test, no fill.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

import config
from src.brain import detectors as det
from src.brain import explain as ex
from src.brain import forward, rediscovery
from src.brain.brain import STEP_NS, iso
from src.setups import params, store

OUT = Path(config.ROOT) / "results" / "brain" / "review"
CHARTS = store.RUN_DIR / "charts"


def _win(df, i):
    s = slice(i - det.WINDOW + 1, i + 1)
    return df["high"].to_numpy(float)[s], df["low"].to_numpy(float)[s], df["close"].to_numpy(float)[s]


def explain_at(df, sid, i, thr):
    if i < det.WINDOW - 1:
        return None
    h, l, c = _win(df, i)
    return ex.explain(sid, h, l, c, thr)


def cited_review(df, stage_a, support, fires, thr) -> dict:
    rows = {r["chart_id"]: r for r in stage_a if r.get("error") is None and r["parsed"]["status"] == "ACTIONABLE_NOW"}
    fired = {(f["setup_id"], f["trigger_idx"]) for f in fires}
    ts = df["ts"]
    out = {}
    for sid in det.IDS:
        items = []
        for cid in sorted(i for i in support.get(sid, []) if i in rows):
            r = rows[cid]
            pos = int(ts.searchsorted(pd.Timestamp(r["end_ts"])))
            e = explain_at(df, sid, pos, thr)
            if e is None:
                continue
            prev = explain_at(df, sid, pos - 1, thr)
            items.append({"chart_id": cid, "end_ts": r["end_ts"], "ai": {k: r["parsed"].get(k) for k in ("visible_summary", "context", "location", "development", "trigger", "direction")},
                          "present_at_T": e["present"], "present_at_T_minus_1": bool(prev and prev["present"]),
                          "fired_last_two_candles": any((sid, pos - k) in fired for k in range(2)),
                          "first_failure": ex.first_failure(e), "conditions": e["conditions"]})
        fails: dict = {}
        near: dict = {}
        for it in items:
            bad = [k["condition"] for k in it["conditions"] if not k["ok"]]
            for b in bad:
                fails[b] = fails.get(b, 0) + 1
            if len(bad) == 1:
                near[bad[0]] = near.get(bad[0], 0) + 1
        out[sid] = {"charts": items, "n": len(items), "recognized": sum(1 for i in items if i["present_at_T"] or i["fired_last_two_candles"]),
                    "charts_failing_each_condition": fails, "charts_missing_by_exactly_one_condition": near}
    return out


def fire_checks(df, fires, thr, per_setup: int = 5) -> dict:
    ts = df["ts"].dt.as_unit("ns").astype("int64").to_numpy()
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    out = {}
    for sid in det.IDS:
        fs = [f for f in fires if f["setup_id"] == sid]
        base = [f for f in fs if f["streak_position"] == 0] or fs
        pick = []
        if base:
            pick = [base[i] for i in sorted({0, *np.linspace(0, len(base) - 1, per_setup).round().astype(int).tolist()})][:per_setup]
        sheets = []
        for f in pick:
            t, d = f["trigger_idx"], f["direction"]
            e1 = explain_at(df, sid, t - 1, thr)
            lvl = e1["level"][d] if isinstance(e1["level"], dict) else e1["level"]
            beyond = (c[t] > lvl) if d == "up" else (c[t] < lvl)
            e2 = explain_at(df, sid, t - 2, thr)
            lv2 = None if not e2 or not e2["present"] else (e2["level"][d] if isinstance(e2["level"], dict) else e2["level"])
            prev_would = lv2 is not None and ((c[t - 1] > lv2) if d == "up" else (c[t - 1] < lv2))
            run, k = 0, t - 1
            while k >= det.WINDOW - 1 and (explain_at(df, sid, k, thr) or {"present": False})["present"]:
                run += 1
                k -= 1
            checks = {
                "trigger candle in the DB equals the FIRE's candle": bool(ts[t] == pd.Timestamp(f["trigger_candle_open_ts"]).value and
                                                                           np.isclose([o[t], h[t], l[t], c[t]], [f["trigger_candle"][x] for x in ("open", "high", "low", "close")]).all()),
                "setup was PRESENT on the previous candle (all conditions)": bool(e1["present"]),
                "operative level recomputed independently equals the FIRE's level": bool(e1["present"] and np.isclose(lvl, f["operative_level"])),
                "trigger candle closed beyond that level": bool(beyond),
                "no earlier fire in the run (first valid candle) == streak_position 0": bool(prev_would == (f["streak_position"] > 0)),
                "presence run length recomputed equals the FIRE's": bool(run == f["presence_len"] or (run >= det.WINDOW and f["presence_len"] >= det.WINDOW)),
            }
            sheets.append({"fire_id": f["fire_id"], "trigger_ts": f["trigger_ts"], "direction": d, "level": float(lvl), "presence_len": f["presence_len"],
                           "recomputed_run": run, "streak_position": f["streak_position"], "checks": checks,
                           "previous_conditions": e1["conditions"],
                           "candles": [{"open_ts": iso(int(ts[j])), "o": o[j], "h": h[j], "l": l[j], "c": c[j]} for j in range(t - 5, t + 1)]})
        out[sid] = sheets
    return out


def baseline(df, fires_rows: list[dict], cutoff_ns: int) -> dict:
    """Unconditional distribution: a pseudo-FIRE on every candle that has a 96-candle history, measured with the SAME function as real fires."""
    ts = df["ts"].dt.as_unit("ns").astype("int64").to_numpy()
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n = len(c)
    base_rows = {}
    for d in ("up", "down"):
        pf = [{"event": "FIRE", "fire_id": f"B-{t}-{d}", "setup_id": "BASE", "direction": d, "trigger_idx": t, "streak_position": 0} for t in range(det.WINDOW, n - 1)]
        base_rows[d] = forward.observe(pf, [], ts, o, h, l, c, cutoff_ns)

    def stats(rows):
        rows = [r for r in rows if not (r["period"] == "IN_SAMPLE" and r["forward_crosses_boundary"])]
        g = lambda k: np.array([r[k] for r in rows if r.get(k) is not None], float)          # noqa: E731
        out = {"n": len(rows)}
        for H in forward.HORIZONS:
            a = g(f"fwd_return_pct_h{H}")
            out[f"h{H}"] = {"mean": float(a.mean()), "median": float(np.median(a)), "share_positive": float((a > 0).mean())} if len(a) else None
        for k in ("mfe_pct", "mae_pct"):
            out[k + "_median"] = float(np.median(g(k))) if len(g(k)) else None
        return out
    res = {"baseline": {}, "setups": {}}
    terc = {}
    for d in ("up", "down"):
        for p in ("IN_SAMPLE", "UNSEEN"):
            rr = [r for r in base_rows[d] if r["period"] == p]
            res["baseline"][f"{d}/{p}"] = stats(rr)
            for t in ("low", "mid", "high"):
                terc[(d, p, t)] = stats([r for r in rr if r["vol_tercile"] == t])
    for sid in det.IDS:
        for p in ("IN_SAMPLE", "UNSEEN"):
            for d in ("up", "down"):
                rr = [r for r in fires_rows if r["setup_id"] == sid and r["period"] == p and r["direction"] == d]
                if not rr:
                    continue
                s = stats(rr)
                b = res["baseline"][f"{d}/{p}"]
                usable = [r for r in rr if not (p == "IN_SAMPLE" and r["forward_crosses_boundary"])]
                row = {"n": s["n"], "baseline_n": b["n"]}
                for H in (1, 6, 24):
                    x = np.array([r[f"fwd_return_pct_h{H}"] for r in usable if r.get(f"fwd_return_pct_h{H}") is not None], float)
                    if not len(x) or not b[f"h{H}"]:
                        continue
                    matched = 0.0
                    for t in ("low", "mid", "high"):
                        share = np.mean([r["vol_tercile"] == t for r in usable]) if usable else 0
                        tb = terc[(d, p, t)].get(f"h{H}")
                        matched += share * (tb["mean"] if tb else 0.0)
                    row[f"h{H}"] = {"setup_mean": float(x.mean()), "baseline_mean": b[f"h{H}"]["mean"], "difference": float(x.mean() - b[f"h{H}"]["mean"]),
                                    "volatility_matched_baseline_mean": float(matched), "setup_se_of_mean": float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else None,
                                    "setup_share_positive": float((x > 0).mean()), "baseline_share_positive": b[f"h{H}"]["share_positive"]}
                row["setup_mfe_median"], row["baseline_mfe_median"] = s["mfe_pct_median"], b["mfe_pct_median"]
                row["setup_mae_median"], row["baseline_mae_median"] = s["mae_pct_median"], b["mae_pct_median"]
                res["setups"][f"{sid}/{d}/{p}"] = row
    return res


def render(cited: dict, checks: dict, base: dict) -> dict:
    L = ["# Cited-chart review: AI description -> chart -> frozen detector", "",
         "Each block is a Stage A chart the AI rated ACTIONABLE_NOW and cited for the setup. Detector readings are for the window ending at the chart's last candle. Nothing was changed.", ""]
    for sid in det.IDS:
        c = cited[sid]
        L += [f"## {sid} {det.NAMES[sid]}: {c['n']} cited charts, recognized (present at T or fired on the last two candles): {c['recognized']}", "",
              f"Charts failing each condition: {json.dumps(c['charts_failing_each_condition'])}", f"Charts missing by exactly one condition: {json.dumps(c['charts_missing_by_exactly_one_condition'])}", ""]
        for it in c["charts"]:
            a = it["ai"]
            L += [f"### {it['chart_id']} ({it['end_ts']}) - present at T: {it['present_at_T']}, present at T-1: {it['present_at_T_minus_1']}, fired on last two: {it['fired_last_two_candles']}",
                  f"![{it['chart_id']}](charts/{it['chart_id']}.png)", "",
                  f"AI summary: {a['visible_summary']}", f"AI context: {a['context']}", f"AI location: {a['location']}", f"AI development: {a['development']}", f"AI trigger: {a['trigger']}", "",
                  "| condition | ok | detail |", "|---|---|---|"]
            L += [f"| {k['condition']} | {ex.OKTXT[k['ok']]} | {k['detail']} |" for k in it["conditions"]]
            L.append("")
    F = ["# Hand-check of FIREs (independent recomputation from the raw Binance candles)", "",
         "Every check re-derives the previous-candle state with `src/brain/explain.py`, which is written separately from the detectors. MISMATCH would mean a bug.", ""]
    total = bad = 0
    for sid in det.IDS:
        F.append(f"## {sid} {det.NAMES[sid]}")
        for s in checks[sid]:
            F += ["", f"### {s['fire_id']} {s['trigger_ts']} {s['direction']} level {s['level']:.2f} (presence {s['presence_len']} / recomputed {s['recomputed_run']}, streak {s['streak_position']})", "",
                  "| check | result |", "|---|---|"]
            for k, v in s["checks"].items():
                total += 1
                bad += not v
                F.append(f"| {k} | {'ok' if v else 'MISMATCH'} |")
            F += ["", "| candle open | open | high | low | close |", "|---|---:|---:|---:|---:|"] + [f"| {x['open_ts']} | {x['o']:.2f} | {x['h']:.2f} | {x['l']:.2f} | {x['c']:.2f} |" for x in s["candles"]] + [""]
            F += ["| previous-candle condition | ok | detail |", "|---|---|---|"] + [f"| {k['condition']} | {ex.OKTXT[k['ok']]} | {k['detail']} |" for k in s["previous_conditions"]] + [""]
    F.insert(2, f"**{total - bad}/{total} checks agree; {bad} MISMATCH.**")
    B = ["# Unconditional baseline vs setup fires (descriptive; direction-signed % from the next candle open; NOT fills)", "",
         "Baseline = every candle with a 96-candle history treated as if a FIRE occurred on it, in the same direction and period, measured with the same code. "
         "The volatility-matched column re-weights the baseline to the setup's own trailing-volatility tercile mix. The s.e. ignores overlap between fires, so it is optimistic. "
         "No significance test is made and nothing here is a trading result.", "",
         "| setup/direction/period | fires | h1 setup | h1 base | h6 setup | h6 base | h6 vol-matched | h6 diff | h6 s.e. | h24 setup | h24 base | h24 diff | share>0 h6 setup/base | MFE med setup/base | MAE med setup/base |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|"]
    f = lambda v, nd=3: "-" if v is None else f"{v:.{nd}f}"           # noqa: E731
    for k, r in base["setups"].items():
        h1, h6, h24 = r.get("h1"), r.get("h6"), r.get("h24")
        if not (h1 and h6 and h24):
            continue
        B.append(f"| {k} | {r['n']} | {f(h1['setup_mean'])} | {f(h1['baseline_mean'])} | {f(h6['setup_mean'])} | {f(h6['baseline_mean'])} | {f(h6['volatility_matched_baseline_mean'])} | "
                 f"{f(h6['difference'])} | {f(h6['setup_se_of_mean'])} | {f(h24['setup_mean'])} | {f(h24['baseline_mean'])} | {f(h24['difference'])} | "
                 f"{f(h6['setup_share_positive'], 2)}/{f(h6['baseline_share_positive'], 2)} | {f(r['setup_mfe_median'])}/{f(r['baseline_mfe_median'])} | {f(r['setup_mae_median'])}/{f(r['baseline_mae_median'])} |")
    return {"cited_review.md": "\n".join(L) + "\n", "fire_checks.md": "\n".join(F) + "\n", "baseline_comparison.md": "\n".join(B) + "\n"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=None)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    out = Path(a.out)
    from src.brain import freeze, scan
    from src.data.loader import load_candles
    from src.setups import lock
    freeze.verify()
    db = Path(a.db) if a.db else lock.CANONICAL_DB
    lock.verify_database(db)
    df = load_candles(db, params.SYMBOL, params.TIMEFRAME).df
    thr = scan.load_thresholds()
    fires = [json.loads(x) for x in (Path(config.ROOT) / "results/brain/fires.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    stage_a = store.load_jsonl(store.RUN_DIR / "stage_a.jsonl")
    cited = cited_review(df, stage_a, rediscovery.supporting_ids(), fires, thr)
    checks = fire_checks(df, fires, thr)
    base = baseline(df, fires, int(pd.Timestamp(params.DISCOVERY_END).as_unit("ns").value))
    out.mkdir(parents=True, exist_ok=True)
    (out / "charts").mkdir(exist_ok=True)
    for sid in det.IDS:
        for it in cited[sid]["charts"]:
            src = CHARTS / f"{it['chart_id']}.png"
            if src.exists():
                shutil.copy(src, out / "charts" / src.name)
    for name, text in render(cited, checks, base).items():
        (out / name).write_text(text, encoding="utf-8")
    (out / "review.json").write_text(json.dumps({"cited": cited, "fire_checks": checks, "baseline": base}, indent=2, default=float), encoding="utf-8")
    print(json.dumps({s: {"cited": cited[s]["n"], "recognized": cited[s]["recognized"], "failing": cited[s]["charts_failing_each_condition"]} for s in det.IDS}, indent=1))
    bad = sum(not v for s in checks.values() for x in s for v in x["checks"].values())
    print(f"fire checks: {sum(len(x['checks']) for s in checks.values() for x in s)} checks, {bad} MISMATCH")
    print((out / "baseline_comparison.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
