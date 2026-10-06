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
    "xtick_every": 10,    # candles between time-axis labels
}
