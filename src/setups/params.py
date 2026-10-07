"""Frozen parameters of the Setup Discovery experiment (docs/PREREGISTRATION_SETUPS.md). Changing any value after the
design lock blocks every pipeline step. Nothing here is tuned on outcomes; no outcome exists when it is written."""
from __future__ import annotations

EXPERIMENT = "setups_15m_v1"

# --- canonical dataset (pre-registration section 1) -------------------------------------------------------------
DB_NAME = "research_binance.db"
FORBIDDEN_DB_NAMES = ("market_data_clean.db",)
EXPECTED_DB_BYTES = 71_098_368
EXPECTED_DB_SHA256 = "1535c5352c56096f5e50c6ac6522715048d19c6c887548c6f5dc5f0576c27e9f"
SYMBOL = "BTC/USDT"
TIMEFRAME = "15m"

# --- periods (section 2) ----------------------------------------------------------------------------------------
LOOKBACK = 96                      # candles in every chart
FORWARD_MAX = 24                   # longest horizon; every sampled window needs this forward path inside discovery
DISCOVERY_END = "2026-06-01T00:00:00Z"
HORIZONS = (1, 3, 6, 12, 24)

# --- chart (section 4): candles only, % axis, relative time axis, vertical range fits the visible window ---------
AXIS_LABELS = "pct"
TIME_LABELS = "relative"
Y_SPAN_PCT = None

# --- Stage A sample (section 5) ---------------------------------------------------------------------------------
STRATA = ("S1_directional", "S2_sideways", "S3_expansion", "S4_compression", "S5_sharp", "S6_slow")
N_STRATA = len(STRATA)
PER_STRATUM = 100
N_TARGET = N_STRATA * PER_STRATUM  # 600
MIN_GAP_CANDLES = 32
RE_RECENT, RE_PRIOR = 24, 72       # range expansion = range(last 24 candles) / range(preceding 72 candles)
SEED_ORDER = 777                   # shuffle of the 600 charts before sending

# --- model calls (sections 5, 6) -------------------------------------------------------------------------------
MODEL = "gpt-5.4-mini"             # no temperature is set; stored raw responses are the reproducibility record
MAX_ATTEMPTS = 3
CHUNK_SIZE = 120
SEED_CHUNK = 12345
MAX_CANDIDATES = 8
MIN_SUPPORT = 15

# --- budget (section 11): hard ceilings in USD, no automatic continuation --------------------------------------
CAP_STAGE_A = 3.00
CAP_STAGE_B = 0.50
CAP_AUDIT = 1.00
CAP_TOTAL = 4.50
CAPS = {"stage_a": CAP_STAGE_A, "stage_b": CAP_STAGE_B, "audit": CAP_AUDIT}
FIRST_CALL_ESTIMATE_USD = {"stage_a": 0.0060, "stage_b": 0.0600, "audit": 0.0060}   # before any call has been measured
DRY_RUN_TOKENS = {"stage_a": (900, 800)}                                          # (input, output) per call, estimate only
COST_SAFETY = 1.25                 # next-call estimate = this x the largest call cost seen so far in the step

# --- recognizer / fidelity (section 7) --------------------------------------------------------------------------
FREQ_MIN, FREQ_MAX = 0.002, 0.10   # share of discovery candles on which a recognizer may trigger
AUDIT_N_TRIGGER = 100
AUDIT_N_NONTRIGGER = 100
SEED_AUDIT = 12345
MIN_TRIGGER_CASES = 10             # precision is evaluated only with at least this many audited trigger cases
MIN_RECALL_CHARTS = 10             # recall is evaluated only with at least this many eligible supporting charts
PRECISION_MIN = 0.70
RECALL_MIN = 0.50
RECALL_WINDOW_CANDLES = 2          # PRESENT, or TRIGGERED within the last 2 candles

# --- statistics (sections 9, 10); used by the later, separately frozen outcome code -----------------------------
ALPHA = 0.05
B_PERM = B_BOOT = 10_000
SEED_PERM = 12345
SEED_BOOT = 20240601
EFFECT_FLOOR_PCT = 0.15            # research effect-size screen; NOT assumed net trading profit
N_MIN_DISCOVERY = 100
N_MIN_HOLDOUT = 50
ROBUST_MONTH_FRACTION = 0.80
