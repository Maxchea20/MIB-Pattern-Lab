"""Central configuration for MIB Pattern Lab (research only, no trading code)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# --- Data -------------------------------------------------------------------
DB_PATH = ROOT / "data" / "market_Data_Clean.db"   # lives outside Git (see .gitignore)
SYMBOL = "BTC/USDT"
TIMEFRAME = "5m"          # V1 uses ONLY BTC/USDT 5m

# Optional overrides if auto-detection of the schema is wrong. None = auto-detect.
TABLE = None
COLUMN_OVERRIDES = {      # logical name -> actual column name
    "timestamp": None,
    "symbol": None,
    "timeframe": None,
    "open": None,
    "high": None,
    "low": None,
    "close": None,
    "closed_flag": None,
}

# Policy for duplicate timestamps in the loader: "error" (default, safest)
# or "keep_last" (explicit, documented de-duplication).
ON_DUPLICATES = "error"

# The newest stored candle(s) may have been written while still forming (e.g. DB synced
# mid-candle). Drop this many from the END of the loaded series. Set 0 to disable.
DROP_LAST_CANDLES = 1

# --- Windows ----------------------------------------------------------------
LOOKBACK = 60             # candles per window; window = candles[T-59 .. T]

# --- Sampling / output ------------------------------------------------------
SAMPLE_COUNT = 20
SAMPLE_SEED = None        # None = evenly spaced across history (deterministic)
SAMPLE_DIR = ROOT / "results" / "sample_charts"
SINGLE_DIR = ROOT / "results" / "single_chart"

# --- Chart style (fixed so every chart looks identical) ---------------------
CHART_STYLE = {
    "figsize": (8.0, 5.0),
    "dpi": 100,
    "up_color": "#1a9850",
    "down_color": "#d73027",
    "background": "#ffffff",
    "axis_color": "#222222",
    "body_width": 0.7,
    "wick_width": 1.0,
    "y_pad_frac": 0.05,
    "xtick_every": 10,
    # Right-axis labels: "raw" = real prices (e.g. 94,250), "pct" = % vs close at T.
    # Candle shapes are identical either way (always drawn normalized).
    "axis_labels": "raw",
    "time_labels": "datetime",   # "datetime" (real dates) or "relative" (T-50 ... T)
    "y_span_pct": None,          # None = fit each chart to its own range; number = fixed span in %    # candles between time-axis labels
}

# --- Stage 2: OpenAI visual discovery --------------------------------------
# Discovery may only ever see candles BEFORE this instant (UTC, exclusive). Everything
# at/after it is the held-out period for later blind / out-of-sample validation.
DISCOVERY_END = "2026-06-01T00:00:00Z"
# Per-timeframe override of the discovery/hold-out split (UTC, exclusive). 1h has 6 years of history, so it
# gets a bigger hold-out (2024-06-01 onward) than the ~13-month 5m/15m series. Fixed BEFORE any outcome
# analysis - see docs/PREREGISTRATION.md.
DISCOVERY_END_BY_TF = {"1h": "2024-06-01T00:00:00Z"}


def discovery_end(timeframe=None) -> str:
    """Cutoff for `timeframe` (falls back to DISCOVERY_END). Read dynamically (tests may patch it)."""
    key = str(timeframe or TIMEFRAME).strip().lower()
    return DISCOVERY_END_BY_TF.get(key, DISCOVERY_END)


DISCOVERY_COUNT = 200                  # charts sent to the model (each one costs API money)
DISCOVERY_SEED = None                  # None = evenly spaced across the discovery period
OPENAI_MODEL = "gpt-5.4-mini"
# Discovery charts: fixed vertical scale (same % span for every chart), and NO dates / absolute
# prices (price axis = % vs close at T, time axis = candle offset from T). Changing any of this
# changes the images, so bump DISCOVERY_RUN: results go to results/discovery/<DISCOVERY_RUN>/.
DISCOVERY_RUN = "v2_fixed_scale_anon"
DISCOVERY_CHART_STYLE = {"axis_labels": "pct", "time_labels": "relative"}
SPAN_QUANTILE = 0.99      # fixed span = this quantile of window ranges in the discovery period
SPAN_STEP_PCT = 0.05      # span rounded UP to a multiple of this
DISCOVERY_DIR = ROOT / "results" / "discovery"

# --- Stage 3: frozen vocabulary re-tagging + recurrence counts ----------------------------
RETAG_PASSES = 2          # independent passes per chart (even passes list the vocabulary reversed)
MIN_SUPPORT_N = 3         # a shape counts as "recurring" only if stable on >= this many charts
MIN_SUPPORT_FRAC = 0.05   # ... and on >= this fraction of charts

# --- Stage 3 at scale: tag-only run with a hard spending cap -----------------------------
# USD per 1M tokens. From third-party pricing pages (Aug 2026) - VERIFY on your OpenAI dashboard.
OPENAI_PRICE_USD_PER_M = {"input": 0.75, "output": 4.50}
TAGSET_RUN = "tagset_v1"            # results/discovery/<TAGSET_RUN>/  (separate from the 50-chart run)
TAGSET_COUNT = 1000                 # windows to tag
TAGSET_BUDGET_USD = 4.00            # hard stop; leaves reserve of whatever is left on the account
TAGSET_SAMPLING = "stratified"      # "stratified" (equal counts per window-range quartile) or "even"
