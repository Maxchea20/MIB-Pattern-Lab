"""Read-only loader for the clean market database.

Nothing here assumes column names: the schema is discovered from the database
(``PRAGMA table_info``) using name heuristics, with explicit overrides in
``config.COLUMN_OVERRIDES``.

Timestamp convention: a candle's timestamp is its OPEN time (UTC). A candle is
*closed* only when ``open_time + timeframe <= as_of``.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

import config

OHLC = ["open", "high", "low", "close"]

_CANDIDATES = {
    "timestamp": ["timestamp", "ts", "time", "datetime", "open_time", "open_time_ms",
                  "candle_time", "date", "t"],
    "symbol": ["symbol", "pair", "ticker", "instrument", "market", "asset"],
    "timeframe": ["timeframe", "tf", "interval", "resolution", "period"],
    "open": ["open", "o", "open_price"],
    "high": ["high", "h", "high_price"],
    "low": ["low", "l", "low_price"],
    "close": ["close", "c", "close_price"],
    "closed_flag": ["is_closed", "closed", "is_complete", "complete", "confirmed", "final"],
}


class DataError(Exception):
    pass


class DuplicateTimestampError(DataError):
    pass


# ---------------------------------------------------------------- utilities --
def tf_to_seconds(tf) -> int:
    """'5m'/'5min'/'M5'/'1H'/'4h'/'1d'/300 -> seconds. Bare numbers <=1440 are minutes."""
    if isinstance(tf, (int, float, np.integer)):
        v = int(tf)
        return v * 60 if v <= 1440 else v
    s = str(tf).strip().lower()
    m = re.fullmatch(r"(\d+)\s*(s|sec|m|min|h|hr|hour|d|day)?", s)
    if m:
        n, unit = int(m.group(1)), m.group(2)
    else:
        m = re.fullmatch(r"(m|h|d)(\d+)", s)
        if not m:
            raise DataError(f"Unrecognised timeframe: {tf!r}")
        n, unit = int(m.group(2)), m.group(1)
    if unit is None:
        return n * 60 if n <= 1440 else n
    mult = {"s": 1, "sec": 1, "m": 60, "min": 60, "h": 3600, "hr": 3600,
            "hour": 3600, "d": 86400, "day": 86400}[unit]
    return n * mult


def norm_symbol(sym) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(sym).upper())


def parse_timestamps(s: pd.Series) -> pd.Series:
    """Parse epoch seconds / milliseconds / ISO strings into tz-aware UTC datetimes."""
    if pd.api.types.is_numeric_dtype(s):
        mx = float(np.nanmax(np.abs(s.to_numpy(dtype=float)))) if len(s) else 0.0
        unit = "ms" if mx > 1e11 else "s"
        if mx > 1e14:
            unit = "us"
        return pd.to_datetime(s, unit=unit, utc=True)
    return pd.to_datetime(s, utc=True)


def connect_readonly(db_path) -> sqlite3.Connection:
    p = Path(db_path)
    if not p.exists():
        raise DataError(f"Database not found: {p}. Place it at data/market_Data_Clean.db")
    return sqlite3.connect(f"file:{p.resolve().as_posix()}?mode=ro", uri=True)


# ---------------------------------------------------------- schema discovery --
@dataclass
class TableSchema:
    table: str
    columns: list[str]
    types: dict[str, str]
    mapping: dict[str, str | None]   # logical -> actual column

    @property
    def usable(self) -> bool:
        return all(self.mapping.get(k) for k in ["timestamp", *OHLC])


def list_tables(conn) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') "
                        "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    return [r[0] for r in rows]


def detect_schema(conn, table: str) -> TableSchema:
    info = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    cols = [r[1] for r in info]
    types = {r[1]: r[2] for r in info}
    lower = {c.lower(): c for c in cols}
    mapping: dict[str, str | None] = {}
    for logical, names in _CANDIDATES.items():
        override = (config.COLUMN_OVERRIDES or {}).get(logical)
        if override:
            mapping[logical] = override
            continue
        mapping[logical] = next((lower[n] for n in names if n in lower), None)
    return TableSchema(table, cols, types, mapping)


@dataclass
class Source:
    schema: TableSchema
    symbol_value: str | None       # value in the symbol column (None if no such column)
    timeframe_value: str | None    # value in the timeframe column (None if no such column)

    @property
    def table(self) -> str:
        return self.schema.table

    def label(self) -> str:
        return f"{self.table} | symbol={self.symbol_value} | timeframe={self.timeframe_value}"


def discover_sources(conn) -> list[Source]:
    out: list[Source] = []
    for t in list_tables(conn):
        sc = detect_schema(conn, t)
        if not sc.usable:
            continue
        sym, tf = sc.mapping["symbol"], sc.mapping["timeframe"]
        sel = ", ".join(f'"{c}"' for c in (sym, tf) if c)
        if sel:
            rows = conn.execute(f'SELECT DISTINCT {sel} FROM "{t}"').fetchall()
            for r in rows:
                i = 0
                sv = tv = None
                if sym:
                    sv = r[i]; i += 1
                if tf:
                    tv = r[i]
                out.append(Source(sc, None if sv is None else str(sv), None if tv is None else str(tv)))
        else:
            out.append(Source(sc, None, None))
    return out


def fetch_source(conn, src: Source) -> pd.DataFrame:
    """Raw fetch of one source, columns renamed to logical names, unsorted/unfiltered."""
    m = src.schema.mapping
    cols = {k: m[k] for k in ["timestamp", *OHLC, "closed_flag"] if m.get(k)}
    sel = ", ".join(f'"{v}" AS "{k}"' for k, v in cols.items())
    where, params = [], []
    if m["symbol"] and src.symbol_value is not None:
        where.append(f'"{m["symbol"]}" = ?'); params.append(src.symbol_value)
    if m["timeframe"] and src.timeframe_value is not None:
        where.append(f'"{m["timeframe"]}" = ?'); params.append(src.timeframe_value)
    q = f'SELECT {sel} FROM "{src.table}"' + (" WHERE " + " AND ".join(where) if where else "")
    return pd.read_sql_query(q, conn, params=params)


def select_source(sources: list[Source], symbol: str, timeframe: str) -> Source:
    want_sym, want_tf = norm_symbol(symbol), tf_to_seconds(timeframe)
    base = re.sub(r"(USDT|USD|USDC|BUSD)$", "", want_sym)
    scored = []
    for s in sources:
        if config.TABLE and s.table != config.TABLE:
            continue
        score = 0
        if s.symbol_value is not None:
            if norm_symbol(s.symbol_value) != want_sym:
                continue
            score += 2
        elif base.lower() in s.table.lower():
            score += 1
        if s.timeframe_value is not None:
            try:
                if tf_to_seconds(s.timeframe_value) != want_tf:
                    continue
            except DataError:
                continue
            score += 2
        else:
            hint = re.search(r"(\d+\s*(?:m|min|h|d))(?![a-z])", s.table.lower())
            if hint:
                try:
                    if tf_to_seconds(hint.group(1)) != want_tf:
                        continue
                    score += 1
                except DataError:
                    pass
        scored.append((score, s))
    if not scored:
        avail = "\n  ".join(s.label() for s in sources) or "(none)"
        raise DataError(f"No source matches {symbol} {timeframe}. Available:\n  {avail}")
    scored.sort(key=lambda x: -x[0])
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        avail = "\n  ".join(s.label() for _, s in scored)
        raise DataError("Ambiguous source; set config.TABLE / COLUMN_OVERRIDES. Candidates:\n  " + avail)
    return scored[0][1]


# ------------------------------------------------------------------ cleaning --
def invalid_ohlc_mask(df: pd.DataFrame) -> pd.Series:
    o, h, l, c = (df[k].astype(float) for k in OHLC)
    finite = np.isfinite(o) & np.isfinite(h) & np.isfinite(l) & np.isfinite(c)
    ok = (finite & (o > 0) & (h > 0) & (l > 0) & (c > 0)
          & (h >= np.maximum(o, c)) & (l <= np.minimum(o, c)) & (h >= l))
    return ~ok


def filter_closed(df: pd.DataFrame, timeframe, as_of=None) -> pd.DataFrame:
    """Keep only CLOSED candles: open_time + timeframe <= as_of (default: now, UTC).
    If the database has a closed/complete flag column it is honoured too."""
    step = pd.Timedelta(seconds=tf_to_seconds(timeframe))
    as_of = pd.Timestamp.now(tz="UTC") if as_of is None else pd.Timestamp(as_of)
    if as_of.tzinfo is None:
        as_of = as_of.tz_localize("UTC")
    keep = (df["ts"] + step) <= as_of
    if "closed_flag" in df.columns:
        keep &= df["closed_flag"].fillna(0).astype(bool)
    return df[keep].reset_index(drop=True)


def check_duplicates(df: pd.DataFrame, on_duplicates: str = "error") -> pd.DataFrame:
    dup = df["ts"].duplicated(keep=False)
    if not dup.any():
        return df
    if on_duplicates == "error":
        n = int(df["ts"].duplicated().sum())
        raise DuplicateTimestampError(
            f"{n} duplicate timestamps (first: {df.loc[dup, 'ts'].iloc[0]}). "
            "Inspect with `python -m src.data.inspect_db` or set ON_DUPLICATES='keep_last'.")
    if on_duplicates == "keep_last":
        return df.drop_duplicates("ts", keep="last").reset_index(drop=True)
    raise DataError(f"Unknown on_duplicates policy: {on_duplicates!r}")


@dataclass
class CandleSet:
    df: pd.DataFrame            # columns: ts, open, high, low, close (sorted, unique, closed, valid)
    symbol: str
    timeframe: str
    source: str
    stats: dict = field(default_factory=dict)


def load_candles(db_path=None, symbol=None, timeframe=None, as_of=None,
                 on_duplicates=None) -> CandleSet:
    """Load clean, sorted, de-duplicated(policy), closed, valid candles for one symbol/timeframe."""
    db_path = db_path or config.DB_PATH
    symbol = symbol or config.SYMBOL
    timeframe = timeframe or config.TIMEFRAME
    on_duplicates = on_duplicates or config.ON_DUPLICATES
    conn = connect_readonly(db_path)
    try:
        src = select_source(discover_sources(conn), symbol, timeframe)
        raw = fetch_source(conn, src)
    finally:
        conn.close()
    cs = build_candles(raw, symbol, timeframe, src.label(), as_of, on_duplicates)
    n = int(getattr(config, "DROP_LAST_CANDLES", 0))
    if n > 0:
        cs.df = cs.df.iloc[:-n].reset_index(drop=True)
        cs.stats["trailing_dropped"] = n
        cs.stats["rows_usable"] = len(cs.df)
    return cs


def build_candles(raw: pd.DataFrame, symbol, timeframe, source="", as_of=None,
                  on_duplicates="error") -> CandleSet:
    """Pure function (no DB): raw logical-column frame -> CandleSet."""
    df = raw.copy()
    df["ts"] = parse_timestamps(df["timestamp"])
    df = df.drop(columns=["timestamp"])
    for k in OHLC:
        df[k] = pd.to_numeric(df[k], errors="coerce")
    n_raw = len(df)
    df = df.sort_values("ts", kind="stable").reset_index(drop=True)
    df = check_duplicates(df, on_duplicates)
    bad = invalid_ohlc_mask(df)
    n_invalid = int(bad.sum())
    df = df[~bad].reset_index(drop=True)
    n_before_closed = len(df)
    df = filter_closed(df, timeframe, as_of)
    step = tf_to_seconds(timeframe)
    if len(df) > 2:
        med = int(df["ts"].diff().dropna().dt.total_seconds().median())
        if med != step:
            raise DataError(f"Median candle spacing is {med}s but timeframe {timeframe} "
                            f"expects {step}s (source: {source}).")
    cols = ["ts", *OHLC] + (["closed_flag"] if "closed_flag" in df.columns else [])
    df = df[cols].reset_index(drop=True)
    stats = {"rows_raw": n_raw, "invalid_dropped": n_invalid,
             "unclosed_dropped": n_before_closed - len(df), "rows_usable": len(df)}
    return CandleSet(df, symbol, str(timeframe), source, stats)
