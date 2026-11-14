"""Run the written rules.

    python -m src.trendrsi.run --label dev  --data-dir data/ext       --out results/trendrsi/dev     # development look: code sanity, no decisions
    python -m src.trendrsi.run --label test --data-dir data/ext_old   --out results/trendrsi/test    # the ONE run on the untouched data (needs the freeze)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.trendrsi import study


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--label", choices=["dev", "test"], required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out)
    if a.label == "test":
        from src.trendrsi import freeze
        freeze.verify(Path(a.data_dir))                                       # code, charter and the exact data files must match the freeze
        if (out / "RUN_DONE.json").exists():
            raise SystemExit(f"{out / 'RUN_DONE.json'} exists: the untouched data is analysed once. Refusing to run again.")
    rep = study.report(Path(a.data_dir))
    recs = rep.pop("records")
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(rep, indent=2, default=float), encoding="utf-8")
    (out / "signals.jsonl").write_text("\n".join(json.dumps({"mode": m, **{k: (float(v) if isinstance(v, (np.floating,)) else (int(v) if isinstance(v, np.integer) else v)) for k, v in r.items()}}) for m, rs in recs.items() for r in rs) + "\n", encoding="utf-8")
    if a.label == "test":
        (out / "RUN_DONE.json").write_text(json.dumps({"summary_sha256": __import__("hashlib").sha256((out / "summary.json").read_bytes()).hexdigest()}), encoding="utf-8")
    w = rep["with_trend"]
    print(json.dumps({"label": a.label, "first": rep["first_utc"], "last": rep["last_utc"], "bear_candles": rep["bear_candles"], "bull_candles": rep["bull_candles"],
                      "with_trend": {"signals": w["signals"], "ok": w["ok"], "excluded": w["excluded"], "long": w["long"]["n"], "short": w["short"]["n"],
                                     "net_R_slip0.01": w["all"]["net_R_slip0.01"], "stop_rule": w["stop_rule"]},
                      "counter_trend_diag": {"ok": rep["counter_trend"]["ok"], "net_R_slip0.01": rep["counter_trend"]["all"]["net_R_slip0.01"]}}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
