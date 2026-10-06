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
Uses only data inside the window (no future candles). Raw OHLC is kept alongside. Candles are drawn in this normalized space with the Y range fit to the window itself. The right-axis
labels show real prices by default (`CHART_STYLE["axis_labels"]="raw"`) or "% vs. close at T" (`"pct"`);
the candle shapes are identical either way.

## Charts
Candlesticks + price axis + time axis only, fixed style (`config.CHART_STYLE`), byte-deterministic PNGs.

## Stage 2: OpenAI visual discovery (descriptions only)
```
copy .env.example .env        # then put your key in .env (git-ignored)
python -m src.discovery.discover --dry-run      # builds charts, shows the exact request, NO API call
python -m src.discovery.discover --count 200    # real run, model = config.OPENAI_MODEL
```
* **Held-out data:** candles at/after `config.DISCOVERY_END` (2026-06-01 UTC) are removed *before*
  any window is built. Discovery never sees them; they are reserved for blind/out-of-sample validation.
* **Outcome-blind:** the model gets only the PNG + a fixed prompt (`src/discovery/prompts.py`). No
  timestamp, filename or outcome. The prompt is versioned and hashed in every result row.
* **Output:** `results/discovery/descriptions.jsonl` (one row per chart: model, prompt hash, image
  hash, raw + parsed response, token usage) and `report.html`. Runs are resumable; failed charts are
  retried on the next run. No clustering, pattern families or backtest yet.

### Discovery chart scale and labels (run `v2_fixed_scale_anon`)
* **Fixed scale:** one vertical span (in %) for every discovery chart = 99th percentile of window
  ranges in the discovery period (never held-out data), rounded up to 0.05%. Windows wider than the
  span (~1%) are excluded from sampling instead of being clipped. Saved in `scale.json`.
* **Anonymised axes:** price axis = % vs. close at T; time axis = candle offsets `T-50 ... T`. No dates
  or absolute prices reach the model (it cannot recognise real BTC history from labels).
* Results go to `results/discovery/<DISCOVERY_RUN>/`, so earlier runs with different images are never mixed in.

## Stage 3: frozen vocabulary + recurrence counts (still no market outcomes)
```
python -m src.discovery.retag --dry-run     # shows prompt + number of API calls
python -m src.discovery.retag               # re-tag the run's charts, RETAG_PASSES (2) independent passes
python -m src.discovery.vocab_report        # counts + report: results/discovery/<run>/vocab_report.html
```
* `src/discovery/vocab.py` is a fixed list of 18 shape names + `none`, with visual definitions
  (hash-pinned: `VOCAB_SHA256`). Distilled from the free-form descriptions; no direction/outcome language.
* Re-tagging is image-only (the earlier text is not shown), reads the PNGs already rendered in the run
  folder (verified against their recorded hashes) and needs no database.
* Pass 2 lists the vocabulary in reverse order to expose order bias. Unknown/invalid tags are errors
  (never silently fixed) and are retried.
* A chart's **stable** tags are those present in every pass. Only stable tags are counted. A shape is
  **recurring** only if stable on >= `MIN_SUPPORT_N` charts and >= `MIN_SUPPORT_FRAC` of charts.
  The report also shows primary-tag agreement between passes: if that is low, the labelling is not reliable.

### Tagging at scale (hard budget cap)
```
python -m src.discovery.tagset --dry-run        # sampling plan, no charts, no API
python -m src.discovery.tagset                  # TAGSET_COUNT windows x RETAG_PASSES, stops at TAGSET_BUDGET_USD
python -m src.discovery.vocab_report --run-dir results/discovery/tagset_v1
```
Tag-only (no free-text step), discovery period only, same fixed-span anonymised charts. Default sampling is
stratified by window range (equal counts per quartile; uses only chart size, no outcomes), so report shares
are not population frequencies. Token use is recorded per call; the run stops *between charts* when the
projected spend would pass the cap, and re-running resumes. Prices in `config.OPENAI_PRICE_USD_PER_M`
come from third-party pricing pages - verify them on your OpenAI dashboard.

### Label audit (free, no outcomes)
```
python -m src.discovery.audit --run-dir results/discovery/tagset_v1
```
Computes simple window-only features (net move, range, efficiency, biggest 5-candle rise/fall, where the
high/low sit, last-10 move) for every tagged window and shows their mean per stable tag. Use it to check
that tag names match the geometry (e.g. `drift_down` should have negative net move) and that the AI tags
add information beyond net move / range.

### Other timeframes
`tagset`, `vocab_report` and `audit` take `--timeframe` (e.g. `15m`, `1h`). Each timeframe gets its own folder
(`results/discovery/tagset_v1_15m`), its own fixed chart scale (computed from that timeframe's discovery
windows), and windows are kept >= one full window apart. The prompt never mentions the timeframe.

### Discovery / hold-out split per timeframe
`config.DISCOVERY_END_BY_TF` overrides the cutoff per timeframe (1h: 2024-06-01, so ~2.3 years stay locked for
validation). The split, and everything still to be fixed before any outcome is examined, is in
`docs/PREREGISTRATION.md`. Runs with a custom cutoff get their own folder (e.g. `tagset_v1_1h_cut20240601`).

### Adding discovery windows (top-up) and the experiment's pre-registration
```
python -m src.discovery.tagset --timeframe 1h --topup 999 --dry-run     # how many more fit (no API, no render)
python -m src.discovery.tagset --timeframe 1h --topup 999 --budget-usd 1  # add them and tag them
```
Existing windows are never changed; new ones never overlap them and stay inside the discovery period. Re-running
the plain command reuses the existing window list. The full experiment design (frozen tagging setup, families,
outcome measures, permutation test, decision rule, one-shot hold-out) is in `docs/PREREGISTRATION.md`.

### Locking the discovery sample (before any outcome)
```
python -m src.discovery.lock --timeframe 1h --write     # verifies + writes docs/PREREG_LOCK.json
```
See `docs/PREREGISTRATION.md` section 13. The outcome module is built only after this lock exists.

### Outcome module (built to the frozen pre-registration; NOT yet run)
`src/outcomes/` is the only code allowed to read candles after a window end T. It runs only if
`docs/PREREG_LOCK.json` matches every frozen file, `docs/OUTCOME_CODE_FREEZE.json` matches the code, and the run
is confirmed with the first 12 characters of the lock's pre-registration hash. Hold-out candles are removed before
anything is read; the analysis completes once (`RUN_COMPLETE.json`). Standard library + numpy only (no scipy).

## Experiment 2: 5M visual-pattern discovery (design in progress)
The completed 1H experiment is archived and untouched. The 5M experiment has its own pre-registration
(`docs/PREREGISTRATION_5M.md`, DRAFT until `docs/PREREG_5M_DESIGN_LOCK.json` exists) and its own code in `src/exp5m/`:
```
python -m src.exp5m.coverage                    # verify the 5M data actually in the database (read-only)
python -m src.exp5m.sampling --dry-run          # funnel + deterministic sample plan (nothing rendered)
python -m src.exp5m.lock5m --write              # freeze the design (after the open decisions are answered)
python -m src.exp5m.sampling --build --confirm-design-sha <12 chars>   # generate the discovery sample + charts
```
Order of work, freezes and the outcome-blind discovery architecture are in section 11 of the 5M pre-registration.

## Permanent policy: REAL FILLS ONLY
`docs/REAL_FILLS_POLICY.md` is permanent for this project. The 1H and 5M experiments measure forward return, future
high/low, MFE and MAE as **descriptive statistics, not trade fills**. No trading backtest may be written until a separate
execution specification is frozen; `tests/test_policy.py` fails if backtest/execution/fill code appears earlier.
