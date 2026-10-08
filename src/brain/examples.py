"""Inspectable examples: for a FIRE, the 96 candles up to the trigger candle (nothing else is used to decide), the operative level, the
start of presence, and then - drawn separately - what the next candles did. Descriptive only; no entry, stop, target or fill is drawn."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from src.brain import detectors as det  # noqa: E402

FWD = 24


def condition_text(f: dict) -> str:
    side = "above" if f["direction"] == "up" else "below"
    tc = f["trigger_candle"]
    return (f"{f['setup_id']} ({f['setup_name']}) was PRESENT for {f['presence_len']} completed candle(s) up to the previous candle; "
            f"the trigger candle closed at {tc['close']:.2f}, {side} the operative level {f['operative_level']:.2f}, so the brain fired {f['direction'].upper()} "
            f"on that close. Invalidation rules at the fire: " + ", ".join(f"close {op} {v:.2f}" for op, v in f["invalidation_rules"]) + ".")


def pick(fires: list[dict], k: int = 5) -> list[dict]:
    """First fire, then fires spread evenly over time (first-in-streak preferred). Deterministic."""
    base = [f for f in fires if f["streak_position"] == 0] or fires
    if not base:
        return []
    idx = sorted({0, *np.linspace(0, len(base) - 1, k).round().astype(int).tolist()})
    return [base[i] for i in idx][:k]


def draw(f: dict, ts, o, h, l, c, path: Path) -> Path:
    t = f["trigger_idx"]
    a, b = max(0, t - 95), min(len(c) - 1, t + FWD)
    x = np.arange(a, b + 1) - t
    fig, ax = plt.subplots(figsize=(11, 5), dpi=80)
    for i in range(a, b + 1):
        col = "#2a9d8f" if c[i] >= o[i] else "#e76f51"
        ax.vlines(i - t, l[i], h[i], color=col, lw=0.8)
        ax.add_patch(plt.Rectangle((i - t - 0.35, min(o[i], c[i])), 0.7, max(abs(c[i] - o[i]), 1e-9), color=col))
    ax.axhline(f["operative_level"], color="#264653", ls="--", lw=1, label=f"operative level {f['operative_level']:.2f}")
    ax.axvline(0, color="#e9c46a", lw=1.2, label="trigger candle (FIRE at its close)")
    ax.axvspan(0.5, FWD + 0.5, color="#999999", alpha=0.10, label="after the FIRE (observation only)")
    ps = -f["presence_len"]
    ax.axvline(ps, color="#6a4c93", ls=":", lw=1, label=f"presence began ({f['presence_len']} candles)")
    ax.set_title(f"{f['setup_id']} {f['setup_name']} - FIRE {f['direction'].upper()} at {f['trigger_ts']}", fontsize=10)
    ax.set_xlabel("candles relative to the trigger candle (15m)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def make_examples(rows: list[dict], ts, o, h, l, c, out_dir: Path, per_setup: int = 5) -> list[dict]:
    idx = []
    for sid in det.IDS:
        for n, f in enumerate(pick([r for r in rows if r["setup_id"] == sid], per_setup), 1):
            p = draw(f, ts, o, h, l, c, out_dir / f"{sid}_{n}.png")
            idx.append({"setup_id": sid, "n": n, "chart": p.name, "fire_id": f["fire_id"], "trigger_ts": f["trigger_ts"],
                        "period": f.get("period"), "condition": condition_text(f),
                        "after": {k: f.get(k) for k in ("analytical_reference_price", "fwd_return_pct_h1", "fwd_return_pct_h6", "fwd_return_pct_h24",
                                                        "mfe_pct", "mae_pct", "candles_to_invalidation")}})
    return idx
