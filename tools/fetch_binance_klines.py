"""Download PUBLIC Binance spot BTCUSDT klines from the bulk-data host and store them locally. Read-only: no account, no key, no order.

    python tools/fetch_binance_klines.py --start 2023-01 --end 2025-08 --intervals 1m 5m 15m 1h 4h 1d
    python tools/fetch_binance_klines.py --start 2026-10-01 --end 2026-11-13 --intervals 1m 5m 15m 1h 4h

Full calendar months come from the monthly files, a partial last month from the daily files. Every zip is checked against its published
SHA-256 (.CHECKSUM) before it is used. Timestamps are normalised to UTC milliseconds (files from 2025 on use microseconds). Output:
data/ext/BTCUSDT-<interval>.csv.gz  (ts_ms,open,high,low,close,volume) plus data/ext/integrity_<interval>.json (rows, gaps, duplicates, bad OHLC).
These files are research input only and stay out of git. Nothing here touches the canonical database.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import time
import urllib.request
import zipfile
from pathlib import Path

HOST = "https://data.binance.vision/data/spot"
STEP_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
OUT = Path("data/ext")


def month_starts(start: str, end: dt.date):
    y, m = map(int, start.split("-")[:2])      # accepts YYYY-MM or YYYY-MM-DD
    while (y, m) <= (end.year, end.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def plan(symbol: str, interval: str, start: str, end: dt.date) -> list[str]:
    """URLs of the zip files covering [start month, end date]: monthly files for complete months, daily files for the last partial month."""
    urls = []
    for y, m in month_starts(start, end):
        last = calendar.monthrange(y, m)[1]
        if (y, m) == (end.year, end.month) and end.day < last:
            urls += [f"{HOST}/daily/klines/{symbol}/{interval}/{symbol}-{interval}-{y}-{m:02d}-{d:02d}.zip" for d in range(1, end.day + 1)]
        else:
            urls.append(f"{HOST}/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{y}-{m:02d}.zip")
    return urls


def to_ms(ts: int) -> int:
    """Binance spot kline files use milliseconds until 2024 and microseconds from 2025."""
    return ts // 1000 if ts > 10**14 else ts


def parse_zip(data: bytes) -> list[tuple]:
    rows = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            for r in csv.reader(io.TextIOWrapper(z.open(name), encoding="utf-8")):
                if r and r[0].isdigit():
                    rows.append((to_ms(int(r[0])), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])))
    return rows


def verify_checksum(data: bytes, checksum_text: str) -> bool:
    return checksum_text.split()[0].lower() == hashlib.sha256(data).hexdigest()


def fetch(url: str, retries: int = 3) -> bytes | None:
    for k in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
        time.sleep(2 ** k)
    raise SystemExit(f"could not download {url}")


def integrity(rows: list[tuple], step_ms: int) -> dict:
    ts = [r[0] for r in rows]
    d = [b - a for a, b in zip(ts, ts[1:])]
    bad = sum(1 for r in rows if r[2] < r[3] or r[2] < max(r[1], r[4]) or r[3] > min(r[1], r[4]))
    return {"rows": len(rows), "first": ts[0] if ts else None, "last": ts[-1] if ts else None,
            "first_utc": dt.datetime.fromtimestamp(ts[0] / 1000, dt.timezone.utc).isoformat() if ts else None,
            "last_utc": dt.datetime.fromtimestamp(ts[-1] / 1000, dt.timezone.utc).isoformat() if ts else None,
            "gaps": sum(1 for x in d if x > step_ms), "missing_candles": sum(x // step_ms - 1 for x in d if x > step_ms),
            "duplicates": sum(1 for x in d if x == 0), "out_of_order": sum(1 for x in d if x < 0), "invalid_ohlc_rows": bad}


def build(urls: list[str], getter=fetch) -> tuple[list[tuple], list[str]]:
    rows, missing = [], []
    for u in urls:
        z = getter(u)
        c = getter(u + ".CHECKSUM")
        if z is None or c is None:
            missing.append(u)
            continue
        if not verify_checksum(z, c.decode()):
            raise SystemExit(f"CHECKSUM MISMATCH for {u}")
        rows += parse_zip(z)
    rows = sorted(set(rows))
    return rows, missing


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--start", required=True, help="first month, YYYY-MM (a full date is accepted; only the month is used)")
    ap.add_argument("--end", required=True, help="last day, YYYY-MM-DD (UTC)")
    ap.add_argument("--intervals", nargs="+", default=["15m", "1h", "4h", "1d"], choices=sorted(STEP_MS))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    end = dt.date.fromisoformat(a.end)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for iv in a.intervals:
        rows, missing = build(plan(a.symbol, iv, a.start, end))
        with gzip.open(out / f"{a.symbol}-{iv}.csv.gz", "wt", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ts_ms", "open", "high", "low", "close", "volume"])
            w.writerows(rows)
        rep = {**integrity(rows, STEP_MS[iv]), "interval": iv, "symbol": a.symbol, "source": HOST, "files_missing": missing,
               "csv_sha256": hashlib.sha256((out / f"{a.symbol}-{iv}.csv.gz").read_bytes()).hexdigest()}
        (out / f"integrity_{iv}.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
        print(iv, {k: rep[k] for k in ("rows", "first_utc", "last_utc", "gaps", "duplicates", "invalid_ohlc_rows")}, "missing files:", len(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
