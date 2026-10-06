# MIB Pattern Lab

A **research experiment** to determine whether AI can discover recurring visual patterns in
clean price charts that are followed by favorable market movement.

Fully isolated from MIB Trader: no imports from, or dependency on, Hunt, Hunt V4, S1, S2,
lifecycle, autotrader or any production trading code.

## What it is NOT
Not a trading bot, not a live trading system, not a Hunt replacement, not an execution engine.
It contains no indicators, no entry/exit logic and no trading rules. No pattern is assumed to exist.

## Current milestone (V1)
```
Database -> clean OHLC -> BTC/USDT 5m -> 60-candle windows -> clean chart images
```
Future stages (NOT implemented): clean charts -> OpenAI visual discovery -> pattern families ->
frozen pattern representation -> blind backtest -> out-of-sample validation.

## Setup
```
pip install -r requirements.txt
# put the database (never committed) at:
data/market_Data_Clean.db
```
`*.db`, `*.sqlite`, `*.sqlite3` and `.env` are git-ignored. No API keys are used or stored.

## Usage (run from the repo root)
```
python -m src.data.inspect_db                      # read-only DB report (tables, schema, range, dups, gaps, invalid rows)
python -m src.charts.generate                      # SAMPLE_COUNT (20) evenly spaced windows -> results/sample_charts/
python -m src.charts.generate --count 20 --seed 1  # seeded random sample instead
python -m src.charts.generate --timestamp 2025-03-01T12:00:00Z   # one exact chart -> results/single_chart/
python -m pytest
```
Open `results/sample_charts/index.html` (or `index.md`) for the visual QA report; `manifest.json`
records timestamps, DB sha256, source table and each PNG's sha256 for reproducibility.

The schema is auto-detected (nothing is assumed). If detection is wrong, set `TABLE` /
`COLUMN_OVERRIDES` in `config.py`.

## Window design
* Timestamp = candle **open** time (UTC). A candle is *closed* only if `open + 5m <= as_of`
  (and a closed/complete flag column is honoured if the DB has one).
* For each valid T: `window = candles[T-59 ... T]`, exactly 60 closed, gap-free, strictly ordered
  candles; the last candle is T and nothing after T is ever read (`build_window` slices at T before
  anything else; `validate_window` re-checks every window).
* Windows that would span a missing candle are skipped, not interpolated.
* Duplicate timestamps raise an error by default (`ON_DUPLICATES="keep_last"` to de-duplicate explicitly).
  Invalid OHLC rows are dropped and counted.

## Normalization (`src/charts/normalize.py`)
`norm = (price / close_T - 1) * 100` for O/H/L/C, where `close_T` is the last close in the window.
Uses only data inside the window (no future candles). Raw OHLC is kept alongside. The chart's price
axis is therefore "% vs. close at T", with the Y range fit to the window itself.

## Charts
Candlesticks + price axis + time axis only, fixed style (`config.CHART_STYLE`), byte-deterministic PNGs.
