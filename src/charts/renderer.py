"""Deterministic clean candlestick renderer.

Draws ONLY candlesticks, a price axis (normalized % vs. last close) and a time axis.
No title, grid, volume, indicators, markers or annotations. Fixed style from
``config.CHART_STYLE``; the Y range is derived only from the window itself.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

import config  # noqa: E402
from src.charts.windows import Window  # noqa: E402


def chart_filename(w: Window) -> str:
    sym = "".join(ch for ch in w.symbol if ch.isalnum())
    return f"{sym}_{w.timeframe}_{w.end_ts.strftime('%Y%m%dT%H%M%SZ')}.png"


def render_window(w: Window, path, style: dict | None = None) -> Path:
    st = {**config.CHART_STYLE, **(style or {})}
    n = st["xtick_every"]
    d = w.norm.reset_index(drop=True)
    fig, ax = plt.subplots(figsize=st["figsize"], dpi=st["dpi"])
    fig.patch.set_facecolor(st["background"])
    ax.set_facecolor(st["background"])
    bw = st["body_width"]
    for i, r in d.iterrows():
        color = st["up_color"] if r["close"] >= r["open"] else st["down_color"]
        ax.vlines(i, r["low"], r["high"], color=color, linewidth=st["wick_width"], zorder=2)
        lo, hi = sorted((r["open"], r["close"]))
        ax.add_patch(Rectangle((i - bw / 2, lo), bw, max(hi - lo, 1e-9),
                               facecolor=color, edgecolor=color, linewidth=0.5, zorder=3))
    lo, hi = float(d["low"].min()), float(d["high"].max())
    pad = (hi - lo) * st["y_pad_frac"] or 0.01
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlim(-1, len(d))
    ticks = list(range(len(d) - 1, -1, -n))[::-1]           # anchored on candle T
    ax.set_xticks(ticks)
    ax.set_xticklabels([d["ts"].iloc[i].strftime("%m-%d\n%H:%M") for i in ticks], fontsize=8)
    ax.yaxis.tick_right()
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:+.2f}%")
    ax.tick_params(colors=st["axis_color"], labelsize=8)
    for s in ("top", "left"):
        ax.spines[s].set_visible(False)
    for s in ("bottom", "right"):
        ax.spines[s].set_color(st["axis_color"])
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="png", facecolor=st["background"],
                metadata={"Software": None})                # no version strings -> byte-deterministic
    plt.close(fig)
    return path
