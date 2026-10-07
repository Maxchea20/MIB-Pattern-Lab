"""READ-ONLY sampler review for the locked Setup Discovery design (pre-registration section 5).

    python -m src.setups.dryrun_report --confirm-design-sha <12 chars>

Runs the locked sampler exactly as `--build` would, but renders nothing, writes nothing, calls no API and reads no
outcome. It prints what you need to inspect before Stage A: the funnel, tercile cut-points, the size of each stratum's
eligible pool, how many windows are selected per stratum and per month, shortfalls, spacing, dataset/lock verification and
two determinism checks. It is a reporting helper OUTSIDE the design lock (it is not used by any pipeline step).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.loader import load_candles, tf_to_seconds
from src.setups import params, sampling


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def report(df: pd.DataFrame) -> dict:
    cand, funnel, d = sampling.candidates(df)
    cuts = sampling.cutpoints(cand)
    picks, shortfall, c = sampling.select(cand, cuts)
    picks2, shortfall2, _ = sampling.select(cand, cuts)
    meta1, _ = sampling.build(df, Path("."), render=False)
    meta2, _ = sampling.build(df, Path("."), render=False)
    masks = sampling.stratum_masks(c, cuts)
    pool = {n: int(masks[n].sum()) for n in params.STRATA}
    first = pd.Series([sampling.first_stratum(masks, i) for i in range(len(c))]).value_counts()
    first = {n: int(first.get(n, 0)) for n in (*params.STRATA, "S0_other")}
    times = [t for t, _, _ in picks]
    gaps = [(b - a) / pd.Timedelta(minutes=15) for a, b in zip(times, times[1:])]
    per_month = pd.Series([t.strftime("%Y-%m") for t in times]).value_counts().sort_index()
    per_stratum = pd.Series([s for _, s, _ in picks]).value_counts()
    listing = [(t.isoformat(), s) for t, s, _ in picks]
    order = list(range(len(picks)))
    random.Random(params.SEED_ORDER).shuffle(order)
    return {
        "funnel": funnel,
        "tercile_cutpoints_[lower_cut,upper_cut]": cuts,
        "eligible_pool_per_stratum_(a_window_may_qualify_for_several)": pool,
        "candidates_by_first_matching_stratum": first,
        "selected_per_stratum": {n: int(per_stratum.get(n, 0)) for n in params.STRATA},
        "quota_per_stratum": params.PER_STRATUM,
        "n_selected": len(picks), "n_target": params.N_TARGET, "shortfall": shortfall,
        "min_gap_between_selected_windows_candles": float(min(gaps)) if gaps else None,
        "required_min_gap_candles": params.MIN_GAP_CANDLES,
        "first_window_end": times[0].isoformat() if times else None, "last_window_end": times[-1].isoformat() if times else None,
        "selected_per_month": {k: int(v) for k, v in per_month.items()},
        "all_selected_before_cutoff": bool(all(t < pd.Timestamp(params.DISCOVERY_END) for t in times)),
        "chart_style_sha256": sampling.style_sha(),
        "determinism": {"selection_identical_on_rerun": listing == [(t.isoformat(), s) for t, s, _ in picks2] and shortfall == shortfall2,
                        "build_metadata_identical_on_rerun": meta1 == meta2,
                        "selection_sha256": _sha(listing), "send_order_sha256": _sha([listing[i] for i in order])},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--confirm-design-sha", required=True)
    ap.add_argument("--db", default=None)
    a = ap.parse_args(argv)
    from src.setups import lock
    lk = lock.require_design_lock(a.confirm_design_sha)
    db = lock.verify_database(Path(a.db) if a.db else lock.CANONICAL_DB)
    cs = load_candles(Path(a.db) if a.db else lock.CANONICAL_DB, params.SYMBOL, params.TIMEFRAME)
    out = {"design_lock": {"verified": True, "locked_at": lk["locked_at"], "git_commit": lk["git_commit"],
                           "preregistration_sha256": lk["sha256"]["preregistration_setups"]},
           "dataset": {**db, "matches_f0_lock": db["sha256"] == lk["dataset"]["sha256"] and db["bytes"] == lk["dataset"]["bytes"]},
           **report(cs.df)}
    print(json.dumps(out, indent=2))
    print("\nread-only: nothing rendered, nothing written, no API call, no outcome read")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
