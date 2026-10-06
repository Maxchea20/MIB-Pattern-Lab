"""Stage 2: ask an OpenAI vision model to describe clean charts (discovery period ONLY).

    python -m src.discovery.discover --dry-run          # build charts + show the request, no API call
    python -m src.discovery.discover --count 200        # real run (needs OPENAI_API_KEY in .env)

Safety rules enforced here:
* Candles at/after config.discovery_end(timeframe) are removed BEFORE any window is built.
* The model receives only the PNG and the fixed prompt: no timestamp, filename, or outcome.
* Results are appended to descriptions.jsonl with model, prompt version/hash, image hash;
  re-running skips charts already described (resumable).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import time
from html import escape
from pathlib import Path

import pandas as pd

import config
from src.charts.renderer import chart_filename, render_window
from src.charts.windows import build_window, sample_end_timestamps
from src.data.loader import CandleSet, load_candles
from src.discovery import prompts, scale


# ------------------------------------------------------------------ safety --
def discovery_candles(cs: CandleSet, end=None) -> CandleSet:
    """Return a copy of `cs` with every candle at/after the discovery cutoff removed."""
    cut = pd.Timestamp(end or config.discovery_end(cs.timeframe))
    cut = cut.tz_localize("UTC") if cut.tzinfo is None else cut.tz_convert("UTC")
    df = cs.df[cs.df["ts"] < cut].reset_index(drop=True)
    if df.empty:
        raise ValueError(f"No candles before discovery cutoff {cut}")
    stats = {**cs.stats, "discovery_cutoff": cut.isoformat(), "rows_discovery": len(df)}
    return CandleSet(df, cs.symbol, cs.timeframe, cs.source, stats)


def load_env(path=None) -> None:
    """Minimal .env reader (KEY=VALUE). Does not override variables already set."""
    p = Path(path or config.ROOT / ".env")
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ----------------------------------------------------------------- request --
def build_messages(png_bytes: bytes, system: str | None = None, user: str | None = None) -> list[dict]:
    b64 = base64.b64encode(png_bytes).decode()
    return [
        {"role": "system", "content": system or prompts.SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text": user or prompts.USER_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]},
    ]


class OpenAIDescriber:
    def __init__(self, model: str, system: str | None = None, user: str | None = None):
        self.system, self.user = system, user
        load_env()
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise SystemExit("OPENAI_API_KEY not set. Create a .env file (see .env.example).")
        from openai import OpenAI          # imported lazily so tests/dry-run need no key
        self.client = OpenAI(api_key=key)
        self.model = model

    def describe(self, png_bytes: bytes) -> dict:
        r = self.client.chat.completions.create(
            model=self.model, messages=build_messages(png_bytes, self.system, self.user),
            response_format={"type": "json_object"})
        u = r.usage
        return {"text": r.choices[0].message.content or "",
                "model_served": getattr(r, "model", self.model),
                "usage": {"prompt": getattr(u, "prompt_tokens", None),
                          "completion": getattr(u, "completion_tokens", None)}}


# ------------------------------------------------------------------- run ----
def parse_response(text: str):
    try:
        obj = json.loads(text)
        return (obj, None) if isinstance(obj, dict) else (None, "response is not a JSON object")
    except json.JSONDecodeError as e:
        return None, f"invalid JSON: {e}"


def done_keys(jsonl: Path) -> set[str]:
    if not jsonl.exists():
        return set()
    out = set()
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("error") is None:
                out.add(r["end_ts"])
    return out


def plan(dcs: CandleSet, count: int, seed, lookback: int):
    """Fixed span from discovery data, eligible windows, sampled ends, chart style."""
    ranges = scale.window_ranges_pct(dcs.df, dcs.timeframe, lookback)
    span = scale.choose_span(ranges)
    elig = scale.eligible_ends(ranges, span)
    ends = sample_end_timestamps(dcs, lookback, count, seed, ends=elig)
    style = {**config.DISCOVERY_CHART_STYLE, "y_span_pct": span}
    info = {"span_pct": span, "span_quantile": config.SPAN_QUANTILE, "windows_total": len(ranges),
            "windows_eligible": len(elig), "chart_style": {**config.CHART_STYLE, **style}}
    info["chart_style_sha256"] = hashlib.sha256(
        json.dumps(info["chart_style"], sort_keys=True, default=str).encode()).hexdigest()
    return ends, style, info


def run(cs: CandleSet, describer, out_dir: Path, count: int, seed=None, lookback=None) -> list[dict]:
    lookback = lookback or config.LOOKBACK
    dcs = discovery_candles(cs)
    ends, style, info = plan(dcs, count, seed, lookback)
    assert all(t < pd.Timestamp(config.discovery_end(cs.timeframe)) for t in ends), "window beyond discovery cutoff"
    chart_dir = out_dir / "charts"
    jsonl = out_dir / "descriptions.jsonl"
    done = done_keys(jsonl)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "scale.json").write_text(json.dumps(info, indent=2, default=str), encoding="utf-8")
    print(f"fixed span {info['span_pct']}% | eligible windows {info['windows_eligible']}/{info['windows_total']}")
    for i, t in enumerate(ends, 1):
        if t.isoformat() in done:
            print(f"[{i}/{len(ends)}] skip {t} (already described)")
            continue
        w = build_window(dcs, t, lookback)
        png = render_window(w, chart_dir / chart_filename(w), style).read_bytes()
        rec = {"end_ts": t.isoformat(), "chart": chart_filename(w), "symbol": w.symbol,
               "timeframe": w.timeframe, "lookback": lookback,
               "model": getattr(describer, "model", None), "prompt_version": prompts.PROMPT_VERSION,
               "prompt_sha256": prompts.PROMPT_SHA256,
               "image_sha256": hashlib.sha256(png).hexdigest(),
               "chart_style_sha256": info["chart_style_sha256"], "run": config.DISCOVERY_RUN,
               "requested_at": pd.Timestamp.now(tz="UTC").isoformat(),
               "parsed": None, "raw": None, "usage": None, "error": None}
        try:
            r = describer.describe(png)
            rec["raw"], rec["usage"], rec["model_served"] = r["text"], r.get("usage"), r.get("model_served")
            rec["parsed"], rec["error"] = parse_response(r["text"])
        except Exception as e:                       # keep going; failed rows are retried next run
            rec["error"] = f"{type(e).__name__}: {e}"
        with open(jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[{i}/{len(ends)}] {t} {'OK' if rec['error'] is None else 'ERROR ' + rec['error']}")
    return load_results(jsonl)


def load_results(jsonl: Path) -> list[dict]:
    if not jsonl.exists():
        return []
    latest = {}
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r["error"] is None or r["end_ts"] not in latest:
                latest[r["end_ts"]] = r
    return [latest[k] for k in sorted(latest)]


def write_report(out_dir: Path, results: list[dict]) -> Path:
    rows = []
    for r in results:
        p = r.get("parsed") or {}
        rows.append(
            f"<tr><td><img src='charts/{escape(r['chart'])}' width='360'></td><td><b>{escape(r['end_ts'])}</b><br>"
            f"{escape(str(p.get('summary', r.get('error'))))}<br><i>tags:</i> {escape(', '.join(map(str, p.get('pattern_tags', []))))}"
            f"<br><i>structure:</i> {escape(' → '.join(map(str, p.get('structure', []))))}"
            f"<br><i>clarity:</i> {escape(str(p.get('clarity', '')))}</td></tr>")
    path = out_dir / "report.html"
    path.write_text("<!doctype html><meta charset='utf-8'><title>Discovery descriptions</title>"
                    "<style>body{font-family:sans-serif;margin:20px}td{vertical-align:top;padding:8px;"
                    "border-bottom:1px solid #ddd;font-size:13px}</style>"
                    f"<h1>Discovery descriptions ({len(results)})</h1><p>prompt: {prompts.PROMPT_VERSION}</p>"
                    f"<table>{''.join(rows)}</table>", encoding="utf-8")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--db", default=str(config.DB_PATH))
    ap.add_argument("--count", type=int, default=config.DISCOVERY_COUNT)
    ap.add_argument("--seed", type=int, default=config.DISCOVERY_SEED)
    ap.add_argument("--model", default=config.OPENAI_MODEL)
    ap.add_argument("--out", default=str(config.DISCOVERY_DIR / config.DISCOVERY_RUN))
    ap.add_argument("--dry-run", action="store_true", help="build charts and print the request; no API call")
    a = ap.parse_args(argv)

    cs = load_candles(a.db)
    out = Path(a.out)
    if a.dry_run:
        dcs = discovery_candles(cs)
        ends, style, info = plan(dcs, a.count, a.seed, config.LOOKBACK)
        w = build_window(dcs, ends[0], config.LOOKBACK)
        png = render_window(w, out / "charts" / chart_filename(w), style).read_bytes()
        msgs = build_messages(png)
        msgs[1]["content"][1]["image_url"]["url"] = msgs[1]["content"][1]["image_url"]["url"][:60] + "...(truncated)"
        print(f"model: {a.model}\ndiscovery period: {dcs.df['ts'].iloc[0]} -> {dcs.df['ts'].iloc[-1]} "
              f"(cutoff {config.discovery_end(cs.timeframe)}, {len(dcs.df)} candles)\n"
              f"run: {config.DISCOVERY_RUN} -> {out}\nfixed span {info['span_pct']}% (eligible windows "
              f"{info['windows_eligible']}/{info['windows_total']}); axes: {config.DISCOVERY_CHART_STYLE}\n"
              f"would send {len(ends)} charts, from {ends[0]} to {ends[-1]}\n"
              f"prompt {prompts.PROMPT_VERSION} sha {prompts.PROMPT_SHA256[:12]}\n"
              f"--- first request (no timestamp, no filename, no outcome) ---")
        print(json.dumps(msgs, indent=2))
        return 0
    results = run(cs, OpenAIDescriber(a.model), out, a.count, a.seed)
    print(f"report: {write_report(out, results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
