"""One chart with the RSI(14) of every timeframe (1m, 5m, 15m, 1H, 4H, 1D) on the same time axis, plus price.

    python tools/rsi_overlay.py --data-dir data/ext --hours 48 --tz 8 --out results/rsi_overlay.png

Each timeframe's RSI uses COMPLETED candles only and is drawn as a step: it changes only when a candle of that timeframe closes, exactly as you would
see it at that moment (nothing from the still-forming candle, nothing from the future). Read-only visual aid: no signal, no trade.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.trendrsi.indicators import rsi_wilder  # noqa: E402

STEP_MIN = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
STYLE = {"1m": ("#b9c3cf", 0.9), "5m": ("#7fb2e5", 1.1), "15m": ("#2a78c8", 1.5), "1h": ("#e8a33d", 1.8), "4h": ("#d1495b", 2.2), "1d": ("#3b1f6e", 2.8)}


def load(data_dir: Path, iv: str):
    with gzip.open(Path(data_dir) / f"BTCUSDT-{iv}.csv.gz", "rt") as f:
        a = np.array(list(csv.reader(f))[1:], float)
    return a[:, 0].astype(np.int64), a[:, 4]


def completed_rsi(data_dir: Path, iv: str):
    """-> (close time in ms, RSI) per completed candle of that timeframe. The value is usable only from the candle's close time."""
    ts, c = load(data_dir, iv)
    return ts + STEP_MIN[iv] * 60_000, rsi_wilder(c)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--data-dir", default="data/ext")
    ap.add_argument("--hours", type=float, default=48)
    ap.add_argument("--tz", type=float, default=8, help="hours to add to UTC for the axis (8 = UTC+8)")
    ap.add_argument("--out", default="results/rsi_overlay.png")
    ap.add_argument("--intervals", nargs="+", default=list(STEP_MIN), choices=list(STEP_MIN))
    a = ap.parse_args(argv)
    ts15, c15 = load(a.data_dir, "15m")
    end = ts15[-1] + 15 * 60_000
    t0 = end - int(a.hours * 3_600_000)
    off = a.tz * 3600
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8.5), sharex=True, gridspec_kw={"height_ratios": [1, 2.2]}, dpi=110)
    m = (ts15 + 15 * 60_000 >= t0)
    x15 = (ts15[m] + 15 * 60_000) / 1000 + off
    ax1.plot(mdates.date2num(np.array(x15, "datetime64[s]").astype("datetime64[ms]").astype(object)), c15[m], color="#222", lw=1.2)
    ax1.set_ylabel("BTC price (15m close)")
    ax1.grid(alpha=.25)
    latest = {}
    for iv in a.intervals:
        cl, r = completed_rsi(a.data_dir, iv)
        k = (cl >= t0) & (cl <= end) & np.isfinite(r)
        prev = np.flatnonzero(cl < t0)
        xs = np.r_[t0, cl[k]]
        ys = np.r_[r[prev[-1]] if len(prev) and np.isfinite(r[prev[-1]]) else np.nan, r[k]]       # value in force at the left edge
        xs = np.r_[xs, end]
        ys = np.r_[ys, ys[-1]]
        xd = mdates.date2num((np.array(xs / 1000 + off, "datetime64[s]")).astype(object))
        col, lw = STYLE[iv]
        ax2.step(xd, ys, where="post", color=col, lw=lw, label=f"{iv}  {ys[-1]:.0f}", zorder=3 + STEP_MIN[iv] / 400)
        latest[iv] = float(ys[-1])
    ax2.axhspan(70, 100, color="#d1495b", alpha=.07)
    ax2.axhspan(0, 30, color="#2a9d8f", alpha=.07)
    for lv in (30, 50, 70):
        ax2.axhline(lv, color="#666", lw=.8, ls="--" if lv != 50 else ":")
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("RSI(14), completed candles only")
    ax2.grid(alpha=.2)
    ax2.legend(loc="upper left", ncol=3, fontsize=9, frameon=True, title="timeframe  latest RSI")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    fig.autofmt_xdate()
    tzname = f"UTC{a.tz:+g}"
    fig.suptitle(f"BTCUSDT RSI(14) on every timeframe, last {a.hours:g} h (axis {tzname}); Binance spot", fontsize=11)
    fig.tight_layout()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    print(out, {k: round(v) for k, v in latest.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
